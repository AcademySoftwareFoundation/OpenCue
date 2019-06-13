
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



package com.imageworks.spcue.test.dispatcher;

import com.google.common.collect.ImmutableList;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.util.CueUtil;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class TestBookingQueue extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    HostDao hostDao;

    @Autowired
    Dispatcher dispatcher;

    @Autowired
    HostManager hostManager;

    private static final String HOSTNAME = "beta";

    @Before
    public void create() {
        RenderHost host = RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(1)
                .setCoresPerProc(100)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .addAllTags(ImmutableList.of("mcore", "4core", "8g"))
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();

        hostManager.createHost(host);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testBookingQueue() {

        DispatchHost host1 = hostDao.findDispatchHost(HOSTNAME);
        host1.idleCores = 500;
        DispatchHost host2 = hostDao.findDispatchHost(HOSTNAME);
        DispatchHost host3 = hostDao.findDispatchHost(HOSTNAME);
        BookingQueue queue = new BookingQueue(1000);

        queue.execute(new DispatchBookHost(host2,dispatcher));
        queue.execute(new DispatchBookHost(host3,dispatcher));
        queue.execute(new DispatchBookHost(host1,dispatcher));
        try {
            Thread.sleep(10000);
        } catch (InterruptedException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }

    }




}

