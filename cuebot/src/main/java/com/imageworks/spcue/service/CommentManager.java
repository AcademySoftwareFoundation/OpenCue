
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

package com.imageworks.spcue.service;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;

import java.util.List;

public interface CommentManager {

    /**
     * Add a comment to a job.
     *
     * @param job
     * @param comment
     */
    public void addComment(JobInterface job, CommentDetail comment);

    /**
     * Add a comment to a host
     *
     * @param host
     * @param comment
     */
    public void addComment(HostInterface host, CommentDetail comment);

    /**
     *
     * @param id
     */
    public void deleteComment(String id);

    /**
     * Deletes comments using host, user, and subject
     *
     * @param host
     * @param user
     * @param subject
     * @return boolean: returns true if one or more comments where deleted
     */
    public boolean deleteCommentByHostUserAndSubject(HostInterface host, String user,
            String subject);

    /**
     * Get comments using host, user, and subject
     *
     * @param host
     * @param user
     * @param subject
     * @return List<Comment>
     */
    public List<CommentDetail> getCommentsByHostUserAndSubject(HostInterface host, String user,
            String subject);

    /**
     *
     * @param id
     * @param message
     */
    public void setCommentMessage(String id, String message);

    /**
     *
     * @param id
     * @param subject
     */
    public void setCommentSubject(String id, String subject);

    /**
     * Save the specified comment
     *
     * @param detail
     */
    public void saveComment(CommentDetail detail);

}
