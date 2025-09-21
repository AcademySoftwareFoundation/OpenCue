
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

package com.imageworks.spcue.dao;

import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.grpc.host.NestedHostSeq;
import com.imageworks.spcue.grpc.job.NestedGroup;

/**
 * A DAO for nested data structures being returned to the client.
 *
 * @category DAO
 */
public interface NestedWhiteboardDao {

    /**
     * returns a grouped whiteboard for specified show.
     *
     * @param show
     * @return
     */
    NestedGroup getJobWhiteboard(ShowInterface show);

    /**
     * get a list of hosts
     *
     * @return List<Host>
     */
    NestedHostSeq getHostWhiteboard();

}
