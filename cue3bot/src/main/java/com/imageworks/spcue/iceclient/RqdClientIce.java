
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



package com.imageworks.spcue.iceclient;

import org.apache.log4j.Logger;

import com.imageworks.common.spring.remoting.IceCommunicatorBean;
import com.imageworks.spcue.RqdIce.RqdStaticPrx;
import com.imageworks.spcue.RqdIce.RqdStaticPrxHelper;
import com.imageworks.spcue.RqdIce.RunFrame;
import com.imageworks.spcue.RqdIce.RunningFrameInfo;
import com.imageworks.spcue.RqdIce.RunningFramePrx;
import com.imageworks.spcue.RqdIce.RunningFramePrxHelper;

import com.imageworks.spcue.Host;
import com.imageworks.spcue.VirtualProc;

public final class RqdClientIce implements RqdClient {
    private static final Logger logger = Logger.getLogger(RqdClientIce.class);

    private Ice.Communicator communicator;
    private boolean testMode = false;

    private static final int PROXY_TIMEOUT = 5000;
    private static final int PROXY_PORT = 10021;

    public RqdClientIce() { }

    public RqdClientIce(IceCommunicatorBean bean) {
        this.communicator = bean.getCommunicator();
    }

    public void rebootNow(Host host) {
        if (testMode) {
            return;
        }

        RqdStaticPrx proxy = getStaticProxy(host.getName());
        try {
            proxy.rebootNow();
        } catch (java.lang.Throwable e) {
            throw new RqdClientException("failed to reboot host: " + host.getName(),e);
        }
    }

    public void rebootWhenIdle(Host host) {
        if (testMode) {
            return;
        }

        RqdStaticPrx proxy = getStaticProxy(host.getName());
        try {
            proxy.rebootIdle();
        } catch (java.lang.Throwable e) {
            throw new RqdClientException("failed to reboot host: " + host.getName(),e);
        }
    }

    public void killFrame(VirtualProc proc, String message) {
        if (testMode) {
            return;
        }
        try {
            logger.info("killing frame on " + proc.getName() + ", source: " + message);
            RunningFramePrx proxy = getRunningFrameProxy(proc.hostName, proc.frameId);
            proxy.kill(message);
        }
        catch(java.lang.Throwable e) {
            throw new RqdClientException("failed to kill frame " + proc.frameId + ", " + e);
        }
    }

    public void killFrame(String host, String frameid, String message) {
        if (testMode) {
            return;
        }
        try {
            logger.info("killing frame on " + host + ", source: " + message);
            RunningFramePrx proxy = getRunningFrameProxy(host, frameid);
            proxy.kill(message);
        }
        catch(java.lang.Throwable e) {
            throw new RqdClientException("failed to kill frame " + frameid+ ", " + e);
        }
    }

    public RunningFrameInfo getFrameStatus(VirtualProc proc) {
        try {
            RunningFramePrx proxy = getRunningFrameProxy(proc.hostName, proc.frameId);
            return proxy.status();
        }
        catch(java.lang.Throwable e) {
            throw new RqdClientException("failed to obtain status for frame " + proc.frameId);
        }
    }

    public void launchFrame(final RunFrame frame, final VirtualProc proc) {
        if (testMode) {
            return;
        }
        try{
            RqdStaticPrx proxy = getStaticProxy(proc.hostName);
            proxy.launchFrame(frame);
        } catch (java.lang.Throwable e) {
            throw new RqdClientException("RQD comm error" + e,e);
        }
    }

    private RunningFramePrx getRunningFrameProxy(String host, String frameId) {

        StringBuilder sb = new StringBuilder(128);
        sb.append("RunningFrame/");
        sb.append(frameId);
        sb.append(" -t:tcp -p ");
        sb.append(PROXY_PORT);
        sb.append(" -t ");
        sb.append(PROXY_TIMEOUT);
        sb.append(" -h ");
        sb.append(host);

        Ice.ObjectPrx conn = communicator.stringToProxy(sb.toString());
        RunningFramePrx proxy = RunningFramePrxHelper.checkedCast(conn);

        if (proxy == null) {
            throw new RqdClientException("Unable to obtain proxy to frame " + frameId +
                    " on " + host);
        }

        return proxy;
    }

    private RqdStaticPrx getStaticProxy(String host) {

        StringBuilder sb = new StringBuilder(128);
        sb.append("RqdStatic:tcp -p ");
        sb.append(PROXY_PORT);
        sb.append(" -t ");
        sb.append(PROXY_TIMEOUT);
        sb.append(" -h ");
        sb.append(host);

        Ice.ObjectPrx conn = communicator.stringToProxy(sb.toString());
        RqdStaticPrx proxy = RqdStaticPrxHelper.checkedCast(conn);

        if (proxy == null) {
            throw new RqdClientException("unable to build proxy for " + host);
        }
        return proxy;
    }

    @Override
    public void setTestMode(boolean tests) {
        this.testMode = tests;
    }
}

