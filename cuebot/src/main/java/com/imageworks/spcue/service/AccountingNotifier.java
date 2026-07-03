
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

import java.util.Map;

import javax.annotation.PostConstruct;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.ShowDao;

/**
 * Publishes per-release and admin cap-change accounting deltas to the standalone Rust scheduler via
 * Postgres {@code LISTEN/NOTIFY}. Every notification is emitted with {@code pg_notify(channel,
 * payload)} <em>inside</em> the same transaction as the DB write it describes, so the payload is
 * delivered if and only if that transaction commits (this replaces the old afterCommit Redis
 * publish with a transactional, stronger failure model).
 *
 * <p>
 * See the Scheduler Accounting Reference at
 * {@code docs/_docs/developer-guide/scheduler-accounting.md} for the wire contract.
 *
 * <p>
 * Gated by {@code accounting.notify.enabled} (default true). When false, every method is a no-op;
 * the scheduler then degrades to recompute-only from {@code SUM(proc)}, which under-books rather
 * than over-books, so disabling is safe (visibility-only WARN on startup, not a hard guard).
 *
 * <p>
 * Unit invariant: Cuebot stores cores as centicores (cores × 100). The scheduler accounts in cores,
 * so cores are integer-divided by 100 on the way out. GPUs are stored in whole units and pass
 * through unconverted. The {@code -1} "unlimited" sentinel on max caps is preserved.
 */
public class AccountingNotifier extends JdbcDaoSupport {

    private static final Logger logger = LogManager.getLogger(AccountingNotifier.class);

    /** NOTIFY channel for proc releases (negated cores/gpus deltas). */
    static final String CHANNEL_RELEASE = "acct_release";

    /** NOTIFY channel for enforced admin cap changes (subscription burst, folder/job max). */
    static final String CHANNEL_LIMIT_CHANGE = "acct_limit_change";

    /**
     * Cuebot stores cores as centicores (cores × 100; see VirtualProc.java). The scheduler accounts
     * in cores, so we divide on the way out. The divide is exact: VirtualProc forces coresReserved
     * to a multiple of 100 at booking time, and cap values are whole-core multiples of 100.
     */
    static final int CENTICORES_PER_CORE = 100;

    @Autowired
    private Environment env;

    @Autowired
    private ShowDao showDao;

    private volatile boolean notifyEnabled = true;

    @PostConstruct
    public void initialize() {
        notifyEnabled = env.getProperty("accounting.notify.enabled", Boolean.class, true);
        if (!notifyEnabled) {
            // Visibility only (NOT a hard guard): flag-off degrades the scheduler to
            // recompute-only from SUM(proc), which under-books rather than over-books.
            int managedCount = showDao.countSchedulerManagedShows();
            if (managedCount > 0) {
                logger.warn("accounting.notify.enabled=false but {} scheduler-managed show(s) "
                        + "exist; the standalone scheduler will rely on periodic recompute only "
                        + "(no live release/limit-change deltas).", managedCount);
            }
            logger.info("Accounting NOTIFY publishing disabled (accounting.notify.enabled=false)");
        } else {
            logger.info("Accounting NOTIFY publishing enabled");
        }
    }

    /** True when this notifier actually emits pg_notify. */
    public boolean isEnabled() {
        return notifyEnabled;
    }

    /**
     * Emit an {@code acct_release} delta for a destroyed proc on the {@code acct_release} channel.
     * Cores and GPUs are NEGATED (a release returns resources). Must be called from within the same
     * transaction as the {@code DELETE proc} it describes.
     *
     * <p>
     * folderId, deptId, and allocationId are read directly from the {@link VirtualProc} fields
     * hydrated by {@code ProcDaoJdbc.VIRTUAL_PROC_MAPPER}. A defensive fallback populates
     * folderId/deptId from the job table and allocationId from the host table if a caller built the
     * proc manually instead of going through a SELECT.
     */
    public void notifyRelease(VirtualProc proc) {
        if (!notifyEnabled) {
            return;
        }

        if (proc.folderId == null || proc.deptId == null) {
            Map<String, Object> jobMeta = getJdbcTemplate().queryForMap(
                    "SELECT pk_folder, pk_dept FROM job WHERE pk_job=?", proc.getJobId());
            proc.folderId = (String) jobMeta.get("pk_folder");
            proc.deptId = (String) jobMeta.get("pk_dept");
        }

        // allocationId is sourced from host.pk_alloc (see VIRTUAL_PROC_MAPPER), not the job row, so
        // backfill it separately to avoid publishing an alloc of null.
        if (proc.getAllocationId() == null) {
            proc.allocationId = getJdbcTemplate().queryForObject(
                    "SELECT pk_alloc FROM host WHERE pk_host=?", String.class, proc.getHostId());
        }

        int cores = -proc.coresReserved / CENTICORES_PER_CORE;
        int gpus = -proc.gpusReserved;
        // Slots are whole counts (no centicore conversion); negated like cores/gpus. 0 for
        // regular procs, so this is a no-op on the scheduler's slot axis for non-slot procs.
        int slots = -proc.slotsReserved;
        String payload = String.format(
                "{\"show\":\"%s\",\"alloc\":\"%s\",\"folder\":\"%s\",\"job\":\"%s\","
                        + "\"layer\":\"%s\",\"dept\":\"%s\",\"cores\":%d,\"gpus\":%d,\"slots\":%d}",
                proc.getShowId(), proc.getAllocationId(), proc.folderId, proc.getJobId(),
                proc.getLayerId(), proc.deptId, cores, gpus, slots);
        notify(CHANNEL_RELEASE, payload);
    }

    /** Emit a subscription-burst cap change. {@code burst} is in centicores. */
    public void notifySubscriptionBurst(String showId, String allocId, int burst) {
        if (!notifyEnabled) {
            return;
        }
        String payload =
                String.format("{\"vertex\":\"sub\",\"show\":\"%s\",\"alloc\":\"%s\",\"burst\":%d}",
                        showId, allocId, burst / CENTICORES_PER_CORE);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /**
     * Emit a folder max-cores cap change. {@code value} is in centicores; &lt;0 means unlimited.
     */
    public void notifyFolderMaxCores(String folderId, int value) {
        if (!notifyEnabled) {
            return;
        }
        int maxCores = value < 0 ? -1 : value / CENTICORES_PER_CORE;
        String payload = String.format("{\"vertex\":\"folder\",\"id\":\"%s\",\"max_cores\":%d}",
                folderId, maxCores);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /**
     * Emit a folder max-gpus cap change. GPUs pass through unconverted ({@code -1} = unlimited).
     */
    public void notifyFolderMaxGpus(String folderId, int value) {
        if (!notifyEnabled) {
            return;
        }
        String payload = String.format("{\"vertex\":\"folder\",\"id\":\"%s\",\"max_gpus\":%d}",
                folderId, value);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /** Emit a job max-cores cap change. {@code value} is in centicores; &lt;0 means unlimited. */
    public void notifyJobMaxCores(String jobId, int value) {
        if (!notifyEnabled) {
            return;
        }
        int maxCores = value < 0 ? -1 : value / CENTICORES_PER_CORE;
        String payload = String.format("{\"vertex\":\"job\",\"id\":\"%s\",\"max_cores\":%d}", jobId,
                maxCores);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /** Emit a job max-gpus cap change. GPUs pass through unconverted ({@code -1} = unlimited). */
    public void notifyJobMaxGpus(String jobId, int value) {
        if (!notifyEnabled) {
            return;
        }
        String payload =
                String.format("{\"vertex\":\"job\",\"id\":\"%s\",\"max_gpus\":%d}", jobId, value);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /**
     * Emit a subscription max-slots cap change. Slots are whole counts (no centicore conversion);
     * {@code -1} = unlimited, {@code 0} = reject all slot work.
     */
    public void notifySubscriptionMaxSlots(String showId, String allocId, int value) {
        if (!notifyEnabled) {
            return;
        }
        String payload = String.format(
                "{\"vertex\":\"sub\",\"show\":\"%s\",\"alloc\":\"%s\",\"max_slots\":%d}", showId,
                allocId, value);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /** Emit a folder max-slots cap change. Whole counts; {@code -1} = unlimited. */
    public void notifyFolderMaxSlots(String folderId, int value) {
        if (!notifyEnabled) {
            return;
        }
        String payload = String.format("{\"vertex\":\"folder\",\"id\":\"%s\",\"max_slots\":%d}",
                folderId, value);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /** Emit a job max-slots cap change. Whole counts; {@code -1} = unlimited. */
    public void notifyJobMaxSlots(String jobId, int value) {
        if (!notifyEnabled) {
            return;
        }
        String payload =
                String.format("{\"vertex\":\"job\",\"id\":\"%s\",\"max_slots\":%d}", jobId, value);
        notify(CHANNEL_LIMIT_CHANGE, payload);
    }

    /**
     * Issue the {@code pg_notify} inside the current transaction. All payload fields are UUIDs or
     * integers (built via String.format), so no JSON escaping is required.
     *
     * <p>
     * {@code pg_notify} is a {@code SELECT} that returns a (void) result set, so it MUST be run as
     * a query, not via {@code update()}/{@code executeUpdate()} — pgjdbc throws "A result was
     * returned when none was expected" from {@code executeUpdate()}, which would roll back the
     * surrounding unbook/admin transaction. {@code queryForList} routes through
     * {@code executeQuery()} and discards the single void row; the NOTIFY still queues against the
     * transaction-bound connection and is delivered on commit.
     */
    private void notify(String channel, String payload) {
        getJdbcTemplate().queryForList("SELECT pg_notify(?, ?)", channel, payload);
    }
}
