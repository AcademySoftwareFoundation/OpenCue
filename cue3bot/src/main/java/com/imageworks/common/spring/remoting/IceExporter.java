
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
import org.springframework.context.ApplicationContext;

/*
 * Used to export a static servant interface.
 */
public class IceExporter implements ServiceBean {
    private static final Logger logger = Logger.getLogger(IceExporter.class);

    private ApplicationContext context;
    private IceServer iceServer;
    private String iceIdentity;
    private Ice.Object iceServant;

    public IceExporter() {}

    public void afterPropertiesSet() throws Exception {
        iceServer.getAdapter().add(iceServant,
                Ice.Util.stringToIdentity(iceIdentity));
        iceServer.getAdapter().activate();
    }

    public String getIceIdentity() {
        return iceIdentity;
    }

    public void setIceIdentity(String iceIdenity) {
        this.iceIdentity = iceIdenity;
    }

    public IceServer getIceServer() {
        return iceServer;
    }

    public void setIceServer(IceServer iceServer) {
        this.iceServer = iceServer;
    }

    public Ice.Object getIceServant() {
        return iceServant;
    }

    public void setIceServant(Ice.Object iceServant) {
        this.iceServant = iceServant;
    }

    public void setApplicationContext(ApplicationContext arg0) throws BeansException {
        this.context = arg0;

    }
}

