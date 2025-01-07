
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

package com.imageworks.spcue.dispatcher.commands;

import java.util.List;

import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.service.GroupManager;

public class DispatchMoveJobs extends KeyRunnable {

    private GroupDetail group;
    private List<JobInterface> jobs;
    private GroupManager groupManager;

    public DispatchMoveJobs(GroupDetail group, List<JobInterface> jobs, GroupManager groupManager) {
        super("disp_move_jobs_" + group.getGroupId() + "_dept_" + group.getDepartmentId() + "_show_"
                + group.getShowId());
        this.group = group;
        this.jobs = jobs;
        this.groupManager = groupManager;
    }

    @Override
    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                for (JobInterface job : jobs) {
                    groupManager.reparentJob(job, group, new Inherit[] {Inherit.All});
                }
            }
        }.execute();
    }
}
