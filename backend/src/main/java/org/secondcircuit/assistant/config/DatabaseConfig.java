package org.secondcircuit.assistant.config;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;
import java.net.URI;

@Configuration
public class DatabaseConfig {
    @Bean
    DataSource dataSource(@Value("${DATABASE_URL:jdbc:postgresql://localhost:5432/ewaste}") String configuredUrl,
                          @Value("${DATABASE_USER:ewaste}") String username,
                          @Value("${DATABASE_PASSWORD:}") String password) {
        String jdbcUrl = configuredUrl;
        if (jdbcUrl.startsWith("postgres://") || jdbcUrl.startsWith("postgresql://")) {
            URI uri = URI.create(configuredUrl);
            if (uri.getHost() == null) throw new IllegalArgumentException("DATABASE_URL must include a PostgreSQL host");
            jdbcUrl = "jdbc:postgresql://" + uri.getHost()
                    + (uri.getPort() == -1 ? "" : ":" + uri.getPort())
                    + (uri.getRawPath() == null ? "" : uri.getRawPath())
                    + (uri.getRawQuery() == null ? "" : "?" + uri.getRawQuery());
        }
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl(jdbcUrl);
        dataSource.setUsername(username);
        dataSource.setPassword(password);
        return dataSource;
    }
}
