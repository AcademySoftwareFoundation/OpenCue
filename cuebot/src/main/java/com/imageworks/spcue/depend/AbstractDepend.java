
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

import com.imageworks.spcue.grpc.depend.DependTarget;

/**
 * Base class for all dependency types.
 */
public abstract class AbstractDepend {

    private boolean launch = false;
    private boolean active = true;
    private boolean anyFrame = false;

    /**
     * True if the dependency is just a container for other depends and cannot be satisfied by
     * frames completing. Its essentially a way to group related depends.
     */
    private boolean composite = false;

    private String id = null;

    public String getId() {
        return id;
    }

    public boolean isActive() {
        return active;
    }

    public boolean isAnyFrame() {
        return anyFrame;
    }

    public void setAnyFrame(boolean anyFrame) {
        this.anyFrame = anyFrame;
    }

    public void setActive(boolean active) {
        this.active = active;
    }

    public void setId(String id) {
        this.id = id;
    }

    public boolean isLaunchDepend() {
        return launch;
    }

    public void setLaunchDepend(boolean launch) {
        this.launch = launch;
    }

    public boolean isComposite() {
        return composite;
    }

    public void setComposite(boolean composite) {
        this.composite = composite;
    }

    public abstract String getSignature();

    public abstract DependTarget getTarget();
}
