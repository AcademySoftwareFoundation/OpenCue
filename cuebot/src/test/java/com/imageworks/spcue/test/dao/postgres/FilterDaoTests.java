
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

import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.service.AdminManager;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class FilterDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    FilterDao filterDao;

    @Autowired
    ShowDao showDao;

    @Autowired
    AdminManager adminManager;

    private static String FILTER_NAME = "test_filter";

    public ShowInterface createShow() {
        ShowEntity show = new ShowEntity();
        show.name = "testtest";
        adminManager.createShow(show);
        return show;
    }

    public ShowInterface getShow() {
        return showDao.findShowDetail("testtest");
    }

    public FilterEntity buildFilter(ShowInterface show) {
        FilterEntity filter = new FilterEntity();
        filter.name = FILTER_NAME;
        filter.showId = show.getId();
        filter.type = FilterType.MATCH_ANY;
        filter.enabled = true;

        return filter;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetActiveFilters() {
        filterDao.getActiveFilters(createShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFilters() {
        filterDao.getFilters(createShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateSetFilterEnabled() {
        FilterEntity f = buildFilter(createShow());
        filterDao.insertFilter(f);
        filterDao.updateSetFilterEnabled(f, false);
        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_enabled FROM filter WHERE pk_filter=?",
                Boolean.class, f.getFilterId()));
        filterDao.updateSetFilterEnabled(f, true);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_enabled FROM filter WHERE pk_filter=?",
                Boolean.class, f.getFilterId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateSetFilterName() {
        FilterEntity f = buildFilter(createShow());
        filterDao.insertFilter(f);
        assertEquals(FILTER_NAME, jdbcTemplate.queryForObject(
                "SELECT str_name FROM filter WHERE pk_filter=?",
                String.class,
                f.getFilterId()));
        filterDao.updateSetFilterName(f, "TEST");
        assertEquals("TEST", jdbcTemplate.queryForObject(
                "SELECT str_name FROM filter WHERE pk_filter=?",
                String.class,
                f.getFilterId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateSetFilterType() {
        FilterEntity f = buildFilter(createShow());
        filterDao.insertFilter(f);
        assertEquals(FilterType.MATCH_ANY.toString(), jdbcTemplate.queryForObject(
                "SELECT str_type FROM filter WHERE pk_filter=?",
                String.class,
                f.getFilterId()));
        filterDao.updateSetFilterType(f, FilterType.MATCH_ALL);
        assertEquals(FilterType.MATCH_ALL.toString(), jdbcTemplate.queryForObject(
                "SELECT str_type FROM filter WHERE pk_filter=?",
                String.class,
                f.getFilterId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateSetFilterOrder() {

        ShowInterface show = createShow();
        int currentFilters = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM filter WHERE pk_show=?",
                Integer.class, show.getShowId());

        FilterEntity f1 = buildFilter(show);
        filterDao.insertFilter(f1);

        FilterEntity f2 = buildFilter(show);
        f2.name = "TEST";
        filterDao.insertFilter(f2);

        assertEquals(Integer.valueOf(currentFilters+1), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f1.getFilterId()));

        assertEquals(Integer.valueOf(currentFilters+2), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f2.getFilterId()));

        filterDao.updateSetFilterOrder(f2,1);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f2.getFilterId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteFilter() {
        FilterEntity f = buildFilter(createShow());
        filterDao.insertFilter(f);
        filterDao.deleteFilter(f);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertFilter() {
        FilterEntity f = buildFilter(createShow());
        filterDao.insertFilter(f);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReorderFilters() {
        buildFilter(createShow());
        filterDao.reorderFilters(getShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLowerFilterOrder() {

        ShowInterface show = createShow();

        FilterEntity f1 = buildFilter(show);
        filterDao.insertFilter(f1);

        FilterEntity f2 = buildFilter(show);
        f2.name = "TEST";
        filterDao.insertFilter(f2);


        /**
         * These could fail if the test DB has other filters.
         */
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f1.getFilterId()));

        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f2.getFilterId()));

        filterDao.lowerFilterOrder(f2,1);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f1.getFilterId()));

        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f2.getFilterId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testRaiseFilterOrder() {

        ShowInterface show = createShow();

        FilterEntity f1 = buildFilter(show);
        filterDao.insertFilter(f1);

        FilterEntity f2 = buildFilter(show);
        f2.name = "TEST";
        filterDao.insertFilter(f2);

        /**
         * These could fail if the test DB has other filters.
         */
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f1.getFilterId()));

        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f2.getFilterId()));

        filterDao.raiseFilterOrder(f1, 1);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f1.getFilterId()));

        assertEquals(Integer.valueOf(2), jdbcTemplate.queryForObject(
                "SELECT f_order FROM filter WHERE pk_filter=?",
                Integer.class, f2.getFilterId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFilter() {
        FilterEntity f = buildFilter(createShow());
        filterDao.insertFilter(f);

        filterDao.getFilter(f);
        filterDao.getFilter(f.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindFilter() {
        FilterEntity f = buildFilter(createShow());
        filterDao.insertFilter(f);

        filterDao.findFilter(getShow(), FILTER_NAME);
    }

}


