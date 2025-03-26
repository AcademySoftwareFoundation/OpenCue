
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

import com.imageworks.spcue.service.DependManager;

public class DependCreationVisitor implements DependVisitor {

    DependManager dependManager;

    public DependCreationVisitor(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    @Override
    public void accept(FrameOnFrame depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(JobOnJob depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(JobOnLayer depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(JobOnFrame depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(LayerOnJob depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(LayerOnLayer depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(LayerOnFrame depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(FrameOnJob depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(FrameOnLayer depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(FrameByFrame depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(PreviousFrame depend) {
        dependManager.createDepend(depend);
    }

    @Override
    public void accept(LayerOnSimFrame depend) {
        dependManager.createDepend(depend);
    }
}
