package org.secondcircuit.assistant.api;

import java.util.List;

public final class ApiModels {
    private ApiModels() {}
    public record Envelope<T>(boolean success, T data, ApiError error) {
        public static <T> Envelope<T> ok(T data) { return new Envelope<>(true, data, null); }
        public static <T> Envelope<T> fail(String code, String message) { return new Envelope<>(false, null, new ApiError(code, message)); }
    }
    public record ApiError(String code, String message) {}
    public record ClassificationView(String status, String categoryName, double confidence, String confidenceLevel,
            List<Alternative> alternatives, GuideView guide) {}
    public record Alternative(String category, double confidence) {}
    public record GuideView(String recyclingMethod, List<String> preparationInstructions,
            String safetyInstructions, String sourceName, String sourceUrl, String jurisdiction,
            String lastVerifiedAt) {}
}
