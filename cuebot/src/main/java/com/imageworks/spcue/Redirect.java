
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

package com.imageworks.spcue;

import java.io.Serializable;
import java.util.concurrent.TimeUnit;

import com.imageworks.spcue.grpc.host.RedirectType;
import com.imageworks.spcue.util.SqlUtil;

/**
 * A Redirect contains the new destination for a proc. The destination type may be a job or a group.
 */
public class Redirect implements Serializable {

    private static final long serialVersionUID = -6461503320817105280L;

    /**
     * Track requests to redirect multiple procs together by assigning a group id.
     */
    private final String groupId;
    private final RedirectType type;
    private final String destinationId;
    private final String name;
    private final long creationTime;

    public static final long EXPIRE_TIME = TimeUnit.MILLISECONDS.convert(24, TimeUnit.HOURS);

    public Redirect(String groupId, RedirectType type, String destinationId, String name,
            long creationTime) {
        this.groupId = groupId;
        this.type = type;
        this.destinationId = destinationId;
        this.name = name;
        this.creationTime = creationTime;
    }

    public Redirect(RedirectType type, String destinationId, String name) {
        this.groupId = SqlUtil.genKeyRandom();
        this.type = type;
        this.destinationId = destinationId;
        this.name = name;
        this.creationTime = System.currentTimeMillis();
    }

    public Redirect(String groupId, JobInterface job) {
        this.groupId = groupId;
        this.type = RedirectType.JOB_REDIRECT;
        this.destinationId = job.getJobId();
        this.name = job.getName();
        this.creationTime = System.currentTimeMillis();
    }

    public Redirect(JobInterface job) {
        this.groupId = SqlUtil.genKeyRandom();
        this.type = RedirectType.JOB_REDIRECT;
        this.destinationId = job.getJobId();
        this.name = job.getName();
        this.creationTime = System.currentTimeMillis();
    }

    public Redirect(GroupInterface group) {
        this.groupId = SqlUtil.genKeyRandom();
        this.type = RedirectType.GROUP_REDIRECT;
        this.destinationId = group.getGroupId();
        this.name = group.getName();
        this.creationTime = System.currentTimeMillis();
    }

    public String getGroupId() {
        return groupId;
    }

    public RedirectType getType() {
        return type;
    }

    public String getDestinationId() {
        return destinationId;
    }

    public String getDestinationName() {
        return name;
    }

    public boolean isExpired() {
        return System.currentTimeMillis() - creationTime >= EXPIRE_TIME;
    }

    public long getCreationTime() {
        return creationTime;
    }
}
