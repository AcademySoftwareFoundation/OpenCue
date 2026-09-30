
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

package com.imageworks.spcue.test.dao.postgres;

import java.io.File;
import javax.annotation.Resource;

import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.NestedWhiteboardDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.NestedGroup;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.test.AssumingPostgresEngine;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class NestedWhiteboardDaoTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    NestedWhiteboardDao nestedWhiteboardDao;

    @Resource
    ShowDao showDao;

    @Resource
    JobLauncher jobLauncher;

    public ShowEntity getShow() {
        return showDao.findShowDetail("pipe");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetNestedJobWhiteboard() {
        nestedWhiteboardDao.getJobWhiteboard(getShow());
        nestedWhiteboardDao.getJobWhiteboard(getShow());
        nestedWhiteboardDao.getJobWhiteboard(getShow());
        nestedWhiteboardDao.getJobWhiteboard(getShow());
        nestedWhiteboardDao.getJobWhiteboard(getShow());
    }

    /**
     * Guards the inline_jobs hydration: the whiteboard mapper must populate NestedGroup.inline_jobs
     * alongside the existing job-ID list. CueGUI now relies on this to skip the per-group getJobs
     * fan-out — if a future change drops the addInlineJobs call (or trims a column from
     * GET_NESTED_GROUPS so JOB_MAPPER fails silently), the client falls back to the slow path with
     * no visible error.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testGetNestedJobWhiteboardPopulatesInlineJobs() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));

        NestedGroup root = nestedWhiteboardDao.getJobWhiteboard(getShow());
        assertNotNull(root);
        boolean foundInlineJob = hasInlineJob(root);
        assertTrue("expected at least one NestedGroup to expose inline_jobs", foundInlineJob);
    }

    private boolean hasInlineJob(NestedGroup group) {
        if (!group.getInlineJobsList().isEmpty()) {
            // Inline jobs must carry the same IDs as the parallel job-ID list — the
            // client switches branches on inline_jobs and would otherwise display
            // ghosts.
            assertFalse("inline_jobs populated but jobs list empty", group.getJobsList().isEmpty());
            Job inline = group.getInlineJobsList().get(0);
            assertFalse("inline job missing id", inline.getId().isEmpty());
            assertFalse("inline job missing name", inline.getName().isEmpty());
            return true;
        }
        for (NestedGroup child : group.getGroups().getNestedGroupsList()) {
            if (hasInlineJob(child)) {
                return true;
            }
        }
        return false;
    }
}
