
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



package com.imageworks.spcue.servant;

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.SubscriptionDetail;
import com.imageworks.spcue.CueClientIce._SubscriptionInterfaceDisp;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.util.Convert;

public class ManageSubscriptionI extends _SubscriptionInterfaceDisp  implements InitializingBean {

    private final String id;
    private SubscriptionDetail subscriptionDetail;
    private AdminManager adminManager;

    public ManageSubscriptionI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    public void afterPropertiesSet() throws Exception {
        subscriptionDetail = adminManager.getSubscriptionDetail(id);
    }

    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.deleteSubscription(subscriptionDetail);
            }
        }.execute();
    }

    public void setBurst(final float burst, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.setSubscriptionBurst(subscriptionDetail,
                        Convert.coresToWholeCoreUnits(burst));
            }
        }.execute();
    }

    public void setSize(final float size, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                adminManager.setSubscriptionSize(subscriptionDetail,
                        Convert.coresToWholeCoreUnits(size));
            }
        }.execute();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }
    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }
}

