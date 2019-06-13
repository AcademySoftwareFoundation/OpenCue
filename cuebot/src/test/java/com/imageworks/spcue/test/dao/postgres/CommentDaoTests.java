
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



package com.imageworks.spcue.test.dao.postgres;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.CommentDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.CueUtil;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class CommentDaoTests  extends AbstractTransactionalJUnit4SpringContextTests  {
    
    @Autowired
    CommentDao commentDao;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    HostManager hostManager;

    @Before
    public void testMode() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteComment() {

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        CommentDetail d = new CommentDetail();
        d.message = "a message";
        d.subject = "a subject";
        d.user = "user";

        commentDao.insertComment(job, d);
        commentDao.deleteComment(d.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetComment() {

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        CommentDetail d = new CommentDetail();
        d.message = "a message";
        d.subject = "a subject";
        d.user = "user";

        commentDao.insertComment(job, d);

        CommentDetail nd = commentDao.getCommentDetail(d.getId());

        assertEquals(d.message,nd.message);
        assertEquals(d.subject,nd.subject);
        assertEquals(d.user,nd.user);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertCommentOnJob() {

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        CommentDetail d = new CommentDetail();
        d.message = "a message";
        d.subject = "a subject";
        d.user = "user";

        commentDao.insertComment(job, d);

        CommentDetail nd = commentDao.getCommentDetail(d.getId());

        assertEquals(d.message,nd.message);
        assertEquals(d.subject,nd.subject);
        assertEquals(d.user,nd.user);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertCommentOnHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName("boo")
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(15290520)
                .setFreeSwap(2076)
                .setLoad(1)
                .setTotalMcp(19543)
                .setTotalMem(15290520)
                .setTotalSwap(2096)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(400)
                .addTags("linux")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();

        CommentDetail d = new CommentDetail();
        d.message = "a message";
        d.subject = "a subject";
        d.user = "user";

        DispatchHost h = hostManager.createHost(host);
        commentDao.insertComment(h, d);

        assertNotNull(d.id);

        CommentDetail nd = commentDao.getCommentDetail(d.getId());

        assertEquals(d.message,nd.message);
        assertEquals(d.subject,nd.subject);
        assertEquals(d.user,nd.user);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateComment() {

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        CommentDetail d = new CommentDetail();
        d.message = "a message";
        d.subject = "a subject";
        d.user = "user";

        commentDao.insertComment(job, d);

        d.message = "no";
        d.subject = "no";

        commentDao.updateComment(d);

        CommentDetail nd = commentDao.getCommentDetail(d.getId());

        assertEquals("no",nd.message);
        assertEquals("no",nd.subject);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateCommentMessage() {

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        CommentDetail d = new CommentDetail();
        d.message = "a message";
        d.subject = "a subject";
        d.user = "user";

        commentDao.insertComment(job, d);
        commentDao.updateCommentMessage(d.getId(), "no");
        CommentDetail nd = commentDao.getCommentDetail(d.getId());
        assertEquals("no",nd.message);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateCommentSubject() {

        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        CommentDetail d = new CommentDetail();
        d.message = "a message";
        d.subject = "a subject";
        d.user = "user";

        commentDao.insertComment(job, d);
        commentDao.updateCommentSubject(d.getId(), "no");
        CommentDetail nd = commentDao.getCommentDetail(d.getId());
        assertEquals("no",nd.subject);
    }
}

