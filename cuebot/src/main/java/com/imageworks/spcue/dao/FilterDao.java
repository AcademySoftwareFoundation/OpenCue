
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

package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.FilterInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.grpc.filter.FilterType;

/**
 * DAO for filter database operations.
 *
 * @category DAO
 */
public interface FilterDao {

    List<FilterEntity> getActiveFilters(ShowInterface show);

    List<FilterEntity> getFilters(ShowInterface show);

    void updateSetFilterEnabled(FilterInterface f, boolean enabled);

    void updateSetFilterName(FilterInterface f, String name);

    void updateSetFilterType(FilterInterface f, FilterType type);

    void updateSetFilterOrder(FilterInterface f, double order);

    void deleteFilter(FilterInterface f);

    void insertFilter(FilterEntity f);

    void reorderFilters(ShowInterface s);

    void lowerFilterOrder(FilterInterface f, int by);

    void raiseFilterOrder(FilterInterface f, int by);

    FilterEntity getFilter(String id);

    FilterEntity getFilter(FilterInterface filter);

    FilterEntity findFilter(ShowInterface show, String name);

}
