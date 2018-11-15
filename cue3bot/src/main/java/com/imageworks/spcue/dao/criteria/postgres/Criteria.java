
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

package com.imageworks.spcue.dao.criteria.postgres;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import com.google.common.collect.ImmutableList;

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

    public String getWhereClause() {
        build();
        return generateWhereClause();
    }

    public String getQueryWithPaging(String query) {
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
                // TODO(cipriano) Remove this check. (b/117847423)
                if ("postgres".equals(getDatabaseEngine())) {
                    query = query.replaceFirst("SELECT ", "SELECT row_number() OVER () AS RN,");
                } else {
                    query = query.replaceFirst("SELECT ", "SELECT ROWNUM AS RN,");
                }
            } else {
                query = query.replaceFirst("SELECT ", "SELECT row_number() OVER (" + getOrder(order) + ") AS RN, ");
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

    private String getOrder(List<Sort> order) {
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

    void addGreaterThanTimestamp(String col, int t) {
        StringBuilder sb = new StringBuilder(128);
        sb.append("(epoch(");
        sb.append(col);
        sb.append(") > ?");
        sb.append(") ");
        values.add(t);
        chunks.add(sb);
    }

    boolean isValid(String v) {
        return v != null && !v.isEmpty();
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
