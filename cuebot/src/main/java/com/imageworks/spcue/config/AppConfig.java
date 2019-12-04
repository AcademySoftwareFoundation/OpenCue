
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



package com.imageworks.spcue.config;

import com.imageworks.spcue.servlet.JobLaunchServlet;

import javax.sql.DataSource;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.boot.web.servlet.ServletRegistrationBean;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Conditional;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.ImportResource;
import org.springframework.context.annotation.Lazy;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.PropertySource;

@Configuration
@ImportResource({"classpath:conf/spring/applicationContext-dbEngine.xml",
                 "classpath:conf/spring/applicationContext-grpc.xml",
                 "classpath:conf/spring/applicationContext-grpcServer.xml",
                 "classpath:conf/spring/applicationContext-service.xml",
                 "classpath:conf/spring/applicationContext-jms.xml",
                 "classpath:conf/spring/applicationContext-trackit.xml",
                 "classpath:conf/spring/applicationContext-criteria.xml"})
@EnableConfigurationProperties
@PropertySource({"classpath:opencue.properties"})
public class AppConfig {

    @Configuration
    @Conditional(OracleDatabaseCondition.class)
    @ImportResource({"classpath:conf/spring/applicationContext-dao-oracle.xml"})
    static class OracleEngineConfig {}

    @Configuration
    @Conditional(PostgresDatabaseCondition.class)
    @ImportResource({"classpath:conf/spring/applicationContext-dao-postgres.xml"})
    static class PostgresEngineConfig {}

    @Bean
    @Primary
    @ConfigurationProperties(prefix="datasource.cue-data-source")
    public DataSource cueDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    @ConfigurationProperties(prefix="datasource.trackit-data-source")
    public DataSource trackitDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    public ServletRegistrationBean jobLaunchServlet() {
        ServletRegistrationBean b = new ServletRegistrationBean();
        b.addUrlMappings("/launch");
        b.addInitParameter("contextConfigLocation", "classpath:conf/spring/jobLaunchServlet-servlet.xml");
        b.setServlet(new JobLaunchServlet());
        return b;
    }

}

