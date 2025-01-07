
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

package com.imageworks.spcue;

import java.util.Arrays;
import java.util.Optional;
import java.util.stream.Stream;

import org.apache.commons.lang.StringUtils;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CuebotApplication extends SpringApplication {
    private static String[] checkArgs(String[] args) {
        Optional<String> deprecatedFlag = Arrays.stream(args)
                .filter(arg -> arg.startsWith("--log.frame-log-root=")).findFirst();
        if (deprecatedFlag.isPresent()) {
            // Log a deprecation warning.
            Logger warning_logger = LogManager.getLogger(CuebotApplication.class);
            warning_logger.warn("`--log.frame-log-root` is deprecated and will be removed in an "
                    + "upcoming release. It has been replaced with `--log.frame-log-root.default_os`. "
                    + "See opencue.properties for details on OpenCue's new OS-dependent root directories.");
            // If new flags are not present, swap in the value provided using the new flag.
            // If the new flags are already present, don't do anything.
            Optional<String> newFlags = Arrays.stream(args)
                    .filter(arg -> arg.startsWith("--log.frame-log-root.")).findAny();
            if (!newFlags.isPresent()) {
                String fixedFlag = "--log.frame-log-root.default_os="
                        + StringUtils.substringAfter(deprecatedFlag.get(), "=");
                args = Stream.concat(
                        Arrays.stream(args).filter(arg -> !arg.startsWith("--log.frame-log-root=")),
                        Stream.of(fixedFlag)).toArray(String[]::new);
            }
        }
        return args;
    }

    public static void main(String[] args) {
        // Cuebot startup
        String[] filteredArgs = checkArgs(args);
        SpringApplication.run(CuebotApplication.class, filteredArgs);
    }
}
