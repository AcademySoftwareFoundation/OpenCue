
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
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;

import java.util.List;

public interface FrameSearchInterface extends CriteriaInterface {
    int DEFAULT_PAGE = 1;
    int DEFAULT_LIMIT = 1000;

    FrameSearchCriteria getCriteria();
    void setCriteria(FrameSearchCriteria criteria);
    String getSortedQuery(String query);
    void filterByFrameIds(List<String> frameIds);
    void filterByJob(JobInterface job);
    void filterByFrame(FrameInterface frame);
    void filterByLayer(LayerInterface layer);
    void filterByLayers(List<LayerInterface> layers);
    void filterByFrameStates(List<FrameState> frameStates);
    void filterByFrameSet(String frameSet);
    void filterByMemoryRange(String range);
    void filterByDurationRange(String range);
    void filterByChangeDate(int changeDate);

    static FrameSearchCriteria criteriaFactory() {
        return FrameSearchCriteria.newBuilder()
                .setPage(DEFAULT_PAGE)
                .setLimit(DEFAULT_LIMIT)
                .setChangeDate(0)
                .build();
    }
}
