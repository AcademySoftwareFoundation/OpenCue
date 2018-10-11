
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



package com.imageworks.spcue.servant;

import java.util.ArrayList;
import java.util.List;

import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerSeq;

public class ServantUtil {

    public static List<LayerInterface> convertLayerFilterList(LayerSeq layers) {
        final List<LayerInterface> result = new ArrayList<LayerInterface>();
        for (final Layer layer: layers.getLayersList()) {
            final String id = layer.getId();
            result.add(new LayerInterface() {
                String _id = id;
                public String getLayerId() { return _id; }
                public String getJobId() {  throw new RuntimeException("not implemented"); }
                public String getShowId() {  throw new RuntimeException("not implemented"); }
                public String getId() { return _id; }
                public String getName() {  throw new RuntimeException("not implemented"); }
                public String getFacilityId() { throw new RuntimeException("not implemented"); }
            });
        }
        return result;
    }
}

