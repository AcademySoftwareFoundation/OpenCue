
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

package com.imageworks.spcue.test.servant;

import javax.annotation.Resource;

import io.grpc.stub.StreamObserver;

import org.junit.Test;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.grpc.facility.AllocCreateRequest;
import com.imageworks.spcue.grpc.facility.AllocCreateResponse;
import com.imageworks.spcue.grpc.facility.AllocDeleteRequest;
import com.imageworks.spcue.grpc.facility.AllocDeleteResponse;
import com.imageworks.spcue.grpc.facility.AllocSetDefaultRequest;
import com.imageworks.spcue.grpc.facility.AllocSetDefaultResponse;
import com.imageworks.spcue.grpc.facility.Allocation;
import com.imageworks.spcue.grpc.facility.Facility;
import com.imageworks.spcue.servant.ManageAllocation;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class ManageAllocationTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    AllocationDao allocationDao;

    @Resource
    FacilityDao facilityDao;

    @Resource
    ManageAllocation manageAllocation;

    @Test
    @Transactional
    @Rollback(true)
    public void testCreate() {
        Facility facility =
                Facility.newBuilder().setName(facilityDao.getFacility("spi").getName()).build();

        // Use <facility>.<tag> name
        AllocCreateRequest request = AllocCreateRequest.newBuilder().setName("spi.test_tag")
                .setTag("test_tag").setFacility(facility).build();

        FakeStreamObserver<AllocCreateResponse> responseObserver =
                new FakeStreamObserver<AllocCreateResponse>();
        manageAllocation.create(request, responseObserver);

        allocationDao.findAllocationEntity("spi", "test_tag");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDelete() {
        Facility facility =
                Facility.newBuilder().setName(facilityDao.getFacility("spi").getName()).build();

        // Non <facility>.<tag> name should work too.
        AllocCreateRequest createRequest = AllocCreateRequest.newBuilder().setName("test_tag")
                .setTag("test_tag").setFacility(facility).build();

        FakeStreamObserver<AllocCreateResponse> createResponseObserver =
                new FakeStreamObserver<AllocCreateResponse>();
        manageAllocation.create(createRequest, createResponseObserver);

        Allocation allocation = Allocation.newBuilder().setName("spi.test_tag").setTag("test_tag")
                .setFacility("spi").build();

        AllocDeleteRequest deleteRequest =
                AllocDeleteRequest.newBuilder().setAllocation(allocation).build();

        FakeStreamObserver<AllocDeleteResponse> deleteResponseObserver =
                new FakeStreamObserver<AllocDeleteResponse>();

        manageAllocation.delete(deleteRequest, deleteResponseObserver);

        try {
            allocationDao.findAllocationEntity("spi", "test_tag");
            fail("Expected exception");
        } catch (EmptyResultDataAccessException e) {
            assertEquals(e.getMessage(), "Incorrect result size: expected 1, actual 0");
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetDefault() {
        AllocationEntity alloc = allocationDao.getDefaultAllocationEntity();
        assertEquals(alloc.getName(), "lax.unassigned");

        Allocation allocation = Allocation.newBuilder().setName("spi.general").setTag("general")
                .setFacility("spi").build();
        AllocSetDefaultRequest request =
                AllocSetDefaultRequest.newBuilder().setAllocation(allocation).build();

        FakeStreamObserver<AllocSetDefaultResponse> observer =
                new FakeStreamObserver<AllocSetDefaultResponse>();
        manageAllocation.setDefault(request, observer);

        alloc = allocationDao.getDefaultAllocationEntity();
        assertEquals(alloc.getName(), "spi.general");
    }
}
