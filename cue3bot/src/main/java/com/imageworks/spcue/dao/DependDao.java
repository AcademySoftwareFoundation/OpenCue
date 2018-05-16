
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



package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.Frame;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.CueIce.DependTarget;
import com.imageworks.spcue.depend.*;
import com.imageworks.spcue.LightweightDependency;

/**
 * DAO class for managing dependencies
 *
 * @category DAO
 */
public interface DependDao {

    /**
     * Returns a LightweightDependency from its ID
     *
     * @param id
     * @return LightweightDependency
     */
    LightweightDependency getDepend(String id);

    /**
     * Returns a LightweightDependency from its ID
     *
     * @param signature
     * @return LightweightDependency
     */
    LightweightDependency getDependBySignature(String s);

    /**
     * Gets a list of LightweightDependenies that depend on
     * the specified job
     *
     * @param job
     * @return List<LightweightDependency>
     */
    List<LightweightDependency> getWhatDependsOn(Job job);

    /**
     * Get a list of LightweightDependenies that depend on this job
     * and are either intenral, external, or either.
     * The depends returned can depend on any part of the job.
     *
     * @param job
     * @param target
     * @return
     */
    List<LightweightDependency> getWhatDependsOn(Job job, DependTarget target);

    /**
     * Gets a list of LightweightDependencies that depend on
     * the specified layer
     *
     * @param job
     * @param layer
     * @return List<LightweightDependency>
     */
    List<LightweightDependency> getWhatDependsOn(Layer layer);

    /**
     * Gets a list of LightweightDependencies that depend on
     * the specified frame
     *
     * @param frame
     * @return
     */
    List<LightweightDependency> getWhatDependsOn(Frame frame);

    /**
     * Deletes a dependency
     *
     * @param depend
     */
    void deleteDepend(LightweightDependency depend);

    /**
     * Returns a list of depends where the specified job is the depender.  Passing a
     * depend target will limit the results to either internal or external. This
     * method returns active depends only.
     *
     * @param Job
     * @param DependTarget
     * @return  List<LightweightDependency>
     */
    List<LightweightDependency> getWhatThisDependsOn(Job job, DependTarget target);

    /**
     * Returns a list of depends the layer depends on.  Passing in a depend
     * target will limit the results to either internal, external or both.
     * This method returns active depends only.
     *
     * @param Layer
     * @return List<LightweightDependency>
     */
    List<LightweightDependency> getWhatThisDependsOn(Layer layer, DependTarget target);

    /**
     * Returns a list of depends the frame depends on.  Passing in a depend
     * target will limit the results to either inernal, external, or both.This
     * method returns active depends only.
     *
     * @param Frame
     * @return List<LightweightDependency>
     */
    List<LightweightDependency> getWhatThisDependsOn(Frame frame, DependTarget target);

    /**
     * Returns a list of dependencies where the supplied frame is the element
     * being depended on.
     *
     * @param frame
     * @param active
     * @return
     */
    List<LightweightDependency> getWhatDependsOn(Frame frame, boolean active);


    /**
     *
     * @param layer
     * @param active
     * @return
     */
    List<LightweightDependency> getWhatDependsOn(Layer layer, boolean active);

    /**
     * Returns a list of child FrameByFrame dependencies
     *
     * @param depend
     * @return
     */
    List<LightweightDependency> getChildDepends(LightweightDependency depend);

    void insertDepend(JobOnJob d);

    void insertDepend(JobOnLayer d);

    void insertDepend(JobOnFrame d);

    void insertDepend(LayerOnJob d);

    void insertDepend(LayerOnLayer d);

    void insertDepend(LayerOnFrame d);

    void insertDepend(FrameOnJob d);

    void insertDepend(FrameOnLayer d);

    void insertDepend(FrameByFrame d);

    void insertDepend(FrameOnFrame d);

    void insertDepend(PreviousFrame d);

    void updateFrameState(Frame f);

    /**
     * Increment the depend count for the specified frame.
     *
     * @param f
     * @throws DependException if the depend count was not
     * incremented.
     */
    void incrementDependCount(Frame f);

    /**
     * Decrement the depend count for the specified frame.
     * Return false if the depend count is already 0, true
     * if the depend count was decremented.
     *
     * @param f
     */
    boolean decrementDependCount(Frame f);

    /**
     * Returns true if this is the thread that set
     * the depend to inactive.
     *
     * @param depend
     * @return
     */
    boolean setInactive(LightweightDependency depend);

    /**
     * Sets a dependency as active.  If the dependency is
     * already active return false, otherwise return true.
     * Currently this only works on FrameOnFrame and LayerOnLayer.
     *
     * @param depend
     * @return true if this thread actually updated the row.
     */
    boolean setActive(LightweightDependency depend);
}

