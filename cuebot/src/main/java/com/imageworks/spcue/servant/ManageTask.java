
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

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.grpc.task.Task;
import com.imageworks.spcue.grpc.task.TaskClearAdjustmentsRequest;
import com.imageworks.spcue.grpc.task.TaskClearAdjustmentsResponse;
import com.imageworks.spcue.grpc.task.TaskDeleteRequest;
import com.imageworks.spcue.grpc.task.TaskDeleteResponse;
import com.imageworks.spcue.grpc.task.TaskInterfaceGrpc;
import com.imageworks.spcue.grpc.task.TaskSetMinCoresRequest;
import com.imageworks.spcue.grpc.task.TaskSetMinCoresResponse;
import com.imageworks.spcue.service.DepartmentManager;
import com.imageworks.spcue.util.Convert;

public class ManageTask extends TaskInterfaceGrpc.TaskInterfaceImplBase {

    private DepartmentManager departmentManager;

    @Override
    public void delete(TaskDeleteRequest request,
            StreamObserver<TaskDeleteResponse> responseObserver) {
        departmentManager.removeTask(getTaskDetail(request.getTask()));
        TaskDeleteResponse response = TaskDeleteResponse.newBuilder().build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void setMinCores(TaskSetMinCoresRequest request,
            StreamObserver<TaskSetMinCoresResponse> responseObserver) {
        departmentManager.setMinCores(getTaskDetail(request.getTask()),
                Convert.coresToWholeCoreUnits(request.getNewMinCores()));
        TaskSetMinCoresResponse response = TaskSetMinCoresResponse.newBuilder().build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void clearAdjustments(TaskClearAdjustmentsRequest request,
            StreamObserver<TaskClearAdjustmentsResponse> responseObserver) {
        departmentManager.clearTaskAdjustment(getTaskDetail(request.getTask()));
        TaskClearAdjustmentsResponse response = TaskClearAdjustmentsResponse.newBuilder().build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }

    private TaskEntity getTaskDetail(Task task) {
        return departmentManager.getTaskDetail(task.getName());
    }
}
