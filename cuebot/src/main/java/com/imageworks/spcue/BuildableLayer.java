
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

import java.util.HashMap;
import java.util.Map;

/**
 * A buildable layer represents a layer stored in the job spec XML file.
 *
 * @category Job Launching
 */
public class BuildableLayer {
    /**
     * If the user manually set memory, this is updated to true.
     */
    public boolean isMemoryOverride = false;

    /**
     * Stores the layer detail. LayerDetail is needed to actually insert the layer into the DB.
     */
    public LayerDetail layerDetail = new LayerDetail();

    /**
     * Map for storing environment vars
     */
    public Map<String, String> env = new HashMap<String, String>();

    public BuildableLayer() {}

    public BuildableLayer(LayerDetail detail) {
        this.layerDetail = detail;
    }
}
