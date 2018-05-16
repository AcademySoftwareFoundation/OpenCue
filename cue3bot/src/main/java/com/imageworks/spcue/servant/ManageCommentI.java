
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



package com.imageworks.spcue.servant;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.CueClientIce.CommentData;
import com.imageworks.spcue.CueClientIce._CommentInterfaceDisp;
import com.imageworks.spcue.service.CommentManager;

public class ManageCommentI extends _CommentInterfaceDisp {

    private CommentManager commentManager;
    private final String id;

    public ManageCommentI(Ice.Identity i) throws SpiIceException {
        this.id = i.name;
    }

    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                commentManager.deleteComment(id);
            }
        }.execute();
    }

    public void save(final CommentData comment, Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                CommentDetail c = new CommentDetail();
                c.id = id;
                c.message = comment.message;
                c.subject = comment.subject;
                commentManager.saveComment(c);
            }
        }.execute();
    }

    public CommentManager getCommentManager() {
        return commentManager;
    }

    public void setCommentManager(CommentManager commentManager) {
        this.commentManager = commentManager;
    }
}

