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

package com.imageworks.spcue.test.dispatcher;

import org.junit.Before;
import org.junit.Test;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.DispatchSupportService;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the fence that keeps a dispatch rollback from resetting a frame it does not own:
 * {@link DispatchSupportService#startFrameAndProc} records the version its start produced and
 * {@link DispatchSupportService#clearFrame} only resets that run.
 */
public class DispatchSupportServiceClearFrameTests {

    private DispatchSupportService dispatchSupport;
    private FrameDao frameDao;
    private ProcDao procDao;
    private VirtualProc proc;
    private DispatchFrame frame;

    @Before
    public void setup() {
        dispatchSupport = new DispatchSupportService();
        frameDao = mock(FrameDao.class);
        procDao = mock(ProcDao.class);

        dispatchSupport.setFrameDao(frameDao);
        dispatchSupport.setProcDao(procDao);
        dispatchSupport.setJobDao(mock(JobDao.class));
        dispatchSupport.setLayerDao(mock(LayerDao.class));

        proc = new VirtualProc();
        proc.id = "00000000-0000-0000-0000-000000000001";
        proc.frameId = "00000000-0000-0000-0000-0000000000f1";
        proc.hostName = "test-host";

        frame = new DispatchFrame();
        frame.id = proc.frameId;
        frame.name = "0001-test_layer";
        frame.version = 7;
    }

    @Test
    public void startRecordsTheVersionOfTheRunItStarted() {
        when(frameDao.updateFrameStarted(proc, frame)).thenReturn(8);

        dispatchSupport.startFrameAndProc(proc, frame);

        assertEquals(8, frame.getVersion());
    }

    @Test
    public void clearsTheFrameItStarted() {
        when(frameDao.updateFrameClearedIfRunning(frame)).thenReturn(true);

        assertTrue(dispatchSupport.clearFrame(frame));
    }

    @Test
    public void leavesAFrameOwnedByAnotherRunAlone() {
        // The fenced update matches nothing: the frame is not RUNNING at this dispatch's version,
        // so it either never started here or has already been re-dispatched elsewhere.
        when(frameDao.updateFrameClearedIfRunning(frame)).thenReturn(false);

        assertFalse(dispatchSupport.clearFrame(frame));
    }
}
