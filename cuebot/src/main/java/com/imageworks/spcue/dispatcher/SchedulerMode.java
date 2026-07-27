
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

import com.imageworks.spcue.dao.ShowDao;
import org.springframework.core.env.Environment;

/**
 * Interprets {@code scheduler.enabled} as a tri-state progressive-rollout switch (rather than a
 * plain boolean), so the in-process Scheduler can be turned on for one show at a time -- the same
 * per-show model the standalone Rust scheduler uses via {@code show.b_scheduler_managed}:
 *
 * <ul>
 * <li>{@code no} -- Scheduler off; the legacy dispatcher owns every show.</li>
 * <li>{@code facility} -- Scheduler plans ALL shows; legacy booking globally suppressed (this is
 * the old {@code scheduler.enabled=true} behaviour).</li>
 * <li>{@code managed} -- Scheduler plans only shows flagged {@code b_scheduler_managed=true} (set
 * per show via the show API, exactly like Rust); the legacy dispatcher keeps the rest. The legacy
 * dispatch query already excludes managed shows, so the two partition cleanly.</li>
 * </ul>
 *
 * Back-compat: {@code "true"} maps to {@code facility}, {@code "false"} to {@code no}. Show
 * selection lives in the per-show flag, NOT in this string, so Cuebot never has to reconcile a
 * config value into the database.
 */
public final class SchedulerMode {

    private SchedulerMode() {}

    public static String mode(Environment env) {
        String m = env.getProperty("scheduler.enabled", "no");
        return (m == null || m.trim().isEmpty()) ? "no" : m.trim();
    }

    /** True when the in-process Scheduler runs at all (facility or managed). */
    public static boolean enabled(Environment env) {
        String m = mode(env);
        return !(m.equalsIgnoreCase("no") || m.equalsIgnoreCase("false"));
    }

    /**
     * True when the Scheduler owns EVERY show and the legacy BookingQueue is globally suppressed
     * (facility-wide rollout / the old boolean {@code true}).
     */
    public static boolean facility(Environment env) {
        String m = mode(env);
        return m.equalsIgnoreCase("facility") || m.equalsIgnoreCase("true");
    }

    /**
     * Whether the in-process Scheduler -- not the legacy dispatcher -- owns this show. In
     * {@code managed} mode this defers to the per-show {@code b_scheduler_managed} flag.
     */
    public static boolean schedules(Environment env, ShowDao showDao, String showId) {
        if (!enabled(env)) {
            return false;
        }
        if (facility(env)) {
            return true;
        }
        return showDao.isSchedulerManaged(showId);
    }
}
