
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

import com.imageworks.spcue.grpc.depend.DependType;

public class BuildableDependency {

    public DependType type;
    public boolean anyFrame = false;
    public boolean launchDepend = false;

    public String dependErJobName;
    public String dependErLayerName;
    public String dependErFrameName;

    public String dependOnJobName;
    public String dependOnLayerName;
    public String dependOnFrameName;

    public boolean isAnyFrame() {
        return anyFrame;
    }

    public void setAnyFrame(boolean anyFrame) {
        this.anyFrame = anyFrame;
    }

    public String getDependErFrameName() {
        return dependErFrameName;
    }

    public void setDependErFrameName(String dependErFrameName) {
        this.dependErFrameName = dependErFrameName;
    }

    public String getDependErJobName() {
        return dependErJobName;
    }

    public void setDependErJobName(String dependErJobName) {
        this.dependErJobName = dependErJobName;
    }

    public String getDependErLayerName() {
        return dependErLayerName;
    }

    public void setDependErLayerName(String dependErLayerName) {
        this.dependErLayerName = dependErLayerName;
    }

    public String getDependOnFrameName() {
        return dependOnFrameName;
    }

    public void setDependOnFrameName(String dependOnFrameName) {
        this.dependOnFrameName = dependOnFrameName;
    }

    public String getDependOnJobName() {
        return dependOnJobName;
    }

    public void setDependOnJobName(String dependOnJobName) {
        this.dependOnJobName = dependOnJobName;
    }

    public String getDependOnLayerName() {
        return dependOnLayerName;
    }

    public void setDependOnLayerName(String dependOnLayerName) {
        this.dependOnLayerName = dependOnLayerName;
    }

    public DependType getType() {
        return type;
    }

    public void setType(DependType type) {
        this.type = type;
    }

    public String toString() {
        StringBuilder sb = new StringBuilder(1024);
        sb.append("Depend Type: " + type.toString() + "\n");
        sb.append("Depend on job: " + dependErJobName + "\n");
        sb.append("Depend on layer: " + dependOnLayerName + "\n");
        sb.append("Depend on frame: " + dependOnFrameName + "\n");
        sb.append("Depend er job: " + dependOnJobName + "\n");
        sb.append("Depend er layer: " + dependErLayerName + "\n");
        sb.append("Depend er frame: " + dependErFrameName + "\n");
        return sb.toString();
    }

    public boolean isLaunchDepend() {
        return launchDepend;
    }

    public void setLaunchDepend(boolean launchDepend) {
        this.launchDepend = launchDepend;
    }

}
