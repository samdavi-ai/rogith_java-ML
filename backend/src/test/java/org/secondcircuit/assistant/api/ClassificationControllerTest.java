package org.secondcircuit.assistant.api;

import org.junit.jupiter.api.Test;
import org.secondcircuit.assistant.service.ClassificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.secondcircuit.assistant.config.SecurityConfig;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.mock.web.MockMultipartFile;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ClassificationController.class)
@Import(SecurityConfig.class)
class ClassificationControllerTest {
    @Autowired MockMvc mvc;
    @MockBean ClassificationService service;

    @Test void reportsUnavailableModelAsServiceUnavailableWithoutPrediction() throws Exception {
        when(service.classify(any())).thenThrow(new ClassificationService.ModelUnavailableException());
        MockMultipartFile image = new MockMultipartFile("image", "item.jpg", MediaType.IMAGE_JPEG_VALUE, new byte[]{1,2,3});
        mvc.perform(multipart("/api/classifications").file(image))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("MODEL_UNAVAILABLE"))
                .andExpect(jsonPath("$.error.message").value("Image identification is not configured yet. Please use the guide while the model is being prepared."));
    }
}
