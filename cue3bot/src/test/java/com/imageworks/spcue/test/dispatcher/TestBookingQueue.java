
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

import java.util.ArrayList;
import java.util.HashMap;

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.BeforeTransaction;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.CueIce.HardwareState;
import com.imageworks.spcue.RqdIce.RenderHost;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.util.CueUtil;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class TestBookingQueue extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    HostDao hostDao;

    @Resource
    Dispatcher dispatcher;

    @Resource
    HostManager hostManager;

    private static final String HOSTNAME = "beta";

    @Before
    public void create() {

        RenderHost host = new RenderHost();
        host.name = HOSTNAME;
        host.bootTime = 1192369572;
        host.freeMcp = 76020;
        host.freeMem = 53500;
        host.freeSwap = 20760;
        host.load = 1;
        host.totalMcp = 195430;
        host.totalMem = 8173264;
        host.totalSwap = 20960;
        host.nimbyEnabled = false;
        host.numProcs = 1;
        host.coresPerProc = 100;
        host.tags = new ArrayList<String>();
        host.tags.add("mcore");
        host.tags.add("4core");
        host.tags.add("8g");
        host.state = HardwareState.Up;
        host.facility = "spi";
        host.attributes = new HashMap<String, String>();
        host.attributes.put("freeGpu", String.format("%d", CueUtil.MB512));
        host.attributes.put("totalGpu", String.format("%d", CueUtil.MB512));

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

