
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

package com.imageworks.spcue.test.servant;

import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.grpc.show.Show;
import com.imageworks.spcue.grpc.show.ShowSetCommentEmailRequest;
import com.imageworks.spcue.grpc.show.ShowSetCommentEmailResponse;
import com.imageworks.spcue.grpc.show.ShowSetSchedulerManagedRequest;
import com.imageworks.spcue.grpc.show.ShowSetSchedulerManagedResponse;
import com.imageworks.spcue.servant.ManageShow;

import io.grpc.stub.StreamObserver;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class ManageShowTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    ShowDao showDao;

    @Resource
    ManageShow manageShow;

    private static final String SHOW_NAME = "pipe";

    /**
     * StreamObserver that records whether onNext / onCompleted were called, so a servant method
     * that forgets to close the stream (onCompleted) is caught.
     */
    private static class RecordingStreamObserver<T> implements StreamObserver<T> {
        boolean nextCalled = false;
        boolean completed = false;
        Throwable error = null;

        @Override
        public void onNext(T value) {
            nextCalled = true;
        }

        @Override
        public void onError(Throwable t) {
            error = t;
        }

        @Override
        public void onCompleted() {
            completed = true;
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetCommentEmail() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        Show showProto = Show.newBuilder().setId(show.id).setName(show.name).build();

        ShowSetCommentEmailRequest request = ShowSetCommentEmailRequest.newBuilder()
                .setShow(showProto).setEmail("first@example.com,second@example.com").build();
        RecordingStreamObserver<ShowSetCommentEmailResponse> observer =
                new RecordingStreamObserver<ShowSetCommentEmailResponse>();

        manageShow.setCommentEmail(request, observer);

        // The RPC must both emit a response and CLOSE the stream; a missing
        // onCompleted() leaves callers hanging until they time out.
        assertTrue(observer.nextCalled);
        assertTrue(observer.completed);

        // And the email is persisted (split on comma, matching the servant).
        assertArrayEquals(new String[] {"first@example.com", "second@example.com"},
                showDao.findShowDetail(SHOW_NAME).commentMail);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetSchedulerManaged() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        assertFalse(show.schedulerManaged);

        Show showProto = Show.newBuilder().setId(show.id).setName(show.name).build();
        ShowSetSchedulerManagedRequest enableRequest = ShowSetSchedulerManagedRequest.newBuilder()
                .setShow(showProto).setEnabled(true).build();
        FakeStreamObserver<ShowSetSchedulerManagedResponse> enableObserver =
                new FakeStreamObserver<ShowSetSchedulerManagedResponse>();
        manageShow.setSchedulerManaged(enableRequest, enableObserver);
        assertTrue(showDao.findShowDetail(SHOW_NAME).schedulerManaged);

        ShowSetSchedulerManagedRequest disableRequest = ShowSetSchedulerManagedRequest.newBuilder()
                .setShow(showProto).setEnabled(false).build();
        FakeStreamObserver<ShowSetSchedulerManagedResponse> disableObserver =
                new FakeStreamObserver<ShowSetSchedulerManagedResponse>();
        manageShow.setSchedulerManaged(disableRequest, disableObserver);
        assertFalse(showDao.findShowDetail(SHOW_NAME).schedulerManaged);
    }
}
