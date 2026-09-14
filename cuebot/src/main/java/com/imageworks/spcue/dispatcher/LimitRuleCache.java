
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

package com.imageworks.spcue.dispatcher;

import java.util.Collections;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;

import com.imageworks.spcue.LimitRule;
import com.imageworks.spcue.dao.LimitDao;

/**
 * In-process cache of the limits' failure rules, keyed by exit status, refreshed lazily on the
 * frame-complete path at most once per limit.usage_refresh_seconds.
 *
 * Caching this in-process is safe where caching usage counters is not: failure rules are read-only
 * operator configuration changed by hand a few times a year, so a few seconds of staleness after an
 * edit is invisible and every Cuebot instance converges on the next tick. The upside over the old
 * dispatcher.layer_delay.rules property is that rules become live-editable without a restart.
 */
public class LimitRuleCache {

    private static final Logger logger = LogManager.getLogger(LimitRuleCache.class);

    private LimitDao limitDao;

    private final long refreshIntervalMs;

    private volatile Map<Integer, LimitRule> rules = Collections.emptyMap();
    private volatile long refreshedAtMs = 0;
    private volatile boolean loadedOnce = false;

    @Autowired
    public LimitRuleCache(Environment env) {
        this.refreshIntervalMs =
                1000L * env.getProperty("limit.usage_refresh_seconds", Integer.class, 5);
    }

    /**
     * The failure rule claiming the given exit status, or null when no limit claims it. A refresh
     * failure keeps serving the previous rule set: discovery must never fail a frame-complete.
     */
    public LimitRule forExitStatus(int exitStatus) {
        long now = System.currentTimeMillis();
        if (now - refreshedAtMs > refreshIntervalMs) {
            refresh(now);
        }
        return rules.get(exitStatus);
    }

    /**
     * Every configured failure rule, keyed by exit status. Same freshness contract as
     * {@link #forExitStatus}.
     */
    public Map<Integer, LimitRule> all() {
        long now = System.currentTimeMillis();
        if (now - refreshedAtMs > refreshIntervalMs) {
            refresh(now);
        }
        return rules;
    }

    /**
     * Drops the cached rules so the next lookup reloads from the database. For tests; production
     * code relies on the interval.
     */
    public synchronized void invalidate() {
        loadedOnce = false;
        rules = Collections.emptyMap();
        refreshedAtMs = 0;
    }

    private synchronized void refresh(long now) {
        if (now - refreshedAtMs <= refreshIntervalMs) {
            return;
        }
        try {
            rules = limitDao.getFailureRules();
            loadedOnce = true;
        } catch (Exception e) {
            logger.warn("Failed to refresh limit failure rules, keeping "
                    + (loadedOnce ? "the previous set" : "an empty set") + ": " + e.getMessage());
        }
        // Stamped even on failure so a broken database is polled once per interval, not once per
        // completing frame.
        refreshedAtMs = now;
    }

    public void setLimitDao(LimitDao limitDao) {
        this.limitDao = limitDao;
    }
}
