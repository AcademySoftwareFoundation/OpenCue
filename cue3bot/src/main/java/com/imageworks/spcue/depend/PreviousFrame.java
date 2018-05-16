
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



package com.imageworks.spcue.depend;

import com.imageworks.spcue.depend.Depend;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.CueIce.DependTarget;
import com.imageworks.spcue.CueIce.DependType;
import com.imageworks.spcue.util.SqlUtil;

public class PreviousFrame extends AbstractDepend implements Depend {

    public final Layer dependErLayer;
    public final Layer dependOnLayer;

    public PreviousFrame(Layer dependErLayer, Layer dependOnLayer) {
        this.dependErLayer = dependErLayer;
        this.dependOnLayer = dependOnLayer;
        setComposite(true);
    }

    @Override
    public String getSignature() {
        StringBuilder key = new StringBuilder(256);
        key.append(DependType.PreviousFrame.toString());
        key.append(dependErLayer.getJobId());
        key.append(dependOnLayer.getJobId());
        key.append(dependErLayer.getLayerId());
        key.append(dependOnLayer.getLayerId());
        return SqlUtil.genKeyByName(key.toString());
    }

    @Override
    public DependTarget getTarget() {
        if (dependErLayer.getJobId().equals(dependOnLayer.getJobId())) {
            return DependTarget.Internal;
        }
        else {
            return DependTarget.External;
        }
    }

    @Override
    public void accept(DependVisitor dependVisitor) {
        dependVisitor.accept(this);
    }

    public Layer getDependErLayer() {
        return dependErLayer;
    }

    public Layer getDependOnLayer() {
        return dependOnLayer;
    }
}

