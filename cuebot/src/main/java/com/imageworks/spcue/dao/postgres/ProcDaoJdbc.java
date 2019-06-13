
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
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.Redirect;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.ResourceDuplicationFailureException;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class ProcDaoJdbc extends AbstractJdbcDao implements ProcDao {

    private static final String VERIFY_RUNNING_PROC =
        "SELECT " +
            "proc.pk_frame " +
        "FROM " +
            "proc, " +
            "job " +
        "WHERE " +
            "proc.pk_job = job.pk_job " +
        "AND " +
            "job.str_state = 'PENDING' " +
        "AND " +
            "proc.pk_proc= ? ";

    public boolean verifyRunningProc(String procId, String frameId) {
        try {
            String pk_frame = getJdbcTemplate().queryForObject(
                    VERIFY_RUNNING_PROC, String.class, procId);
            if (pk_frame != null) {
                return pk_frame.equals(frameId);
            }
            else {
                return false;
            }
        } catch (org.springframework.dao.EmptyResultDataAccessException e) {
            // EAT
        }
        return false;
    }

    private static final String DELETE_VIRTUAL_PROC =
        "DELETE FROM " +
            "proc " +
        "WHERE " +
            "pk_proc=?";

    public boolean deleteVirtualProc(VirtualProc proc) {
        if(getJdbcTemplate().update(DELETE_VIRTUAL_PROC, proc.getProcId()) == 0) {
            logger.warn("failed to delete " + proc + " , proc does not exist.");
            return false;
        }
        // update all of the resource counts.
        procDestroyed(proc);
        return true;
    }

    private static final String INSERT_VIRTUAL_PROC =
        "INSERT INTO " +
            "proc " +
        "( " +
            "pk_proc, " +
            "pk_host, " +
            "pk_show, "+
            "pk_layer,"+
            "pk_job," +
            "pk_frame, "+
            "int_cores_reserved, " +
            "int_mem_reserved, " +
            "int_mem_pre_reserved, " +
            "int_mem_used, "+
            "int_gpu_reserved, " +
            "b_local " +
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ";

    public void insertVirtualProc(VirtualProc proc) {
        proc.id = SqlUtil.genKeyRandom();
        int result = 0;
        try {
            result = getJdbcTemplate().update(INSERT_VIRTUAL_PROC,
                     proc.getProcId(), proc.getHostId(), proc.getShowId(),
                     proc.getLayerId(), proc.getJobId(), proc.getFrameId(),
                     proc.coresReserved, proc.memoryReserved,
                     proc.memoryReserved, Dispatcher.MEM_RESERVED_MIN,
                     proc.gpuReserved, proc.isLocalDispatch);

            // Update all of the resource counts
            procCreated(proc);
        }
        catch (org.springframework.dao.DataIntegrityViolationException d) {
            /*
             * This means the frame is already running.  If that is the
             * case, don't delete it, just set pk_frame to null or
             * the orphaned proc handler will catch it.
             */
            throw new ResourceDuplicationFailureException("The frame " +
                    proc.getFrameId() + " is already assigned to a proc.");
        }
        catch (Exception e) {
            String msg = "unable to book proc " +
                proc.getName() + " on frame " + proc.getFrameId() +
                " , " + e;
            throw new ResourceReservationFailureException(msg,e);
        }

        if (result == 0) {
            String msg = "unable to book proc " + proc.id +
                " the insert query succeeded but returned 0";
            throw new ResourceReservationFailureException(msg);
        }
    }

    private static final String UPDATE_VIRTUAL_PROC_ASSIGN =
        "UPDATE " +
            "proc " +
        "SET " +
            "pk_show = ?, " +
            "pk_job = ?, " +
            "pk_layer = ?, " +
            "pk_frame = ?, " +
            "int_mem_used = 0, " +
            "int_mem_max_used = 0, " +
            "int_virt_used = 0, " +
            "int_virt_max_used = 0, " +
            "ts_dispatched = current_timestamp " +
        "WHERE " +
            "pk_proc = ?";

    public void updateVirtualProcAssignment(VirtualProc proc) {

        int result = 0;
        try {
            result = getJdbcTemplate().update(
                    UPDATE_VIRTUAL_PROC_ASSIGN,
                    proc.getShowId(), proc.getJobId(), proc.getLayerId(),
                    proc.getFrameId(), proc.getProcId());
        }
        catch (org.springframework.dao.DataIntegrityViolationException d) {
            throw new ResourceDuplicationFailureException("The frame " +
                    proc.getFrameId() + " is already assigned to " +
                    "the proc " + proc);
        }
        catch (Exception e) {
            String msg = "unable to book proc " +
                proc.id + ", " + e;
            throw new ResourceReservationFailureException(msg, e);
        }

        /*
         * If the proc was not updated then it has disappeared.
         */
        if (result == 0) {
            String msg = "unable to book proc " +
                proc.id + ", the proc no longer exists,";
            throw new ResourceReservationFailureException(msg);
        }
    }

    private static final String CLEAR_VIRTUAL_PROC_ASSIGN =
        "UPDATE " +
            "proc " +
        "SET " +
            "pk_frame = NULL " +
        "WHERE " +
            "pk_proc = ?";

    public boolean clearVirtualProcAssignment(ProcInterface proc) {
        return getJdbcTemplate().update(CLEAR_VIRTUAL_PROC_ASSIGN,
                proc.getId()) == 1;
    }

    private static final String CLEAR_VIRTUAL_PROC_ASSIGN_BY_FRAME =
        "UPDATE " +
            "proc " +
        "SET " +
            "pk_frame = NULL " +
        "WHERE " +
            "pk_frame = ?";

    public boolean clearVirtualProcAssignment(FrameInterface frame) {
        return getJdbcTemplate().update(CLEAR_VIRTUAL_PROC_ASSIGN_BY_FRAME,
                frame.getFrameId()) == 1;
    }

    private static final String UPDATE_PROC_MEMORY_USAGE =
        "UPDATE " +
            "proc " +
        "SET " +
            "int_mem_used = ?, " +
            "int_mem_max_used = ?," +
            "int_virt_used = ?, " +
            "int_virt_max_used = ?, " +
            "ts_ping = current_timestamp " +
        "WHERE " +
            "pk_frame = ?";

    @Override
    public void updateProcMemoryUsage(FrameInterface f, long rss, long maxRss,
            long vss, long maxVss) {
        /*
         * This method is going to repeat for a proc every 1 minute, so
         * if the proc is being touched by another thread, then return
         * quietly without updating memory usage.
         *
         * If another thread is accessing the proc record, that means
         * the proc is probably being booked to another frame, which
         * makes this update invalid anyway.
         */
        try {
            if (getJdbcTemplate().queryForObject(
                    "SELECT pk_frame FROM proc WHERE pk_frame=? FOR UPDATE",
                    String.class, f.getFrameId()).equals(f.getFrameId())) {

                getJdbcTemplate().update(UPDATE_PROC_MEMORY_USAGE,
                        rss, maxRss, vss, maxVss, f.getFrameId());
            }
        } catch (DataAccessException dae) {
           logger.info("The proc for frame " + f +
                   " could not be updated with new memory stats: " + dae);
        }
    }

    /**
     * Maps a row to a VirtualProc object.
     */
    public static final RowMapper<VirtualProc> VIRTUAL_PROC_MAPPER =
        new RowMapper<VirtualProc>() {
            public VirtualProc mapRow(ResultSet rs, int rowNum) throws SQLException {
                VirtualProc proc = new VirtualProc();
                proc.id = rs.getString("pk_proc");
                proc.hostId = rs.getString("pk_host");
                proc.showId = rs.getString("pk_show");
                proc.jobId=  rs.getString("pk_job");
                proc.layerId = rs.getString("pk_layer");
                proc.frameId = rs.getString("pk_frame");
                proc.hostName = rs.getString("host_name");
                proc.allocationId = rs.getString("pk_alloc");
                proc.facilityId = rs.getString("pk_facility");
                proc.coresReserved =rs.getInt("int_cores_reserved");
                proc.memoryReserved = rs.getInt("int_mem_reserved");
                proc.memoryMax = rs.getInt("int_mem_max_used");
                proc.gpuReserved = rs.getInt("int_gpu_reserved");
                proc.virtualMemoryMax = rs.getLong("int_virt_max_used");
                proc.virtualMemoryUsed = rs.getLong("int_virt_used");
                proc.memoryUsed = rs.getInt("int_mem_used");
                proc.unbooked = rs.getBoolean("b_unbooked");
                proc.isLocalDispatch = rs.getBoolean("b_local");
                proc.os = rs.getString("str_os");
                return proc;
            }
    };

    private static final String GET_VIRTUAL_PROC =
        "SELECT " +
            "proc.pk_proc," +
            "proc.pk_host,"+
            "proc.pk_show,"+
            "proc.pk_job,"+
            "proc.pk_layer,"+
            "proc.pk_frame,"+
            "proc.b_unbooked,"+
            "proc.b_local,"+
            "host.pk_alloc, " +
            "alloc.pk_facility,"+
            "proc.int_cores_reserved,"+
            "proc.int_mem_reserved,"+
            "proc.int_mem_max_used,"+
            "proc.int_mem_used,"+
            "proc.int_gpu_reserved,"+
            "proc.int_virt_max_used,"+
            "proc.int_virt_used,"+
            "host.str_name AS host_name, " +
            "host_stat.str_os " +
        "FROM " +
            "proc," +
            "host, " +
            "host_stat, " +
            "alloc " +
        "WHERE " +
            "proc.pk_host = host.pk_host " +
        "AND " +
            "host.pk_host = host_stat.pk_host " +
        "AND " +
            "host.pk_alloc = alloc.pk_alloc ";

      public VirtualProc getVirtualProc(String id) {
          return getJdbcTemplate().queryForObject(
                  GET_VIRTUAL_PROC + " AND proc.pk_proc=? ",
                  VIRTUAL_PROC_MAPPER, id);
      }

      public VirtualProc findVirtualProc(FrameInterface frame) {
          return getJdbcTemplate().queryForObject(
              GET_VIRTUAL_PROC + " AND proc.pk_frame=? ",
          VIRTUAL_PROC_MAPPER, frame.getFrameId());
      }

      private static final String GET_VIRTUAL_PROC_LIST =
          "SELECT " +
              "proc.*, " +
              "host.str_name AS host_name, " +
              "host.pk_alloc, " +
              "host_stat.str_os, " +
              "alloc.pk_facility " +
          "FROM " +
              "proc, " +
              "frame, " +
              "host," +
              "host_stat, " +
              "alloc, " +
              "layer," +
              "job, " +
              "folder, " +
              "show " +
          "WHERE " +
              "proc.pk_show = show.pk_show " +
          "AND " +
              "proc.pk_host = host.pk_host " +
          "AND " +
              "host.pk_alloc = alloc.pk_alloc " +
          "AND " +
              "host.pk_host = host_stat.pk_host " +
          "AND " +
              "proc.pk_job = job.pk_job " +
          "AND " +
              "proc.pk_layer = layer.pk_layer " +
          "AND " +
              "proc.pk_frame = frame.pk_frame " +
          "AND " +
              "job.pk_folder = folder.pk_folder ";

      public List<VirtualProc> findVirtualProcs(ProcSearchInterface r) {
          return getJdbcTemplate().query(r.getFilteredQuery(GET_VIRTUAL_PROC_LIST),
                  VIRTUAL_PROC_MAPPER, r.getValuesArray());
      }

      @Override
      public List<VirtualProc> findBookedVirtualProcs(ProcSearchInterface r) {
          return getJdbcTemplate().query(r.getFilteredQuery(GET_VIRTUAL_PROC_LIST +
                  "AND proc.b_unbooked = false"), VIRTUAL_PROC_MAPPER, r.getValuesArray());
      }

      public List<VirtualProc> findVirtualProcs(FrameSearchInterface r) {
          return getJdbcTemplate().query(r.getFilteredQuery(GET_VIRTUAL_PROC_LIST),
                  VIRTUAL_PROC_MAPPER, r.getValuesArray());
      }

      public List<VirtualProc> findVirtualProcs(HostInterface host) {
          return getJdbcTemplate().query(GET_VIRTUAL_PROC_LIST + " AND proc.pk_host=?",
                  VIRTUAL_PROC_MAPPER, host.getHostId());
      }

      public List<VirtualProc> findVirtualProcs(LayerInterface layer) {
          return getJdbcTemplate().query(GET_VIRTUAL_PROC_LIST + " AND proc.pk_layer=?",
                  VIRTUAL_PROC_MAPPER, layer.getLayerId());
      }

      public List<VirtualProc> findVirtualProcs(JobInterface job) {
          return getJdbcTemplate().query(GET_VIRTUAL_PROC_LIST + " AND proc.pk_job=?",
                  VIRTUAL_PROC_MAPPER, job.getJobId());
      }

      private static final String FIND_VIRTUAL_PROCS_LJA =
          GET_VIRTUAL_PROC_LIST +
              "AND proc.pk_job=( " +
                  "SELECT pk_job FROM host_local WHERE pk_host_local = ?) " +
              "AND proc.pk_host=(" +
                  "SELECT pk_host FROM host_local WHERE pk_host_local = ?) ";

      @Override
      public List<VirtualProc> findVirtualProcs(LocalHostAssignment l) {
          return getJdbcTemplate().query(
                  FIND_VIRTUAL_PROCS_LJA,
                  VIRTUAL_PROC_MAPPER,
                  l.getId(),
                  l.getId());
      }

      public List<VirtualProc> findVirtualProcs(HardwareState state) {
          return getJdbcTemplate().query(GET_VIRTUAL_PROC_LIST + " AND host_stat.str_state=?",
                  VIRTUAL_PROC_MAPPER, state.toString());
      }

      public void unbookVirtualProcs(List<VirtualProc> procs) {
          List<Object[]> batchArgs = new ArrayList<Object[]>(procs.size());
          for (VirtualProc proc: procs) {
              batchArgs.add(new Object[] { proc.id });
          }

          getJdbcTemplate().batchUpdate(
                  "UPDATE proc SET b_unbooked=true WHERE pk_proc=?", batchArgs);
      }

      @Override
      public boolean setUnbookState(ProcInterface proc, boolean unbooked) {
          return getJdbcTemplate().update(
                  "UPDATE proc SET b_unbooked=? WHERE pk_proc=?",
                  unbooked, proc.getProcId()) == 1;
      }

      @Override
      public boolean setRedirectTarget(ProcInterface p, Redirect r) {
          String name = null;
          boolean unbooked = false;
          if (r != null) {
              name = r.getDestinationName();
              unbooked = true;
          }
          return getJdbcTemplate().update(
                  "UPDATE proc SET str_redirect=?, b_unbooked=? WHERE pk_proc=?",
                  name, unbooked, p.getProcId()) == 1;
      }

      public void unbookProc(ProcInterface proc) {
          getJdbcTemplate().update("UPDATE proc SET b_unbooked=true WHERE pk_proc=?",
                  proc.getProcId());
      }

      public String getCurrentShowId(ProcInterface p) {
          return getJdbcTemplate().queryForObject("SELECT pk_show FROM proc WHERE pk_proc=?",
                  String.class, p.getProcId());
      }

      public String getCurrentJobId(ProcInterface p) {
          return getJdbcTemplate().queryForObject("SELECT pk_job FROM proc WHERE pk_proc=?",
                  String.class, p.getProcId());
      }

      public String getCurrentLayerId(ProcInterface p) {
          return getJdbcTemplate().queryForObject("SELECT pk_layer FROM proc WHERE pk_proc=?",
                  String.class, p.getProcId());
      }

      public String getCurrentFrameId(ProcInterface p) {
          return getJdbcTemplate().queryForObject("SELECT pk_frame FROM proc WHERE pk_proc=?",
                  String.class, p.getProcId());
      }

      private static final String ORPHANED_PROC_INTERVAL = "interval '300' second";
      private static final String GET_ORPHANED_PROC_LIST =
          "SELECT " +
              "proc.*, " +
              "host.str_name AS host_name, " +
              "host_stat.str_os, " +
              "host.pk_alloc, " +
              "alloc.pk_facility " +
          "FROM " +
              "proc, " +
              "host, " +
              "host_stat,"+
              "alloc " +
          "WHERE " +
              "proc.pk_host = host.pk_host " +
          "AND " +
              "host.pk_host = host_stat.pk_host " +
          "AND " +
              "host.pk_alloc = alloc.pk_alloc " +
          "AND " +
              "current_timestamp - proc.ts_ping > " + ORPHANED_PROC_INTERVAL;

      public List<VirtualProc> findOrphanedVirtualProcs() {
          return getJdbcTemplate().query(GET_ORPHANED_PROC_LIST, VIRTUAL_PROC_MAPPER);
      }

      public List<VirtualProc> findOrphanedVirtualProcs(int limit) {
          return getJdbcTemplate().query(
                  GET_ORPHANED_PROC_LIST + " LIMIT " + limit,
                  VIRTUAL_PROC_MAPPER);
      }

      private static final String IS_ORPHAN =
          "SELECT " +
              "COUNT(1) " +
          "FROM " +
              "proc " +
          "WHERE " +
              "proc.pk_proc = ? " +
          "AND " +
              "current_timestamp - proc.ts_ping > " + ORPHANED_PROC_INTERVAL;

      @Override
      public boolean isOrphan(ProcInterface proc) {
          return getJdbcTemplate().queryForObject(IS_ORPHAN,
                  Integer.class, proc.getProcId()) == 1;
      }


      public boolean increaseReservedMemory(ProcInterface p, long value) {
        try {
            return getJdbcTemplate().update("UPDATE proc SET int_mem_reserved=? WHERE pk_proc=? AND int_mem_reserved < ?",
                    value, p.getProcId(), value) == 1;
        } catch (Exception e) {
            // check by trigger erify_host_resources
            throw new ResourceReservationFailureException("failed to increase memory reserveration for proc "
                    + p.getProcId() + " to " + value + ", proc does not have that much memory to spare.");
        }
      }

      private static final String FIND_WORST_MEMORY_OFFENDER =
          "SELECT " +
              "pk_proc, " +
              "pk_host, " +
              "pk_show, "+
              "pk_job, "+
              "pk_layer,"+
              "pk_frame,"+
              "b_unbooked,"+
              "b_local, "+
              "pk_alloc, "+
              "pk_facility, " +
              "int_cores_reserved,"+
              "int_mem_reserved," +
              "int_mem_max_used,"+
              "int_mem_used,"+
              "int_gpu_reserved," +
              "int_virt_max_used,"+
              "int_virt_used,"+
              "host_name, " +
              "str_os " +
          "FROM ("
              + GET_VIRTUAL_PROC + " " +
              "AND " +
                  "host.pk_host = ? " +
              "AND " +
                  "proc.int_mem_reserved != 0 " +
              "ORDER BY " +
                  "proc.int_virt_used / proc.int_mem_pre_reserved DESC " +
          ") AS t1 LIMIT 1";

      @Override
      public VirtualProc getWorstMemoryOffender(HostInterface host) {
          return getJdbcTemplate().queryForObject(FIND_WORST_MEMORY_OFFENDER,
                  VIRTUAL_PROC_MAPPER, host.getHostId());
      }

      public long getReservedMemory(ProcInterface proc) {
          return getJdbcTemplate().queryForObject(
                  "SELECT int_mem_reserved FROM proc WHERE pk_proc=?",
                  Long.class, proc.getProcId());
      }

      public long getReservedGpu(ProcInterface proc) {
          return getJdbcTemplate().queryForObject(
                  "SELECT int_gpu_reserved FROM proc WHERE pk_proc=?",
                  Long.class, proc.getProcId());
      }

      private static final String FIND_UNDERUTILIZED_PROCS =
          "SELECT " +
              "proc.pk_proc," +
              "proc.int_mem_reserved - layer_mem.int_max_rss AS free_mem " +
          "FROM " +
              "proc," +
              "host, " +
              "layer_mem " +
          "WHERE " +
              "proc.pk_host = host.pk_host " +
          "AND " +
              "proc.pk_layer = layer_mem.pk_layer " +
          "AND " +
              "layer_mem.int_max_rss > 0 " +
          "AND " +
              "host.pk_host = ? " +
          "AND " +
              "proc.pk_proc != ? " +
          "AND " +
              "proc.int_mem_reserved - layer_mem.int_max_rss > 0";

      public boolean balanceUnderUtilizedProcs(ProcInterface targetProc, long targetMem) {

          List<Map<String,Object>> result = getJdbcTemplate().queryForList(FIND_UNDERUTILIZED_PROCS,
                  targetProc.getHostId(), targetProc.getProcId());

          if (result.size() == 0) {
              logger.info("unable to find under utilized procs on host " + targetProc.getName());
              return false;
          }

          final Map<String,Long> borrowMap = new HashMap<String,Long>(result.size());
          for (Map<String,Object> map: result) {
              logger.info("creating borrow map for: " + (String) map.get("pk_proc"));
              borrowMap.put((String) map.get("pk_proc"), 0l);
          }

          long memBorrowedTotal = 0l;
          int pass = 0;
          int maxPasses = 3;

          while(true) {
              // the amount of memory we're going to borrow per frame/proc
              long memPerFrame = ((targetMem - memBorrowedTotal) / result.size()) + 1;

              // loop through all of our other running frames and try to borrow
              // a little bit of memory from each one.
              for (Map<String,Object> map: result) {
                  String pk_proc = (String) map.get("pk_proc");
                  Long free_mem = (Long) map.get("free_mem");
                  long available = free_mem - borrowMap.get(pk_proc) - Dispatcher.MEM_RESERVED_MIN;
                  if (available > memPerFrame) {
                      borrowMap.put(pk_proc, borrowMap.get(pk_proc) + memPerFrame);
                      memBorrowedTotal = memBorrowedTotal + memPerFrame;
                  }
              }
              pass++;

              // If we were unable to borrow anything, just break
              if (memBorrowedTotal == 0) { break; }
              // If we got the memory we needed, break
              if (memBorrowedTotal >= targetMem) { break; }
              // If we've exceeded the number of tries in this loop, break
              if (pass >= maxPasses) { break; }
          }

          logger.info("attempted to borrow " + targetMem + " for host "
                 + targetProc.getName() + ", obtained " + memBorrowedTotal);

          if (memBorrowedTotal < targetMem) {
              logger.warn("mem borrowed " + memBorrowedTotal +
                      " was less than the target memory of " + targetMem);
              return false;
          }

          /*
           * This might fail... I'm not really sure if we should
           * fail the whole operation or what.  Just gonna let it ride for now.
           */
          for (Map.Entry<String,Long> set: borrowMap.entrySet()) {
              int success = getJdbcTemplate().update(
                      "UPDATE proc SET int_mem_reserved = int_mem_reserved - ? WHERE pk_proc=?",
                      set.getValue(), set.getKey());
              logger.info("transfering " + (set.getValue() * success) + " from " + set.getKey());
          }

          return true;
      }

      public void updateReservedMemory(ProcInterface p, long value) {
          getJdbcTemplate().update("UPDATE proc SET int_mem_reserved=? WHERE pk_proc=?",
                  value, p.getProcId());
      }

      /**
       * Updates proc counts for the host, subscription,
       * layer, job, folder, and proc point when a proc
       * is destroyed.
       *
       * @param proc
       */
      private void procDestroyed(VirtualProc proc) {


          getJdbcTemplate().update(
              "UPDATE " +
                  "host " +
              "SET " +
                  "int_cores_idle = int_cores_idle + ?," +
                  "int_mem_idle = int_mem_idle + ?, " +
                  "int_gpu_idle = int_gpu_idle + ? " +
              "WHERE " +
                  "pk_host = ?",
            proc.coresReserved, proc.memoryReserved, proc.gpuReserved, proc.getHostId());

          if (!proc.isLocalDispatch) {
              getJdbcTemplate().update(
                  "UPDATE " +
                      "subscription " +
                  "SET " +
                      "int_cores = int_cores - ? " +
                  "WHERE " +
                      "pk_show = ? " +
                  "AND " +
                      "pk_alloc = ?",
                  proc.coresReserved, proc.getShowId(),
                  proc.getAllocationId());
          }

          getJdbcTemplate().update(
                  "UPDATE " +
                      "layer_resource " +
                  "SET " +
                      "int_cores = int_cores - ? " +
                  "WHERE " +
                      "pk_layer = ?",
                  proc.coresReserved, proc.getLayerId());

          if (!proc.isLocalDispatch) {

              getJdbcTemplate().update(
                      "UPDATE " +
                          "job_resource " +
                      "SET " +
                          "int_cores = int_cores - ? " +
                      "WHERE " +
                          "pk_job = ?",
                      proc.coresReserved, proc.getJobId());

              getJdbcTemplate().update(
                      "UPDATE " +
                          "folder_resource " +
                      "SET " +
                          "int_cores = int_cores - ? " +
                      "WHERE " +
                          "pk_folder = " +
                          "(SELECT pk_folder FROM job WHERE pk_job=?)",
                      proc.coresReserved, proc.getJobId());

              getJdbcTemplate().update(
                      "UPDATE " +
                          "point " +
                      "SET " +
                          "int_cores = int_cores - ? " +
                      "WHERE " +
                          "pk_dept = " +
                          "(SELECT pk_dept FROM job WHERE pk_job=?) " +
                      "AND " +
                          "pk_show = " +
                          "(SELECT pk_show FROM job WHERE pk_job=?) ",
                      proc.coresReserved, proc.getJobId(), proc.getJobId());
          }

          if (proc.isLocalDispatch) {

              getJdbcTemplate().update(
                      "UPDATE " +
                          "job_resource " +
                      "SET " +
                          "int_local_cores = int_local_cores - ? " +
                      "WHERE " +
                          "pk_job = ?",
                      proc.coresReserved, proc.getJobId());

              getJdbcTemplate().update(
                      "UPDATE " +
                          "host_local " +
                      "SET " +
                          "int_cores_idle = int_cores_idle + ?, " +
                          "int_mem_idle = int_mem_idle + ?, " +
                          "int_gpu_idle = int_gpu_idle + ? " +
                      "WHERE " +
                          "pk_job = ? " +
                      "AND " +
                          "pk_host = ? ",
                      proc.coresReserved,
                      proc.memoryReserved,
                      proc.gpuReserved,
                      proc.getJobId(),
                      proc.getHostId());
          }
      }

      /**
       * Updates proc counts for the host, subscription,
       * layer, job, folder, and proc point when a new
       * proc is created.
       *
       * @param proc
       */
      private void procCreated(VirtualProc proc) {

          getJdbcTemplate().update(
                "UPDATE " +
                    "host " +
                "SET " +
                    "int_cores_idle = int_cores_idle - ?," +
                    "int_mem_idle = int_mem_idle - ?, " +
                    "int_gpu_idle = int_gpu_idle - ? " +
                "WHERE " +
                    "pk_host = ?",
                proc.coresReserved, proc.memoryReserved, proc.gpuReserved, proc.getHostId());


          /**
           * Not keeping track of local cores this way.
           */

          if (!proc.isLocalDispatch) {
              getJdbcTemplate().update(
                      "UPDATE " +
                          "subscription " +
                      "SET " +
                          "int_cores = int_cores + ? " +
                      "WHERE " +
                          "pk_show = ? " +
                      "AND " +
                          "pk_alloc = ?",
                      proc.coresReserved, proc.getShowId(),
                      proc.getAllocationId());
          }

          getJdbcTemplate().update(
                  "UPDATE " +
                      "layer_resource " +
                  "SET " +
                      "int_cores = int_cores + ? " +
                  "WHERE " +
                      "pk_layer = ?",
                  proc.coresReserved, proc.getLayerId());

          if (!proc.isLocalDispatch) {

              getJdbcTemplate().update(
                      "UPDATE " +
                          "job_resource " +
                      "SET " +
                          "int_cores = int_cores + ? " +
                      "WHERE " +
                          "pk_job = ?",
                      proc.coresReserved, proc.getJobId());

              getJdbcTemplate().update(
                      "UPDATE " +
                          "folder_resource " +
                      "SET " +
                          "int_cores = int_cores + ? " +
                      "WHERE " +
                          "pk_folder = " +
                          "(SELECT pk_folder FROM job WHERE pk_job=?)",
                      proc.coresReserved, proc.getJobId());

              getJdbcTemplate().update(
                      "UPDATE " +
                          "point " +
                      "SET " +
                          "int_cores = int_cores + ? " +
                      "WHERE " +
                          "pk_dept = " +
                          "(SELECT pk_dept FROM job WHERE pk_job=?) " +
                      "AND " +
                          "pk_show = " +
                          "(SELECT pk_show FROM job WHERE pk_job=?) ",
                      proc.coresReserved, proc.getJobId(), proc.getJobId());
          }

          if (proc.isLocalDispatch) {

              getJdbcTemplate().update(
                      "UPDATE " +
                          "job_resource " +
                      "SET " +
                          "int_local_cores = int_local_cores + ? " +
                      "WHERE " +
                          "pk_job = ?",
                      proc.coresReserved, proc.getJobId());

              getJdbcTemplate().update(
                      "UPDATE " +
                          "host_local " +
                      "SET " +
                          "int_cores_idle = int_cores_idle - ?, " +
                          "int_mem_idle = int_mem_idle - ? " +
                      "WHERE " +
                          "pk_job = ? " +
                      "AND " +
                          "pk_host = ?",
                      proc.coresReserved,
                      proc.memoryReserved,
                      proc.getJobId(),
                      proc.getHostId());
          }
      }
}

