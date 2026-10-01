package org.secondcircuit.assistant.api;

import jakarta.validation.constraints.NotNull;
import org.secondcircuit.assistant.service.ClassificationService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/classifications")
@Validated
public class ClassificationController {
    private final ClassificationService service;
    public ClassificationController(ClassificationService service) { this.service = service; }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<ApiModels.Envelope<?>> classify(@RequestPart("image") @NotNull MultipartFile image) {
        return ResponseEntity.ok(ApiModels.Envelope.ok(java.util.Map.of("classification", service.classify(image))));
    }
}
