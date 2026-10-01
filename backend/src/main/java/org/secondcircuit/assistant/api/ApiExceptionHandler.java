package org.secondcircuit.assistant.api;

import org.secondcircuit.assistant.service.ClassificationService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestControllerAdvice
public class ApiExceptionHandler {
    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);
    @ExceptionHandler(ClassificationService.InvalidImageException.class)
    ResponseEntity<ApiModels.Envelope<?>> invalidImage(Exception ex) {
        return ResponseEntity.badRequest().body(ApiModels.Envelope.fail("INVALID_IMAGE", ex.getMessage()));
    }
    @ExceptionHandler(ClassificationService.ModelUnavailableException.class)
    ResponseEntity<ApiModels.Envelope<?>> modelUnavailable(Exception ex) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(ApiModels.Envelope.fail("MODEL_UNAVAILABLE", "Image identification is not configured yet. Please use the guide while the model is being prepared."));
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    ResponseEntity<ApiModels.Envelope<?>> uploadTooLarge(Exception ex) {
        return ResponseEntity.status(HttpStatus.PAYLOAD_TOO_LARGE)
                .body(ApiModels.Envelope.fail("IMAGE_TOO_LARGE", "Choose an image smaller than 10 MB."));
    }

    @ExceptionHandler(MissingServletRequestPartException.class)
    ResponseEntity<ApiModels.Envelope<?>> missingImage(Exception ex) {
        return ResponseEntity.badRequest().body(ApiModels.Envelope.fail("INVALID_IMAGE", "Please attach an image to identify."));
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ApiModels.Envelope<?>> unexpected(Exception ex) {
        log.error("Unhandled classification API error", ex);
        return ResponseEntity.internalServerError()
                .body(ApiModels.Envelope.fail("INTERNAL_ERROR", "We couldn't analyze this image. Please try again later."));
    }
}
