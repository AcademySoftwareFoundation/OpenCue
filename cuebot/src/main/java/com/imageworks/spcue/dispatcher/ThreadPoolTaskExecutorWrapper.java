
/*
 * Copyright Contributors to the OpenCue Project
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



package com.imageworks.spcue.dispatcher;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import com.imageworks.spcue.util.CueUtil;

/**
 * Wrapper class of spring ThreadPoolTaskExecutor to initialize with the thread pool properties.
 */
public class ThreadPoolTaskExecutorWrapper extends ThreadPoolTaskExecutor {

    private static final Logger logger = LogManager.getLogger(ThreadPoolTaskExecutorWrapper.class);
    private static final long serialVersionUID = -2977068663355369141L;

    private int queueCapacity;

    private ThreadPoolTaskExecutorWrapper(String name, int corePoolSize, int maxPoolSize,
            int queueCapacity) {
        super();
        this.setMaxPoolSize(maxPoolSize);
        this.setCorePoolSize(corePoolSize);
        this.setQueueCapacity(queueCapacity);
        this.queueCapacity = queueCapacity;
        logger.info(name +
                    " core:" + getCorePoolSize() +
                    " max:" + getMaxPoolSize() +
                    " capacity:" + queueCapacity);
    }

    @Autowired
    public ThreadPoolTaskExecutorWrapper(Environment env, String name, String propertyKeyPrefix) {
        this(name,
             CueUtil.getIntProperty(env, propertyKeyPrefix, "core_pool_size"),
             CueUtil.getIntProperty(env, propertyKeyPrefix, "max_pool_size"),
             CueUtil.getIntProperty(env, propertyKeyPrefix, "queue_capacity"));
    }

    public int getQueueCapacity() {
        return queueCapacity;
    }
}
