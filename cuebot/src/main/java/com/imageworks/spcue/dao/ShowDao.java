
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



package com.imageworks.spcue.dao;

import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.ShowInterface;

/**
 * @category DAO
 */
public interface ShowDao {

    /**
     * find show detail by name
     *
     * @param name
     * @return ShowDetail
     */
    ShowEntity findShowDetail(String name);

    /**
     * get show detail from its unique id
     *
     * @param id
     * @return ShowDetail
     */
    ShowEntity getShowDetail(String id);

    /**
     * Get show detail from its preferred show.
     *
     * @param id
     * @return ShowDetail
     */
    ShowEntity getShowDetail(HostInterface host);

    /**
     * create a show from ShowDetail
     *
     * @param show
     */
    void insertShow(ShowEntity show);

    /**
     * return true if show exists, false if not
     *
     * @param name
     * @return boolean
     */
    boolean showExists(String name);

    /**
     *
     * @param s
     * @param val
     */
    void updateShowDefaultMinCores(ShowInterface s, int val);

    /**
     *
     * @param s
     * @param val
     */
    void updateShowDefaultMaxCores(ShowInterface s, int val);

    /**
     *
     * @param s
     * @param val
     */
    void updateShowDefaultMinGpus(ShowInterface s, int val);

    /**
     *
     * @param s
     * @param val
     */
    void updateShowDefaultMaxGpus(ShowInterface s, int val);


    /**
     * Disabling this would stop new proc assignement. The show would get no new
     * procs, but any procs already assigned to a job would continue to
     * dispatch.
     *
     * @param s
     * @param enabled
     */
    void updateBookingEnabled(ShowInterface s, boolean enabled);

    /**
     * Disabling dispatching would unbook each proc after it had completed a
     * frame.
     *
     * @param s
     * @param enabled
     */
    void updateDispatchingEnabled(ShowInterface s, boolean enabled);

    /**
     * Deletes a show if no data has been added to it.
     *
     * @param s
     */
    void delete(ShowInterface s);

    /**
     * Updates the show frame counter. This counts all failed succceeded frames,
     * forver.
     *
     * @param s
     * @param exitStatus
     */
    void updateFrameCounters(ShowInterface s, int exitStatus);

    /**
     * Set the enabled status of a show to true/false.
     *
     * @param s
     * @param enabled
     */
    void updateActive(ShowInterface s, boolean enabled);

    /**
     * An array of email addresses for which all job comments are echoed to.
     *
     * @param s
     * @param emails
     */
    void updateShowCommentEmail(ShowInterface s, String[] emails);
}

