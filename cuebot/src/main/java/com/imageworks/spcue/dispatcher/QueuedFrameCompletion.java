
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

package com.imageworks.spcue.dispatcher;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;

/**
 * A frame completion report, fully resolved on the RQD report thread and queued for the scheduler's
 * batched flush at the next tick start (see {@link FrameCompleteHandler#flushCompletionBatch}).
 * Everything the flush needs is captured here so the batch never re-reads what the report thread
 * already loaded; in particular {@code frame.getVersion()} is the version observed at arrival,
 * which is what makes the batched stop update lose cleanly (0 rows) if a kill, eat or retry beat
 * the flush to the frame.
 */
public final class QueuedFrameCompletion {
    public final FrameCompleteReport report;
    public final VirtualProc proc;
    public final DispatchJob job;
    public final LayerDetail layer;
    public final FrameDetail frameDetail;
    public final DispatchFrame frame;
    public final FrameState newFrameState;
    public final int exitStatus;

    public QueuedFrameCompletion(FrameCompleteReport report, VirtualProc proc, DispatchJob job,
            LayerDetail layer, FrameDetail frameDetail, DispatchFrame frame,
            FrameState newFrameState, int exitStatus) {
        this.report = report;
        this.proc = proc;
        this.job = job;
        this.layer = layer;
        this.frameDetail = frameDetail;
        this.frame = frame;
        this.newFrameState = newFrameState;
        this.exitStatus = exitStatus;
    }
}
