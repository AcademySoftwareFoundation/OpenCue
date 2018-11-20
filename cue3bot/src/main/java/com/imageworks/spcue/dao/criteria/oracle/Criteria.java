
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

package com.imageworks.spcue.dao.criteria.oracle;

import java.security.Timestamp;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import com.google.common.collect.ImmutableList;

import com.imageworks.common.SpiIce.EqualsFloatSearchCriterion;
import com.imageworks.common.SpiIce.EqualsIntegerSearchCriterion;
import com.imageworks.common.SpiIce.FloatSearchCriterion;
import com.imageworks.common.SpiIce.GreaterThanFloatSearchCriterion;
import com.imageworks.common.SpiIce.GreaterThanIntegerSearchCriterion;
import com.imageworks.common.SpiIce.InRangeFloatSearchCriterion;
import com.imageworks.common.SpiIce.InRangeIntegerSearchCriterion;
import com.imageworks.common.SpiIce.IntegerSearchCriterion;
import com.imageworks.common.SpiIce.LessThanFloatSearchCriterion;
import com.imageworks.common.SpiIce.LessThanIntegerSearchCriterion;
import com.imageworks.spcue.dao.criteria.CriteriaException;
import com.imageworks.spcue.dao.criteria.CriteriaInterface;
import com.imageworks.spcue.dao.criteria.Phrase;
import com.imageworks.spcue.dao.criteria.Sort;

public abstract class Criteria implements CriteriaInterface {

    List<StringBuilder> chunks = new ArrayList<StringBuilder>(12);
    List<Object> values = new ArrayList<Object>(32);

    boolean built = false;
    private int firstResult = 1;
    private int maxResults = 0;
    private ArrayList<Sort> order = new ArrayList<Sort>();

    abstract void buildWhereClause();

    public String toString() { return this.getWhereClause(); }

    public void setFirstResult(int firstResult) {
        this.firstResult = Math.max(firstResult, 1);
    }

    public void setMaxResults(int maxResults) {
        this.maxResults = maxResults;
    }

    public void addSort(Sort sort) {
        this.order.add(sort);
    }

    public List<Object> getValues() {
        return values;
    }

    public Object[] getValuesArray() {
        return values.toArray();
    }

    public String getWhereClause() {
        build();
        return generateWhereClause();
    }

    public String getFilteredQuery(String query) {
        build();
        return queryWithPaging(query);
    }

    private void build() {
        if (!built) {
            buildWhereClause();
        }
        built = true;
    }

    private String generateWhereClause() {
        return chunks.stream()
                .map(StringBuilder::toString)
                .collect(Collectors.joining(" AND "));
    }

    private String queryWithPaging(String query) {
        if (firstResult > 1 || maxResults > 0) {
            if (order.size() == 0) {
                query = query.replaceFirst("SELECT ", "SELECT ROWNUM AS RN,");
            } else {
                query = query.replaceFirst("SELECT ", "SELECT row_number() OVER (" + getOrder() + ") AS RN, ");
            }
        }

        StringBuilder sb = new StringBuilder(4096);
        if (maxResults > 0 || firstResult > 1) {
            sb.append("SELECT * FROM ( ");
        }

        sb.append(query);
        sb.append(" ");
        if (chunks.size() > 0) {
            sb.append("AND ");
            sb.append(
                    chunks.stream()
                            .map(StringBuilder::toString)
                            .collect(Collectors.joining(" AND ")));
        }

        if (firstResult > 1 || maxResults > 0) {
            sb.append(") WHERE ");
        }

        if (firstResult > 1) {
            sb.append (" RN >= ? ");
            values.add(firstResult);
        }

        if (maxResults > 0) {
            if (firstResult > 1) {
                sb.append(" AND ");
            }
            sb.append(" RN < ? ");
            values.add(firstResult + maxResults);
        }

        return sb.toString();
    }

    private String getOrder() {
        if (order.size() < 1) {
            return "";
        }
        return " ORDER BY " + order.stream()
                .map(sort -> sort.getColumn() + " " + sort.getDirection().toString())
                .collect(Collectors.joining(", "));
    }

    void addPhrase(String col, Collection<String> s) {
        if (s == null || s.size() == 0) { return; }

        StringBuilder sb = new StringBuilder(1024);
        sb.append("(");
        for (String w: s) {
            sb.append(col);
            sb.append("=?");
            sb.append(" OR ");
            values.add(w);
        }
        sb.delete(sb.length()-4, sb.length());
        sb.append(")");
        chunks.add(sb);
    }

    void addPhrases(Collection<Phrase> phrases, String inclusion) {
        if (phrases.size() == 0) { return; }
        StringBuilder sb = new StringBuilder(1024);
        sb.append("(");
        for (Phrase p: phrases) {
            sb.append(p.getColumn());
            sb.append(p.getComparison());
            sb.append("?");
            sb.append(" ");
            sb.append(inclusion);
            sb.append(" ");
            values.add(p.getValue());
        }
        sb.delete(sb.length()-4, sb.length());
        sb.append(")");
        chunks.add(sb);
    }

    void addPhrase(String col, String v) {
        if (v == null) { return; }
        addPhrase(col, ImmutableList.of(v));
    }

    void addRegexPhrase(String col, Set<String> s) {
        if (s == null) { return; }
        if (s.size() == 0) { return; }
        StringBuilder sb = new StringBuilder(1024);
        sb.append("(");
        for (String w: s) {
            sb.append(String.format("REGEXP_LIKE(%s,?)", col));
            sb.append(" OR ");
            values.add(w);
        }
        sb.delete(sb.length()-4, sb.length());
        sb.append(")");
        chunks.add(sb);
    }

    void addLikePhrase(String col, Set<String> s) {
        if (s == null) { return; }
        if (s.size() == 0) { return; }
        StringBuilder sb = new StringBuilder(1024);
        sb.append("(");
        for (String w: s) {
            sb.append(col);
            sb.append(" LIKE ?");
            sb.append(" OR ");
            values.add("%" + w + "%");
        }
        sb.delete(sb.length()-4, sb.length());
        sb.append(")");
        chunks.add(sb);
    }

    void addGreaterThanTimestamp(String col, Timestamp timestamp) {
        if (timestamp == null) { return; }
        StringBuilder sb = new StringBuilder(128);
        sb.append("(");
        sb.append(col);
        sb.append(" > ?");
        sb.append(") ");
        values.add(timestamp);
        chunks.add(sb);
    }

    void addLessThanTimestamp(String col, Timestamp timestamp) {
        if (timestamp == null) { return; }
        StringBuilder sb = new StringBuilder(128);
        sb.append("(");
        sb.append(col);
        sb.append(" < ?");
        sb.append(") ");
        values.add(timestamp);
        chunks.add(sb);
    }

    void addRangePhrase(String col, IntegerSearchCriterion e) {
        StringBuilder sb = new StringBuilder(128);
        final Class<? extends IntegerSearchCriterion> c = e.getClass();
        if (c == EqualsIntegerSearchCriterion.class) {
            EqualsIntegerSearchCriterion r = (EqualsIntegerSearchCriterion) e;
            values.add(r.value);
            sb.append(" " + col + " = ?");
        }
        else if (c == LessThanIntegerSearchCriterion.class) {
            LessThanIntegerSearchCriterion r = (LessThanIntegerSearchCriterion) e;
            values.add(r.value);
            sb.append(" " + col + "<=? ");
        }
        else if (c == GreaterThanIntegerSearchCriterion.class) {
            GreaterThanIntegerSearchCriterion r = (GreaterThanIntegerSearchCriterion) e;
            values.add(r.value);
            sb.append(" " + col + " >= ? ");
        }
        else if (c == InRangeIntegerSearchCriterion.class) {
            InRangeIntegerSearchCriterion r = (InRangeIntegerSearchCriterion) e;
            values.add(r.min);
            values.add(r.max);
            sb.append(" (" + col +" >= ? AND " + col + " <= ?) ");
        }
        else {
            throw new CriteriaException("Invalid criteria class used for memory range search: "
                    + e.getClass().getCanonicalName());
        }
        chunks.add(sb);
    }

    void addRangePhrase(String col, FloatSearchCriterion e) {
        StringBuilder sb = new StringBuilder(128);
        final Class<? extends FloatSearchCriterion> c = e.getClass();
        if (c == EqualsFloatSearchCriterion.class) {
            EqualsFloatSearchCriterion r = (EqualsFloatSearchCriterion) e;
            values.add(r.value);
            sb.append(" " + col + " = ?");
        }
        else if (c == LessThanFloatSearchCriterion.class) {
            LessThanFloatSearchCriterion r = (LessThanFloatSearchCriterion) e;
            values.add(r.value);
            sb.append(" " + col + "<=? ");
        }
        else if (c == GreaterThanFloatSearchCriterion.class) {
            GreaterThanFloatSearchCriterion r = (GreaterThanFloatSearchCriterion) e;
            values.add(r.value);
            sb.append(" " + col + " >= ? ");
        }
        else if (c == InRangeFloatSearchCriterion.class) {
            InRangeFloatSearchCriterion r = (InRangeFloatSearchCriterion) e;
            values.add(r.min);
            values.add(r.max);
            sb.append(" (" + col +" >= ? AND " + col + " <= ?) ");
        }
        else {
            throw new CriteriaException("Invalid criteria class used for memory range search: "
                    + e.getClass().getCanonicalName());
        }
        chunks.add(sb);
    }

    boolean isValid(String v) {
        return v != null && !v.isEmpty();
    }
}
