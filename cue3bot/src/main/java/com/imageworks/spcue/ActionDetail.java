
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

import com.imageworks.spcue.CueClientIce.ActionData;
import com.imageworks.spcue.CueIce.ActionType;
import com.imageworks.spcue.CueIce.ActionValueType;

public class ActionDetail extends Entity implements Action {

    public String filterId;
    public String showId;

    public ActionType type;
    public ActionValueType valueType;
    public String stringValue;
    public long intValue;
    public boolean booleanValue;
    public String groupValue;
    public float floatValue;

    public ActionDetail() {
        this.name = null;
    }

    public static ActionDetail build(Filter filter, ActionData data) {

        ActionDetail detail = new ActionDetail();
        if (data.groupValue != null) {
            detail.groupValue = data.groupValue.ice_getIdentity().name;
        }
        detail.stringValue = data.stringValue;
        detail.booleanValue = data.booleanValue;
        detail.intValue = data.integerValue;
        detail.floatValue = data.floatValue;
        detail.name = "";
        detail.filterId = filter.getFilterId();
        detail.showId = filter.getShowId();
        detail.type = data.type;
        detail.valueType = data.valueType;

        return detail;
    }

    public static ActionDetail build(Filter filter, ActionData data, String id) {
        ActionDetail action = build(filter, data);
        action.id = id;
        if (action.isNew()) {
            throw new SpcueRuntimeException("the action has not been created yet");
        }
        return action;

    }

    public String getId() {
        return id;
    }

    public String getName() {
        return null;
    }

    public String getActionId() {
        return id;
    }

    public String getFilterId() {
        return filterId;
    }

    public String getShowId() {
        return showId;
    }

}

