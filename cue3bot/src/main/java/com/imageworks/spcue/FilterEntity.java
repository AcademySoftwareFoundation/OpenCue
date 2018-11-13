
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



package com.imageworks.spcue;

import com.imageworks.spcue.grpc.filter.FilterType;

public class FilterEntity extends Entity implements FilterInterface {

    public FilterType type;
    public String showId;
    public boolean enabled;
    public float order;

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getFilterId() {
        return id;
    }

    public String getShowId() {
        return showId;
    }

}

