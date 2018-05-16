
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

public class Deed extends Entity {

    public String owner;
    public String host;

    /**
     * The owner can set a black out time for booking where Cue will not
     * automatically book the cores, even if NIMBY locked.
     *
     * This is measured in seconds past midnight.
     */
    public int blackoutStart = 0;
    public int blackoutStop = 0;

    /**
     * Quickly disable and enable the current black out time settings.
     */
    public boolean isBlackoutEnabled = false;

    public String getName() {
        return String.format("%s.%s", owner, host);
    }
}

