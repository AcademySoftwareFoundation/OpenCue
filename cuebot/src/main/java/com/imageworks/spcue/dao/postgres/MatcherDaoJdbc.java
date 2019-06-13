
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



package com.imageworks.spcue.dao.postgres;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.FilterInterface;
import com.imageworks.spcue.MatcherEntity;
import com.imageworks.spcue.MatcherInterface;
import com.imageworks.spcue.dao.MatcherDao;
import com.imageworks.spcue.grpc.filter.MatchSubject;
import com.imageworks.spcue.grpc.filter.MatchType;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class MatcherDaoJdbc extends AbstractJdbcDao implements MatcherDao {

    private static final String INSERT_MATCHER =
        "INSERT INTO " +
            "matcher " +
        "( " +
            "pk_matcher,pk_filter,str_subject,str_match,str_value"+
        ") VALUES (?,?,?,?,?)";

    public void insertMatcher(MatcherEntity matcher) {
        matcher.id = SqlUtil.genKeyRandom();

        getJdbcTemplate().update(INSERT_MATCHER,
                matcher.id, matcher.getFilterId(), matcher.subject.toString(),
                matcher.type.toString(), matcher.value);
    }

    public void deleteMatcher(MatcherInterface matcher) {
        getJdbcTemplate().update(
                "DELETE FROM matcher WHERE pk_matcher=?",
                matcher.getMatcherId());
    }

    private static final String GET_MATCHER =
        "SELECT " +
            "matcher.*, " +
            "filter.pk_show "+
        "FROM " +
            "matcher, " +
            "filter " +
        "WHERE " +
            "matcher.pk_filter = filter.pk_filter";

    public MatcherEntity getMatcher(String id) {
        return getJdbcTemplate().queryForObject(
                GET_MATCHER + " AND matcher.pk_matcher=?",
                MATCHER_DETAIL_MAPPER, id);
    }

    public MatcherEntity getMatcher(MatcherInterface matcher) {
        return getJdbcTemplate().queryForObject(
                GET_MATCHER + " AND matcher.pk_matcher=?", MATCHER_DETAIL_MAPPER,
                matcher.getMatcherId());
    }

    public List<MatcherEntity> getMatchers(FilterInterface filter) {
        return getJdbcTemplate().query(
                GET_MATCHER + " AND filter.pk_filter=? ORDER BY ts_created ASC",
                MATCHER_DETAIL_MAPPER, filter.getFilterId());
    }


    public void updateMatcher(MatcherEntity matcher) {
        getJdbcTemplate().update(
                "UPDATE matcher SET str_subject=?,str_match=?,str_value=? WHERE pk_matcher=?",
                matcher.subject.toString(), matcher.type.toString(), matcher.value, matcher.getMatcherId());
    }

    public static final RowMapper<MatcherEntity> MATCHER_DETAIL_MAPPER = new RowMapper<MatcherEntity>() {
        public MatcherEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            MatcherEntity matcher = new MatcherEntity();
            matcher.id = rs.getString("pk_matcher");
            matcher.showId = rs.getString("pk_show");
            matcher.filterId = rs.getString("pk_filter");
            matcher.name = null;
            matcher.subject = MatchSubject.valueOf(rs.getString("str_subject"));
            matcher.type = MatchType.valueOf(rs.getString("str_match"));
            matcher.value = rs.getString("str_value");
            return matcher;
        }
    };
}

