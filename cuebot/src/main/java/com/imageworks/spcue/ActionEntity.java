
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

package com.imageworks.spcue;

import com.imageworks.spcue.grpc.filter.Action;
import com.imageworks.spcue.grpc.filter.ActionType;
import com.imageworks.spcue.grpc.filter.ActionValueType;

public class ActionEntity extends Entity implements ActionInterface {

    public String filterId;
    public String showId;

    public ActionType type;
    public ActionValueType valueType;
    public String stringValue;
    public long intValue;
    public boolean booleanValue;
    public String groupValue;
    public float floatValue;

    public ActionEntity() {
        this.name = null;
    }

    public static ActionEntity build(Action data) {
        ActionEntity entity = new ActionEntity();
        if (data.getGroupValue() != null) {
            entity.groupValue = data.getGroupValue();
        }
        entity.stringValue = data.getStringValue();
        entity.booleanValue = data.getBooleanValue();
        entity.intValue = data.getIntegerValue();
        entity.floatValue = data.getFloatValue();
        entity.name = "";
        entity.type = data.getType();
        entity.valueType = data.getValueType();
        return entity;
    }

    public static ActionEntity build(FilterInterface filter, Action data) {
        ActionEntity entity = build(data);
        entity.filterId = filter.getFilterId();
        entity.showId = filter.getShowId();
        return entity;
    }

    public static ActionEntity build(FilterInterface filter, Action data, String id) {
        ActionEntity action = build(filter, data);
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
        if (filterId == null) {
            throw new SpcueRuntimeException(
                    "Trying to get a filterId from a ActityEntity created without a filter");
        }
        return filterId;
    }

    public String getShowId() {
        return showId;
    }

}
