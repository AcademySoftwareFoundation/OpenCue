
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

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.imageworks.spcue.dao.AbstractJdbcDao;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.CallableStatementCreator;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.SqlParameter;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.EntityCreationError;
import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.HostTagType;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.SqlUtil;
import org.springframework.stereotype.Repository;

@Repository
public class HostDaoJdbc extends AbstractJdbcDao implements HostDao {

    public static final RowMapper<HostEntity> HOST_DETAIL_MAPPER = new RowMapper<HostEntity>() {
        public HostEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            HostEntity host = new HostEntity();
            host.facilityId = rs.getString("pk_facility");
            host.allocId = rs.getString("pk_alloc");
            host.id = rs.getString("pk_host");
            host.lockState = LockState.valueOf(rs.getString("str_lock_state"));
            host.name = rs.getString("str_name");
            host.nimbyEnabled = rs.getBoolean("b_nimby");
            host.state = HardwareState.valueOf(rs.getString("str_state"));
            host.unlockAtBoot = rs.getBoolean("b_unlock_boot");
            host.cores = rs.getInt("int_cores");
            host.idleCores = rs.getInt("int_cores_idle");
            host.memory = rs.getInt("int_mem");
            host.idleMemory = rs.getInt("int_mem_idle");
            host.gpu = rs.getInt("int_gpu");
            host.idleGpu = rs.getInt("int_gpu_idle");
            host.dateBooted = rs.getDate("ts_booted");
            host.dateCreated = rs.getDate("ts_created");
            host.datePinged = rs.getDate("ts_ping");
            return host;
        }
    };

    public static final RowMapper<HostInterface> HOST_MAPPER = new RowMapper<HostInterface>() {
        public HostInterface mapRow(final ResultSet rs, int rowNum) throws SQLException {
            return new HostInterface() {
                final String id = rs.getString("pk_host");
                final String allocid =  rs.getString("pk_alloc");
                final String name = rs.getString("str_name");
                final String facility =  rs.getString("pk_facility");

                public String getHostId() { return id; }
                public String getAllocationId() { return allocid; }
                public String getId() { return id; }
                public String getName() { return name; }
                public String getFacilityId() { return facility; };
            };
        }
    };

    private static final String GET_HOST_DETAIL =
        "SELECT " +
            "host.pk_host, " +
            "host.pk_alloc,"+
            "host.str_lock_state,"+
            "host.b_nimby,"+
            "host.b_unlock_boot,"+
            "host.int_cores,"+
            "host.int_cores_idle,"+
            "host.int_mem,"+
            "host.int_mem_idle,"+
            "host.int_gpu,"+
            "host.int_gpu_idle,"+
            "host.ts_created,"+
            "host.str_name, " +
            "host_stat.str_state,"+
            "host_stat.ts_ping,"+
            "host_stat.ts_booted, "+
            "alloc.pk_facility " +
        "FROM " +
            "host, " +
            "alloc, " +
            "host_stat " +
        "WHERE " +
            "host.pk_host = host_stat.pk_host " +
        "AND " +
            "host.pk_alloc = alloc.pk_alloc ";

    @Override
    public void lockForUpdate(HostInterface host) {
        try {
            getJdbcTemplate().queryForObject(
                    "SELECT pk_host FROM host WHERE pk_host=? " +
                    "FOR UPDATE NOWAIT",
                    String.class, host.getHostId());
        } catch (Exception e) {
            throw new ResourceReservationFailureException("unable to lock host " +
                    host.getName() + ", the host was locked by another thread.", e);
        }
    }

    @Override
    public HostEntity getHostDetail(HostInterface host) {
        return getJdbcTemplate().queryForObject(GET_HOST_DETAIL + " AND host.pk_host=?",
                HOST_DETAIL_MAPPER, host.getHostId());
    }

    @Override
    public HostEntity getHostDetail(String id) {
        return getJdbcTemplate().queryForObject(GET_HOST_DETAIL + " AND host.pk_host=?",
                HOST_DETAIL_MAPPER, id);
    }

    @Override
    public HostEntity findHostDetail(String name) {
        return getJdbcTemplate().queryForObject(GET_HOST_DETAIL + " AND host.str_name=?",
                HOST_DETAIL_MAPPER, name);
    }

    private static final String GET_HOST=
        "SELECT " +
            "host.pk_host, " +
            "host.pk_alloc,"+
            "host.str_name, " +
            "alloc.pk_facility " +
        "FROM " +
            "host," +
            "alloc " +
        "WHERE " +
            "host.pk_alloc = alloc.pk_alloc " ;

    @Override
    public HostInterface getHost(String id) {
        return getJdbcTemplate().queryForObject(GET_HOST + " AND host.pk_host=?",
                HOST_MAPPER, id);
    }

    @Override
    public HostInterface getHost(LocalHostAssignment l) {
        return getJdbcTemplate().queryForObject(GET_HOST + " AND host.pk_host = ("+
                "SELECT pk_host FROM host_local WHERE pk_host_local=?)",
                HOST_MAPPER, l.getId());
    }

    @Override
    public HostInterface findHost(String name) {
        return getJdbcTemplate().queryForObject(
                GET_HOST + " AND (host.str_name=? OR host.str_fqdn=?)",
                HOST_MAPPER, name, name);
    }

    public static final RowMapper<DispatchHost> DISPATCH_HOST_MAPPER =
        new RowMapper<DispatchHost>() {
        public DispatchHost mapRow(ResultSet rs, int rowNum) throws SQLException {
            DispatchHost host = new DispatchHost();
            host.id = rs.getString("pk_host");
            host.allocationId = rs.getString("pk_alloc");
            host.facilityId = rs.getString("pk_facility");
            host.name = rs.getString("str_name");
            host.lockState = LockState.valueOf(rs.getString("str_lock_state"));
            host.memory = rs.getInt("int_mem");
            host.cores = rs.getInt("int_cores");
            host.gpu= rs.getInt("int_gpu");
            host.idleMemory= rs.getInt("int_mem_idle");
            host.idleCores = rs.getInt("int_cores_idle");
            host.idleGpu= rs.getInt("int_gpu_idle");
            host.isNimby = rs.getBoolean("b_nimby");
            host.threadMode = rs.getInt("int_thread_mode");
            host.tags = rs.getString("str_tags");
            host.os = rs.getString("str_os");
            host.hardwareState =
                HardwareState.valueOf(rs.getString("str_state"));
            return host;
        }
    };

    public static final String GET_DISPATCH_HOST =
        "SELECT " +
            "host.pk_host,"+
            "host.pk_alloc,"+
            "host.str_name," +
            "host.str_lock_state, " +
            "host.int_cores, "+
            "host.int_cores_idle, " +
            "host.int_mem,"+
            "host.int_mem_idle, "+
            "host.int_gpu,"+
            "host.int_gpu_idle, "+
            "host.b_nimby, "+
            "host.int_thread_mode, "+
            "host.str_tags, " +
            "host_stat.str_os, " +
            "host_stat.str_state, " +
            "alloc.pk_facility " +
        "FROM " +
            "host " +
        "INNER JOIN host_stat " +
            "ON (host.pk_host = host_stat.pk_host) " +
        "INNER JOIN alloc " +
            "ON (host.pk_alloc = alloc.pk_alloc) ";

    @Override
    public DispatchHost findDispatchHost(String name) {
        try {
            return getJdbcTemplate().queryForObject(
                    GET_DISPATCH_HOST +
                    "WHERE (host.str_name=? OR host.str_fqdn=?)",
                    DISPATCH_HOST_MAPPER, name, name);
        } catch (EmptyResultDataAccessException e) {
            throw new EmptyResultDataAccessException(
                    "Failed to find host " + name, 1);
        }
    }

    @Override
    public DispatchHost getDispatchHost(String id) {
        return getJdbcTemplate().queryForObject(
                GET_DISPATCH_HOST +
                "WHERE host.pk_host=?",
                DISPATCH_HOST_MAPPER, id);
    }

    private static final String[] INSERT_HOST_DETAIL =
    {
        "INSERT INTO " +
            "host " +
        "("+
            "pk_host, " +
            "pk_alloc, " +
            "str_name, " +
            "b_nimby, " +
            "str_lock_state, " +
            "int_procs,"+
            "int_cores, " +
            "int_cores_idle, " +
            "int_mem,"+
            "int_mem_idle,"+
            "int_gpu,"+
            "int_gpu_idle,"+
            "str_fqdn, " +
            "int_thread_mode "+
        ") " +
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",

        "INSERT INTO " +
        "host_stat " +
        "("+
            "pk_host_stat," +
            "pk_host,"+
            "int_mem_total, " +
            "int_mem_free,"+
            "int_gpu_total, " +
            "int_gpu_free,"+
            "int_swap_total, " +
            "int_swap_free,"+
            "int_mcp_total, " +
            "int_mcp_free,"+
            "int_load, " +
            "ts_booted, " +
            "str_state, " +
            "str_os " +
        ") "+
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"

    };

    @Override
    public void insertRenderHost(RenderHost host, AllocationInterface a, boolean useLongNames) {

        ThreadMode threadMode = ThreadMode.AUTO;
        if (host.getNimbyEnabled()) {
            threadMode = ThreadMode.ALL;
        }

        long memUnits = convertMemoryUnits(host);
        if (memUnits < Dispatcher.MEM_RESERVED_MIN) {
            throw new EntityCreationError("could not create host " + host.getName() + ", " +
                    " must have at least " + Dispatcher.MEM_RESERVED_MIN + " free memory.");
        }

        String fqdn;
        String name = host.getName();
        try {
            fqdn = InetAddress.getByName(host.getName()).getCanonicalHostName();
            // If the provided host name matches the pinged name, use the pinged name.
            // Otherwise use the provided name.
            // If the host lookup fails, use the provided name.
            // In all cases attempt to strip off the domain when setting the name.
            if (fqdn.equals(host.getName())) {
                name = getHostNameFromFQDN(fqdn, useLongNames);
            }
            else {
                name = getHostNameFromFQDN(host.getName(), useLongNames);
                fqdn = host.getName();
            }
        } catch (UnknownHostException e) {
            logger.warn(e);
            fqdn = host.getName();
            name = getHostNameFromFQDN(name, useLongNames);
        }

        String hid = SqlUtil.genKeyRandom();
        int coreUnits = host.getNumProcs() * host.getCoresPerProc();
        String os = host.getAttributes().get("SP_OS");
        if (os == null) {
            os = Dispatcher.OS_DEFAULT;
        }

        long totalGpu;
        if (host.getAttributes().containsKey("totalGpu"))
            totalGpu = Integer.parseInt(host.getAttributes().get("totalGpu"));
        else
            totalGpu = 0;

        long freeGpu;
        if (host.getAttributes().containsKey("freeGpu"))
            freeGpu = Integer.parseInt(host.getAttributes().get("freeGpu"));
        else
            freeGpu = 0;


        getJdbcTemplate().update(INSERT_HOST_DETAIL[0],
                hid, a.getAllocationId(), name, host.getNimbyEnabled(),
                LockState.OPEN.toString(), host.getNumProcs(), coreUnits, coreUnits,
                memUnits, memUnits, totalGpu, totalGpu,
                fqdn, threadMode.getNumber());

        getJdbcTemplate().update(INSERT_HOST_DETAIL[1],
                hid, hid, host.getTotalMem(), host.getFreeMem(),
                totalGpu, freeGpu,
                host.getTotalSwap(), host.getFreeSwap(),
                host.getTotalMcp(), host.getFreeMcp(),
                host.getLoad(), new Timestamp(host.getBootTime() * 1000l),
                host.getState().toString(), os);
    }

    @Override
    public void recalcuateTags(final String id) {
        getJdbcTemplate().call(new CallableStatementCreator() {
            public CallableStatement createCallableStatement(Connection con) throws SQLException {
                CallableStatement c = con.prepareCall("{ call recalculate_tags(?) }");
                c.setString(1, id);
                return c;
            }
        }, new ArrayList<SqlParameter>());
    }

    private static final String UPDATE_RENDER_HOST =
        "UPDATE " +
            "host_stat " +
        "SET " +
            "int_mem_total = ?, " +
            "int_mem_free = ?, " +
            "int_swap_total = ?, " +
            "int_swap_free = ?, "+
            "int_mcp_total = ?, " +
            "int_mcp_free = ?, " +
            "int_gpu_total = ?, " +
            "int_gpu_free = ?, " +
            "int_load = ?," +
            "ts_booted = ?,  " +
            "ts_ping = current_timestamp, "+
            "str_os = ? " +
        "WHERE " +
            "pk_host = ?";

    @Override
    public void updateHostStats(HostInterface host,
            long totalMemory, long freeMemory,
            long totalSwap, long freeSwap,
            long totalMcp, long freeMcp,
            long totalGpu, long freeGpu,
            int load, Timestamp bootTime,
            String os) {

        if (os == null) {
            os = Dispatcher.OS_DEFAULT;
        }

        getJdbcTemplate().update(UPDATE_RENDER_HOST,
                totalMemory, freeMemory, totalSwap,
                freeSwap, totalMcp, freeMcp, totalGpu, freeGpu, load,
                bootTime, os, host.getHostId());
    }

    @Override
    public boolean hostExists(String hostname) {
        try {
            return getJdbcTemplate().queryForObject(
                    "SELECT 1 FROM host WHERE (str_fqdn=? OR str_name=?)",
                    Integer.class, hostname, hostname) > 0;
        } catch (EmptyResultDataAccessException e) {
            return false;
        }
    }

    @Override
    public void updateHostResources(HostInterface host, HostReport report) {

        long memory = convertMemoryUnits(report.getHost());
        int cores = report.getHost().getNumProcs() * report.getHost().getCoresPerProc();

        long totalGpu;
        if (report.getHost().getAttributes().containsKey("totalGpu"))
            totalGpu = Integer.parseInt(report.getHost().getAttributes().get("totalGpu"));
        else
            totalGpu = 0;

        getJdbcTemplate().update(
                "UPDATE " +
                    "host " +
                "SET " +
                    "b_nimby=?,"+
                    "int_cores=?," +
                    "int_cores_idle=?," +
                    "int_mem=?," +
                    "int_mem_idle=?, " +
                    "int_gpu=?," +
                    "int_gpu_idle=? " +
                "WHERE " +
                    "pk_host=? "+
                "AND " +
                    "int_cores = int_cores_idle " +
                "AND " +
                    "int_mem = int_mem_idle",
                    report.getHost().getNimbyEnabled(), cores, cores,
                    memory, memory, totalGpu, totalGpu, host.getId());
    }

    @Override
    public void updateHostLock(HostInterface host, LockState state, Source source) {
        getJdbcTemplate().update(
                "UPDATE host SET str_lock_state=?, str_lock_source=? WHERE pk_host=?",
                state.toString(), source.toString(), host.getHostId());
    }

    @Override
    public void updateHostRebootWhenIdle(HostInterface host, boolean enabled) {
        getJdbcTemplate().update("UPDATE host SET b_reboot_idle=? WHERE pk_host=?",
                enabled, host.getHostId());
    }

    @Override
    public void deleteHost(HostInterface host) {
        getJdbcTemplate().update(
                "DELETE FROM comments WHERE pk_host=?",host.getHostId());
        getJdbcTemplate().update(
                "DELETE FROM host WHERE pk_host=?",host.getHostId());
    }

    @Override
    public void updateHostState(HostInterface host, HardwareState state) {
        getJdbcTemplate().update(
                "UPDATE host_stat SET str_state=? WHERE pk_host=?",
                state.toString(), host.getHostId());
    }

    @Override
    public void updateHostSetAllocation(HostInterface host, AllocationInterface alloc) {

        String tag = getJdbcTemplate().queryForObject(
                "SELECT str_tag FROM alloc WHERE pk_alloc=?",
                String.class, alloc.getAllocationId());
        getJdbcTemplate().update(
                "UPDATE host SET pk_alloc=? WHERE pk_host=?",
                alloc.getAllocationId(), host.getHostId());

        removeTagsByType(host, HostTagType.ALLOC);
        tagHost(host, tag, HostTagType.ALLOC);
    }

    @Override
    public boolean isHostLocked(HostInterface host) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM host WHERE pk_host=? AND str_lock_state!=?",
                Integer.class, host.getHostId(), LockState.OPEN.toString()) > 0;
    }

    private static final String INSERT_TAG =
        "INSERT INTO " +
            "host_tag " +
        "(" +
            "pk_host_tag,"+
            "pk_host,"+
            "str_tag,"+
            "str_tag_type, " +
            "b_constant " +
        ") VALUES (?,?,?,?,?)";


    @Override
    public void tagHost(String id, String tag, HostTagType type) {
        boolean constant = false;
        if (type.equals(HostTagType.ALLOC))
            constant = true;

        getJdbcTemplate().update(INSERT_TAG,
                SqlUtil.genKeyRandom(), id, tag.trim(), type.toString(), constant);
    }

    @Override
    public void tagHost(HostInterface host, String tag, HostTagType type) {
        tagHost(host.getHostId(), tag, type);
    }

    @Override
    public void removeTagsByType(HostInterface host, HostTagType type) {
        getJdbcTemplate().update("DELETE FROM host_tag WHERE pk_host=? AND str_tag_type=?",
                host.getHostId(), type.toString());
    }

    @Override
    public void removeTag(HostInterface host, String tag) {
        getJdbcTemplate().update(
                "DELETE FROM host_tag WHERE pk_host=? AND str_tag=? AND b_constant=false",
                host.getHostId(), tag);
    }

    @Override
    public void renameTag(HostInterface host, String oldTag, String newTag) {
        getJdbcTemplate().update(
                "UPDATE host_tag SET str_tag=? WHERE pk_host=? AND str_tag=? AND b_constant=false",
                newTag, host.getHostId(), oldTag);
    }

    @Override
    public void updateThreadMode(HostInterface host, ThreadMode mode) {
        getJdbcTemplate().update(
                "UPDATE host SET int_thread_mode=? WHERE pk_host=?",
                mode.getNumber(), host.getHostId());
    }

    @Override
    public void updateHostOs(HostInterface host, String os) {
        getJdbcTemplate().update(
                "UPDATE host_stat SET str_os=? WHERE pk_host=?",
                 os, host.getHostId());
    }

    @Override
    public boolean isKillMode(HostInterface h) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM host_stat WHERE pk_host = ? " +
                "AND int_swap_total - int_swap_free > ? AND int_mem_free < ?",
                Integer.class, h.getHostId(), Dispatcher.KILL_MODE_SWAP_THRESHOLD,
                Dispatcher.KILL_MODE_MEM_THRESHOLD) > 0;
    }

    @Override
    public int getStrandedCoreUnits(HostInterface h) {
        try {
            int idle_cores =  getJdbcTemplate().queryForObject(
                    "SELECT int_cores_idle FROM host WHERE pk_host = ? AND int_mem_idle <= ?",
                    Integer.class, h.getHostId(),
                    Dispatcher.MEM_STRANDED_THRESHHOLD);
            return (int) (Math.floor(idle_cores / 100.0)) * 100;
        } catch (EmptyResultDataAccessException e) {
            return 0;
        }
    }

    private static final String IS_HOST_UP =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "host_stat "+
        "WHERE " +
            "host_stat.str_state = ? " +
        "AND " +
            "host_stat.pk_host = ? ";

    @Override
    public boolean isHostUp(HostInterface host) {
        return getJdbcTemplate().queryForObject(IS_HOST_UP,
                Integer.class, HardwareState.UP.toString(),
                host.getHostId()) == 1;
    }

    private static final String IS_PREFER_SHOW =
        "SELECT " +
            "COUNT(1) " +
        "FROM " +
            "host," +
            "owner," +
            "deed "+
        "WHERE " +
            "host.pk_host = deed.pk_host " +
        "AND " +
            "deed.pk_owner = owner.pk_owner " +
        "AND " +
            "host.pk_host = ?";

    @Override
    public boolean isPreferShow(HostInterface h) {
        return getJdbcTemplate().queryForObject(IS_PREFER_SHOW,
                Integer.class, h.getHostId()) > 0;
    }

    @Override
    public boolean isNimbyHost(HostInterface h) {
        return getJdbcTemplate().queryForObject(
                "SELECT COUNT(1) FROM host WHERE b_nimby=true AND pk_host=?",
                Integer.class, h.getHostId()) > 0;
    }

    /**
     * Checks if the passed in name looks like a fully qualified domain name.
     * If so, returns the hostname without the domain. Otherwise returns the passed
     * in name unchanged.
     * @param fqdn - String
     * @return String - hostname
     */
    private String getHostNameFromFQDN(String fqdn, Boolean useLongNames) {
        String hostName;
        Pattern ipPattern = Pattern.compile("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$");
        Matcher ipMatcher = ipPattern.matcher(fqdn);
        if (ipMatcher.matches()){
            hostName = fqdn;
        }
        else if (useLongNames) {
            hostName = fqdn;
            Pattern domainPattern = Pattern.compile(
                ".*(\\.(.*)\\.(co(m|.[a-z]{2})|biz|edu|info|net|org|cn|de|eu|nl))$");
            Matcher domainMatcher = domainPattern.matcher(fqdn);
            if (domainMatcher.matches()){
                hostName = fqdn.replace(domainMatcher.group(1), "");
            }
        }
        else {
            hostName = fqdn.split("\\.")[0];
        }
        return hostName;

    }

    /**
     * Converts the amount of memory reported by the machine
     * to a modificed value which takes into account the
     * operating system and the possibility of user applications.
     *
     * @param host
     * @return
     */
    private long convertMemoryUnits(RenderHost host) {

        long memUnits;
        if (host.getTagsList().contains("64bit")) {
            memUnits = CueUtil.convertKbToFakeKb64bit(host.getTotalMem());
        }
        else {
            memUnits = CueUtil.convertKbToFakeKb32bit(host.getTotalMem());
        }

        /*
         * If this is a desktop, we'll just cut the memory
         * so we don't annoy the user.
         */
        if (host.getNimbyEnabled()) {
            memUnits = (long) (memUnits / 1.5) + Dispatcher.MEM_RESERVED_SYSTEM;
        }

        return memUnits;
    }

}

