
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

import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Savepoint;
import java.util.ArrayList;
import java.util.Map;
import java.util.regex.Pattern;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.CallableStatementCreator;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.EntityRemovalError;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class AllocationDaoJdbc extends AbstractJdbcDao implements AllocationDao {

     public static RowMapper<AllocationEntity> ALLOC_MAPPER = new RowMapper<AllocationEntity>() {
         public AllocationEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
             AllocationEntity alloc = new AllocationEntity();
             alloc.id = rs.getString("pk_alloc");
             alloc.facilityId = rs.getString("pk_facility");
             alloc.name = rs.getString("str_name");
             alloc.tag = rs.getString("str_tag");
             return alloc;
         }
     };

     private static final String GET_ALLOCATION =
         "SELECT " +
             "alloc.pk_facility,"+
             "alloc.pk_alloc, " +
             "alloc.str_name, "+
             "alloc.str_tag, " +
             "facility.str_name AS facility_name " +
         "FROM " +
             "alloc, " +
             "facility " +
         "WHERE " +
             "alloc.pk_facility = facility.pk_facility ";

     public AllocationEntity getAllocationEntity(String id) {
         return getJdbcTemplate().queryForObject(
                 GET_ALLOCATION + " AND pk_alloc=?",
                 ALLOC_MAPPER, id);
     }

     public AllocationEntity findAllocationEntity(String facility, String name) {
         return getJdbcTemplate().queryForObject(
                 GET_ALLOCATION + " AND alloc.str_name=?",
                 ALLOC_MAPPER, String.format("%s.%s", facility, name));
     }

     @Override
     public AllocationEntity findAllocationEntity(String name) {
         return getJdbcTemplate().queryForObject(
                 GET_ALLOCATION + " AND alloc.str_name=?",
                 ALLOC_MAPPER, name);
     }

     private static final String INSERT_ALLOCATION =
         "INSERT INTO " +
             "alloc " +
          "(" +
              "pk_alloc,"+
              "pk_facility,"+
              "str_name, "+
              "str_tag "+
          ") VALUES (?,?,?,?)";

     public void insertAllocation(FacilityInterface facility, AllocationEntity detail) {

         String new_alloc_name = String.format("%s.%s",
                 facility.getName(), detail.getName());
         /*
          * Checks if the allocation already exits.
          */
         if (getJdbcTemplate().queryForObject(
                 "SELECT COUNT(1) FROM alloc WHERE str_name=?",
                 Integer.class, new_alloc_name) > 0) {

             getJdbcTemplate().update(
                     "UPDATE alloc SET b_enabled=1 WHERE str_name=?",
                     new_alloc_name);
         }
         else {
             detail.id =  SqlUtil.genKeyRandom();
             detail.name = new_alloc_name;
             getJdbcTemplate().update(INSERT_ALLOCATION,
                     detail.id, facility.getFacilityId(),
                     detail.name, detail.tag);
         }
     }

     public void deleteAllocation(AllocationInterface a) {
         if (getJdbcTemplate().queryForObject(
                 "SELECT COUNT(1) FROM host WHERE pk_alloc=?", Integer.class,
                 a.getAllocationId()) > 0) {
             throw new EntityRemovalError("allocation still contains hosts", a);
         }

         if (getJdbcTemplate().queryForObject(
                 "SELECT b_default FROM alloc WHERE pk_alloc=?", Boolean.class,
                 a.getAllocationId())) {
             throw new EntityRemovalError("you cannot delete the default allocation", a);
         }

         Savepoint sp1;
         try {
             sp1 = getConnection().setSavepoint();
         } catch (SQLException e) {
             throw new RuntimeException("failed to create savepoint", e);
         }

         /*
          * Allocations are logged in historical data so once they are used you
          * can't specifically delete them. They are disabled instead.
          */
         try {
             getJdbcTemplate().update("DELETE FROM alloc WHERE pk_alloc=?",
                 a.getAllocationId());
         } catch (DataIntegrityViolationException e) {
             try {
                 getConnection().rollback(sp1);
             } catch (SQLException e1) {
                 throw new RuntimeException("failed to roll back failed delete", e);
             }
             getJdbcTemplate().update("UPDATE alloc SET b_enabled = false WHERE pk_alloc = ?",
                 a.getAllocationId());
         }
     }

     public void updateAllocationName(AllocationInterface a, String name) {
         if (!Pattern.matches("^\\w+$", name)) {
             throw new IllegalArgumentException("The new allocation name" +
             		"must be alpha numeric and not contain the facility prefix.");
         }

         String[] parts = a.getName().split("\\.", 2);
         String new_name = String.format("%s.%s", parts[0], name);

         getJdbcTemplate().update(
                 "UPDATE alloc SET str_name=? WHERE pk_alloc=?",
                 new_name, a.getAllocationId());
     }

     public void updateAllocationTag(AllocationInterface a, String tag) {
         getJdbcTemplate().update("UPDATE alloc SET str_tag=? WHERE pk_alloc=?",
                 tag, a.getAllocationId());

         getJdbcTemplate().update("UPDATE host_tag SET str_tag=? WHERE " +
                 "host_tag.str_tag_type='Alloc' AND pk_host IN " +
                 "(SELECT pk_host FROM host WHERE host.pk_alloc=?)", tag,
                 a.getAllocationId());

         for (Map<String, Object> e: getJdbcTemplate().queryForList(
                 "SELECT pk_host FROM host WHERE pk_alloc=?",a.getAllocationId())) {
             final String pk_host = (String) e.get("pk_host");
             getJdbcTemplate().call(new CallableStatementCreator() {
                 public CallableStatement createCallableStatement(Connection con) throws SQLException {
                     CallableStatement c = con.prepareCall("{ call recalculate_tags(?) }");
                     c.setString(1, pk_host);
                     return c;
                 }
             }, new ArrayList<SqlParameter>());
         }
     }

     public void setDefaultAllocation(AllocationInterface a) {
         getJdbcTemplate().update("UPDATE alloc SET b_default = 0 WHERE b_default = 1");
         getJdbcTemplate().update("UPDATE alloc SET b_default = 1 WHERe pk_alloc=?",
                 a.getAllocationId());
     }

     public AllocationEntity getDefaultAllocationEntity() {
         return getJdbcTemplate().queryForObject(
                 GET_ALLOCATION + " AND alloc.b_default = true LIMIT 1",
                 ALLOC_MAPPER);
     }

     @Override
     public void updateAllocationBillable(AllocationInterface alloc, boolean value) {
         getJdbcTemplate().update(
                 "UPDATE alloc SET b_billable = ? WHERE pk_alloc = ?",
                 value, alloc.getAllocationId());

     }
}

