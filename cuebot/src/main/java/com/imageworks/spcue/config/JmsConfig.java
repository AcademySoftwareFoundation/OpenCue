package com.imageworks.spcue.config;

import org.apache.activemq.ActiveMQConnectionFactory;
import org.apache.activemq.command.ActiveMQTopic;
import org.apache.activemq.jms.pool.PooledConnectionFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jms.core.JmsTemplate;

@Configuration
public class JmsConfig {


    @Bean()
    public PooledConnectionFactory jmsFactory() {
        ActiveMQConnectionFactory amq = new ActiveMQConnectionFactory();
        amq.setBrokerURL("failover:(tcp://mq1:61616,tcp://mq2:61616)?maxReconnectAttempts=1&amp;maxReconnectDelay=10)");

        PooledConnectionFactory factory = new PooledConnectionFactory();
        factory.setConnectionFactory(amq);
        return factory;
    }

    @Bean
    public JmsTemplate jmsTemplate() {
        JmsTemplate tmpl = new JmsTemplate();
        tmpl.setConnectionFactory(jmsFactory());
        return tmpl;
    }

    @Bean
    public ActiveMQTopic jobTopic() {
        return new ActiveMQTopic("cue.job");
    }
}
