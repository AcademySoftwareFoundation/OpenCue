
/*
 * Copyright Contributors to the OpenCue Project
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


package com.imageworks.spcue.dao.oracle;

import java.sql.ResultSet;
import java.sql.SQLException;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.Redirect;
import com.imageworks.spcue.dao.RedirectDao;
import com.imageworks.spcue.grpc.host.RedirectType;

public class RedirectDaoJdbc extends JdbcDaoSupport implements RedirectDao {
    @Override
    public boolean containsKey(String key) {
        return getJdbcTemplate().queryForObject(
            "SELECT count(1) FROM redirect WHERE pk_proc = ?",
            Integer.class,
            key) > 0;
    }

    @Override
    public int countRedirectsWithGroup(String groupId) {
        return getJdbcTemplate().queryForObject(
            "SELECT count(1) FROM redirect WHERE str_group_id = ?",
            Integer.class,
            groupId);
    }

    @Override
    public int deleteExpired() {
        long cutoff = System.currentTimeMillis() - Redirect.EXPIRE_TIME;
        return getJdbcTemplate().update(
            "DELETE FROM redirect WHERE lng_creation_time < ?",
            cutoff);
    }

    @Override
    public void put(String key, Redirect r) {
        getJdbcTemplate().update(
            "MERGE INTO redirect D "
          + "USING (SELECT 1 FROM dual) S "
          + "ON (D.pk_proc = ?) "
          + "WHEN MATCHED THEN UPDATE SET "
          + "  D.str_group_id = ?, "
          + "  D.int_type = ?, "
          + "  D.str_destination_id = ?, "
          + "  D.str_name = ?, "
          + "  D.lng_creation_time = ? "
          + "WHEN NOT MATCHED THEN INSERT (D.pk_proc, D.str_group_id, D.int_type, D.str_destination_id, D.str_name, D.lng_creation_time) "
          + "                      VALUES (        ?,             ?,          ?,                    ?,          ?,                   ?)",
          key,

          r.getGroupId(),
          r.getType().getNumber(),
          r.getDestinationId(),
          r.getDestinationName(),
          r.getCreationTime(),

          key,
          r.getGroupId(),
          r.getType().getNumber(),
          r.getDestinationId(),
          r.getDestinationName(),
          r.getCreationTime());
    }

    @Override
    public Redirect remove(String key) {
        Redirect r = null;
        try {
            r = getJdbcTemplate().queryForObject(
                "SELECT str_group_id, int_type, str_destination_id, str_name, lng_creation_time "
            + "FROM redirect "
            + "WHERE pk_proc = ? "
            + "FOR UPDATE",
            new RowMapper<Redirect>() {
                @Override
                public Redirect mapRow(ResultSet rs, int rowNum) throws SQLException {
                    return new Redirect(
                        rs.getString("str_group_id"),
                        RedirectType.forNumber(rs.getInt("int_type")),
                        rs.getString("str_destination_id"),
                        rs.getString("str_name"),
                        rs.getLong("lng_creation_time"));
                }
            },
            key);
        }
        catch (EmptyResultDataAccessException e) {
            return null;
        }

        getJdbcTemplate().update(
            "DELETE FROM redirect WHERE pk_proc = ?",
            key);

        return r;
    }
}
