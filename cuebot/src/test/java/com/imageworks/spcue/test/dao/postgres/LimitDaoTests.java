
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
import java.sql.Timestamp;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import javax.annotation.Resource;

import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.LimitRule;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitBinding;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHold;
import com.imageworks.spcue.grpc.limit.LimitHoldSource;
import com.imageworks.spcue.grpc.limit.LimitHostUsage;
import com.imageworks.spcue.grpc.limit.LimitType;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.test.AssumingPostgresEngine;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
@SuppressWarnings("deprecation")
public class LimitDaoTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    LimitDao limitDao;

    @Resource
    LayerDao layerDao;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    private static String LIMIT_NAME = "test-limit";
    private static int LIMIT_MAX_VALUE = 32;

    private static Timestamp now() {
        return new Timestamp(System.currentTimeMillis());
    }

    private static LimitHostUsage hold(String host, int tokens, String user) {
        return LimitHostUsage.newBuilder().setHostName(host).setTokens(tokens).setUser(user)
                .build();
    }

    private LayerDetail launchJobAndGetLayer() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");
        return layerDao.findLayerDetail(job, "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCreateLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);
        assertEquals(limit.id, limitId);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);

        assertEquals(Integer.valueOf(1),
                jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM limit_record WHERE pk_limit_record=?", Integer.class,
                        limitId));

        limitDao.deleteLimit(limit);

        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM limit_record WHERE pk_limit_record=?", Integer.class,
                        limitId));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);

        LimitEntity limit = limitDao.findLimit(LIMIT_NAME);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindMissingLimitNames() {
        limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);

        assertEquals(Collections.emptyList(),
                limitDao.findMissingLimitNames(Collections.emptyList()));
        assertEquals(Collections.emptyList(),
                limitDao.findMissingLimitNames(Arrays.asList(LIMIT_NAME)));

        List<String> missing =
                limitDao.findMissingLimitNames(Arrays.asList("nope", LIMIT_NAME, "nada", "nope"));
        assertEquals(Arrays.asList("nope", "nada"), missing);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);

        LimitEntity limit = limitDao.getLimit(limitId);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetLimitName() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);
        String newName = "heyIChanged";

        limitDao.setLimitName(limit, newName);

        limit = limitDao.getLimit(limitId);
        assertEquals(limit.id, limitId);
        assertEquals(limit.name, newName);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetMaxValue() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);
        int newValue = 600;

        limitDao.setMaxValue(limit, newValue);

        limit = limitDao.getLimit(limitId);
        assertEquals(limit.id, limitId);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, newValue);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCreateLimitDefaults() {
        // The deprecated overload and the schema defaults both produce an ENFORCED FRAME limit
        // with no soft threshold: every pre-existing limit keeps today's semantics exactly.
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE));
        assertEquals(LimitType.FRAME, limit.type);
        assertEquals(LimitEnforcement.ENFORCED, limit.enforcement);
        assertEquals(-1, limit.softValue);
        assertEquals(0, limit.reportedTime);
        assertNull(limit.exitStatus);
        assertFalse(limit.isReportStale());
        assertTrue(limit.isBlocking());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testConfigurationRoundTrip() {
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 30, LimitType.HOST,
                LimitEnforcement.ADVISORY, 20));
        assertEquals(LimitType.HOST, limit.type);
        assertEquals(LimitEnforcement.ADVISORY, limit.enforcement);
        assertEquals(20, limit.softValue);
        assertFalse(limit.isBlocking());

        limitDao.setLimitType(limit, LimitType.FRAME);
        limitDao.setEnforcement(limit, LimitEnforcement.ENFORCED);
        limitDao.setSoftValue(limit, -1);
        limitDao.setReportTtl(limit, 300);

        limit = limitDao.getLimit(limit.getLimitId());
        assertEquals(LimitType.FRAME, limit.type);
        assertEquals(LimitEnforcement.ENFORCED, limit.enforcement);
        assertEquals(-1, limit.softValue);
        assertEquals(300, limit.reportTtl);
        assertTrue(limit.isBlocking());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSoftValueZeroMeansSameAsMax() {
        // 0 is the proto's "same as max_value" spelling on create; the dispatch gate only
        // understands -1, and a stored 0 would block every host that isn't already holding.
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 30, LimitType.HOST,
                LimitEnforcement.ENFORCED, 20));
        assertEquals(20, limit.softValue);

        limitDao.setSoftValue(limit, 0);

        assertEquals(-1, limitDao.getLimit(limit.getLimitId()).softValue);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFailureRuleRoundTrip() {
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE));
        limitDao.setFailureRule(limit, 330, 5, true);

        Map<Integer, LimitRule> rules = limitDao.getFailureRules();
        LimitRule rule = rules.get(330);
        assertEquals(limit.getLimitId(), rule.limitId);
        assertEquals(LIMIT_NAME, rule.limitName);
        assertEquals(5, rule.delayMinutes);
        assertTrue(rule.autoTag);

        // Clearing the rule removes the status claim entirely.
        limitDao.setFailureRule(limit, null, 0, true);
        assertNull(limitDao.getFailureRules().get(330));
        assertNull(limitDao.getLimit(limit.getLimitId()).exitStatus);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReplaceExternalHoldsInsertUpdateSweepAndClear() {
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 50, LimitType.HOST,
                LimitEnforcement.ENFORCED, -1));

        limitDao.replaceExternalHolds(limit,
                Arrays.asList(hold("alpha", 1, "artist1"), hold("bravo", 2, "")), "test", now());
        limitDao.refreshUsage(limit);
        limit = limitDao.getLimit(limit.getLimitId());
        assertEquals(2, limit.settledUsage);
        assertEquals(2, limit.hostCount);

        // bravo drops a token, alpha disappears, charlie shows up: upsert + sweep.
        limitDao.replaceExternalHolds(limit,
                Arrays.asList(hold("bravo", 1, ""), hold("charlie", 1, "artist2")), "test", now());
        limitDao.refreshUsage(limit);
        assertEquals(Integer.valueOf(1),
                jdbcTemplate.queryForObject(
                        "SELECT int_tokens FROM limit_host "
                                + "WHERE pk_limit_record=? AND str_host_name='bravo'",
                        Integer.class, limit.getLimitId()));
        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM limit_host "
                                + "WHERE pk_limit_record=? AND str_host_name='alpha'",
                        Integer.class, limit.getLimitId()));
        assertEquals(2, limitDao.getLimit(limit.getLimitId()).hostCount);

        // An empty holder list is meaningful: it clears the hold set.
        limitDao.replaceExternalHolds(limit, Collections.emptyList(), "test", now());
        limitDao.refreshUsage(limit);
        limit = limitDao.getLimit(limit.getLimitId());
        assertEquals(0, limit.settledUsage);
        assertEquals(0, limit.hostCount);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClaimReportWatermarkIsAtomicAdmission() {
        // The service-level OUT_OF_ORDER / RATE_LIMITED checks read the watermark without a
        // lock; this conditional update is what actually keeps two concurrent reporters from
        // both being admitted. Each rejection branch of the WHERE clause is exercised here.
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 50));
        long minIntervalMs = 5000L;

        assertTrue("A never-reported limit must admit the first report",
                limitDao.claimReportWatermark(limit, now(), "test", minIntervalMs));

        assertFalse("A second claim inside the interval must be rejected",
                limitDao.claimReportWatermark(limit, now(), "test", minIntervalMs));

        // Age the stored watermark past the interval; an older capture stays rejected while a
        // fresh one is admitted.
        Timestamp aged = new Timestamp(System.currentTimeMillis() - 60_000L);
        jdbcTemplate.update("UPDATE limit_record SET ts_reported = ? WHERE pk_limit_record = ?",
                aged, limit.getLimitId());
        assertFalse("A capture older than the stored watermark must be rejected",
                limitDao.claimReportWatermark(limit,
                        new Timestamp(System.currentTimeMillis() - 120_000L), "test",
                        minIntervalMs));
        assertTrue("A fresh capture after the interval must be admitted",
                limitDao.claimReportWatermark(limit, now(), "test", minIntervalMs));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnchangedHolderProducesNoNewRowVersion() {
        // The vacuum-churn guard: a 5-second reporter whose holders rarely change must not
        // rewrite the table every poll. An unchanged holder keeps its xmin; this regresses
        // silently if the DO UPDATE loses its IS DISTINCT FROM clause.
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 50));
        limitDao.replaceExternalHolds(limit, Arrays.asList(hold("alpha", 1, "artist1")), "test",
                now());
        String rowVersion = jdbcTemplate.queryForObject(
                "SELECT cmin::text FROM limit_host WHERE pk_limit_record=?", String.class,
                limit.getLimitId());

        limitDao.replaceExternalHolds(limit, Arrays.asList(hold("alpha", 1, "artist1")), "test",
                now());
        assertEquals("An unchanged holder must not produce a new row version", rowVersion,
                jdbcTemplate.queryForObject(
                        "SELECT cmin::text FROM limit_host WHERE pk_limit_record=?", String.class,
                        limit.getLimitId()));

        limitDao.replaceExternalHolds(limit, Arrays.asList(hold("alpha", 2, "artist1")), "test",
                now());
        assertNotEquals("A changed token count must write the row", rowVersion,
                jdbcTemplate.queryForObject(
                        "SELECT cmin::text FROM limit_host WHERE pk_limit_record=?", String.class,
                        limit.getLimitId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHostnameNormalizationCoalesces() {
        // An FQDN and a mixed-case short name for the same machine collapse to one row with
        // the highest token count seen.
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 50));
        limitDao.replaceExternalHolds(limit,
                Arrays.asList(hold("Render0142.studio.local", 1, "a"), hold("RENDER0142", 3, "b")),
                "test", now());
        limitDao.refreshUsage(limit);

        assertEquals(Integer.valueOf(1),
                jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM limit_host WHERE pk_limit_record=?", Integer.class,
                        limit.getLimitId()));
        assertEquals(Integer.valueOf(3),
                jdbcTemplate.queryForObject(
                        "SELECT int_tokens FROM limit_host "
                                + "WHERE pk_limit_record=? AND str_host_name='render0142'",
                        Integer.class, limit.getLimitId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testRefreshAllUsageAgreesWithRefreshUsage() {
        LimitEntity limitA = limitDao.getLimit(limitDao.createLimit("limit-a", 10));
        LimitEntity limitB = limitDao.getLimit(limitDao.createLimit("limit-b", 10));
        limitDao.replaceExternalHolds(limitA, Arrays.asList(hold("alpha", 2, "")), "test", now());
        limitDao.replaceExternalHolds(limitB, Arrays.asList(hold("bravo", 5, "")), "test", now());

        limitDao.refreshUsage(limitA);
        int settledA = limitDao.getLimit(limitA.getLimitId()).settledUsage;

        limitDao.refreshAllUsage();
        assertEquals(settledA, limitDao.getLimit(limitA.getLimitId()).settledUsage);
        assertEquals(5, limitDao.getLimit(limitB.getLimitId()).settledUsage);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetHoldsClassifiesExternalWorkstations() {
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 50));
        limitDao.replaceExternalHolds(limit, Arrays.asList(hold("ws-artist", 1, "artist1")), "test",
                now());

        List<LimitHold> holds = limitDao.getHolds(limit, null);
        assertEquals(1, holds.size());
        LimitHold hold = holds.get(0);
        assertEquals("ws-artist", hold.getHostName());
        assertEquals(LimitHoldSource.EXTERNAL, hold.getSource());
        assertEquals("artist1", hold.getUser());
        // Not a registered render host, so there is no host id to jump to.
        assertEquals("", hold.getHostId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetHoldsFiltersByHost() {
        LimitEntity limit = limitDao.getLimit(limitDao.createLimit(LIMIT_NAME, 50));
        limitDao.replaceExternalHolds(limit,
                Arrays.asList(hold("alpha", 1, ""), hold("bravo", 1, "")), "test", now());

        // Callers asking about one machine must not pull every holder on the farm. An FQDN
        // resolves the same as the short name the holder set is keyed by.
        assertEquals(2, limitDao.getHolds(null).size());
        assertEquals(1, limitDao.getHolds("alpha").size());
        assertEquals("alpha", limitDao.getHolds("ALPHA.studio.local").get(0).getHostName());
        assertEquals(1, limitDao.getHolds(limit, "bravo").size());
        assertEquals(0, limitDao.getHolds("charlie").size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testBindingProvenanceAndClear() {
        LayerDetail layer = launchJobAndGetLayer();
        LimitEntity specLimit = limitDao.getLimit(limitDao.createLimit("spec-limit", 10));
        LimitEntity autoLimit = limitDao.getLimit(limitDao.createLimit("auto-limit", 10));

        assertTrue(layerDao.addLimit(layer, specLimit.getLimitId(), LimitBindSource.SPEC));
        assertTrue(layerDao.addLimit(layer, autoLimit.getLimitId(), LimitBindSource.AUTO));

        // A layer already bound by its job spec keeps SPEC after an auto-tag attempt: a
        // submitter's declaration is never downgraded to a machine's guess.
        assertFalse(layerDao.addLimit(layer, specLimit.getLimitId(), LimitBindSource.AUTO));
        List<LimitBinding> specBindings =
                limitDao.getBindings(specLimit, EnumSet.of(LimitBindSource.SPEC), null);
        assertEquals(1, specBindings.size());
        assertEquals(layer.getLayerId(), specBindings.get(0).getLayerId());

        List<LimitBinding> autoBindings =
                limitDao.getBindings(autoLimit, EnumSet.noneOf(LimitBindSource.class), null);
        assertEquals(1, autoBindings.size());
        assertEquals(LimitBindSource.AUTO, autoBindings.get(0).getSource());
        assertTrue(autoBindings.get(0).getServicesList().contains("katana"));

        // Filtering by layer answers "is this layer bound?" without returning every binding
        // the limit has farm-wide.
        assertEquals(1,
                limitDao.getBindings(autoLimit, null, Arrays.asList(layer.getLayerId())).size());
        assertEquals(0, limitDao
                .getBindings(autoLimit, null, Arrays.asList("00000000-0000-0000-0000-000000000000"))
                .size());

        assertEquals(1, limitDao.getLimit(specLimit.getLimitId()).specLayerCount);
        assertEquals(1, limitDao.getLimit(autoLimit.getLimitId()).autoLayerCount);

        // clearBindings removes AUTO and never touches SPEC, even when asked to.
        assertEquals(1, limitDao.clearBindings(autoLimit, EnumSet.of(LimitBindSource.AUTO)));
        assertEquals(0, limitDao.clearBindings(specLimit, EnumSet.of(LimitBindSource.SPEC)));
        assertEquals(1, limitDao.getLimit(specLimit.getLimitId()).specLayerCount);
        assertEquals(0, limitDao.getLimit(autoLimit.getLimitId()).autoLayerCount);
    }
}
