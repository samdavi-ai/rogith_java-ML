package org.secondcircuit.assistant.config;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;

@Configuration
public class DatabaseConfig {
    @Bean
    DataSource dataSource(@Value("${DATABASE_URL:jdbc:postgresql://localhost:5432/ewaste}") String configuredUrl,
                          @Value("${DATABASE_USER:ewaste}") String username,
                          @Value("${DATABASE_PASSWORD:}") String password) {
        String jdbcUrl = configuredUrl;
        if (jdbcUrl.startsWith("postgresql://")) jdbcUrl = "jdbc:" + jdbcUrl;
        else if (jdbcUrl.startsWith("postgres://")) jdbcUrl = "jdbc:postgresql://" + jdbcUrl.substring("postgres://".length());
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl(jdbcUrl);
        dataSource.setUsername(username);
        dataSource.setPassword(password);
        return dataSource;
    }
}
