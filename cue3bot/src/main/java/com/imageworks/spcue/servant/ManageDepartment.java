
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



package com.imageworks.spcue.servant;

import com.imageworks.spcue.grpc.department.*;
import com.imageworks.spcue.grpc.task.Task;
import com.imageworks.spcue.grpc.task.TaskSeq;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.DepartmentManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import io.grpc.stub.StreamObserver;

import java.util.List;
import java.util.Map;

public class ManageDepartment extends DepartmentInterfaceGrpc.DepartmentInterfaceImplBase {

    private AdminManager adminManager;
    private DepartmentManager departmentManager;
    private Whiteboard whiteboard;

    private TaskSeq.Builder addTasksToDepartment(Map<String, Integer> tmap, PointDetail deptConfig) {
        TaskSeq.Builder builder = TaskSeq.newBuilder();
        for (Map.Entry<String, Integer> e: tmap.entrySet()) {
            TaskEntity t = new TaskEntity(deptConfig, e.getKey(), e.getValue());
            departmentManager.createTask(t);
            builder.addTasks(toTask(t));
        }
        return builder;
    }

    @Override
    public void addDepartmentName(DeptAddDeptNameRequest request, StreamObserver<DeptAddDeptNameResponse> responseObserver) {
        adminManager.createDepartment(request.getName());
        responseObserver.onNext(DeptAddDeptNameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void addTask(DeptAddTaskRequest request, StreamObserver<DeptAddTaskResponse> responseObserver) {
        TaskEntity t = new TaskEntity(
                departmentManager.getDepartmentConfigDetail(request.getDepartment().getId()),
                        request.getShot(), Convert.coresToCoreUnits(request.getMinCores()));
        departmentManager.createTask(t);
        Task createdTask = toTask(t);
        responseObserver.onNext(DeptAddTaskResponse.newBuilder().setTask(createdTask).build());
        responseObserver.onCompleted();
    }

    @Override
    public void addTasks(DeptAddTasksRequest request, StreamObserver<DeptAddTasksResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        TaskSeq.Builder builder = addTasksToDepartment(request.getTmapMap(), deptConfig);
        responseObserver.onNext(DeptAddTasksResponse.newBuilder().setTasks(builder.build()).build());
        responseObserver.onCompleted();
    }

    @Override
    public void clearTasks(DeptClearTasksRequest request, StreamObserver<DeptClearTasksResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        departmentManager.clearTasks(deptConfig);
        responseObserver.onNext(DeptClearTasksResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void clearTaskAdjustments(DeptClearTaskAdjustmentsRequest request,
                                     StreamObserver<DeptClearTaskAdjustmentsResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        departmentManager.clearTaskAdjustments(deptConfig);
        responseObserver.onNext(DeptClearTaskAdjustmentsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void disableTiManaged(DeptDisableTiManagedRequest request,
                                 StreamObserver<DeptDisableTiManagedResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        departmentManager.disableTiManaged(deptConfig);
        responseObserver.onNext(DeptDisableTiManagedResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void enableTiManaged(DeptEnableTiManagedRequest request,
                                StreamObserver<DeptEnableTiManagedResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        departmentManager.enableTiManaged(deptConfig, request.getTiTask(),
                Convert.coresToWholeCoreUnits(request.getManagedCores()));
        responseObserver.onNext(DeptEnableTiManagedResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getDepartmentNames(DeptGetDepartmentNamesRequest request,
                                   StreamObserver<DeptGetDepartmentNamesResponse> responseObserver) {
        responseObserver.onNext(DeptGetDepartmentNamesResponse.newBuilder()
                .addAllNames(whiteboard.getDepartmentNames())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getTasks(DeptGetTasksRequest request, StreamObserver<DeptGetTasksResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        List<Task> tasks = whiteboard.getTasks(deptConfig, deptConfig);
        TaskSeq taskSeq = TaskSeq.newBuilder().addAllTasks(tasks).build();
        responseObserver.onNext(DeptGetTasksResponse.newBuilder().setTasks(taskSeq).build());
        responseObserver.onCompleted();
    }

    @Override
    public void removeDepartmentName(DeptRemoveDepartmentNameRequest request,
                                     StreamObserver<DeptRemoveDepartmentNameResponse> responseObserver) {
        adminManager.removeDepartment(adminManager.findDepartment(request.getName()));
        responseObserver.onNext(DeptRemoveDepartmentNameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void replaceTasks(DeptReplaceTaskRequest request, StreamObserver<DeptReplaceTaskResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        departmentManager.clearTasks(deptConfig);
        TaskSeq.Builder builder = addTasksToDepartment(request.getTmapMap(), deptConfig);
        responseObserver.onNext(DeptReplaceTaskResponse.newBuilder().setTasks(builder.build()).build());
        responseObserver.onCompleted();
    }

    public void setManagedCores(DeptSetManagedCoresRequest request,
                                StreamObserver<DeptSetManagedCoresResponse> responseObserver) {
        PointDetail deptConfig = departmentManager.getDepartmentConfigDetail(request.getDepartment().getId());
        departmentManager.setManagedCores(deptConfig,
                Convert.coresToWholeCoreUnits(request.getManagedCores()));
        responseObserver.onNext(DeptSetManagedCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    private Task toTask(TaskEntity detail) {
        return Task.newBuilder()
                .setId(detail.id)
                .setName(detail.name)
                .setShot(detail.shot)
                .setDept(detail.deptId)
                .setMinCores(detail.minCoreUnits)
                .setPointId(detail.pointId)
                .build();
    }
}

