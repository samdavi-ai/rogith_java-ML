package org.secondcircuit.assistant.service;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import ai.onnxruntime.TensorInfo;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.secondcircuit.assistant.api.ApiModels;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import jakarta.annotation.PreDestroy;
import javax.imageio.ImageIO;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.nio.FloatBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

@Component
public class OnnxClassifier {
    private static final Logger log = LoggerFactory.getLogger(OnnxClassifier.class);
    private final OrtEnvironment environment;
    private final OrtSession session;
    private final String inputName;
    private final List<String> labels;
    private final double highThreshold, mediumThreshold, minimumConfidence;
    private final String modelStatus;
    private final long modelLoadTimeMs;

    public OnnxClassifier(@Value("${app.ml.model-path:ml/models/ewaste.onnx}") String modelPath,
                          @Value("${app.ml.labels-path:ml/class_mapping.json}") String labelsPath,
                          @Value("${app.ml.high-threshold:0.85}") double highThreshold,
                          @Value("${app.ml.medium-threshold:0.60}") double mediumThreshold,
                          @Value("${app.ml.minimum-confidence:0.66}") double minimumConfidence) {
        this.highThreshold = highThreshold;
        this.mediumThreshold = mediumThreshold;
        this.minimumConfidence = minimumConfidence;
        if (!Files.isRegularFile(Path.of(modelPath)) || !Files.isRegularFile(Path.of(labelsPath))) {
            environment = null;
            session = null;
            inputName = null;
            labels = List.of();
            modelStatus = "MODEL_UNAVAILABLE";
            modelLoadTimeMs = 0;
            return;
        }
        long loadStart = System.nanoTime();
        OrtEnvironment loadedEnvironment = null;
        OrtSession loadedSession = null;
        String loadedInput = null;
        List<String> loadedLabels = List.of();
        String status;
        try {
            var root = new ObjectMapper().readTree(Path.of(labelsPath).toFile());
            var classNodes = root.path("classes");
            if (!classNodes.isArray() || classNodes.isEmpty()) throw new IllegalArgumentException("class_mapping.json has no classes");
            var names = new java.util.ArrayList<String>();
            for (int i = 0; i < classNodes.size(); i++) {
                var item = classNodes.get(i);
                if (item.path("id").asInt(-1) != i || item.path("name").asText().isBlank())
                    throw new IllegalArgumentException("class_mapping.json IDs must be contiguous and ordered");
                names.add(item.path("displayName").asText(item.path("name").asText()));
            }
            loadedLabels = List.copyOf(names);
            loadedEnvironment = OrtEnvironment.getEnvironment();
            loadedSession = loadedEnvironment.createSession(modelPath, new OrtSession.SessionOptions());
            loadedInput = loadedSession.getInputNames().iterator().next();
            var shape = ((TensorInfo) loadedSession.getInputInfo().get(loadedInput).getInfo()).getShape();
            if (shape.length != 4 || shape[1] != 3 || shape[2] != 224 || shape[3] != 224)
                throw new IllegalArgumentException("ONNX input must be NCHW float32 [N,3,224,224]");
            var outputName = loadedSession.getOutputNames().iterator().next();
            var outputShape = ((TensorInfo) loadedSession.getOutputInfo().get(outputName).getInfo()).getShape();
            if (outputShape.length != 2 || outputShape[1] != loadedLabels.size())
                throw new IllegalArgumentException("ONNX output class count does not match class_mapping.json");
            status = "MODEL_READY";
        } catch (Exception e) {
            log.error("Configured e-waste model could not be loaded; classifier is disabled ({})", e.getClass().getSimpleName());
            if (loadedSession != null) try { loadedSession.close(); } catch (Exception ignored) { }
            loadedSession = null;
            loadedEnvironment = null;
            loadedInput = null;
            loadedLabels = List.of();
            status = "MODEL_LOAD_ERROR";
        }
        environment = loadedEnvironment;
        session = loadedSession;
        inputName = loadedInput;
        labels = loadedLabels;
        modelStatus = status;
        modelLoadTimeMs = (System.nanoTime() - loadStart) / 1_000_000;
    }

    public String modelStatus() { return modelStatus; }
    public long modelLoadTimeMs() { return modelLoadTimeMs; }

    public ApiModels.ClassificationView predict(BufferedImage source) {
        if (session == null) {
            if ("MODEL_LOAD_ERROR".equals(modelStatus)) throw new ClassificationService.ModelLoadException();
            throw new ClassificationService.ModelUnavailableException();
        }
        try {
            BufferedImage resized = new BufferedImage(224, 224, BufferedImage.TYPE_INT_RGB);
            Graphics2D g = resized.createGraphics();
            g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
            g.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
            g.drawImage(source, 0, 0, 224, 224, null);
            g.dispose();
            FloatBuffer pixels = FloatBuffer.allocate(3 * 224 * 224);
            for (int channel = 0; channel < 3; channel++) for (int y = 0; y < 224; y++) for (int x = 0; x < 224; x++) {
                int rgb = resized.getRGB(x, y);
                int value = channel == 0 ? (rgb >> 16) & 255 : channel == 1 ? (rgb >> 8) & 255 : rgb & 255;
                pixels.put(value / 127.5f - 1.0f);
            }
            pixels.rewind();
            try (OnnxTensor tensor = OnnxTensor.createTensor(environment, pixels, new long[]{1, 3, 224, 224});
                 OrtSession.Result output = session.run(Map.of(inputName, tensor))) {
                float[][] logits = (float[][]) output.get(0).getValue();
                if (logits.length != 1 || logits[0].length != labels.size()) throw new IllegalStateException("Model output does not match class mapping");
                double[] probabilities = softmax(logits[0]);
                Integer[] order = new Integer[probabilities.length];
                for (int i = 0; i < order.length; i++) order[i] = i;
                Arrays.sort(order, (a, b) -> Double.compare(probabilities[b], probabilities[a]));
                double confidence = probabilities[order[0]];
                List<ApiModels.Alternative> alternatives = Arrays.stream(order).skip(1).limit(3)
                        .map(i -> new ApiModels.Alternative(labels.get(i), probabilities[i])).toList();
                String level = confidence >= highThreshold ? "HIGH" : confidence >= mediumThreshold ? "MODERATE" : "LOW";
                boolean classified = confidence >= minimumConfidence;
                return new ApiModels.ClassificationView(classified ? "CLASSIFIED" : "UNSURE",
                        classified ? labels.get(order[0]) : null, confidence,
                        classified ? level : "UNSURE", alternatives, null);
            }
        } catch (ClassificationService.ModelUnavailableException e) { throw e; }
        catch (Exception e) { throw new IllegalStateException("Image analysis failed", e); }
    }

    @PreDestroy
    public void close() {
        if (session != null) try { session.close(); } catch (Exception ignored) { }
    }

    private static double[] softmax(float[] logits) {
        double max = Arrays.stream(toDouble(logits)).max().orElse(0);
        double sum = 0;
        double[] probabilities = new double[logits.length];
        for (int i = 0; i < probabilities.length; i++) { probabilities[i] = Math.exp(logits[i] - max); sum += probabilities[i]; }
        for (int i = 0; i < probabilities.length; i++) probabilities[i] /= sum;
        return probabilities;
    }
    private static double[] toDouble(float[] values) {
        double[] result = new double[values.length];
        for (int i = 0; i < values.length; i++) result[i] = values[i];
        return result;
    }
}
