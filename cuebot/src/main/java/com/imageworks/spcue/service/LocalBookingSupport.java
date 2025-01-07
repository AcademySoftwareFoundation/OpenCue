
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.service;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.SpcueRuntimeException;
import com.imageworks.spcue.dispatcher.LocalDispatcher;
import com.imageworks.spcue.grpc.host.LockState;

/**
 * Non transactional class for handling local booking logic.
 */
public class LocalBookingSupport {

    private static final Logger logger = LogManager.getLogger(LocalBookingSupport.class);

    private HostManager hostManager;
    private LocalDispatcher localDispatcher;
    private OwnerManager ownerManager;
    private BookingManager bookingManager;

    public boolean bookLocal(JobInterface job, String hostname, String user,
            LocalHostAssignment lha) {

        logger.info("Setting up local booking for " + user + " on " + job);

        DispatchHost host = hostManager.findDispatchHost(hostname);
        if (host.lockState.equals(LockState.OPEN)) {
            throw new SpcueRuntimeException("The host " + host + " is not NIMBY locked");
        }

        OwnerEntity owner = ownerManager.findOwner(user);
        if (!ownerManager.isOwner(owner, host)) {
            throw new SpcueRuntimeException(
                    user + " is not the owner of the host " + host.getName());
        }

        bookingManager.createLocalHostAssignment(host, job, lha);

        try {
            if (localDispatcher.dispatchHost(host, job).size() > 0) {
                return true;
            }
        } catch (Exception e) {
            /*
             * Eat everything here and we'll throw our own ice exception.
             */
            logger.info("addRenderPartition to job " + job + " failed, " + e);
        }

        logger.info("bookLocal failed to book " + host + " to " + job
                + ", there were no suitable frames to book.");

        return false;
    }

    public boolean bookLocal(LayerInterface layer, String hostname, String user,
            LocalHostAssignment lha) {

        logger.info("Setting up local booking for " + user + " on " + layer);

        DispatchHost host = hostManager.findDispatchHost(hostname);
        if (host.lockState.equals(LockState.OPEN)) {
            throw new SpcueRuntimeException("The host " + host + " is not NIMBY locked");
        }

        OwnerEntity owner = ownerManager.findOwner(user);
        if (!ownerManager.isOwner(owner, host)) {
            throw new SpcueRuntimeException(
                    user + " is not the owner of the host " + host.getName());
        }

        bookingManager.createLocalHostAssignment(host, layer, lha);

        try {
            if (localDispatcher.dispatchHost(host, layer).size() > 0) {
                return true;
            }
        } catch (Exception e) {
            /*
             * Eat everything here and we'll throw our own ice exception.
             */
            logger.info("addRenderPartition to job " + layer + " failed, " + e);
        }

        logger.info("bookLocafailed to book " + host + " to " + layer
                + ", there were no suitable frames to book.");

        return false;

    }

    public boolean bookLocal(FrameInterface frame, String hostname, String user,
            LocalHostAssignment lha) {

        logger.info("Setting up local booking for " + user + " on " + frame);

        DispatchHost host = hostManager.findDispatchHost(hostname);
        if (host.lockState.equals(LockState.OPEN)) {
            throw new SpcueRuntimeException("The host " + host + " is not NIMBY locked");
        }

        OwnerEntity owner = ownerManager.findOwner(user);
        if (!ownerManager.isOwner(owner, host)) {
            throw new SpcueRuntimeException(
                    user + " is not the owner of the host " + host.getName());
        }

        bookingManager.createLocalHostAssignment(host, frame, lha);
        try {
            if (localDispatcher.dispatchHost(host, frame).size() > 0) {
                return true;
            }
        } catch (Exception e) {
            /*
             * Eat everything here and we'll throw our own ice exception.
             */
            logger.info("addRenderPartition to job " + frame + " failed, " + e);
        }

        logger.info("bookLocafailed to book " + host + " to " + frame
                + ", there were no suitable frames to book.");

        return false;
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public LocalDispatcher getLocalDispatcher() {
        return localDispatcher;
    }

    public void setLocalDispatcher(LocalDispatcher localDispatcher) {
        this.localDispatcher = localDispatcher;
    }

    public OwnerManager getOwnerManager() {
        return ownerManager;
    }

    public void setOwnerManager(OwnerManager ownerManager) {
        this.ownerManager = ownerManager;
    }

    public BookingManager getBookingManager() {
        return bookingManager;
    }

    public void setBookingManager(BookingManager bookingManager) {
        this.bookingManager = bookingManager;
    }
}
