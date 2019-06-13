
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

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.dao.CommentDao;

@Service
@Transactional
public class CommentManagerService implements CommentManager {

    @Autowired
    private EmailSupport emailSupport;

    @Autowired
    private AdminManager adminManager;

    CommentDao commentDao;

    @Transactional(propagation = Propagation.SUPPORTS)
    public void addComment(JobInterface job, CommentDetail comment) {
        commentDao.insertComment(job, comment);
        ShowEntity show = adminManager.getShowEntity(job.getShowId());
        if (show.commentMail.length > 0) {
            emailSupport.reportJobComment(job, comment, show.commentMail);
        }
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void addComment(HostInterface host, CommentDetail comment) {
        commentDao.insertComment(host, comment);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void deleteComment(String id) {
        commentDao.deleteComment(id);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void setCommentSubject(String id, String subject) {
        commentDao.updateCommentSubject(id, subject);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void setCommentMessage(String id, String message) {
        commentDao.updateCommentMessage(id, message);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void saveComment(CommentDetail detail) {
        commentDao.updateComment(detail);
    }
}

