
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

import com.imageworks.spcue.CueClientIce.MatcherData;
import com.imageworks.spcue.CueIce.MatchSubject;
import com.imageworks.spcue.CueIce.MatchType;

public class MatcherDetail extends Entity implements Matcher {

    public MatchSubject subject;
    public MatchType type;
    public String value;

    public String filterId;
    public String showId;

    public static MatcherDetail build(Filter filter, MatcherData data) {

        MatcherDetail detail = new MatcherDetail();
        detail.name = null;
        detail.subject = data.subject;
        detail.type = data.type;
        detail.value = data.input;

        return detail;
    }

    public static MatcherDetail build(Filter filter, MatcherData data, String id) {
        MatcherDetail detail = build(filter, data);
        detail.id = id.toString();
        return detail;
    }

    public String getFilterId() {
        return filterId;
    }

    public String getShowId() {
        return showId;
    }

    public String getMatcherId() {
        return this.id;
    }
}

