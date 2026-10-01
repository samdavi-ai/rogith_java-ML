package org.secondcircuit.assistant.service;

import org.secondcircuit.assistant.api.ApiModels;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
import java.io.ByteArrayInputStream;
import java.util.Iterator;

@Service
public class ClassificationService {
    private final OnnxClassifier classifier;
    private final long maxBytes;
    public ClassificationService(OnnxClassifier classifier, @Value("${app.upload.max-bytes:10485760}") long maxBytes) {
        this.classifier = classifier; this.maxBytes = maxBytes;
    }
    public ApiModels.ClassificationView classify(MultipartFile image) {
        if (image == null || image.isEmpty() || image.getSize() > maxBytes) throw new InvalidImageException("Choose a readable image smaller than 10 MB.");
        String mime = image.getContentType();
        if (mime == null || !mime.matches("image/(jpeg|png)")) throw new InvalidImageException("Please upload a JPG or PNG image.");
        try (ImageInputStream stream = ImageIO.createImageInputStream(new ByteArrayInputStream(image.getBytes()))) {
            if (stream == null) throw new InvalidImageException("We couldn't read this image. Please try another photo.");
            Iterator<ImageReader> readers = ImageIO.getImageReaders(stream);
            if (!readers.hasNext()) throw new InvalidImageException("Please upload a valid JPG or PNG image.");
            ImageReader reader = readers.next();
            try {
                reader.setInput(stream, true, true);
                String format = reader.getFormatName().toLowerCase();
                int width = reader.getWidth(0), height = reader.getHeight(0);
                if (!(format.equals("jpeg") || format.equals("jpg") || format.equals("png")) || width < 32 || height < 32 || width > 12000 || height > 12000 || (long) width * height > 40_000_000L)
                    throw new InvalidImageException("Please upload a valid JPG or PNG image between 32 and 12000 pixels per side.");
                boolean matchesMime = (format.equals("png") && mime.equals("image/png")) || ((format.equals("jpeg") || format.equals("jpg")) && mime.equals("image/jpeg"));
                if (!matchesMime) throw new InvalidImageException("The image content does not match its declared file type.");
                var decoded = reader.read(0);
                if (decoded == null) throw new InvalidImageException("We couldn't read this image. Please try another photo.");
                return classifier.predict(decoded);
            } finally { reader.dispose(); }
        } catch (InvalidImageException | ModelUnavailableException e) { throw e; }
        catch (Exception e) { throw new InvalidImageException("We couldn't read this image. Please try another photo."); }
    }
    public static class InvalidImageException extends RuntimeException { public InvalidImageException(String message) { super(message); } }
    public static class ModelUnavailableException extends RuntimeException { public ModelUnavailableException() { super("Model not configured"); } }
}
