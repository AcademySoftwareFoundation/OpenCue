
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

import static org.junit.Assert.*;

import javax.annotation.Resource;

import org.junit.ClassRule;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.ActionDetail;
import com.imageworks.spcue.FilterDetail;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.CueIce.ActionType;
import com.imageworks.spcue.CueIce.ActionValueType;
import com.imageworks.spcue.CueIce.FilterType;
import com.imageworks.spcue.dao.ActionDao;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class ActionDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    private static final ActionType ActionType = null;

    @Resource
    ActionDao actionDao;

    @Resource
    FilterDao filterDao;

    @Resource
    ShowDao showDao;

    @Resource
    GroupDao groupDao;

    @Resource
    JobManager jobManager;

    private static String FILTER_NAME = "test_filter";

    public Show getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public FilterDetail buildFilter() {
        FilterDetail filter = new FilterDetail();
        filter.name = FILTER_NAME;
        filter.showId = "00000000-0000-0000-0000-000000000000";
        filter.type = FilterType.MatchAny;
        filter.enabled = true;

        return filter;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCreateAction() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a1 = new ActionDetail();
        a1.type = ActionType.PauseJob;
        a1.filterId = f.getFilterId();
        a1.booleanValue = true;
        a1.valueType = ActionValueType.BooleanType;
        actionDao.createAction(a1);

        ActionDetail a2 = new ActionDetail();
        a2.type = ActionType.MoveJobToGroup;
        a2.filterId = f.getFilterId();
        a2.groupValue = groupDao.getRootGroupId(getShow());
        a2.valueType = ActionValueType.GroupType;
        actionDao.createAction(a2);

        ActionDetail a3 = new ActionDetail();
        a3.type = ActionType.SetJobMaxCores;
        a3.filterId = f.getFilterId();
        a3.floatValue = 1f;
        a3.valueType = ActionValueType.FloatType;
        actionDao.createAction(a3);

        ActionDetail a4 = new ActionDetail();
        a4.type = ActionType.SetJobMinCores;
        a4.filterId = f.getFilterId();
        a4.floatValue = 1;
        a4.valueType = ActionValueType.FloatType;
        actionDao.createAction(a4);

        ActionDetail a5 = new ActionDetail();
        a5.type = ActionType.StopProcessing;
        a5.filterId = f.getFilterId();
        a5.valueType = ActionValueType.NoneType;
        actionDao.createAction(a5);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteAction() {

        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a = new ActionDetail();
        a.type = ActionType.StopProcessing;
        a.filterId = f.getFilterId();
        a.valueType = ActionValueType.NoneType;
        actionDao.createAction(a);
        actionDao.deleteAction(a);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetAction() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a = new ActionDetail();
        a.type = ActionType.StopProcessing;
        a.filterId = f.getFilterId();
        a.valueType = ActionValueType.NoneType;
        actionDao.createAction(a);
        actionDao.getAction(a);
        actionDao.getAction(a.getActionId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateAction() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a = new ActionDetail();
        a.type = ActionType.StopProcessing;
        a.filterId = f.getFilterId();
        a.name = null;
        a.valueType = ActionValueType.NoneType;
        actionDao.createAction(a);

        a.floatValue = 1f;
        a.type = ActionType.SetJobMinCores;
        a.valueType = ActionValueType.FloatType;

        actionDao.updateAction(a);

        assertEquals(Integer.valueOf(1),
                jdbcTemplate.queryForObject(
                        "SELECT float_value FROM action WHERE pk_action=?",
                        Integer.class, a.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetActions() {
        FilterDetail f = buildFilter();
        filterDao.insertFilter(f);

        ActionDetail a = new ActionDetail();
        a.type = ActionType.StopProcessing;
        a.filterId = f.getFilterId();
        a.name = null;
        a.valueType = ActionValueType.NoneType;
        actionDao.createAction(a);

        actionDao.getActions(f);
    }
}


