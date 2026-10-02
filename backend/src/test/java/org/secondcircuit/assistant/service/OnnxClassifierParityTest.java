package org.secondcircuit.assistant.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

class OnnxClassifierParityTest {
    private record Expected(String category, double probability) {}

    @Test void javaImagePipelineMatchesPythonOnnxTopFourOnIdenticalHeldOutFiles() throws Exception {
        String reference = System.getProperty("recolens.parity.reference");
        assumeTrue(reference != null, "Generate the Python reference with ml/scripts/verify_java_onnx_parity.py");
        JsonNode records = new ObjectMapper().readTree(Path.of(reference).toFile()).path("records");
        Path model = Path.of("../ml/models/ewaste.onnx");
        Path classes = Path.of("../ml/class_mapping.json");
        assertTrue(model.toFile().isFile());
        assertTrue(classes.toFile().isFile());
        OnnxClassifier classifier = new OnnxClassifier(model.toString(), classes.toString(), .85, .60, 0.0);
        List<String> mismatches = new ArrayList<>();
        double maxDelta = 0.0;
        int compared = 0;
        try {
            assertEquals("MODEL_READY", classifier.modelStatus());
            for (JsonNode record : records) {
                Path imagePath = Path.of(record.path("path").asText());
                var image = ImageIO.read(imagePath.toFile());
                assertNotNull(image, "Java ImageIO could not decode " + imagePath);
                var actual = classifier.predict(image);
                List<Expected> expected = new ArrayList<>();
                for (JsonNode item : record.path("topK")) {
                    expected.add(new Expected(item.path("category").asText(), item.path("probability").asDouble()));
                }
                List<Expected> javaTop = new ArrayList<>();
                javaTop.add(new Expected(actual.categoryName(), actual.confidence()));
                for (var item : actual.alternatives()) javaTop.add(new Expected(item.category(), item.confidence()));
                assertEquals(expected.size(), javaTop.size(), "Top-k count changed for " + imagePath);
                for (int i = 0; i < expected.size(); i++) {
                    double delta = Math.abs(expected.get(i).probability() - javaTop.get(i).probability());
                    maxDelta = Math.max(maxDelta, delta);
                    compared++;
                    if (!expected.get(i).category().equals(javaTop.get(i).category())) {
                        mismatches.add("rank " + (i + 1) + " label " + imagePath);
                    }
                    if (delta > 0.02) {
                        mismatches.add("rank " + (i + 1) + " probability delta=" + delta + " " + imagePath);
                    }
                }
            }
            System.out.printf("Java/Python ONNX parity: images=%d values=%d maxTop4ProbabilityDelta=%.6f mismatches=%d%n",
                    records.size(), compared, maxDelta, mismatches.size());
            assertTrue(mismatches.isEmpty(), String.join("\n", mismatches));
        } finally {
            classifier.close();
        }
    }
}
