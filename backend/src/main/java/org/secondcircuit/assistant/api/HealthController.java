package org.secondcircuit.assistant.api;

import org.secondcircuit.assistant.service.OnnxClassifier;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class HealthController {
    private final OnnxClassifier classifier;

    public HealthController(OnnxClassifier classifier) { this.classifier = classifier; }

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("status", "UP");
        result.put("modelStatus", classifier.modelStatus());
        if ("MODEL_READY".equals(classifier.modelStatus())) result.put("modelLoadTimeMs", classifier.modelLoadTimeMs());
        return Map.copyOf(result);
    }
}
