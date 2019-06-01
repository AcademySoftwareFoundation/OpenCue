
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

package com.imageworks.spcue.dao.criteria;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.dao.criteria.postgres.FrameSearch;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;

import java.util.List;

public class FrameSearchFactory {

    public FrameSearchInterface create() {
        return new FrameSearch();
    }

    public FrameSearchInterface create(List<String> frameIds) {
        FrameSearchInterface frameSearch = create();
        frameSearch.filterByFrameIds(frameIds);
        return frameSearch;
    }

    public FrameSearchInterface create(JobInterface job) {
        FrameSearchInterface frameSearch = create();
        frameSearch.filterByJob(job);
        return frameSearch;
    }

    public FrameSearchInterface create(FrameInterface frame) {
        FrameSearchInterface frameSearch = create();
        frameSearch.filterByFrame(frame);
        return frameSearch;
    }

    public FrameSearchInterface create(JobInterface job, FrameSearchCriteria criteria) {
        FrameSearchInterface frameSearch = create();
        frameSearch.setCriteria(criteria);
        frameSearch.filterByJob(job);
        return frameSearch;
    }

    public FrameSearchInterface create(LayerInterface layer) {
        FrameSearchInterface frameSearch = create();
        frameSearch.filterByLayer(layer);
        return frameSearch;
    }

    public FrameSearchInterface create(LayerInterface layer, FrameSearchCriteria criteria) {
        FrameSearchInterface frameSearch = create();
        frameSearch.setCriteria(criteria);
        frameSearch.filterByLayer(layer);
        return frameSearch;
    }
}
