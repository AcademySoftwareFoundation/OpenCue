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

package com.imageworks.spcue.dispatcher;

import java.io.File;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHostUsage;
import com.imageworks.spcue.grpc.limit.LimitType;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * Maestro's per-tick limit budgets against the real limit tables: the resolver must count exactly
 * like the legacy dispatcher's gate (it reuses that gate's CTE), give HOST limits their holder
 * seats, and give no budget at all to limits the gate would not apply.
 */
@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class MaestroLimitBudgetTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    Maestro maestro;
    @Resource
    LimitDao limitDao;
    @Resource
    LayerDao layerDao;
    @Resource
    JobManager jobManager;
    @Resource
    JobLauncher jobLauncher;

    private static final String LIMIT_NAME = "houdini";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    private JobDetail getJob() {
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");
    }

    /** Creates the limit and binds pass_1 to it. */
    private LimitEntity createBoundLimit(int maxValue, LimitType type,
            LimitEnforcement enforcement) {
        String limitId = limitDao.createLimit(LIMIT_NAME, maxValue, type, enforcement, -1);
        LayerDetail layer = layerDao.findLayerDetail(getJob(), "pass_1");
        assertTrue(layerDao.addLimit(layer, limitId, LimitBindSource.SPEC));
        return limitDao.getLimit(limitId);
    }

    /** Applies an external report of one token per named host and refreshes the usage row. */
    private void report(LimitEntity limit, String... hosts) {
        List<LimitHostUsage> holds = new ArrayList<LimitHostUsage>();
        for (String host : hosts) {
            holds.add(LimitHostUsage.newBuilder().setHostName(host).setTokens(1).build());
        }
        limitDao.replaceExternalHolds(limit, holds, "test",
                new Timestamp(System.currentTimeMillis()));
        limitDao.refreshUsage(limit);
    }

    /** One synthetic candidate bound to the given limit ids. */
    private Maestro.LayerCandidate candidate(String... limitIds) {
        Maestro.LayerCandidate c = new Maestro.LayerCandidate();
        c.layerId = layerDao.findLayerDetail(getJob(), "pass_1").getLayerId();
        c.limitIds = limitIds.length == 0 ? null : new ArrayList<>(List.of(limitIds));
        return c;
    }

    private Map<String, Maestro.LimitBudget> resolve(Maestro.LayerCandidate c) {
        Map<String, List<String>> layerLimits = new HashMap<>();
        Map<String, Maestro.LimitBudget> budgets = new HashMap<>();
        maestro.limitBudgetsResolved = false;
        maestro.resolveLimitBudgets(Collections.singletonList(c), layerLimits, budgets);
        if (c.limitIds != null) {
            assertEquals(c.limitIds, layerLimits.get(c.layerId));
        }
        return budgets;
    }

    @Test
    public void frameLimitBudgetIsMaxMinusUsage() {
        LimitEntity limit = createBoundLimit(5, LimitType.FRAME, LimitEnforcement.ENFORCED);
        Map<String, Maestro.LimitBudget> budgets = resolve(candidate(limit.getLimitId()));
        Maestro.LimitBudget b = budgets.get(limit.getLimitId());
        assertFalse(b.hostBased);
        assertEquals(5, b.usable);
        assertEquals(LIMIT_NAME, b.name);
    }

    @Test
    public void advisoryAndDisabledLimitsGetNoBudget() {
        LimitEntity advisory = createBoundLimit(5, LimitType.FRAME, LimitEnforcement.ADVISORY);
        String disabledId =
                limitDao.createLimit("nuke", 5, LimitType.FRAME, LimitEnforcement.DISABLED, -1);
        Map<String, Maestro.LimitBudget> budgets =
                resolve(candidate(advisory.getLimitId(), disabledId));
        assertNull(budgets.get(advisory.getLimitId()));
        assertNull(budgets.get(disabledId));
    }

    @Test
    public void staleReportedLimitGetsNoBudget() {
        LimitEntity limit = createBoundLimit(5, LimitType.HOST, LimitEnforcement.ENFORCED);
        report(limit, "wolf1018");
        // Age the report past the TTL: the gate must stop applying the limit.
        jdbcTemplate.update(
                "UPDATE limit_record SET ts_reported = current_timestamp - INTERVAL '1 hour', "
                        + "int_report_ttl = 60 WHERE pk_limit_record = ?",
                limit.getLimitId());
        Map<String, Maestro.LimitBudget> budgets = resolve(candidate(limit.getLimitId()));
        assertNull(budgets.get(limit.getLimitId()));
    }

    @Test
    public void hostLimitBudgetCarriesSeatsAndCap() {
        LimitEntity limit = createBoundLimit(3, LimitType.HOST, LimitEnforcement.ENFORCED);
        report(limit, "wolf1018");
        Map<String, Maestro.LimitBudget> budgets = resolve(candidate(limit.getLimitId()));
        Maestro.LimitBudget b = budgets.get(limit.getLimitId());
        assertTrue(b.hostBased);
        assertTrue(b.seats.contains("wolf1018"));
        // One seat held, usage 1 of 3: the holder plus two new machines.
        assertEquals(3, b.seatCap);
    }

    @Test
    public void limitSeatsAllowHoldersAndHeadroomOnly() {
        Set<String> seats = new HashSet<>(List.of("held1"));
        Maestro.LimitBudget pool = new Maestro.LimitBudget("id1", LIMIT_NAME, true, 0, 2, seats);
        Map<String, Set<String>> limitSeats = new HashMap<>();
        limitSeats.put("id1", seats);
        List<Maestro.LimitBudget> pools = Collections.singletonList(pool);

        Maestro.BookableHost holder = new Maestro.BookableHost();
        holder.hostName = "HELD1.example.com";
        Maestro.BookableHost fresh = new Maestro.BookableHost();
        fresh.hostName = "fresh1";

        // The holder is always allowed; a new machine takes the last seat.
        assertTrue(Maestro.limitSeatsAllow(pools, limitSeats, holder));
        assertTrue(Maestro.limitSeatsAllow(pools, limitSeats, fresh));
        seats.add("fresh1");

        // Cap reached: only holders may book now.
        Maestro.BookableHost third = new Maestro.BookableHost();
        third.hostName = "fresh2";
        assertFalse(Maestro.limitSeatsAllow(pools, limitSeats, third));
        assertTrue(Maestro.limitSeatsAllow(pools, limitSeats, holder));
    }

    @Test
    public void splitIdsDropsBlanksAndDuplicates() {
        assertEquals(List.of("a", "b"), Maestro.splitIds("a, b ,a,"));
        assertTrue(Maestro.splitIds(null).isEmpty());
        assertTrue(Maestro.splitIds(" ").isEmpty());
    }
}
