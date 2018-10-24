
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

import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.FilterDetail;
import com.imageworks.spcue.MatcherDetail;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.CueIce.FilterType;
import com.imageworks.spcue.CueIce.MatchSubject;
import com.imageworks.spcue.CueIce.MatchType;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.MatcherDao;
import com.imageworks.spcue.dao.ShowDao;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class MatcherDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    MatcherDao matcherDao;

    @Resource
    FilterDao filterDao;

    @Resource
    ShowDao showDao;

    @Resource
    GroupDao groupDao;

    private static String FILTER_NAME = "test_filter";

    public Show getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public MatcherDetail createMatcher() {
        FilterDetail filter = createFilter();
        MatcherDetail matcher = new MatcherDetail();
        matcher.filterId = filter.id;
        matcher.name = null;
        matcher.showId = getShow().getId();
        matcher.subject = MatchSubject.JobName;
        matcher.type = MatchType.Contains;
        matcher.value = "testuser";
        matcherDao.insertMatcher(matcher);
        return matcher;
    }

    public FilterDetail createFilter() {
        FilterDetail filter = new FilterDetail();
        filter.name = FILTER_NAME;
        filter.showId = "00000000-0000-0000-0000-000000000000";
        filter.type = FilterType.MatchAny;
        filter.enabled = true;
        filterDao.insertFilter(filter);
        return filter;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertMatcher() {
        createMatcher();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteMatcher() {
        MatcherDetail matcher = createMatcher();
        matcherDao.deleteMatcher(matcher);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateMatcher() {
        MatcherDetail matcher = createMatcher();
        matcher.subject = MatchSubject.User;
        matcher.value = "testuser";
        matcher.type = MatchType.Is;
        matcherDao.updateMatcher(matcher);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetMatcher() {
        MatcherDetail matcher = createMatcher();
        matcherDao.getMatcher(matcher);
        matcherDao.getMatcher(matcher.getMatcherId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetMatchers() {
        MatcherDetail matcher = createMatcher();
        matcherDao.getMatchers(matcher);
    }

}


