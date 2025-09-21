
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

import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.ServiceOverrideEntity;

public interface ServiceDao {

    void insert(ServiceEntity service);

    void insert(ServiceOverrideEntity service);

    ServiceEntity get(String identifier);

    void update(ServiceEntity service);

    void update(ServiceOverrideEntity service);

    void delete(ServiceOverrideEntity service);

    void delete(ServiceEntity service);

    ServiceOverrideEntity getOverride(String id);

    ServiceOverrideEntity getOverride(String id, String show);

    boolean isOverridden(String service, String show);
}
