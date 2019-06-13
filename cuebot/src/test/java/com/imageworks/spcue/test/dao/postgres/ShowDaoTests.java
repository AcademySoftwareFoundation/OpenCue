
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

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.util.CueUtil;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class ShowDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    ShowDao showDao;

    @Autowired
    HostManager hostManager;

    @Autowired
    AdminManager adminManager;

    private static String SHOW_ID = "00000000-0000-0000-0000-000000000000";
    private static String SHOW_NAME= "pipe";

    public DispatchHost createHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName("test_host")
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem((int) CueUtil.GB16)
                .setTotalSwap((int) CueUtil.GB16)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("general")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return dh;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindShowDetail() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        assertEquals(SHOW_ID, show.id);
        assertEquals(SHOW_NAME,show.name);
        assertFalse(show.paused);
    }

    @Test(expected=EmptyResultDataAccessException.class)
    @Transactional
    @Rollback(true)
    public void testFindShowDetailByHost() {
        // TODO: Add code to setup a host and make the sow
        //  prefer the host, then check result again.
        showDao.getShowDetail(createHost());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetShowDetail() {
        ShowEntity show = showDao.getShowDetail(SHOW_ID);
        assertEquals(SHOW_ID, show.id);
        assertEquals(SHOW_NAME,show.name);
        assertFalse(show.paused);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertShow() {
        ShowEntity show = new ShowEntity();
        show.name = "uber";
        showDao.insertShow(show);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT count(*) FROM show where str_name=?",
                Integer.class, show.name));

        ShowEntity newShow = showDao.findShowDetail(show.name);
        assertEquals(newShow.id, show.id);
        assertEquals(newShow.name,show.name);
        assertFalse(show.paused);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShowExists() {
        assertFalse(showDao.showExists("uber"));
        assertTrue(showDao.showExists("pipe"));
        assertTrue(showDao.showExists("fx"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateShowDefaultMinCores() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateShowDefaultMinCores(show, 100);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT int_default_min_cores FROM show WHERE pk_show=?",
                Integer.class, show.id) == 100);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateShowDefaultMaxCores() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateShowDefaultMaxCores(show, 1000);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT int_default_max_cores FROM show WHERE pk_show=?",
                Integer.class, show.id) == 1000);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateShowCommentEmail() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateShowCommentEmail(show, new String[] {"test@imageworks.com"});
        String email = jdbcTemplate.queryForObject(
                "SELECT str_comment_email FROM show WHERE pk_show=?",
                String.class, show.id);
        assertEquals("test@imageworks.com", email);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateBookingEnabled() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateBookingEnabled(show,false);
        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_booking_enabled FROM show WHERE pk_show=?",
                Boolean.class, show.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateActive() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateActive(show, false);
        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_active FROM show WHERE pk_show=?",
                Boolean.class, show.id));
        showDao.updateActive(show, true);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_active FROM show WHERE pk_show=?",
                Boolean.class, show.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateFrameCounters() {
        ShowEntity show = showDao.findShowDetail(SHOW_NAME);
        int frameSuccess =  jdbcTemplate.queryForObject(
                "SELECT int_frame_success_count FROM show WHERE pk_show=?",
                Integer.class, show.id);
        showDao.updateFrameCounters(show, 0);
        int frameSucces2 =  jdbcTemplate.queryForObject(
                "SELECT int_frame_success_count FROM show WHERE pk_show=?",
                Integer.class, show.id);
        assertEquals(frameSuccess + 1,frameSucces2);

        int frameFail=  jdbcTemplate.queryForObject(
                "SELECT int_frame_fail_count FROM show WHERE pk_show=?",
                Integer.class, show.id);
        showDao.updateFrameCounters(show, 1);
        int frameFail2 =  jdbcTemplate.queryForObject(
                "SELECT int_frame_fail_count FROM show WHERE pk_show=?",
                Integer.class, show.id);
        assertEquals(frameFail+ 1,frameFail2);
    }
}


