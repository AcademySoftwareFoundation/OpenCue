
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.test.dao.criteria;

import java.util.List;
import java.util.stream.Collectors;
import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.HostSearchFactory;
import com.imageworks.spcue.dao.criteria.HostSearchInterface;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;
import com.imageworks.spcue.grpc.host.NimbyFilter;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class HostSearchTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    HostSearchFactory hostSearchFactory;

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

    @Resource
    WhiteboardDao whiteboardDao;

    @Resource
    HostDao hostDao;

    private AllocationEntity createAlloc(FacilityInterface facility, String allocName) {
        AllocationEntity alloc = new AllocationEntity();
        alloc.name = allocName;
        alloc.tag = "test-tag";
        adminManager.createAllocation(facility, alloc);
        return alloc;
    }

    private DispatchHost createHost(AllocationEntity alloc, String hostName) {
        return createHost(alloc, hostName, false);
    }

    private DispatchHost createHost(AllocationEntity alloc, String hostName, boolean nimby) {
        DispatchHost host = hostManager.createHost(RenderHost.newBuilder().setName(hostName)
                .setTotalMem(50000000).setNimbyEnabled(nimby).build());
        hostManager.setAllocation(host, alloc);
        return host;
    }

    private List<String> findHostNames(String allocName, NimbyFilter nimby) {
        HostSearchCriteria criteria =
                HostSearchCriteria.newBuilder().addAllocs(allocName).setNimby(nimby).build();
        return hostDao.findHosts(hostSearchFactory.create(criteria)).stream()
                .map(HostEntity::getName).collect(Collectors.toList());
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
        HostSearchInterface hostSearch =
                hostSearchFactory.create(HostSearchInterface.criteriaFactory());
        hostSearch.filterByAlloc(alloc1);

        List<Host> hosts = whiteboardDao.getHosts(hostSearch).getHostsList();

        assertThat(hosts.stream().map(Host::getId).collect(Collectors.toList()))
                .containsOnly(expectedHost.getHostId());
    }

    @Test
    public void testNimbyFilterWhereClause() {
        assertEquals("",
                hostSearchFactory.create(HostSearchInterface.criteriaFactory()).getWhereClause());

        HostSearchInterface nimbyOnly = hostSearchFactory
                .create(HostSearchCriteria.newBuilder().setNimby(NimbyFilter.NIMBY_ONLY).build());
        assertEquals("host.b_nimby = ?", nimbyOnly.getWhereClause());
        assertThat(nimbyOnly.getValues()).containsExactly(true);

        HostSearchInterface nimbyExclude = hostSearchFactory.create(
                HostSearchCriteria.newBuilder().setNimby(NimbyFilter.NIMBY_EXCLUDE).build());
        assertEquals("host.b_nimby = ?", nimbyExclude.getWhereClause());
        assertThat(nimbyExclude.getValues()).containsExactly(false);
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByNimby() {
        FacilityInterface facility = adminManager.createFacility("test-facility");
        AllocationEntity alloc = createAlloc(facility, "test-alloc-01");
        createHost(alloc, "test-workstation-01", true);
        createHost(alloc, "test-render-01", false);
        String allocName = alloc.getName();

        assertThat(findHostNames(allocName, NimbyFilter.NIMBY_ONLY))
                .containsOnly("test-workstation-01");
        assertThat(findHostNames(allocName, NimbyFilter.NIMBY_EXCLUDE))
                .containsOnly("test-render-01");
        assertThat(findHostNames(allocName, NimbyFilter.NIMBY_ANY))
                .containsOnly("test-workstation-01", "test-render-01");
    }
}
