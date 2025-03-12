
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

import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;

public class LightweightDependency extends Entity implements DependInterface {

    public DependType type;
    public DependTarget target;

    public String parent = null;

    public String dependErJobId;
    public String dependErLayerId;
    public String dependErFrameId;

    public String dependOnJobId;
    public String dependOnLayerId;
    public String dependOnFrameId;

    public boolean anyFrame;
    public boolean active;

    public String getName() {
        return type.toString() + "/" + dependErJobId;
    }

    public String toString() {
        return String.format("%s/%s", type.toString(), getId());
    }
}
