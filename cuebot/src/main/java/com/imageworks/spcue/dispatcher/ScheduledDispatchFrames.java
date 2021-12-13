
/*
 * Copyright Contributors to the OpenCue Project
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



package com.imageworks.spcue.dispatcher;

import java.lang.AutoCloseable;
import java.lang.Iterable;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;

import com.imageworks.spcue.DispatchFrame;

/**
 * A convenient class to ensure unsheduling frames when the scheduled frames were not dispatched.
 */
public class ScheduledDispatchFrames implements AutoCloseable, Iterable<DispatchFrame> {

    private DispatchSupport dispatchSupport;
    private List<DispatchFrame> dispatchFrames;
    private HashSet<DispatchFrame> excluded;

    public ScheduledDispatchFrames(DispatchSupport dispatchSupport,
            List<DispatchFrame> dispatchFrames) {
        this.dispatchSupport = dispatchSupport;
        this.dispatchFrames = dispatchFrames;
        excluded = new HashSet<DispatchFrame>(dispatchFrames.size());
    }

    public void markFrameAsDispatched(DispatchFrame dispatchFrame) {
        excluded.add(dispatchFrame);
    }

    public int size() {
        return dispatchFrames.size();
    }

    @Override
    public Iterator<DispatchFrame> iterator() {
        return dispatchFrames.iterator();
    }

    @Override
    public void close() {
        dispatchSupport.unscheduleDispatchFrames(dispatchFrames, excluded);
    }
}
