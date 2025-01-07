
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

import java.util.ArrayList;
import java.util.List;

import com.imageworks.spcue.grpc.report.RenderHost;

public class TagUtil {

    /**
     * This will take the RQD tags and convert them into something usable for now until the RQD tag
     * standard is set.
     *
     * @param host
     * @return
     */
    public static List<String> buildHardwareTags(RenderHost host) {
        List<String> tags = new ArrayList<String>();
        if (host.getTagsList().contains("linux")) {
            tags.add("linux");
        }

        if (host.getTagsList().contains("64bit")) {
            tags.add("64bit");
            tags.add("32bit");
        } else {
            tags.add("32bit");
        }
        return tags;
    }
}
