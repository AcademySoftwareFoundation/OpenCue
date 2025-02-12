
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

package com.imageworks.spcue.depend;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.util.SqlUtil;

public class FrameOnJob extends AbstractDepend implements Depend {

    private final FrameInterface dependErFrame;
    private final JobInterface dependOnJob;

    public FrameOnJob(FrameInterface dependErFrame, JobInterface dependOnJob) {

        if (dependErFrame.getJobId().equals(dependOnJob.getJobId())) {
            throw new DependException("A frame cannot depend on its own job.");
        }

        this.dependErFrame = dependErFrame;
        this.dependOnJob = dependOnJob;
    }

    public FrameInterface getDependErFrame() {
        return dependErFrame;
    }

    public JobInterface getDependOnJob() {
        return dependOnJob;
    }

    @Override
    public String getSignature() {
        StringBuilder key = new StringBuilder(256);
        key.append(DependType.FRAME_BY_FRAME.toString());
        key.append(dependErFrame.getFrameId());
        key.append(dependOnJob.getJobId());
        return SqlUtil.genKeyByName(key.toString());
    }

    @Override
    public void accept(DependVisitor dependVisitor) {
        dependVisitor.accept(this);
    }

    @Override
    public DependTarget getTarget() {
        return DependTarget.EXTERNAL;
    }
}
