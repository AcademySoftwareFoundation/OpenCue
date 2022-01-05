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



package com.imageworks.spcue.test.dispatcher;

import java.util.concurrent.ThreadPoolExecutor;
import javax.annotation.Resource;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.HostReportQueue;
import com.imageworks.spcue.dispatcher.ThreadPoolTaskExecutorWrapper;

import org.junit.Test;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;

import static org.junit.Assert.assertEquals;

@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class ThreadPoolTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    ThreadPoolTaskExecutor launchQueue;

    @Resource
    ThreadPoolTaskExecutor dispatchPool;

    @Resource
    ThreadPoolTaskExecutor managePool;

    @Resource
    ThreadPoolExecutor reportQueue;

    @Resource
    ThreadPoolExecutor killQueue;

    @Resource
    BookingQueue bookingQueue;

    private int getQueueCapacity(ThreadPoolTaskExecutor t) {
        return ((ThreadPoolTaskExecutorWrapper) t).getQueueCapacity();
    }

    private int getQueueCapacity(ThreadPoolExecutor t) {
        return ((HostReportQueue) t).getQueueCapacity();
    }

    @Test
    public void testPropertyValues() {
        assertEquals(1, launchQueue.getCorePoolSize());
        assertEquals(1, launchQueue.getMaxPoolSize());
        assertEquals(100, getQueueCapacity(launchQueue));

        assertEquals(4, dispatchPool.getCorePoolSize());
        assertEquals(4, dispatchPool.getMaxPoolSize());
        assertEquals(500, getQueueCapacity(dispatchPool));

        assertEquals(8, managePool.getCorePoolSize());
        assertEquals(8, managePool.getMaxPoolSize());
        assertEquals(250, getQueueCapacity(managePool));

        assertEquals(6, reportQueue.getCorePoolSize());
        assertEquals(8, reportQueue.getMaximumPoolSize());
        assertEquals(1000, getQueueCapacity(reportQueue));

        assertEquals(6, killQueue.getCorePoolSize());
        assertEquals(8, killQueue.getMaximumPoolSize());
        assertEquals(1000, getQueueCapacity(killQueue));

        assertEquals(6, bookingQueue.getCorePoolSize());
        assertEquals(6, bookingQueue.getMaximumPoolSize());
        assertEquals(1000, bookingQueue.getQueueCapacity());
    }
}

