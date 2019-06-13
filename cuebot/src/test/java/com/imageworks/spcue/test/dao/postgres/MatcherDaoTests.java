
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
import com.imageworks.spcue.MatcherEntity;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.MatcherDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.grpc.filter.MatchSubject;
import com.imageworks.spcue.grpc.filter.MatchType;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class MatcherDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    MatcherDao matcherDao;

    @Autowired
    FilterDao filterDao;

    @Autowired
    ShowDao showDao;

    @Autowired
    GroupDao groupDao;

    private static String FILTER_NAME = "test_filter";

    public ShowEntity getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public MatcherEntity createMatcher() {
        FilterEntity filter = createFilter();
        MatcherEntity matcher = new MatcherEntity();
        matcher.filterId = filter.id;
        matcher.name = null;
        matcher.showId = getShow().getId();
        matcher.subject = MatchSubject.JOB_NAME;
        matcher.type = MatchType.CONTAINS;
        matcher.value = "testuser";
        matcherDao.insertMatcher(matcher);
        return matcher;
    }

    public FilterEntity createFilter() {
        FilterEntity filter = new FilterEntity();
        filter.name = FILTER_NAME;
        filter.showId = "00000000-0000-0000-0000-000000000000";
        filter.type = FilterType.MATCH_ANY;
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
        MatcherEntity matcher = createMatcher();
        matcherDao.deleteMatcher(matcher);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateMatcher() {
        MatcherEntity matcher = createMatcher();
        matcher.subject = MatchSubject.USER;
        matcher.value = "testuser";
        matcher.type = MatchType.IS;
        matcherDao.updateMatcher(matcher);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetMatcher() {
        MatcherEntity matcher = createMatcher();
        matcherDao.getMatcher(matcher);
        matcherDao.getMatcher(matcher.getMatcherId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetMatchers() {
        MatcherEntity matcher = createMatcher();
        matcherDao.getMatchers(matcher);
    }

}


