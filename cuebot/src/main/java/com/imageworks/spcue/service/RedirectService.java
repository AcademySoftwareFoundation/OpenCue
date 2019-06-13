
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


package com.imageworks.spcue.service;

import javax.annotation.Resource;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.CannotSerializeTransactionException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.DefaultTransactionDefinition;

import com.imageworks.spcue.Redirect;
import com.imageworks.spcue.dao.RedirectDao;

@Service
@Transactional(isolation=Isolation.SERIALIZABLE, propagation=Propagation.REQUIRES_NEW)
public class RedirectService   {

    private static final Logger logger =
        Logger.getLogger(RedirectService.class);

    @Autowired
    private PlatformTransactionManager txManager;

    @Autowired
    private RedirectDao redirectDao;

    public RedirectService(RedirectDao redirectDao) {
        this.redirectDao = redirectDao;
    }

    /**
     * Check for redirect existence.
     *
     * @param key Redirect key
     *
     * @return True if redirect exists
     */
    @Transactional(readOnly = true)
    public boolean containsKey(String key) {
        return redirectDao.containsKey(key);
    }

    /**
     * Count redirects in a group.
     *
     * @param groupId the group to query
     *
     * @return count of redirects in group
     */
    @Transactional(readOnly = true)
    public int countRedirectsWithGroup(String groupId) {
        return redirectDao.countRedirectsWithGroup(groupId);
    }

    /**
     * Delete all redirects that are past expiration age.
     *
     * @return count of redirects deleted
     */
    public int deleteExpired() {
        return redirectDao.deleteExpired();
    }

    /**
     * Add redirect.
     *
     * @param key Redirect key
     *
     * @param r Redirect to add
     */
    @Transactional(propagation=Propagation.NOT_SUPPORTED)
    public void put(String key, Redirect r) {
        DefaultTransactionDefinition def = new DefaultTransactionDefinition();
        def.setPropagationBehavior(DefaultTransactionDefinition.PROPAGATION_REQUIRES_NEW);
        def.setIsolationLevel(DefaultTransactionDefinition.ISOLATION_SERIALIZABLE);

        while (true) {
            TransactionStatus status = txManager.getTransaction(def);
            try {
                redirectDao.put(key, r);
            }
            catch (CannotSerializeTransactionException e) {
                // MERGE statement race lost; try again.
                txManager.rollback(status);
                continue;
            }
            catch (DuplicateKeyException e) {
                if (e.getMessage().contains("C_REDIRECT_PK")) {
                    // MERGE statement race lost; try again.
                    txManager.rollback(status);
                    continue;
                }
                throw e;
            }
            catch (Exception e) {
                txManager.rollback(status);
                throw e;
            }
            txManager.commit(status);
            break;
        }
    }

    /**
     * Remove a redirect for a specific key.
     *
     * @param key
     *
     * @return The redirect that was removed, or null
     */
    public Redirect remove(String key) {
        return redirectDao.remove(key);
    }
}
