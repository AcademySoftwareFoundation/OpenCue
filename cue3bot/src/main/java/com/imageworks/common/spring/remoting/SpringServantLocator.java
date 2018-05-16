
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



package com.imageworks.common.spring.remoting;

import org.apache.log4j.Logger;
import org.springframework.beans.BeansException;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;

import Ice.Current;
import Ice.LocalObjectHolder;
import Ice.ServantLocator;
import Ice.UserException;

public class SpringServantLocator
        implements ServantLocator, InitializingBean, ApplicationContextAware {
    private static final Logger logger = Logger.getLogger(SpringServantLocator.class);

    private String category;
    private ApplicationContext context;
    private IceServer iceServer;

    public SpringServantLocator(IceServer server, String category) {
        this.iceServer = server;
        this.category = category;
    }

    public void deactivate(String arg0) {}

    public void finished(Current arg0, Ice.Object arg1, Object arg2) throws UserException {
        // TODO Auto-generated method stub

    }

    public Ice.Object locate(Current __current, LocalObjectHolder cookie) throws UserException {
        try {
            return (Ice.Object) this.context.getBean(__current.id.category,
                    new java.lang.Object[] {__current.id});
        } catch (Exception e) {
            logger.info("error creating proxy for " + __current.id.category
                    + "/" + __current.id.name + " from "
                    + __current.con.toString());
            return null;
        }
    }

    public void afterPropertiesSet() throws Exception {
        iceServer.getAdapter().addServantLocator(this, this.category);
    }

    public void setApplicationContext(ApplicationContext arg0) throws BeansException {
        this.context = arg0;
    }

    public String getCategory() {
        return category;
    }

    public IceServer getIceServer() {
        return iceServer;
    }
}

