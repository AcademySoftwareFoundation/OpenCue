
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



package com.imageworks.spcue.service;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.Job;

public interface CommentManager {

    /**
     * Add a comment to a job.
     *
     * @param job
     * @param comment
     */
    public void addComment(Job job, CommentDetail comment);

    /**
     * Add a comment to a host
     *
     * @param host
     * @param comment
     */
    public void addComment(Host host, CommentDetail comment);

    /**
     *
     * @param id
     */
    public void deleteComment(String id);

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

