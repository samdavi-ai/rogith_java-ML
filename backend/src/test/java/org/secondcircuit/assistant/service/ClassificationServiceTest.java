package org.secondcircuit.assistant.service;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ClassificationServiceTest {
    private final OnnxClassifier classifier = mock(OnnxClassifier.class);
    private final ClassificationService service = new ClassificationService(classifier, 1024 * 1024);

    @Test void rejectsEmptyAndOversizedImagesBeforeInference() {
        assertThrows(ClassificationService.InvalidImageException.class,
                () -> service.classify(new MockMultipartFile("image", "empty.png", "image/png", new byte[0])));
        assertThrows(ClassificationService.InvalidImageException.class,
                () -> new ClassificationService(classifier, 10).classify(new MockMultipartFile("image", "large.png", "image/png", new byte[20])));
        verifyNoInteractions(classifier);
    }

    @Test void rejectsUnsupportedMimeAndCorruptImage() {
        assertThrows(ClassificationService.InvalidImageException.class,
                () -> service.classify(new MockMultipartFile("image", "doc.pdf", "application/pdf", new byte[]{1, 2, 3})));
        assertThrows(ClassificationService.InvalidImageException.class,
                () -> service.classify(new MockMultipartFile("image", "bad.png", "image/png", new byte[]{1, 2, 3})));
        verifyNoInteractions(classifier);
    }

    @Test void validJpegReachesClassifierAndKeepsMissingModelUnavailable() throws Exception {
        BufferedImage image = new BufferedImage(40, 40, BufferedImage.TYPE_INT_RGB);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        ImageIO.write(image, "jpeg", bytes);
        when(classifier.predict(any())).thenThrow(new ClassificationService.ModelUnavailableException());
        MockMultipartFile upload = new MockMultipartFile("image", "item.jpg", "image/jpeg", bytes.toByteArray());
        assertThrows(ClassificationService.ModelUnavailableException.class, () -> service.classify(upload));
        verify(classifier, times(1)).predict(any());
    }
}
