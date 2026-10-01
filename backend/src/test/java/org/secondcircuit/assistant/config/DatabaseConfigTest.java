package org.secondcircuit.assistant.config;

import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class DatabaseConfigTest {
    @Test void adaptsRenderPostgresUrisToJdbcUrls() {
        var config = new DatabaseConfig();
        try (var datasource = (HikariDataSource) config.dataSource("postgresql://user:pass@host:5432/db", "user", "pass")) {
            assertEquals("jdbc:postgresql://host:5432/db", datasource.getJdbcUrl());
        }
    }
}
