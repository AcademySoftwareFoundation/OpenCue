
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

package com.imageworks.spcue.service;

import java.util.List;

import com.imageworks.spcue.BuildableDependency;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.depend.FrameByFrame;
import com.imageworks.spcue.depend.FrameOnFrame;
import com.imageworks.spcue.depend.FrameOnJob;
import com.imageworks.spcue.depend.FrameOnLayer;
import com.imageworks.spcue.depend.JobOnFrame;
import com.imageworks.spcue.depend.JobOnJob;
import com.imageworks.spcue.depend.JobOnLayer;
import com.imageworks.spcue.depend.LayerOnFrame;
import com.imageworks.spcue.depend.LayerOnJob;
import com.imageworks.spcue.depend.LayerOnLayer;
import com.imageworks.spcue.depend.LayerOnSimFrame;
import com.imageworks.spcue.depend.PreviousFrame;
import com.imageworks.spcue.grpc.depend.DependTarget;

public interface DependManager {

    /**
     * This just calls createDepend(Dependency depend) with the result of
     * buildDepend(BuildableDependency depend). This is mainly for convenience.
     *
     * @param BuildableDependency depend
     */
    void createDepend(BuildableDependency depend);

    List<LightweightDependency> getWhatDependsOn(JobInterface job);

    List<LightweightDependency> getWhatDependsOn(JobInterface job, DependTarget target);

    /**
     * Return any dependencies that reference the given frame as the frame to depend on.
     *
     * @param frame
     * @param active To limit results to only active depends, set this to true. To limit results to
     *        only inactive depends, set this to false.
     * @return
     */
    List<LightweightDependency> getWhatDependsOn(FrameInterface frame, boolean active);

    List<LightweightDependency> getWhatDependsOn(FrameInterface frame);

    List<LightweightDependency> getWhatDependsOn(LayerInterface layer);

    /**
     * Return any dependencies that reference the given layer as the layer to depend on.
     *
     * @param layer
     * @param active To limit results to only active depends, set this to true. To limit results to
     *        only inactive depends, set this to false.
     * @return
     */
    List<LightweightDependency> getWhatDependsOn(LayerInterface layer, boolean active);

    LightweightDependency getDepend(String id);

    void satisfyDepend(LightweightDependency depend);

    /**
     * Returns a list of depends where the specified job is the depender. Passing a depend target
     * will limit the results to either internal or external. This method returns active depends
     * only.
     *
     * @param Job
     * @param DependTarget
     * @return List<LightweightDependency>
     */
    public List<LightweightDependency> getWhatThisDependsOn(JobInterface job, DependTarget target);

    /**
     * Returns a list of depends the layer depends on. Passing in a depend target will limit the
     * results to either internal, external or both. This method returns active depends only.
     *
     * @param Layer
     * @return List<LightweightDependency>
     */
    public List<LightweightDependency> getWhatThisDependsOn(LayerInterface layer,
            DependTarget target);

    /**
     * Returns a list of depends the frame depends on. Passing in a depend target will limit the
     * results to either internal, external, or both.This method returns active depends only.
     *
     * @param Frame
     * @return List<LightweightDependency>
     */
    public List<LightweightDependency> getWhatThisDependsOn(FrameInterface frame,
            DependTarget target);

    /**
     * Create a JobOnJob depend.
     *
     * @param depend
     */
    void createDepend(JobOnJob depend);

    /**
     * Create a JobOnLayer depend
     *
     * @param depend
     */
    void createDepend(JobOnLayer depend);

    /**
     * Create a JobOnFrame depend
     *
     * @param depend
     */
    void createDepend(JobOnFrame depend);

    /**
     * Create a LayerOnJob depend.
     *
     * @param depend
     */
    void createDepend(LayerOnJob depend);

    /**
     * Create a LayerOnLayer depend.
     *
     * @param depend
     */
    void createDepend(LayerOnLayer depend);

    /**
     * Create a LayerOnFrame depend.
     *
     * @param depend
     */
    void createDepend(LayerOnFrame depend);

    /**
     * Create a FrameOnJob depend.
     *
     * @param depend
     */
    void createDepend(FrameOnJob depend);

    /**
     * Create a FrameOnLayer depend.
     *
     * @param depend
     */
    void createDepend(FrameOnLayer depend);

    /**
     * Create a FrameOnFrame depend.
     *
     * @param depend
     */
    void createDepend(FrameOnFrame depend);

    /**
     * Create a FrameByFrame depend.
     *
     * @param depend
     */
    void createDepend(FrameByFrame depend);

    /**
     * Creates a previous frame dependency.
     *
     * @param depend
     */
    void createDepend(PreviousFrame depend);

    /**
     * Unsatisfy the specified dependency. Currently only works for FrameOnFrame depends.
     *
     * @param depend
     */
    void unsatisfyDepend(LightweightDependency depend);

    /**
     * Create a depend of type LayerOnSimFrame
     *
     * @param depend
     */
    void createDepend(LayerOnSimFrame depend);
}
