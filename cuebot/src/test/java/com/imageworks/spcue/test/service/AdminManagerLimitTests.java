
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

import java.util.Arrays;
import java.util.EnumSet;
import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.LimitExitStatusClaimedException;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHostUsage;
import com.imageworks.spcue.grpc.limit.LimitReport;
import com.imageworks.spcue.grpc.limit.LimitReportSkipReason;
import com.imageworks.spcue.grpc.limit.LimitType;
import com.imageworks.spcue.service.AdminManager;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.fail;

/**
 * The ReportUsage and SetFailureRule contracts as the servant relies on them: validation of exit
 * statuses, single ownership of a status, the per-limit rate limit, unknown limits collected rather
 * than thrown, and the reporter-supplied capture time driving the watermark.
 */
@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class AdminManagerLimitTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    AdminManager adminManager;

    @Resource
    LimitDao limitDao;

    private LimitInterface createLimit(String name) {
        return limitDao.getLimit(adminManager.createLimit(name, 30, LimitType.HOST,
                LimitEnforcement.ADVISORY, -1, null, 0, true));
    }

    private static LimitReport report(String limitName, long captureTime, int totalLicenses,
            String... hosts) {
        LimitReport.Builder builder = LimitReport.newBuilder().setLimitName(limitName)
                .setCaptureTime(captureTime).setTotalLicenses(totalLicenses);
        for (String host : hosts) {
            builder.addHosts(LimitHostUsage.newBuilder().setHostName(host).setTokens(1));
        }
        return builder.build();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetFailureRuleRejectsReservedStatuses() {
        LimitInterface limit = createLimit("houdini");
        for (int status : new int[] {1, -5}) {
            try {
                adminManager.setLimitFailureRule(limit, status, 5, true);
                fail("Exit status " + status + " must be rejected");
            } catch (IllegalArgumentException expected) {
                // 0 is success and 1 is the generic catch-all failure; claiming either would
                // tag nearly every failing layer on the farm.
            }
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testExitStatusHasOneOwner() {
        LimitInterface houdini = createLimit("houdini");
        LimitInterface mari = createLimit("mari");
        adminManager.setLimitFailureRule(houdini, 330, 5, true);

        // Re-setting your own status is fine.
        adminManager.setLimitFailureRule(houdini, 330, 2, false);

        try {
            adminManager.setLimitFailureRule(mari, 330, 5, true);
            fail("A status claimed by another limit must be rejected");
        } catch (LimitExitStatusClaimedException e) {
            assertEquals("houdini", e.getClaimingLimitName());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClearingRuleKeepsAutoBindings() {
        LimitInterface limit = createLimit("houdini");
        adminManager.setLimitFailureRule(limit, 330, 5, true);
        adminManager.setLimitFailureRule(limit, 0, 0, true);
        assertNull("Clearing the rule must drop the status claim",
                limitDao.getLimit(limit.getLimitId()).exitStatus);
        // Turning a rule off is not the same as declaring everything it learned to be wrong;
        // removing AUTO bindings is a separate, explicit call, which never touches SPEC.
        try {
            adminManager.clearLimitBindings(limit, EnumSet.of(LimitBindSource.SPEC));
            fail("Bulk-removing SPEC bindings must be rejected");
        } catch (IllegalArgumentException expected) {
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReportUsageAppliesSnapshotAndCollectsUnknowns() {
        createLimit("houdini");
        long captureTime = System.currentTimeMillis() / 1000 - 60;

        AdminManager.LimitReportResult result = adminManager.reportLimitUsage(
                Arrays.asList(report("houdini", captureTime, 25, "alpha", "bravo"),
                        report("karma", captureTime, 0, "alpha")),
                "sesictrl@test");

        // sesictrl reports every product SideFX sells; the farm has limits for a few of them.
        assertEquals(1, result.appliedLimitIds.size());
        assertEquals(Arrays.asList("karma"), result.unknownLimits);

        LimitEntity applied = limitDao.getLimit(result.appliedLimitIds.get(0));
        assertEquals(2, applied.settledUsage);
        // total_licenses > 0 pushes the pool size into max_value.
        assertEquals(25, applied.maxValue);
        // The reporter-supplied capture time is the watermark, so a slow reporter does not
        // silently discard the bookings made while it ran.
        assertEquals(captureTime, applied.reportedTime / 1000);
        assertEquals("sesictrl@test", applied.reportSource);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReportUsageRejectsZeroTokens() {
        createLimit("houdini");
        LimitReport bad = LimitReport.newBuilder().setLimitName("houdini")
                .addHosts(LimitHostUsage.newBuilder().setHostName("alpha").setTokens(0)).build();
        try {
            adminManager.reportLimitUsage(Arrays.asList(bad), "test");
            fail("tokens = 0 must be rejected; hosts holding nothing are omitted");
        } catch (IllegalArgumentException expected) {
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReportUsageSkipsRateLimitedWithoutLosingTheBatch() {
        createLimit("houdini");
        createLimit("katana");
        long now = System.currentTimeMillis() / 1000;
        adminManager.reportLimitUsage(Arrays.asList(report("houdini", now, 0, "alpha")), "test");

        // Another reporter covering houdini must not cost katana its update: losing that race
        // is normal, and a rolled-back katana would drift stale and stop blocking.
        AdminManager.LimitReportResult result = adminManager.reportLimitUsage(
                Arrays.asList(report("houdini", now, 0, "alpha"), report("katana", now, 0, "beta")),
                "test");

        assertEquals(1, result.skippedLimits.size());
        assertEquals("houdini", result.skippedLimits.get(0).getLimitName());
        assertEquals(LimitReportSkipReason.RATE_LIMITED, result.skippedLimits.get(0).getReason());
        assertEquals(1, result.appliedLimitIds.size());
        assertEquals("katana", limitDao.getLimit(result.appliedLimitIds.get(0)).name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReportUsageSkipsOutOfOrderSnapshot() {
        createLimit("houdini");
        createLimit("katana");
        long now = System.currentTimeMillis() / 1000;
        adminManager.reportLimitUsage(Arrays.asList(report("houdini", now, 0, "alpha")), "test");
        long watermark = limitDao.findLimit("houdini").reportedTime;

        // A snapshot older than the watermark -- a skewed clock or a replayed queue entry --
        // must not rewind ts_reported: that disarms the interval check and reads as stale at
        // once. Skip it, keep the holds already recorded, and still apply the rest of the batch.
        AdminManager.LimitReportResult result = adminManager
                .reportLimitUsage(Arrays.asList(report("houdini", now - 3600, 0, "beta"),
                        report("katana", now, 0, "gamma")), "test");

        assertEquals(1, result.skippedLimits.size());
        assertEquals("houdini", result.skippedLimits.get(0).getLimitName());
        assertEquals(LimitReportSkipReason.OUT_OF_ORDER, result.skippedLimits.get(0).getReason());
        assertEquals(watermark, limitDao.findLimit("houdini").reportedTime);
        assertEquals(1, result.appliedLimitIds.size());
        assertEquals("katana", limitDao.getLimit(result.appliedLimitIds.get(0)).name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReportUsageValidatesWholeBatchBeforeApplyingAny() {
        createLimit("houdini");
        createLimit("katana");
        long now = System.currentTimeMillis() / 1000;
        // A malformed row anywhere in the batch rejects the request; nothing may be applied,
        // otherwise the @Transactional rollback would silently discard the good reports.
        LimitReport bad = LimitReport.newBuilder().setLimitName("katana")
                .addHosts(LimitHostUsage.newBuilder().setHostName("beta").setTokens(0)).build();
        try {
            adminManager.reportLimitUsage(Arrays.asList(report("houdini", now, 0, "alpha"), bad),
                    "test");
            fail("tokens = 0 anywhere in the batch must reject the request");
        } catch (IllegalArgumentException expected) {
        }

        assertEquals(0, limitDao.findLimit("houdini").reportedTime);
    }
}
