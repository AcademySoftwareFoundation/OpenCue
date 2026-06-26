
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

package com.imageworks.spcue.test.service;

import org.junit.Before;
import org.junit.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.service.AccountingNotifier;

import static org.mockito.Mockito.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Unit tests for {@link AccountingNotifier}. Mocks the {@link JdbcTemplate} (injected into the
 * {@code JdbcDaoSupport} base field) and asserts the exact {@code SELECT pg_notify} channel and
 * JSON payload for a release and for each enforced cap change. This pins the wire contract the Rust
 * scheduler's NOTIFY listener parses (see docs/_docs/developer-guide/scheduler-accounting.md).
 */
public class AccountingNotifierTests {

    private static final String NOTIFY_SQL = "SELECT pg_notify(?, ?)";
    private static final String CHANNEL_RELEASE = "acct_release";
    private static final String CHANNEL_LIMIT = "acct_limit_change";

    private static final String SHOW_ID = "show-uuid";
    private static final String JOB_ID = "job-uuid";
    private static final String LAYER_ID = "layer-uuid";
    private static final String ALLOC_ID = "alloc-uuid";
    private static final String FOLDER_ID = "folder-uuid";
    private static final String DEPT_ID = "dept-uuid";

    private AccountingNotifier notifier;
    private JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
    private VirtualProc proc;

    @Before
    public void setUp() {
        notifier = new AccountingNotifier();
        // Bypass @PostConstruct (no Environment); enable and inject the mock JdbcTemplate held by
        // the JdbcDaoSupport base class.
        ReflectionTestUtils.setField(notifier, "notifyEnabled", true);
        ReflectionTestUtils.setField(notifier, "jdbcTemplate", jdbcTemplate);

        proc = new VirtualProc();
        proc.id = "proc-uuid";
        proc.showId = SHOW_ID;
        proc.jobId = JOB_ID;
        proc.layerId = LAYER_ID;
        proc.allocationId = ALLOC_ID;
        proc.folderId = FOLDER_ID;
        proc.deptId = DEPT_ID;
        // 400 centicores = 4 cores; converted to cores on the way out and negated for a release.
        // 4 != 2 (gpus) keeps the two negated values disambiguated in the payload assertion.
        proc.coresReserved = 400;
        proc.gpusReserved = 2;
    }

    @Test
    public void disabledNotifierIsNoop() {
        ReflectionTestUtils.setField(notifier, "notifyEnabled", false);

        notifier.notifyRelease(proc);
        notifier.notifySubscriptionBurst(SHOW_ID, ALLOC_ID, 1500);
        notifier.notifyFolderMaxCores(FOLDER_ID, 800);
        notifier.notifyFolderMaxGpus(FOLDER_ID, 3);
        notifier.notifyJobMaxCores(JOB_ID, 1600);
        notifier.notifyJobMaxGpus(JOB_ID, 4);

        verifyNoInteractions(jdbcTemplate);
    }

    @Test
    public void notifyReleaseEmitsNegatedDelta() {
        notifier.notifyRelease(proc);

        // Cores converted to cores (400/100=4) then negated; gpus pass through then negated.
        String expected = "{\"show\":\"show-uuid\",\"alloc\":\"alloc-uuid\","
                + "\"folder\":\"folder-uuid\",\"job\":\"job-uuid\",\"layer\":\"layer-uuid\","
                + "\"dept\":\"dept-uuid\",\"cores\":-4,\"gpus\":-2}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_RELEASE), eq(expected));
    }

    @Test
    public void notifySubscriptionBurstConvertsCentiCores() {
        notifier.notifySubscriptionBurst(SHOW_ID, ALLOC_ID, 1500);

        String expected = "{\"vertex\":\"sub\",\"show\":\"show-uuid\",\"alloc\":\"alloc-uuid\","
                + "\"burst\":15}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_LIMIT), eq(expected));
    }

    @Test
    public void notifyFolderMaxCoresConvertsCentiCores() {
        notifier.notifyFolderMaxCores(FOLDER_ID, 800);

        String expected = "{\"vertex\":\"folder\",\"id\":\"folder-uuid\",\"max_cores\":8}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_LIMIT), eq(expected));
    }

    @Test
    public void notifyFolderMaxCoresPreservesUnlimitedSentinel() {
        notifier.notifyFolderMaxCores(FOLDER_ID, -1);

        String expected = "{\"vertex\":\"folder\",\"id\":\"folder-uuid\",\"max_cores\":-1}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_LIMIT), eq(expected));
    }

    @Test
    public void notifyFolderMaxGpusPassesThrough() {
        notifier.notifyFolderMaxGpus(FOLDER_ID, 3);

        String expected = "{\"vertex\":\"folder\",\"id\":\"folder-uuid\",\"max_gpus\":3}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_LIMIT), eq(expected));
    }

    @Test
    public void notifyJobMaxCoresConvertsCentiCores() {
        notifier.notifyJobMaxCores(JOB_ID, 1600);

        String expected = "{\"vertex\":\"job\",\"id\":\"job-uuid\",\"max_cores\":16}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_LIMIT), eq(expected));
    }

    @Test
    public void notifyJobMaxCoresPreservesUnlimitedSentinel() {
        notifier.notifyJobMaxCores(JOB_ID, -100);

        String expected = "{\"vertex\":\"job\",\"id\":\"job-uuid\",\"max_cores\":-1}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_LIMIT), eq(expected));
    }

    @Test
    public void notifyJobMaxGpusPassesThrough() {
        notifier.notifyJobMaxGpus(JOB_ID, 4);

        String expected = "{\"vertex\":\"job\",\"id\":\"job-uuid\",\"max_gpus\":4}";
        verify(jdbcTemplate).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_LIMIT), eq(expected));
        verify(jdbcTemplate, never()).queryForList(eq(NOTIFY_SQL), eq(CHANNEL_RELEASE),
                org.mockito.ArgumentMatchers.anyString());
    }
}
