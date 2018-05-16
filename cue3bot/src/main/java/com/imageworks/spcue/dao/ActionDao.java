
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



package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.Action;
import com.imageworks.spcue.ActionDetail;
import com.imageworks.spcue.Filter;

public interface ActionDao {

    void createAction(ActionDetail action);
    void deleteAction(Action action);

    ActionDetail getAction(String id);
    ActionDetail getAction(Action action);
    void updateAction(ActionDetail action);

    List<ActionDetail> getActions(Filter filter);
}

