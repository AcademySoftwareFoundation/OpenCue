
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
import java.util.Map;
import java.util.Set;

import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.ThreadStats;
import com.imageworks.spcue.CueIce.LayerType;

public interface LayerDao {

    /**
     *
     * @param layer
     * @return
     */
    public ExecutionSummary getExecutionSummary(Layer layer);

    /**
     * return the frame state totals for the specified layer
     *
     * @param layer
     * @return
     */
    public FrameStateTotals getFrameStateTotals(Layer layer);

    /**
     * returns a list of layers by job
     *
     * @param job
     * @return
     */
    public List<LayerDetail> getLayerDetails(Job job);

    /**
     * Returns true if supplied layer is compelte.
     *
     * @param layer
     * @return boolean
     */
    boolean isLayerComplete(Layer layer);

    /**
     * Returns true if supplied layer is dispatchable.
     *
     * @param l
     * @return boolean
     */
    boolean isLayerDispatchable(Layer l);

    /**
     * Inserts a LayerDetail
     *
     * @param l
     */
    void insertLayerDetail(LayerDetail l);

    /**
     * gets a layer detail from an object that implments layer
     *
     * @param layer
     * @return LayerDetail
     */
    LayerDetail getLayerDetail(Layer layer);

    /**
     * get layer detail from the the unique id
     *
     * @param id
     * @return
     */
    LayerDetail getLayerDetail(String id);

    /**
     * get a layer detail from the job and layer name
     *
     * @param job
     * @param name
     * @return
     */
    LayerDetail findLayerDetail(Job job, String name);

    /**
     * Get a minimal layer from the layer id
     *
     * @param id
     * @return
     */
    Layer getLayer(String id);

    /**
     * Find a minimal layer from the job and layer name
     *
     * @param job
     * @param name
     * @return
     */
    Layer findLayer(Job job, String name);

    /**
     * update the number of cores the layer requires
     *
     * @param layer
     * @param val
     */
    void updateLayerMinCores(Layer layer, int val);

    /**
     * update the amount of memory required by all subsequent
     * running frames in the specified layer.
     *
     * @param layer
     * @param val
     */
    void updateLayerMinMemory(Layer layer, long kb);

    /**
     * update the amount of gpu memory in kb required by all subsequent
     * running frames in the specified layer.
     *
     * @param layer
     * @param val
     */
    void updateLayerMinGpu(Layer layer, long gpu);

    /**
     * Update a layer with new host tags.
     *
     * @param layer
     * @param val
     */
    void updateLayerTags(Layer layer, Set<String> tags);

    /**
     * Insert a key/valye pair into the layer environment
     *
     * @param layer
     * @param key
     * @param value
     */
    void insertLayerEnvironment(Layer layer, String key, String value);

    /**
     * Insert a map key/value pairs into the layer environement
     *
     * @param layer
     * @param env
     */
    void insertLayerEnvironment(Layer layer, Map<String,String> env);

    /**
     * Get the layer environment map
     *
     * @param layer
     * @return
     */
    Map<String,String> getLayerEnvironment(Layer layer);

    /**
     * Updated the layers MaxRSS value.  If force is true then the
     * value is updated no matter what the current value is.  If force
     * is false, the value is only updated the val is greater than than
     * the existing value.
     *
     * @param layer
     * @param val
     */
    void updateLayerMaxRSS(Layer layer, long val, boolean force);

    /**
     * Increases the value of the minimum memory when the supplied
     * value is larger than the current value
     *
     * @param layer
     * @param val
     */
    void increaseLayerMinMemory(Layer layer, long val);

    /**
     * Increases the value of the minimum gpu when the supplied
     * value is larger than the current value
     *
     * @param layer
     * @param gpu
     */
    void increaseLayerMinGpu(Layer layer, long gpu);

    /**
     * Tries to find a max RSS value for layer in the specified job. The
     * layer must have at least 25% of its pending frames completed
     * for this to return a valid result.  If the layer cannot be
     * found then 0 is returned.
     *
     * @param job
     * @param name
     * @return
     */
    long findPastMaxRSS(Job job, String name);

    /**
     * Returns a list of layers from the specified job.
     *
     * @param job
     * @return
     */
    public List<Layer> getLayers(Job job);

    /**
     * Update all layers of the set type in specified job
     * with the new tags.
     *
     * @param job
     * @param tags
     * @param type
     */
    void updateTags(Job job, String tags, LayerType type);

    /**
     * Update all layers of the set type in the specified
     * job with the new memory requirement.
     *
     * @param job
     * @param mem
     * @param type
     */
    void updateMinMemory(Job job, long mem, LayerType type);

    /**
     * Update all layers of the set type in the specified
     * job with the new gpu requirement.
     *
     * @param job
     * @param gpu
     * @param type
     */
    void updateMinGpu(Job job, long gpu, LayerType type);

    /**
     * Update all layers of the set type in the specified job
     * with the new min cores requirement.
     *
     * @param job
     * @param cores
     * @param type
     */
    void updateMinCores(Job job, int cores, LayerType type);

    /**
     * Update a layer's max cores value, which limits how
     * much threading can go on.
     *
     * @param job
     * @param cores
     * @param type
     */
    void updateThreadable(Layer layer, boolean threadable);

    /**
     * Lowers the minimum memory on a layer if the layer
     * is using less memory and the currnet min memory is
     * the dispatcher default.
     *
     * @param layer
     * @param val
     * @return
     */
    boolean balanceLayerMinMemory(Layer layer, long val);

    /**
     * Appends a tag to the current set of tags.  If the tag
     * already exists than nothing happens.
     *
     * @param layer
     * @param val
     */
    void appendLayerTags(Layer layer, String val);

    /**
     * Returns true if the layer can be optimized to use
     * util based on the specified criteria.
     *
     * @param l
     * @param succeeded
     * @param avg
     * @return
     */
    boolean isOptimizable(Layer l, int succeeded, float avg);

    /**
     * Update layer usage with processor time usage.
     * This happens when the proc has completed or failed some work.
     *
     * @param proc
     * @param newState
     */
    void updateUsage(Layer layer, ResourceUsage usage, int exitStatus);

    /**
     * Returns true of the layer is launching.
     *
     * @param l
     * @return
     */
    boolean isLaunching(Layer l);

    /**
     * Return true if the application running in the given layer
     * is threadable.
     *
     * @param l
     * @return
     */
    boolean isThreadable(Layer l);

    /**
     * Enable/disable memory optimizer.
     */
    void enableMemoryOptimizer(Layer layer, boolean state);

    /**
     * Return a list of outputs mapped to the given layer.
     *
     * @param layer
     * @return
     */
    List<String> getLayerOutputs(Layer layer);

    /**
     * Add a list of filespecs to the given layer's output table.
     *
     * @param layer
     * @param specs
     */
    void insertLayerOutput(Layer layer, String spec);

    /**
     * Return the thread stats for the given layer.
     *
     * @param layer
     * @return
     */
    List<ThreadStats> getThreadStats(Layer layer);

    /**
     * Set the layer's max cores value to the given int.  The
     * max cores value will not allow the dispatcher to
     * book over the given number of cores.
     *
     * @param layer
     * @param val
     */
    void updateLayerMaxCores(Layer layer, int val);

}

