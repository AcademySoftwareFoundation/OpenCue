
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


package com.imageworks.spcue.dao.criteria;

import java.util.ArrayList;
import java.util.List;


public abstract class Criteria {

    CriteriaGeneratorInterface criteriaGenerator;

    boolean built = false;

    /**
     * An offset into the query result that can be used
     * to do result paging.
     */
    private int firstResult = 1;

    /**
     * The maximum number of results the query should return.
     */
    private int maxResults = 0;

    /**
     * An array of storing Sort objects used to sort
     * the result of the query.
     */
    private ArrayList<Sort> order = new ArrayList<Sort>();

    abstract public void buildWhereClause();

    public String toString() { return this.getWhereClause(); }

    public CriteriaGeneratorInterface getCriteriaGenerator() {
        return criteriaGenerator;
    }

    public List<Object> getValues() {
        return values;
    }

    boolean isValid(String v) {
        return v != null && !v.isEmpty();
    }

    public void clear() {
        built = false;
        chunks.clear();
    }

    private String getWhereClause() {
        build();
        return criteriaGenerator.generateWhereClause(chunks);
    }

    public String getQuery(String query) {
        build();
        return criteriaGenerator.queryWithPaging(query, firstResult, maxResults, order);
    }

    public void setFirstResult(int firstResult) {
        this.firstResult = Math.max(firstResult, 1);
    }

    public void setMaxResults(int maxResults) {
        this.maxResults = maxResults;
    }

    public void addSort(Sort o) {
        this.order.add(o);
    }

    private void build() {
        if (!built) {
            buildWhereClause();
        }
        built = true;
    }
}

