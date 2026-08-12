
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

import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.grpc.job.LayerSetStartAfterRequest;
import com.imageworks.spcue.grpc.job.LayerSetStartAfterResponse;
import com.imageworks.spcue.servant.ManageLayer;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;

/**
 * setStartAfter input validation rejects out-of-range timestamps before touching the layer, so
 * these tests run against an unwired servant with no database.
 */
public class ManageLayerStartAfterValidationTests {

    private static class CapturingObserver<T> implements StreamObserver<T> {
        Throwable error;
        boolean completed;

        @Override
        public void onNext(T value) {}

        @Override
        public void onError(Throwable t) {
            error = t;
        }

        @Override
        public void onCompleted() {
            completed = true;
        }
    }

    private CapturingObserver<LayerSetStartAfterResponse> setStartAfter(long startAfter) {
        CapturingObserver<LayerSetStartAfterResponse> observer = new CapturingObserver<>();
        new ManageLayer().setStartAfter(
                LayerSetStartAfterRequest.newBuilder().setStartAfter(startAfter).build(), observer);
        return observer;
    }

    @Test
    public void testRejectsMillisecondTimestamp() {
        // The realistic client mistake: milliseconds where seconds are expected.
        CapturingObserver<LayerSetStartAfterResponse> observer =
                setStartAfter(System.currentTimeMillis());
        assertNotNull(observer.error);
        assertEquals(Status.Code.INVALID_ARGUMENT, Status.fromThrowable(observer.error).getCode());
        assertFalse(observer.completed);
    }

    @Test
    public void testRejectsNegativeTimestamp() {
        CapturingObserver<LayerSetStartAfterResponse> observer = setStartAfter(-1L);
        assertNotNull(observer.error);
        assertEquals(Status.Code.INVALID_ARGUMENT, Status.fromThrowable(observer.error).getCode());
        assertFalse(observer.completed);
    }

    @Test
    public void testRejectsValueThatWouldOverflowMultiplication() {
        CapturingObserver<LayerSetStartAfterResponse> observer = setStartAfter(Long.MAX_VALUE);
        assertNotNull(observer.error);
        assertEquals(Status.Code.INVALID_ARGUMENT, Status.fromThrowable(observer.error).getCode());
        assertFalse(observer.completed);
    }
}
