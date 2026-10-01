package org.secondcircuit.assistant.service;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import ai.onnxruntime.TensorInfo;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.secondcircuit.assistant.api.ApiModels;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

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
    private final OrtEnvironment environment;
    private final OrtSession session;
    private final String inputName;
    private final List<String> labels;
    private final double highThreshold, mediumThreshold;

    public OnnxClassifier(@Value("${app.ml.model-path:ml/models/ewaste.onnx}") String modelPath,
                          @Value("${app.ml.labels-path:ml/classes.json}") String labelsPath,
                          @Value("${app.ml.high-threshold:0.85}") double highThreshold,
                          @Value("${app.ml.medium-threshold:0.60}") double mediumThreshold) {
        this.highThreshold = highThreshold;
        this.mediumThreshold = mediumThreshold;
        if (!Files.isRegularFile(Path.of(modelPath)) || !Files.isRegularFile(Path.of(labelsPath))) {
            environment = null;
            session = null;
            inputName = null;
            labels = List.of();
            return;
        }
        try {
            var root = new ObjectMapper().readTree(Path.of(labelsPath).toFile());
            var classNodes = root.path("classes");
            if (!classNodes.isArray() || classNodes.isEmpty()) throw new IllegalArgumentException("classes.json has no classes");
            var names = new java.util.ArrayList<String>();
            for (int i = 0; i < classNodes.size(); i++) {
                var item = classNodes.get(i);
                if (item.path("id").asInt(-1) != i || item.path("name").asText().isBlank())
                    throw new IllegalArgumentException("classes.json IDs must be contiguous and ordered");
                names.add(item.path("displayName").asText(item.path("name").asText()));
            }
            labels = List.copyOf(names);
            environment = OrtEnvironment.getEnvironment();
            session = environment.createSession(modelPath, new OrtSession.SessionOptions());
            inputName = session.getInputNames().iterator().next();
            var shape = ((TensorInfo) session.getInputInfo().get(inputName).getInfo()).getShape();
            if (shape.length != 4 || shape[1] != 3 || shape[2] != 224 || shape[3] != 224)
                throw new IllegalArgumentException("ONNX input must be NCHW float32 [N,3,224,224]");
            var outputName = session.getOutputNames().iterator().next();
            var outputShape = ((TensorInfo) session.getOutputInfo().get(outputName).getInfo()).getShape();
            if (outputShape.length != 2 || outputShape[1] != labels.size())
                throw new IllegalArgumentException("ONNX output class count does not match classes.json");
        } catch (Exception e) {
            throw new IllegalStateException("Unable to initialize the configured e-waste ONNX model", e);
        }
    }

    public ApiModels.ClassificationView predict(BufferedImage source) {
        if (session == null) throw new ClassificationService.ModelUnavailableException();
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
                return new ApiModels.ClassificationView(labels.get(order[0]), confidence, level, alternatives, null);
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
