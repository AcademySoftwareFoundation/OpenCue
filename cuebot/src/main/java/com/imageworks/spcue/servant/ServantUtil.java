
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

package com.imageworks.spcue.servant;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerSeq;
import com.imageworks.spcue.service.JobManager;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.springframework.core.env.Environment;

public class ServantUtil {

    public static List<LayerInterface> convertLayerFilterList(LayerSeq layers) {
        final List<LayerInterface> result = new ArrayList<LayerInterface>();
        for (final Layer layer : layers.getLayersList()) {
            final String id = layer.getId();
            result.add(new LayerInterface() {
                String _id = id;

                public String getLayerId() {
                    return _id;
                }

                public String getJobId() {
                    throw new RuntimeException("not implemented");
                }

                public String getShowId() {
                    throw new RuntimeException("not implemented");
                }

                public String getId() {
                    return _id;
                }

                public String getName() {
                    throw new RuntimeException("not implemented");
                }

                public String getFacilityId() {
                    throw new RuntimeException("not implemented");
                }
            });
        }
        return result;
    }

    private static boolean isJobFinished(Environment env, String property, JobManager jobManager,
            JobInterface job) {
        if (env.getProperty(property, String.class) != null
                && Objects.equals(env.getProperty(property, String.class), "true")) {
            JobDetail jobDetail = jobManager.getJobDetail(job.getJobId());
            return jobDetail.state == JobState.FINISHED;
        }
        return false;
    }

    public static <T> boolean attemptChange(Environment env, String property, JobManager jobManager,
            JobInterface job, StreamObserver<T> responseObserver) {
        if (ServantUtil.isJobFinished(env, property, jobManager, job)) {
            responseObserver.onError(Status.FAILED_PRECONDITION
                    .withDescription("Finished jobs are readonly").asRuntimeException());
            return false;
        }
        return true;
    }
}
