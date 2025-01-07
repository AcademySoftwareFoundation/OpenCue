
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

package com.imageworks.spcue.util;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.io.Writer;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

/**
 * Utility class for handling and logging exceptions
 *
 */
public class CueExceptionUtil {

    /**
     * returns the stack track for an exception as a string.
     *
     * @param aThrowable
     * @return String
     */
    public static String getStackTrace(Throwable aThrowable) {
        final Writer result = new StringWriter();
        final PrintWriter printWriter = new PrintWriter(result);
        aThrowable.printStackTrace(printWriter);
        return result.toString();
    }

    /**
     * Creates an error message string which w/ a stack track and returns it.
     *
     * @param msg
     * @param aThrowable
     * @return String
     */
    public static void logStackTrace(String msg, Throwable aThrowable) {
        Logger error_logger = LogManager.getLogger(CueExceptionUtil.class);
        error_logger.info("Caught unexpected exception caused by: " + aThrowable);
        error_logger.info("StackTrace: \n" + getStackTrace(aThrowable));
        if (aThrowable.getCause() != null) {
            error_logger.info("Caused By: " + getStackTrace(aThrowable.getCause()));
        }
    }
}
