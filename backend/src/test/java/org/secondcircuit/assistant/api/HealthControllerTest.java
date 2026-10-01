package org.secondcircuit.assistant.api;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class HealthControllerTest {
    @Test void reportsUpWithoutExposingConfiguration() {
        var classifier = new org.secondcircuit.assistant.service.OnnxClassifier("/missing/model", "/missing/classes", .85, .60, .66);
        assertEquals(java.util.Map.of("status", "UP", "modelStatus", "MODEL_UNAVAILABLE"), new HealthController(classifier).health());
    }
}
