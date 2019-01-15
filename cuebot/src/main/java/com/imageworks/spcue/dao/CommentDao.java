
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
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

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;

public interface CommentDao {

    /**
     * deletes the specified comment.
     *
     * @param id
     */
    public void deleteComment(String id);

    /**
     * Retrieves the specified comment.
     *
     * @param id
     * @return
     */
    public CommentDetail getCommentDetail(String id);

    /**
     * Inserts a comment on a job
     *
     * @param job
     * @param comment
     */
    public void insertComment(JobInterface job, CommentDetail comment);

    /**
     * Inserts a comment on a host
     *
     * @param host
     * @param comment
     */
    public void insertComment(HostInterface host, CommentDetail comment);

    /**
     * Update specified comment
     *
     * @param comment
     */
    public void updateComment(CommentDetail comment);

    /**
     * Updates the specified comment's message field with the supplied value.
     *
     * @param id
     * @param message
     */
    public void updateCommentMessage(String id, String message);

    /**
     * Update the specified comment's subject field with the supplied value.
     *
     * @param id
     * @param subject
     */
    public void updateCommentSubject(String id, String subject);

}

