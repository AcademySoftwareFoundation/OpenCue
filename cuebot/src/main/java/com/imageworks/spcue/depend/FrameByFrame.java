
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

import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.util.SqlUtil;

public class FrameByFrame extends AbstractDepend implements Depend {

    private final LayerInterface dependErLayer;
    private final LayerInterface dependOnLayer;

    public FrameByFrame(LayerInterface dependErLayer, LayerInterface dependOnLayer) {

        if (dependErLayer.getLayerId().equals(dependOnLayer.getLayerId())) {
            throw new DependException(
                    "Cannot make the layer " + dependErLayer.getName() + " depend on itself.");
        }

        this.dependErLayer = dependErLayer;
        this.dependOnLayer = dependOnLayer;
        setComposite(true);
    }

    @Override
    public String getSignature() {
        StringBuilder key = new StringBuilder(256);
        key.append(DependType.FRAME_BY_FRAME.toString());
        key.append(dependErLayer.getJobId());
        key.append(dependOnLayer.getJobId());
        key.append(dependErLayer.getLayerId());
        key.append(dependOnLayer.getLayerId());
        return SqlUtil.genKeyByName(key.toString());
    }

    @Override
    public void accept(DependVisitor dependVisitor) {
        dependVisitor.accept(this);
    }

    @Override
    public DependTarget getTarget() {
        if (dependErLayer.getJobId().equals(dependOnLayer.getJobId())) {
            return DependTarget.INTERNAL;
        } else {
            return DependTarget.EXTERNAL;
        }
    }

    public LayerInterface getDependErLayer() {
        return dependErLayer;
    }

    public LayerInterface getDependOnLayer() {
        return dependOnLayer;
    }
}
