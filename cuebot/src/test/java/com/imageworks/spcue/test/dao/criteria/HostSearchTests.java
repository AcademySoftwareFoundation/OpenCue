
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

package com.imageworks.spcue.test.dao.criteria;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.HostSearchFactory;
import com.imageworks.spcue.dao.criteria.HostSearchInterface;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class HostSearchTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    HostSearchFactory hostSearchFactory;

    @Autowired
    AdminManager adminManager;

    @Autowired
    HostManager hostManager;

    @Autowired
    WhiteboardDao whiteboardDao;

    private AllocationEntity createAlloc(FacilityInterface facility, String allocName) {
        AllocationEntity alloc = new AllocationEntity();
        alloc.name = allocName;
        alloc.tag = "test-tag";
        adminManager.createAllocation(facility, alloc);
        return alloc;
    }

    private DispatchHost createHost(AllocationEntity alloc, String hostName) {
        DispatchHost host = hostManager.createHost(
                RenderHost.newBuilder()
                        .setName(hostName)
                        .setTotalMem(50000000)
                        .build());
        hostManager.setAllocation(host, alloc);
        return host;
    }

    @Test
    @Transactional
    @Rollback
    public void testGetCriteria() {
        HostSearchCriteria criteria = HostSearchInterface.criteriaFactory();

        HostSearchInterface hostSearch = hostSearchFactory.create(criteria);

        assertEquals(criteria, hostSearch.getCriteria());
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByAlloc() {
        FacilityInterface facility = adminManager.createFacility("test-facility");
        AllocationEntity alloc1 = createAlloc(facility, "test-alloc-01");
        AllocationEntity alloc2 = createAlloc(facility, "test-alloc-02");
        DispatchHost expectedHost = createHost(alloc1, "test-host-01");
        createHost(alloc2, "test-host-02");
        HostSearchInterface hostSearch = hostSearchFactory.create(
                HostSearchInterface.criteriaFactory());
        hostSearch.filterByAlloc(alloc1);

        List<Host> hosts = whiteboardDao.getHosts(hostSearch).getHostsList();

        assertThat(
                hosts.stream().map(Host::getId).collect(Collectors.toList()))
                .containsOnly(expectedHost.getHostId());
    }
}
