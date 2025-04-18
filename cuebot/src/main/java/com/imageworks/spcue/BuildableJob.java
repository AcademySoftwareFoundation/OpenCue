
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

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * A buildable job represents a job stored in the job spec XML file.
 *
 * @category Job Launching
 */
public class BuildableJob {

    /**
     * Struct for the job detail, used for adding job to DB.
     */
    public JobDetail detail;

    /**
     * Maximum CPU cores and GPU units overrides.
     */
    public Integer maxCoresOverride = null;
    public Integer maxGpusOverride = null;

    /**
     * List of layers
     */
    private List<BuildableLayer> layers = new ArrayList<BuildableLayer>();

    private BuildableJob postJob = null;

    /**
     * Stores the local core assignment if one was launched with the job.
     */
    private LocalHostAssignment runLocalConf = null;

    /**
     * Job specific environment variables
     */
    public Map<String, String> env = new HashMap<String, String>();

    public BuildableJob() {}

    public BuildableJob(JobDetail detail) {
        this.detail = detail;
    }

    /**
     * Add a layer to the job
     *
     * @param layer
     */
    public void addBuildableLayer(BuildableLayer layer) {
        layers.add(layer);
    }

    /**
     * Add a key/value pair environment var to job
     *
     * @param key
     * @param value
     */
    public void addEnvironmentVariable(String key, String value) {
        env.put(key, value);
    }

    public List<BuildableLayer> getBuildableLayers() {
        return layers;
    }

    public void setPostJob(BuildableJob job) {
        this.postJob = job;
    }

    public BuildableJob getPostJob() {
        return this.postJob;
    }

    public void setRunLocalConf(LocalHostAssignment runLocalConf) {
        this.runLocalConf = runLocalConf;
    }

    public LocalHostAssignment getRunLocalConf() {
        return this.runLocalConf;
    }
}
