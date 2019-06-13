
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



package com.imageworks.spcue.test.service;

import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobLauncher;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class GroupManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    GroupManager groupManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    GroupDao groupDao;

    @Autowired
    ShowDao showDao;

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createGroup() {
        ShowInterface pipe = showDao.findShowDetail("pipe");
        GroupDetail group = new GroupDetail();
        group.name = "testGroup";
        group.showId = pipe.getId();
        group.parentId =  groupDao.getRootGroupDetail(pipe).getId();
        groupManager.createGroup(group, null);
    }
}

