
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

import java.util.Collections;
import java.util.Map;


import org.apache.commons.collections.map.LRUMap;
import org.apache.log4j.Logger;
import org.springframework.beans.BeansException;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;


import Ice.Current;
import Ice.LocalObjectHolder;
import Ice.ServantLocator;
import Ice.UserException;

@SuppressWarnings("unchecked")
public class CachingSpringServantLocator
    implements ServantLocator, InitializingBean, ApplicationContextAware {

    private static final Logger logger = Logger.getLogger(CachingSpringServantLocator.class);

    private Map LRUCache;
    private SpringServantLocator locator;

    public CachingSpringServantLocator(IceServer server, String category, int cacheSize) {
        this(new SpringServantLocator(server, category), cacheSize);
    }

    public CachingSpringServantLocator(SpringServantLocator servantLocator, int cacheSize) {
        LRUCache = Collections.synchronizedMap(new LRUMap(cacheSize));
        this.locator = servantLocator;
        this.locator.getIceServer().getAdapter().addServantLocator(this, servantLocator.getCategory());
    }

    public void deactivate(String arg0) {
        // TODO Auto-generated method stub

    }

    public void finished(Current arg0, Ice.Object arg1, Object arg2) throws UserException {
        // TODO Auto-generated method stub

    }

    @SuppressWarnings("unchecked")
    public Ice.Object locate(Current __current, LocalObjectHolder cookie) throws UserException {
        try {
            Ice.Object i = null;
            i = (Ice.Object) LRUCache.get(__current.id.name);
            if (i != null) {
                return i;
            }
            i = locator.locate(__current, cookie);
            if (i != null) {
                LRUCache.put(__current.id.name, i);
            }
            return i;
        }
        catch (Exception e) {
            logger.info("unable to find servant for " + __current.id.category
                    + " / " + __current.id);
        }
        return null;
    }

    public void afterPropertiesSet() throws Exception {
        // don't do anything here
    }

    public void setApplicationContext(ApplicationContext arg0) throws BeansException {
        locator.setApplicationContext(arg0);

    }
}

