
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

public class Entity implements EntityInterface {

    public String id = null;
    public String name = "unknown";

    public Entity() { }

    public Entity(String id) {
        this.id = id;
    }

    public Entity(String id, String name) {
        this.id = id;
        this.name = name;
    }

    public String getId() {
        return id;
    }
    public String getName() {
        return name;
    }

    public boolean isNew() {
        return id == null;
    }

    @Override
    public String toString() {
        return String.format("%s/%s", getName(), getId());
    }

    @Override
    public int hashCode() {
        if (id != null) {
            return id.hashCode();
        }
        else {
            return super.hashCode();
        }
    }

    @Override
    public boolean equals(Object other) {
        return this.toString().equals(
                other.toString());
    }
}

