
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



package com.imageworks.spcue;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

public class SortableShow implements Comparable<SortableShow> {

    private static final Logger logger = LogManager.getLogger(SortableShow.class);

    private String show;
    private float tier;

    private Map<String,long []> failed = new ConcurrentHashMap<String,long[]>();
    private Set<AllocationInterface> failedAllocs = new HashSet<AllocationInterface>();

    public SortableShow(String show, float value) {
        this.show = show;
        this.tier = value;
    }

    public String getShowId() {
        return show;
    }

    public float getValue() {
        return tier;
    }

    public boolean isSkipped(String tags, long cores, long memory) {
        try {
            if (failed.containsKey(tags)) {
                long [] mark = failed.get(tags);
                if (cores <= mark[0]) {
                    logger.info("skipped due to not enough cores " + cores + " <= " + mark[0]);
                    return true;
                }
                else if (memory <= mark[1]) {
                    logger.info("skipped due to not enough memory " + memory + " <= " + mark[1]);
                    return true;
                }
            }
            return false;
        } catch (Exception e ){
            logger.info("exception checking skipped: " + e);
            return false;
        }
    }

    public boolean isSkipped(AllocationInterface a) {
        if (failedAllocs.contains(a)) {
            return true;
        }
        return false;
    }

    public void skip(String tags, long cores, long memory) {
        if (tags != null) {
            failed.put(tags, new long[] { cores, memory});
        }
    }

    /**
     * Adds an allocation that should not be
     * booked on this show.
     *
     * @param Allocation
     */
    public void skip(AllocationInterface a) {
        synchronized (failedAllocs) {
            failedAllocs.add(a);
        }
    }

    @Override
    public int compareTo(SortableShow o) {
        return (int) ((this.tier * 100) - (o.getValue() * 100));
    }

    @Override
    public int hashCode() {
       return show.hashCode();
    };

    @Override
    public boolean equals(Object other) {
        if (other == null) {
            return false;
        }
        if (this.getClass() != other.getClass()) {
            return false;
        }
        SortableShow that = (SortableShow) other;
        return that.getShowId().equals(this.getShowId());
    }
}

