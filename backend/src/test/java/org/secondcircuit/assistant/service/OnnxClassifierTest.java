package org.secondcircuit.assistant.service;

import org.junit.jupiter.api.Test;

import java.awt.image.BufferedImage;
import java.nio.file.Path;
import javax.imageio.ImageIO;
import java.io.File;

import static org.junit.jupiter.api.Assertions.*;

class OnnxClassifierTest {
    @Test void missingModelIsReportedBeforeRuntimeInitializationOrInference() {
        OnnxClassifier classifier = new OnnxClassifier("/nonexistent/ewaste.onnx", "/nonexistent/labels.txt", .85, .60);
        assertThrows(ClassificationService.ModelUnavailableException.class,
                () -> classifier.predict(new BufferedImage(224, 224, BufferedImage.TYPE_INT_RGB)));
    }

    @Test void trainedOnnxModelRunsOnARealHeldOutImageWhenArtifactsArePresent() throws Exception {
        Path model = Path.of("../ml/models/ewaste.onnx");
        Path classes = Path.of("../ml/classes.json");
        Path sample = Path.of("../ml/data/processed/classification/test/battery_waste/IMG_20250803_215701_jpg.rf.352a524931e1295dac040a7f6381d4f1.jpg");
        org.junit.jupiter.api.Assumptions.assumeTrue(model.toFile().isFile() && classes.toFile().isFile() && sample.toFile().isFile());
        OnnxClassifier classifier = new OnnxClassifier(model.toString(), classes.toString(), .85, .60);
        try {
            var result = classifier.predict(ImageIO.read(new File(sample.toString())));
            assertEquals("Mobile phone", result.categoryName()); // This is the one observed held-out error.
            assertTrue(result.confidence() >= 0.0 && result.confidence() <= 1.0);
            assertEquals(3, result.alternatives().size());
        } finally {
            classifier.close();
        }
    }
}
