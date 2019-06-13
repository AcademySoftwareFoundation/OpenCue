
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
import java.util.Map;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.dao.CommentDao;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class CommentDaoJdbc extends AbstractJdbcDao implements CommentDao {

    public void deleteComment(String id) {
        /*
         * Checks what type of comment we have.
         */
        Map<String,Object> type = getJdbcTemplate().queryForMap(
                "SELECT pk_job, pk_host FROM comments WHERE pk_comment=?",id);

        /*
         * If the comment is deleted successfully, check if we need to unset
         * the b_comment boolean flag.
         */
        if (getJdbcTemplate().update(
                "DELETE FROM comments WHERE pk_comment=?",id) > 0) {
            if (type.get("pk_job") != null) {
                getJdbcTemplate().update("UPDATE job SET b_comment=false WHERE job.pk_job = ? AND " +
                        "(SELECT COUNT(1) FROM comments c WHERE c.pk_job = job.pk_job) = 0",type.get("pk_job"));
            }
            else if (type.get("pk_host") != null) {
                getJdbcTemplate().update("UPDATE host SET b_comment=false WHERE host.pk_host = ? AND " +
                    "(SELECT COUNT(1) FROM comments c WHERE c.pk_host = host.pk_host) = 0",type.get("pk_host"));
            }
        }
    }

    private static final RowMapper<CommentDetail> COMMENT_DETAIL_MAPPER =
        new RowMapper<CommentDetail>() {
        public CommentDetail mapRow(ResultSet rs, int row) throws SQLException {
            CommentDetail d = new CommentDetail();
            d.id = rs.getString("pk_comment");
            d.message = rs.getString("str_message");
            d.subject = rs.getString("str_subject");
            d.timestamp = rs.getTimestamp("ts_created");
            d.user = rs.getString("str_user");
            return d;
        }
    };

    public CommentDetail getCommentDetail(String id) {
        return getJdbcTemplate().queryForObject(
                "SELECT * FROM comments WHERE pk_comment=?",
                COMMENT_DETAIL_MAPPER, id);
    }

    public void updateComment(CommentDetail comment) {
        getJdbcTemplate().update(
                "UPDATE comments SET str_message=?,str_subject=? WHERE pk_comment=?",
                comment.message, comment.subject, comment.id);
    }

    public void updateCommentMessage(String id, String message) {
        getJdbcTemplate().update(
                "UPDATE comments SET str_message=? WHERE pk_comment=?",
                message,id);
    }

    public void updateCommentSubject(String id, String subject) {
        getJdbcTemplate().update(
                "UPDATE comments SET str_subject=? WHERE pk_comment=?",
                subject,id);
    }

    private static final String INSERT_JOB_COMMENT =
        "INSERT INTO " +
            "comments " +
        "(" +
            "pk_comment,pk_job,str_user,str_subject,str_message"+
        ") VALUES (?,?,?,?,?)";

    public void insertComment(JobInterface job, CommentDetail comment) {
        comment.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_JOB_COMMENT,
                comment.id, job.getJobId(), comment.user,
                comment.subject, comment.message);
        getJdbcTemplate().update(
                "UPDATE job SET b_comment=true WHERE pk_job=?",
                job.getJobId());
    }

    private static final String INSERT_HOST_COMMENT =
        "INSERT INTO " +
            "comments " +
        "(" +
            "pk_comment,pk_host,str_user,str_subject,str_message"+
        ") VALUES (?,?,?,?,?)";


    public void insertComment(HostInterface host, CommentDetail comment) {
        comment.id = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(INSERT_HOST_COMMENT,
                comment.id, host.getHostId(), comment.user,
                comment.subject, comment.message);
        getJdbcTemplate().update(
                "UPDATE host SET b_comment=true WHERE pk_host=?",
                host.getHostId());
    }

}

