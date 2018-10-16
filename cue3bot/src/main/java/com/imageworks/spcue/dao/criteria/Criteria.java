
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

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;

import org.springframework.util.StringUtils;

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

public abstract class Criteria {

    protected List<StringBuilder> chunks = new ArrayList<StringBuilder>(12);
    protected List<Object> values = new ArrayList<Object>(32);
    protected boolean built = false;

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
     * An array of storing Sort objects used to sorr
     * the result of the query.
     */
    private ArrayList<Sort> order = new ArrayList<Sort>();

    abstract public void buildWhereClause();

    public String toString() { return this.getWhereClause(); }

    public Object[] getValuesArray() {
        return values.toArray();
    }

    public List<Object> getValues() {
        return values;
    }

    protected boolean isValid(String v) {
        if (v == null) { return false; }
        if (v.length() == 0) { return false; }
        return true;
    }

    public void clear() {
        built = false;
        chunks.clear();
    }

    public String getWhereClause() {
        build();
        return StringUtils.collectionToDelimitedString(chunks, " AND ");
    }

    public String getWhereClause(String prefix) {
        build();
        if (chunks.size() > 0) {
            return prefix + StringUtils.collectionToDelimitedString(chunks, " AND ");
        }
        return getOrder();
    }

    public String getQuery(String query, String prefix) {
        build();

        if (firstResult > 1 || maxResults > 0) {
            if (order.size() == 0) {
                // TODO(cipriano) Remove this check. (b/117847423)
                if ("postgres".equals(getDatabaseEngine())) {
                    query = query.replaceFirst("SELECT ", "SELECT row_number() OVER () AS RN,");
                } else {
                    query = query.replaceFirst("SELECT ", "SELECT ROWNUM AS RN,");
                }
            } else {
                query = query.replaceFirst("SELECT ", "SELECT row_number() OVER ("+getOrder()+") AS RN, ");
            }
        }

        StringBuilder sb = new StringBuilder(4096);
        if (maxResults > 0 || firstResult > 1) {
            sb.append("SELECT * FROM ( ");
        }

        sb.append(query);
        sb.append(" ");
        if (chunks.size() > 0) {
            sb.append(prefix);
            sb.append(" ");
            sb.append(StringUtils.collectionToDelimitedString(chunks, " AND "));
        }

        if (firstResult > 1 || maxResults > 0) {
            // TODO(cipriano) Remove this check. (b/117847423)
            if ("postgres".equals(getDatabaseEngine())) {
                sb.append(") AS getQueryT WHERE ");
            } else {
                sb.append(") WHERE ");
            }
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

    public String getQuery(String query) {
        return getQuery(query, "AND");
    }

    private String getOrder() {
        if (order.size() < 1) {
            return "";
        }
        StringBuilder sb = new StringBuilder(256);
        sb.append(" ORDER BY ");
        for (Sort o: order) {
            sb.append(o.getColumn());
            sb.append(" ");
            sb.append(o.getDirection().toString());
            sb.append(",");
        }
        sb.delete(sb.length()-1, sb.length());
        return sb.toString();
    }

    public void addPhrase(String col, Collection<String> s) {
        if (s == null) { return; }
        if (s.size() == 0) { return; }
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

    public void addPhrases(Collection<Phrase> phrases, String inclusion) {
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

    public void addPhrase(String col, String v) {
        if (v == null) { return; }
        StringBuilder sb = new StringBuilder(128);
        sb.append("(");
        sb.append(col);
        sb.append("=?");
        sb.append(")");
        values.add(v);
        chunks.add(sb);
    }

    public void addPhrase(String p) {
        chunks.add(new StringBuilder(p));
    }

    public void addRegexPhrase(String col, Set<String> s) {
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

    public void addLikePhrase(String col, Set<String> s) {
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

    public void addGreaterThanTimestamp(String col, int t) {
        StringBuilder sb = new StringBuilder(128);
        sb.append("(epoch(");
        sb.append(col);
        sb.append(") > ?");
        sb.append(") ");
        values.add(t);
        chunks.add(sb);
    }

    public void addLessThanTimestamp(String col, Timestamp t) {
        if (t == null) { return; }
        StringBuilder sb = new StringBuilder(128);
        sb.append("(");
        sb.append(col);
        sb.append(" < ?");
        sb.append(") ");
        values.add(t);
        chunks.add(sb);
    }

    public void addRangePhrase(String col, IntegerSearchCriterion e) {

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
    public void addRangePhrase(String col, FloatSearchCriterion e) {

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

    public void setFirstResult(int firstResult) {
        this.firstResult = firstResult;
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

    // TODO(cipriano) This is a temporary hack to keep both Oracle and Postgres happy. The
    // Criteria system will be migrated to support multiple database engines in a future
    // change. (b/117847423)
    String getDatabaseEngine() {
        String dbEngine = System.getenv("CUEBOT_DB_ENGINE");
        if (dbEngine == null || dbEngine.toLowerCase().equals("postgres")) {
            return "postgres";
        } else if (dbEngine.toLowerCase().equals("oracle")) {
            return "oracle";
        } else {
            throw new RuntimeException("invalid database engine \"" + dbEngine + "\"");
        }
    }
}

