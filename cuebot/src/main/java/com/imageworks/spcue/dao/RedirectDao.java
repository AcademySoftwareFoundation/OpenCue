
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.dao;

import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.Redirect;

@Transactional(propagation = Propagation.MANDATORY)
public interface RedirectDao {
    /**
     * Check for redirect existence.
     *
     * @param key Redirect key
     *
     * @return True if redirect exists
     */
    boolean containsKey(String key);

    /**
     * Count redirects in a group.
     *
     * @param groupId the group to query
     *
     * @return count of redirects in group
     */
    int countRedirectsWithGroup(String groupId);

    /**
     * Delete all expired redirects.
     *
     * @return number of redirects deleted
     */
    int deleteExpired();

    /**
     * Add redirect.
     *
     * @param key Redirect key
     *
     * @param r Redirect to add
     */
    void put(String key, Redirect r);

    /**
     * Delete and return specified redirect.
     *
     * @param key Redirect key
     *
     * @return the redirect that was deleted or null
     */
    Redirect remove(String key);
}
