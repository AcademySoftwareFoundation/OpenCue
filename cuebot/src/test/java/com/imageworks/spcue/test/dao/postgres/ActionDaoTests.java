
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

import com.imageworks.spcue.ActionEntity;
import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.ActionDao;
import com.imageworks.spcue.dao.FilterDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.grpc.filter.ActionType;
import com.imageworks.spcue.grpc.filter.ActionValueType;
import com.imageworks.spcue.grpc.filter.FilterType;
import com.imageworks.spcue.service.JobManager;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.Assert.assertEquals;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class ActionDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    private static final ActionType ActionType = null;

    @Autowired
    ActionDao actionDao;

    @Autowired
    FilterDao filterDao;

    @Autowired
    ShowDao showDao;

    @Autowired
    GroupDao groupDao;

    @Autowired
    JobManager jobManager;

    private static String FILTER_NAME = "test_filter";

    public ShowInterface getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public FilterEntity buildFilter() {
        FilterEntity filter = new FilterEntity();
        filter.name = FILTER_NAME;
        filter.showId = "00000000-0000-0000-0000-000000000000";
        filter.type = FilterType.MATCH_ANY;
        filter.enabled = true;

        return filter;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCreateAction() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a1 = new ActionEntity();
        a1.type = ActionType.PAUSE_JOB;
        a1.filterId = f.getFilterId();
        a1.booleanValue = true;
        a1.valueType = ActionValueType.BOOLEAN_TYPE;
        actionDao.createAction(a1);

        ActionEntity a2 = new ActionEntity();
        a2.type = ActionType.MOVE_JOB_TO_GROUP;
        a2.filterId = f.getFilterId();
        a2.groupValue = groupDao.getRootGroupId(getShow());
        a2.valueType = ActionValueType.GROUP_TYPE;
        actionDao.createAction(a2);

        ActionEntity a3 = new ActionEntity();
        a3.type = ActionType.SET_JOB_MAX_CORES;
        a3.filterId = f.getFilterId();
        a3.floatValue = 1f;
        a3.valueType = ActionValueType.FLOAT_TYPE;
        actionDao.createAction(a3);

        ActionEntity a4 = new ActionEntity();
        a4.type = ActionType.SET_JOB_MIN_CORES;
        a4.filterId = f.getFilterId();
        a4.floatValue = 1;
        a4.valueType = ActionValueType.FLOAT_TYPE;
        actionDao.createAction(a4);

        ActionEntity a5 = new ActionEntity();
        a5.type = ActionType.STOP_PROCESSING;
        a5.filterId = f.getFilterId();
        a5.valueType = ActionValueType.NONE_TYPE;
        actionDao.createAction(a5);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteAction() {

        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a = new ActionEntity();
        a.type = ActionType.STOP_PROCESSING;
        a.filterId = f.getFilterId();
        a.valueType = ActionValueType.NONE_TYPE;
        actionDao.createAction(a);
        actionDao.deleteAction(a);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetAction() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a = new ActionEntity();
        a.type = ActionType.STOP_PROCESSING;
        a.filterId = f.getFilterId();
        a.valueType = ActionValueType.NONE_TYPE;
        actionDao.createAction(a);
        actionDao.getAction(a);
        actionDao.getAction(a.getActionId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateAction() {
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a = new ActionEntity();
        a.type = ActionType.STOP_PROCESSING;
        a.filterId = f.getFilterId();
        a.name = null;
        a.valueType = ActionValueType.NONE_TYPE;
        actionDao.createAction(a);

        a.floatValue = 1f;
        a.type = ActionType.SET_JOB_MIN_CORES;
        a.valueType = ActionValueType.FLOAT_TYPE;

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
        FilterEntity f = buildFilter();
        filterDao.insertFilter(f);

        ActionEntity a = new ActionEntity();
        a.type = ActionType.STOP_PROCESSING;
        a.filterId = f.getFilterId();
        a.name = null;
        a.valueType = ActionValueType.NONE_TYPE;
        actionDao.createAction(a);

        actionDao.getActions(f);
    }
}


