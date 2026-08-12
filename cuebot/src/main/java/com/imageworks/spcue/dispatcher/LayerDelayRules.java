
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

import java.time.Duration;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Parser for the dispatcher.layer_delay.rules property: comma-separated exit_status:minutes pairs
 * (e.g. "330:5,332:60") mapping a frame exit status to how long its layer's booking should be
 * deferred when a frame reports that status. An empty value (the default) disables the automatic
 * backoff entirely. The exit statuses must agree with the substitute statuses RQD is configured to
 * emit via rqd.yaml runner.log_exit_status_rules.
 */
public final class LayerDelayRules {

    private static final Logger logger = LogManager.getLogger(LayerDelayRules.class);

    private LayerDelayRules() {}

    /**
     * Parse the rules property into a status-to-backoff map. Malformed entries are skipped with a
     * WARN rather than failing startup, mirroring RQD's tolerance for invalid log rules.
     */
    public static Map<Integer, Duration> parse(String rules) {
        if (rules == null || rules.trim().isEmpty()) {
            return Collections.emptyMap();
        }
        Map<Integer, Duration> parsed = new LinkedHashMap<Integer, Duration>();
        for (String entry : rules.split(",")) {
            entry = entry.trim();
            if (entry.isEmpty()) {
                continue;
            }
            String[] parts = entry.split(":");
            try {
                if (parts.length != 2) {
                    throw new NumberFormatException("expected exit_status:minutes");
                }
                int exitStatus = Integer.parseInt(parts[0].trim());
                long minutes = Long.parseLong(parts[1].trim());
                if (exitStatus == 0) {
                    // Exit status 0 is success: a rule on it would delay a layer on every
                    // frame that completes normally, which is never what an operator means.
                    throw new NumberFormatException(
                            "exit status 0 is success and cannot delay a layer");
                }
                if (minutes <= 0) {
                    throw new NumberFormatException("minutes must be positive");
                }
                parsed.put(exitStatus, Duration.ofMinutes(minutes));
            } catch (NumberFormatException | ArithmeticException e) {
                // ArithmeticException: a minute count that parses as a long but overflows
                // when Duration converts it to seconds is malformed like any other bad entry.
                logger.warn("Skipping malformed dispatcher.layer_delay.rules entry \"" + entry
                        + "\": " + e.getMessage());
            }
        }
        return Collections.unmodifiableMap(parsed);
    }
}
