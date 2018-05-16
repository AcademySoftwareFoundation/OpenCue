
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



package com.imageworks.spcue.test.dao.oracle;

import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.HashMap;

import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.ShowDetail;
import com.imageworks.spcue.CueIce.HardwareState;
import com.imageworks.spcue.RqdIce.RenderHost;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.util.CueUtil;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class ShowDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    ShowDao showDao;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    private static String SHOW_ID = "00000000-0000-0000-0000-000000000000";
    private static String SHOW_NAME= "pipe";

    public DispatchHost createHost() {

        RenderHost host = new RenderHost();
        host.name = "test_host";
        host.bootTime = 1192369572;
        host.freeMcp = 76020;
        host.freeMem = 53500;
        host.freeSwap = 20760;
        host.load = 1;
        host.totalMcp = 195430;
        host.totalMem = (int) CueUtil.GB16;
        host.totalSwap = (int) CueUtil.GB16;
        host.nimbyEnabled = false;
        host.numProcs = 2;
        host.coresPerProc = 100;
        host.tags = new ArrayList<String>();
        host.tags.add("general");
        host.state = HardwareState.Up;
        host.facility = "spi";
        host.attributes = new HashMap<String, String>();
        host.attributes.put("freeGpu", String.format("%d", CueUtil.MB512));
        host.attributes.put("totalGpu", String.format("%d", CueUtil.MB512));

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return dh;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindShowDetail() {
        ShowDetail show = showDao.findShowDetail(SHOW_NAME);
        assertEquals(SHOW_ID, show.id);
        assertEquals(SHOW_NAME,show.name);
        assertFalse(show.paused);
    }

    @Test(expected=EmptyResultDataAccessException.class)
    @Transactional
    @Rollback(true)
    public void testFindShowDetailByHost() {
        //TODO: Add code to setup a host and make the sow
        // prefer the host, then check result again.
        showDao.getShowDetail(createHost());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetShowDetail() {
        ShowDetail show = showDao.getShowDetail(SHOW_ID);
        assertEquals(SHOW_ID, show.id);
        assertEquals(SHOW_NAME,show.name);
        assertFalse(show.paused);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertShow() {
        ShowDetail show = new ShowDetail();
        show.name = "uber";
        showDao.insertShow(show);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT count(*) FROM show where str_name=?",
                Integer.class, show.name));

        ShowDetail newShow = showDao.findShowDetail(show.name);
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
        ShowDetail show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateShowDefaultMinCores(show, 100);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT int_default_min_cores FROM show WHERE pk_show=?",
                Integer.class, show.id) == 100);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateShowDefaultMaxCores() {
        ShowDetail show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateShowDefaultMaxCores(show, 1000);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT int_default_max_cores FROM show WHERE pk_show=?",
                Integer.class, show.id) == 1000);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateShowCommentEmail() {
        ShowDetail show = showDao.findShowDetail(SHOW_NAME);
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
        ShowDetail show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateBookingEnabled(show,false);
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_booking_enabled FROM show WHERE pk_show=?",
                Integer.class, show.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateActive() {
        ShowDetail show = showDao.findShowDetail(SHOW_NAME);
        showDao.updateActive(show, false);
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_active FROM show WHERE pk_show=?",
                Integer.class, show.id));
        showDao.updateActive(show, true);
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT b_active FROM show WHERE pk_show=?",
                Integer.class, show.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateFrameCounters() {
        ShowDetail show = showDao.findShowDetail(SHOW_NAME);
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


