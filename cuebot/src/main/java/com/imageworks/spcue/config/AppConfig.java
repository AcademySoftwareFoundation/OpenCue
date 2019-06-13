
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

import com.imageworks.spcue.dispatcher.CoreUnitDispatcher;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.LocalDispatcher;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientGrpc;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.PropertySource;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;


@Configuration
public class AppConfig {

    @Configuration
    @ConfigurationProperties("grpc.rqd")
    public class RqdConfiguration {
        public int cacheSize = 500;
        public int cacheExpiration = 30;
        public int serverPort = 8444;
    }

    @Bean
    @Autowired
    public RqdClient rqdClient(RqdConfiguration config) {
        return new RqdClientGrpc(config.serverPort, config.cacheSize, config.cacheExpiration);
    }

    @Bean("localDispatcher")
    public Dispatcher localDispatcher() {
        return new LocalDispatcher();
    }

    @Bean("dispatcher")
    public Dispatcher coreUnitDispatcher() {
        return new CoreUnitDispatcher();
    }

    @Bean
    public JavaMailSenderImpl mailSender() {
        JavaMailSenderImpl sender =  new JavaMailSenderImpl();
        sender.setHost("smtp");
        return sender;
    }
}

