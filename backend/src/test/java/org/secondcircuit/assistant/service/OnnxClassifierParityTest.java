package org.secondcircuit.assistant.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.zip.ZipFile;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class OnnxClassifierParityTest {
    private record Expected(String category, double probability) {}

    @Test void pythonAndJavaShareTensorAndOnnxOutputs() throws Exception {
        String fixtureProperty = System.getProperty("recolens.parity.fixture");
        assumeTrue(fixtureProperty != null, "Build the persistent fixture with ml/scripts/verify_java_onnx_parity.py");
        Path fixture = Path.of(fixtureProperty);
        JsonNode root = new ObjectMapper().readTree(fixture.resolve("fixture.json").toFile());
        assertEquals("recolens-java-onnx-parity-fixture-v1", root.path("schema").asText());
        Path model = Path.of("../ml/models/ewaste.onnx");
        Path classes = Path.of("../ml/class_mapping.json");
        OnnxClassifier classifier = new OnnxClassifier(model.toString(), classes.toString(), .85, .60, 0.0);
        double maxTensorAbs = 0, meanTensorAbs = 0, maxLogitAbs = 0, meanLogitAbs = 0;
        double maxLogitRel = 0, meanLogitRel = 0, maxProbabilityAbs = 0, meanProbabilityAbs = 0;
        double maxConfidenceAbs = 0, meanConfidenceAbs = 0;
        int decodedHashMismatches = 0;
        int tensorValues = 0, logitValues = 0, probabilityValues = 0;
        int top1 = 0, top3 = 0, top5 = 0, top3Values = 0, top5Values = 0, top3Matched = 0, top5Matched = 0;
        int legacyTop1 = 0, legacyTop4Matches = 0, legacyTop5Matches = 0;
        double legacyMaxConfidenceDelta = 0, legacyMaxTop4ProbabilityDelta = 0, legacyMeanTop4ProbabilityDelta = 0;
        String legacyMaxTop4ProbabilityImage = "";
        String legacyMaxConfidenceImage = "", legacyMaxConfidencePythonTop5 = "", legacyMaxConfidenceJavaTop5 = "";
        int legacyMaxTop4ProbabilityRank = 0, legacyTop4ProbabilityValues = 0;
        int probeDecodedMismatches = 0, preprocessingProbesPassed = 0;
        double probeTensorMaxAbs = 0;
        List<String> top5Mismatches = new ArrayList<>();
        List<String> legacyMismatches = new ArrayList<>();
        try (ZipFile tensorArchive = new ZipFile(fixture.resolve("preprocessed_nchw_f32.zip").toFile())) {
            assertEquals("MODEL_READY", classifier.modelStatus());
            for (JsonNode record : root.path("records")) {
                Path imagePath = fixture.resolve(record.path("image").asText());
                assertEquals(record.path("imageSha256").asText(), sha256(Files.readAllBytes(imagePath)), "Image fixture changed: " + imagePath);
                var image = ImageIO.read(imagePath.toFile());
                assertNotNull(image, "Java ImageIO could not decode " + imagePath);
                JsonNode decodedShape = record.path("decodedShape");
                int decodedOffset = 0;
                byte[] javaDecoded = new byte[image.getWidth() * image.getHeight() * 3];
                for (int y = 0; y < decodedShape.get(0).asInt(); y++) for (int x = 0; x < decodedShape.get(1).asInt(); x++) {
                    int rgb = image.getRGB(x, y);
                    int[] values = {(rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255};
                    for (int channel = 0; channel < 3; channel++) {
                        javaDecoded[decodedOffset++] = (byte) values[channel];
                    }
                }
                if (!record.path("decodedSha256").asText().equals(sha256(javaDecoded))) decodedHashMismatches++;
                float[] javaTensor = OnnxClassifier.preprocess(image);
                byte[] expectedBytes;
                try (InputStream stream = tensorArchive.getInputStream(tensorArchive.getEntry(record.path("tensorEntry").asText()))) {
                    expectedBytes = stream.readAllBytes();
                }
                assertEquals(record.path("tensorSha256").asText(), sha256(expectedBytes), "Tensor reference changed: " + imagePath);
                assertEquals(javaTensor.length * Float.BYTES, expectedBytes.length);
                ByteBuffer expectedTensor = ByteBuffer.wrap(expectedBytes).order(ByteOrder.LITTLE_ENDIAN);
                for (float value : javaTensor) {
                    double delta = Math.abs(value - expectedTensor.getFloat());
                    maxTensorAbs = Math.max(maxTensorAbs, delta);
                    meanTensorAbs += delta;
                    tensorValues++;
                }

                float[] javaLogits = classifier.rawLogits(image);
                JsonNode expectedLogits = record.path("rawLogits");
                assertEquals(expectedLogits.size(), javaLogits.length);
                double[] javaProbabilities = softmax(javaLogits);
                JsonNode expectedProbabilities = record.path("probabilities");
                Integer[] order = new Integer[javaProbabilities.length];
                for (int i = 0; i < order.length; i++) order[i] = i;
                java.util.Arrays.sort(order, Comparator.comparingDouble((Integer i) -> javaProbabilities[i]).reversed());
                for (int i = 0; i < javaLogits.length; i++) {
                    double expected = expectedLogits.get(i).asDouble();
                    double delta = Math.abs(expected - javaLogits[i]);
                    maxLogitAbs = Math.max(maxLogitAbs, delta);
                    meanLogitAbs += delta;
                    double relativeDelta = delta / Math.max(Math.abs(expected), 1e-12);
                    maxLogitRel = Math.max(maxLogitRel, relativeDelta);
                    meanLogitRel += relativeDelta;
                    logitValues++;
                    double probabilityDelta = Math.abs(expectedProbabilities.get(i).asDouble() - javaProbabilities[i]);
                    maxProbabilityAbs = Math.max(maxProbabilityAbs, probabilityDelta);
                    meanProbabilityAbs += probabilityDelta;
                    probabilityValues++;
                }
                double confidenceDelta = Math.abs(expectedTopProbability(record) - javaProbabilities[order[0]]);
                maxConfidenceAbs = Math.max(maxConfidenceAbs, confidenceDelta);
                meanConfidenceAbs += confidenceDelta;
                JsonNode expectedTop = record.path("top5");
                int perImageTop3 = 0, perImageTop5 = 0;
                for (int rank = 0; rank < 5; rank++) {
                    int expectedIndex = expectedTop.get(rank).path("index").asInt();
                    int actualIndex = order[rank];
                    if (expectedIndex == actualIndex) {
                        perImageTop5++;
                        top5Matched++;
                        if (rank < 3) top3Matched++;
                        if (rank < 3) perImageTop3++;
                    } else {
                        top5Mismatches.add(imagePath + " rank=" + (rank + 1) + " python=" + expectedTop.get(rank).path("category").asText()
                                + " java=" + root.path("output").path("classes").get(actualIndex).asText());
                    }
                }
                top5Values += 5;
                top3Values += 3;
                if (perImageTop5 == 5) top5++;
                if (perImageTop3 == 3) top3++;
                if (expectedTop.get(0).path("index").asInt() == order[0]) top1++;

                JsonNode phase8 = record.path("phase8Reference");
                float[] legacyTensor = legacyGraphics2dTensor(image);
                float[] pythonLegacyLogits = new float[phase8.path("rawLogits").size()];
                for (int i = 0; i < pythonLegacyLogits.length; i++) pythonLegacyLogits[i] = (float) phase8.path("rawLogits").get(i).asDouble();
                float[] legacyLogits = classifier.rawLogits(legacyTensor);
                double[] pythonLegacyProbabilities = new double[phase8.path("probabilities").size()];
                for (int i = 0; i < pythonLegacyProbabilities.length; i++) pythonLegacyProbabilities[i] = phase8.path("probabilities").get(i).asDouble();
                assertEquals(pythonLegacyLogits.length, pythonLegacyProbabilities.length);
                double[] legacyProbabilities = softmax(legacyLogits);
                Integer[] legacyOrder = new Integer[legacyProbabilities.length];
                for (int i = 0; i < legacyOrder.length; i++) legacyOrder[i] = i;
                java.util.Arrays.sort(legacyOrder, Comparator.comparingDouble((Integer i) -> legacyProbabilities[i]).reversed());
                JsonNode pythonLegacyTop = phase8.path("top5");
                int rankMismatches = 0;
                StringBuilder pythonTop = new StringBuilder(), javaTop = new StringBuilder();
                for (int rank = 0; rank < 5; rank++) {
                    int pyIndex = pythonLegacyTop.get(rank).path("index").asInt();
                    int javaIndex = legacyOrder[rank];
                    if (rank > 0) { pythonTop.append("; "); javaTop.append("; "); }
                    pythonTop.append(pythonLegacyTop.get(rank).path("category").asText()).append("=").append(String.format("%.9f", pythonLegacyProbabilities[pyIndex]));
                    javaTop.append(root.path("output").path("classes").get(javaIndex).asText()).append("=").append(String.format("%.9f", legacyProbabilities[javaIndex]));
                    if (rank < 4) {
                        double rankDelta = Math.abs(pythonLegacyTop.get(rank).path("probability").asDouble() - legacyProbabilities[javaIndex]);
                        legacyMeanTop4ProbabilityDelta += rankDelta;
                        legacyTop4ProbabilityValues++;
                        if (rankDelta > legacyMaxTop4ProbabilityDelta) {
                            legacyMaxTop4ProbabilityDelta = rankDelta;
                            legacyMaxTop4ProbabilityImage = imagePath.getFileName().toString();
                            legacyMaxTop4ProbabilityRank = rank + 1;
                        }
                    }
                    if (pyIndex != javaIndex) rankMismatches++;
                    if (rank < 4 && pyIndex == javaIndex) legacyTop4Matches++;
                    if (pyIndex == javaIndex) legacyTop5Matches++;
                }
                if (pythonLegacyTop.get(0).path("index").asInt() == legacyOrder[0]) legacyTop1++;
                double top1ConfidenceDelta = Math.abs(pythonLegacyProbabilities[legacyOrder[0]] - legacyProbabilities[legacyOrder[0]]);
                if (top1ConfidenceDelta > legacyMaxConfidenceDelta) {
                    legacyMaxConfidenceDelta = top1ConfidenceDelta;
                    legacyMaxConfidenceImage = imagePath.getFileName().toString();
                    legacyMaxConfidencePythonTop5 = pythonTop.toString();
                    legacyMaxConfidenceJavaTop5 = javaTop.toString();
                }
                if (rankMismatches > 0) {
                    String deltas = rankDeltaSummary(pythonLegacyTop, legacyOrder, pythonLegacyProbabilities, legacyProbabilities, root.path("output").path("classes"));
                    legacyMismatches.add(imagePath.getFileName() + "\n  Python top-5: " + pythonTop + "\n  Java top-5: " + javaTop + "\n  rank-wise probability deltas: " + deltas);
                }
            }
            for (JsonNode probe : root.path("preprocessingProbes")) {
                Path imagePath = fixture.resolve(probe.path("image").asText());
                assertEquals(probe.path("imageSha256").asText(), sha256(Files.readAllBytes(imagePath)));
                var image = ImageIO.read(imagePath.toFile());
                assertNotNull(image, "Java ImageIO could not decode preprocessing probe " + imagePath);
                JsonNode shape = probe.path("decodedShape");
                assertEquals(shape.get(1).asInt(), image.getWidth(), "Decoder must not apply EXIF rotation or alter width");
                assertEquals(shape.get(0).asInt(), image.getHeight(), "Decoder must not apply EXIF rotation or alter height");
                byte[] expectedDecoded;
                try (InputStream stream = tensorArchive.getInputStream(tensorArchive.getEntry(probe.path("decodedEntry").asText()))) {
                    expectedDecoded = stream.readAllBytes();
                }
                assertEquals(probe.path("decodedSha256").asText(), sha256(expectedDecoded));
                int offset = 0;
                for (int y = 0; y < image.getHeight(); y++) for (int x = 0; x < image.getWidth(); x++) {
                    int rgb = image.getRGB(x, y);
                    int[] values = {(rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255};
                    for (int value : values) if ((expectedDecoded[offset++] & 255) != value) probeDecodedMismatches++;
                }
                byte[] expectedTensor;
                try (InputStream stream = tensorArchive.getInputStream(tensorArchive.getEntry(probe.path("tensorEntry").asText()))) {
                    expectedTensor = stream.readAllBytes();
                }
                assertEquals(probe.path("tensorSha256").asText(), sha256(expectedTensor));
                ByteBuffer expected = ByteBuffer.wrap(expectedTensor).order(ByteOrder.LITTLE_ENDIAN);
                for (float value : OnnxClassifier.preprocess(image)) {
                    probeTensorMaxAbs = Math.max(probeTensorMaxAbs, Math.abs(value - expected.getFloat()));
                }
                preprocessingProbesPassed++;
            }
        } finally {
            classifier.close();
        }
        meanTensorAbs /= tensorValues;
        meanLogitAbs /= logitValues;
        meanLogitRel /= logitValues;
        meanProbabilityAbs /= probabilityValues;
        meanConfidenceAbs /= root.path("records").size();
        legacyMeanTop4ProbabilityDelta /= legacyTop4ProbabilityValues;
        System.out.printf("Java/Python parity: images=%d, decoded RGB hash mismatches=%d, tensor max/mean abs=%.9g/%.9g, logits max/mean abs=%.9g/%.9g max/mean rel=%.9g/%.9g, probabilities max/mean abs=%.9g/%.9g, confidence max/mean abs=%.9g/%.9g, top1=%d/%d top3-all=%d/%d top3-labels=%d/%d top5-all=%d/%d top5-labels=%d/%d%n",
                root.path("records").size(), decodedHashMismatches,
                maxTensorAbs, meanTensorAbs, maxLogitAbs, meanLogitAbs, maxLogitRel, meanLogitRel,
                maxProbabilityAbs, meanProbabilityAbs, maxConfidenceAbs, meanConfidenceAbs, top1, root.path("records").size(), top3, root.path("records").size(), top3Matched, top3Values,
                top5, root.path("records").size(), top5Matched, top5Values);
        System.out.printf("Phase 8 legacy reference replay: top1=%d/%d top4-rank-agreement=%d/240 top5-rank-agreement=%d/300 max top1 confidence difference=%.9f max top4 rank probability delta=%.9f (image=%s rank=%d) mean top4 rank probability delta=%.9g%n",
                legacyTop1, root.path("records").size(), legacyTop4Matches, legacyTop5Matches, legacyMaxConfidenceDelta,
                legacyMaxTop4ProbabilityDelta, legacyMaxTop4ProbabilityImage, legacyMaxTop4ProbabilityRank, legacyMeanTop4ProbabilityDelta);
        System.out.println("Phase 8 maximum top1 confidence example: " + legacyMaxConfidenceImage + "\n  Python top-5: " + legacyMaxConfidencePythonTop5
                + "\n  Java top-5: " + legacyMaxConfidenceJavaTop5);
        System.out.printf("Image decode probes: %d/%d decoded RGB channel mismatches=%d tensor max abs=%.9g (JPEG EXIF orientation and alpha PNG included)%n",
                preprocessingProbesPassed, root.path("preprocessingProbes").size(), probeDecodedMismatches, probeTensorMaxAbs);
        if (!top5Mismatches.isEmpty()) System.out.println("Top-5 rank mismatches:\n" + String.join("\n", top5Mismatches));
        if (!legacyMismatches.isEmpty()) System.out.println("Phase 8 exact top-5 mismatch images:\n" + String.join("\n", legacyMismatches));
        assertEquals(root.path("records").size(), top1, "Top-1 labels must agree");
        assertTrue(maxTensorAbs <= 1e-4, "Preprocessed tensors differ beyond the measured float resize envelope: " + maxTensorAbs);
        assertTrue(maxLogitAbs <= 1e-4, "Raw ONNX logits differ beyond the observed CPU runtime envelope: " + maxLogitAbs);
        assertTrue(maxProbabilityAbs <= 3e-5, "Probabilities differ beyond the measured softmax/runtime envelope: " + maxProbabilityAbs);
        assertEquals(0, decodedHashMismatches, "JPEG decoded RGB pixel hashes must match Python reference");
        assertTrue(probeDecodedMismatches == 0, "JPEG/PNG decoded RGB pixels differ from Python reference");
        assertTrue(probeTensorMaxAbs <= 1e-4, "Preprocessing probe resize exceeds measured float envelope: " + probeTensorMaxAbs);
        assertEquals(root.path("preprocessingProbes").size(), preprocessingProbesPassed);
        assertEquals(root.path("records").size(), top3, "All top-three class rankings must agree per image");
        assertEquals(root.path("records").size(), top5, "All five ranked classes must agree per image");
    }

    private static double expectedTopProbability(JsonNode record) {
        return record.path("top5").get(0).path("probability").asDouble();
    }

    private static float[] legacyGraphics2dTensor(BufferedImage source) {
        BufferedImage resized = new BufferedImage(224, 224, BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = resized.createGraphics();
        graphics.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        graphics.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
        graphics.drawImage(source, 0, 0, 224, 224, null);
        graphics.dispose();
        float[] tensor = new float[3 * 224 * 224];
        for (int channel = 0; channel < 3; channel++) for (int y = 0; y < 224; y++) for (int x = 0; x < 224; x++) {
            int rgb = resized.getRGB(x, y);
            int value = channel == 0 ? (rgb >> 16) & 255 : channel == 1 ? (rgb >> 8) & 255 : rgb & 255;
            tensor[channel * 224 * 224 + y * 224 + x] = value / 127.5f - 1.0f;
        }
        return tensor;
    }

    private static String rankDeltaSummary(JsonNode pythonTop, Integer[] javaOrder, double[] pythonProbabilities,
                                           double[] javaProbabilities, JsonNode labels) {
        List<String> deltas = new ArrayList<>();
        for (int rank = 0; rank < 5; rank++) {
            int pythonIndex = pythonTop.get(rank).path("index").asInt();
            deltas.add("r" + (rank + 1) + ":" + String.format("%.9f", Math.abs(pythonProbabilities[pythonIndex] - javaProbabilities[javaOrder[rank]]))
                    + " (" + pythonTop.get(rank).path("category").asText() + " / " + labels.get(javaOrder[rank]).asText() + ")");
        }
        return String.join("; ", deltas);
    }

    private static double[] softmax(float[] logits) {
        double max = -Double.MAX_VALUE;
        for (float value : logits) max = Math.max(max, value);
        double sum = 0;
        double[] probabilities = new double[logits.length];
        for (int i = 0; i < logits.length; i++) { probabilities[i] = Math.exp(logits[i] - max); sum += probabilities[i]; }
        for (int i = 0; i < logits.length; i++) probabilities[i] /= sum;
        return probabilities;
    }

    private static String sha256(byte[] bytes) throws Exception {
        byte[] digest = java.security.MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder value = new StringBuilder();
        for (byte b : digest) value.append(String.format("%02x", b));
        return value.toString();
    }
}
