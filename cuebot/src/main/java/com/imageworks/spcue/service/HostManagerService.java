
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



package com.imageworks.spcue.service;

import java.sql.Timestamp;
import java.util.List;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.EntityModificationError;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.SubscriptionDao;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.HostTagType;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;

@Service
@Transactional
public class HostManagerService implements HostManager {
    private static final Logger logger = Logger.getLogger(HostManagerService.class);

    @Autowired
    private HostDao hostDao;

    @Autowired
    private RqdClient rqdClient;

    @Autowired
    private ProcDao procDao;

    @Autowired
    private ShowDao showDao;

    @Autowired
    private FacilityDao facilityDao;

    @Autowired
    private SubscriptionDao subscriptionDao;

    @Autowired
    private AllocationDao allocationDao;

    public HostManagerService() { }

    @Override
    public void setHostLock(HostInterface host, LockState lock, Source source) {
        hostDao.updateHostLock(host, lock, source);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isLocked(HostInterface host) {
        return hostDao.isHostLocked(host);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isHostUp(HostInterface host) {
        return hostDao.isHostUp(host);
    }

    @Override
    public void setHostState(HostInterface host, HardwareState state) {
        hostDao.updateHostState(host, state);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isSwapping(HostInterface host) {
        return hostDao.isKillMode(host);
    }

    public void rebootWhenIdle(HostInterface host) {
        try {
            hostDao.updateHostState(host, HardwareState.REBOOT_WHEN_IDLE);
            rqdClient.rebootWhenIdle(host);
        }
        catch (RqdClientException e) {
            logger.info("failed to contact host: " + host.getName() + " for reboot");
        }
    }

    public void rebootNow(HostInterface host) {
        try {
            hostDao.updateHostState(host, HardwareState.REBOOTING);
            rqdClient.rebootNow(host);
        }
        catch (RqdClientException e) {
            logger.info("failed to contact host: " + host.getName() + " for reboot");
            hostDao.updateHostState(host, HardwareState.DOWN);
        }
    }

    @Override
    public void setHostStatistics(HostInterface host,
            long totalMemory, long freeMemory,
            long totalSwap, long freeSwap,
            long totalMcp, long freeMcp,
            long totalGpu, long freeGpu,
            int load, Timestamp bootTime,
            String os) {

        hostDao.updateHostStats(host,
                totalMemory, freeMemory,
                totalSwap, freeSwap,
                totalMcp, freeMcp,
                totalGpu, freeGpu,
                load, bootTime, os);
    }

    @Transactional(propagation = Propagation.SUPPORTS, readOnly=true)
    public HostInterface findHost(String name) {
        return hostDao.findHost(name);
    }

    @Transactional(propagation = Propagation.SUPPORTS, readOnly=true)
    public HostInterface getHost(String id) {
        return hostDao.getHost(id);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public DispatchHost createHost(HostReport report) {
        return createHost(report.getHost());
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public DispatchHost createHost(RenderHost rhost) {
        return createHost(rhost, getDefaultAllocationDetail());
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public DispatchHost createHost(RenderHost rhost, AllocationEntity alloc) {

        hostDao.insertRenderHost(rhost, alloc, false);
        DispatchHost host = hostDao.findDispatchHost(rhost.getName());

        hostDao.tagHost(host, alloc.tag, HostTagType.ALLOC);
        hostDao.tagHost(host, host.name, HostTagType.HOSTNAME);

        // Don't tag anything with hardware yet, we don't watch new procs
        // that report in to automatically start running frames.

        hostDao.recalcuateTags(host.id);
        return host;
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public DispatchHost findDispatchHost(String name) {
        return hostDao.findDispatchHost(name);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public HostEntity findHostDetail(String name) {
        return hostDao.findHostDetail(name);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public DispatchHost getDispatchHost(String id) {
        return hostDao.getDispatchHost(id);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public HostEntity getHostDetail(HostInterface host) {
        return hostDao.getHostDetail(host);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public HostEntity getHostDetail(String id) {
        return hostDao.getHostDetail(id);
    }

    @Transactional(propagation = Propagation.SUPPORTS)
    public AllocationEntity getDefaultAllocationDetail() {
        return allocationDao.getDefaultAllocationEntity();
    }

    public void addTags(HostInterface host, String[] tags) {
        for (String tag : tags) {
            if (tag == null) { continue; }
            if (tag.length() == 0) { continue; }
            hostDao.tagHost(host, tag, HostTagType.MANUAL);
        }
        hostDao.recalcuateTags(host.getHostId());
    }

    public void removeTags(HostInterface host, String[] tags) {
        for (String tag: tags) {
            hostDao.removeTag(host, tag);
        }
        hostDao.recalcuateTags(host.getHostId());
    }

    public void renameTag(HostInterface host, String oldTag, String newTag) {
        hostDao.renameTag(host, oldTag, newTag);
        hostDao.recalcuateTags(host.getHostId());
    }

    public void setAllocation(HostInterface host, AllocationInterface alloc) {

        if (procDao.findVirtualProcs(host).size() > 0) {
            throw new EntityModificationError("You cannot move hosts with " +
            		"running procs between allocations.");
        }

        hostDao.lockForUpdate(host);
        hostDao.updateHostSetAllocation(host, alloc);
        hostDao.recalcuateTags(host.getHostId());
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public int getStrandedCoreUnits(HostInterface h) {
        return hostDao.getStrandedCoreUnits(h);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean verifyRunningProc(String procId, String frameId) {
        return procDao.verifyRunningProc(procId, frameId);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<VirtualProc> findVirtualProcs(FrameSearchInterface request) {
        return procDao.findVirtualProcs(request);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public VirtualProc findVirtualProc(FrameInterface frame) {
        return procDao.findVirtualProc(frame);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<VirtualProc> findVirtualProcs(HardwareState state) {
        return procDao.findVirtualProcs(state);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<VirtualProc> findVirtualProcs(LocalHostAssignment l) {
        return procDao.findVirtualProcs(l);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<VirtualProc> findVirtualProcs(ProcSearchInterface r) {
        return procDao.findVirtualProcs(r);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<VirtualProc> findVirtualProcs(HostInterface host) {
        return procDao.findVirtualProcs(host);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<VirtualProc> findBookedVirtualProcs(ProcSearchInterface r) {
        return procDao.findBookedVirtualProcs(r);
    }

    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void unbookVirtualProcs(List<VirtualProc> procs) {
        for (VirtualProc proc: procs) {
            unbookProc(proc);
        }
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void unbookProc(ProcInterface proc) {
        procDao.unbookProc(proc);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void setHostResources(DispatchHost host, HostReport report) {
        hostDao.updateHostResources(host, report);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public VirtualProc getWorstMemoryOffender(HostInterface h) {
        return procDao.getWorstMemoryOffender(h);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public VirtualProc getVirtualProc(String id) {
        return procDao.getVirtualProc(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isOprhan(ProcInterface proc) {
        return procDao.isOrphan(proc);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isPreferShow(HostInterface host) {
        return hostDao.isPreferShow(host);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ShowInterface getPreferredShow(HostInterface host) {
        return showDao.getShowDetail(host);
    }

    public void deleteHost(HostInterface host) {
        hostDao.deleteHost(host);
    }
}

