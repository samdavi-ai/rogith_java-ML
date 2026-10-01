package org.secondcircuit.assistant.api;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

class HealthControllerTest {
    @Test void reportsUpWithoutExposingConfiguration() {
        assertEquals(java.util.Map.of("status", "UP"), new HealthController().health());
    }
}
