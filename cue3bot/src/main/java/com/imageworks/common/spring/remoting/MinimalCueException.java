
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



package com.imageworks.common.spring.remoting;

import java.util.ArrayList;

import com.imageworks.common.SpiIce.SpiIceCause;
import com.imageworks.spcue.CueIce.CueIceException;

public class MinimalCueException extends CueIceException {

    public MinimalCueException(String message) {
        this.message = message;
        this.stackTrace = new String[0];
        this.causedBy = new ArrayList<SpiIceCause>(0);
    }

    public MinimalCueException(String message, String[] stackTrace,
            ArrayList<SpiIceCause> causedBy) {
        super(message, stackTrace, causedBy);
        // TODO Auto-generated constructor stub
    }
}

