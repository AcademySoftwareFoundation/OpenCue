
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

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Locale;

/**
 * Utility class for conversions
 */
public final class Convert {

    public static final int coresToCoreUnits(float cores) {
        return new BigDecimal(cores * 100).setScale(2, RoundingMode.HALF_UP).intValue();
    }

    public static final int coresToCoreUnits(int cores) {
        return cores * 100;
    }

    public static final int coresToWholeCoreUnits(float cores) {
        if (cores == -1) {
            return -1;
        }
        return (int) (((cores * 100.0f) + 0.5f) / 100) * 100;
    }

    public static final float coreUnitsToCores(int coreUnits) {
        if (coreUnits == -1) {
            return -1f;
        }
        return Float.valueOf(String.format(Locale.ROOT, "%6.2f", coreUnits / 100.0f));
    }

    public static final float coreUnitsToWholeCores(int coreUnits) {
        if (coreUnits == -1) {
            return -1f;
        }
        return Float.valueOf((int) ((coreUnits / 100.0f) + 0.5));
    }

    private static final List<String> MATCH_BOOL =
            java.util.Arrays.asList(new String[] {"true", "yes", "1", "on"});

    public static final boolean stringToBool(String value) {
        if (value == null) {
            return false;
        }
        if (MATCH_BOOL.contains(value.toLowerCase())) {
            return true;
        }
        return false;
    }
}
