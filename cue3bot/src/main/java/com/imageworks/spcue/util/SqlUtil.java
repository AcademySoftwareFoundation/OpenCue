
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



package com.imageworks.spcue.util;

import java.util.Collection;
import java.util.UUID;

public class SqlUtil {

    public static String buildBindVariableArray(String col, Collection c) {
        StringBuilder sb = new StringBuilder(1024);
        sb.append(col);
        sb.append(" IN (");
        for (int i = 0; i < c.size(); i++) {
            sb.append("?,");
        }
        sb.delete(sb.length() - 1, sb.length());
        sb.append(")");
        return sb.toString();
    }

    /**
     * returns a 32 character UUID string that will be identical everytime its
     * generated based on the name passed in.
     *
     * @param String name
     * @return String
     */
    public static String genShortKeyByName(String name) {
        return UUID.nameUUIDFromBytes(name.getBytes()).toString().replaceAll("-", "");
    }

    /**
     * returns a 32 character UUID string that will be identical everytime its
     * generated based on the name passed in.
     *
     * @param String name
     * @return String
     */
    public static String genShortKeyByNameAndTime(String name) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(name);
        sb.append(System.currentTimeMillis());
        return UUID.nameUUIDFromBytes(sb.toString().getBytes()).toString().replaceAll("-", "");
    }

    /**
     * returns a random UUID
     *
     * @param String name
     * @return String
     */
    public static String genKeyRandom() {
        return UUID.randomUUID().toString();
    }

    /**
     * returns a 36 character UUID string that will be identical everytime its
     * generated based on the name passed in.
     *
     * @param String name
     * @return String
     */
    public static String genKeyByName(String name) {
        return UUID.nameUUIDFromBytes(name.getBytes()).toString();
    }

    /**
     * returns a 36 character UUID string that is based on the name and the time
     * the UUID is created
     *
     * @param String name
     * @return String
     */
    public static String genKeyByNameAndTime(String name) {
        StringBuilder sb = new StringBuilder(64);
        sb.append(name);
        sb.append(System.currentTimeMillis());
        sb.append(System.getenv("HOSTNAME"));
        return UUID.nameUUIDFromBytes(sb.toString().getBytes()).toString();
    }

    /**
     * returns a 36 character UUID string that is based on time and the IP
     * address of the primary network interface and the time
     *
     * @return
     */
    public static String genKeyByTime() {
        String name = System.getenv("HOSTNAME") + System.currentTimeMillis();
        return UUID.nameUUIDFromBytes(name.getBytes()).toString();
    }
}

