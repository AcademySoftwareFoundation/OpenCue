package com.imageworks.spcue.config;

import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.HostReportQueue;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

@Configuration
public class ThreadPoolConfig {

    @Bean("launchQueue")
    public ThreadPoolTaskExecutor launchQueue() {
        ThreadPoolTaskExecutor pool = new ThreadPoolTaskExecutor();
        pool.setCorePoolSize(1);
        pool.setMaxPoolSize(1);
        pool.setQueueCapacity(100);
        return pool;
    }

    @Bean("dispatchPool")
    public ThreadPoolTaskExecutor dispatchPool() {
        ThreadPoolTaskExecutor pool = new ThreadPoolTaskExecutor();
        pool.setCorePoolSize(4);
        pool.setMaxPoolSize(4);
        pool.setQueueCapacity(500);
        return pool;
    }

    @Bean("killPool")
    public ThreadPoolTaskExecutor killPool() {
        ThreadPoolTaskExecutor pool = new ThreadPoolTaskExecutor();
        pool.setCorePoolSize(4);
        pool.setMaxPoolSize(4);
        pool.setQueueCapacity(500);
        return pool;
    }

    @Bean("managePool")
    public ThreadPoolTaskExecutor managePool() {
        ThreadPoolTaskExecutor pool = new ThreadPoolTaskExecutor();
        pool.setCorePoolSize(4);
        pool.setMaxPoolSize(4);
        pool.setQueueCapacity(500);
        return pool;
    }

    @Bean("dispatchQueue")
    public DispatchQueue dispatchQueue() {
        return new DispatchQueue("DispatchQueue", dispatchPool());
    }

    @Bean("manageQueue")
    public DispatchQueue manageQueue() {
        return new DispatchQueue("DispatchQueue", managePool());
    }

    @Bean("reportQueue")
    public HostReportQueue reportQueue() {
        return new HostReportQueue();
    }

    @Bean("killQueue")
    public HostReportQueue killQueue() {
        return new HostReportQueue();
    }
}
