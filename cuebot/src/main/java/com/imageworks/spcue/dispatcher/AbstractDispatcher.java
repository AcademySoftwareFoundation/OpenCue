
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



package com.imageworks.spcue.dispatcher;

import org.apache.log4j.Logger;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.util.CueUtil;

/**
 * A class to build dispatchers on that contains core dispatching methods that
 * should be the same for all dispatchers.
 */
public abstract class AbstractDispatcher {

    private static final Logger logger = Logger.getLogger(AbstractDispatcher.class);

    public DispatchSupport dispatchSupport;
    public RqdClient rqdClient;

    public boolean testMode = false;

    public boolean dispatchProc(DispatchFrame frame, VirtualProc proc) {

        try {
            dispatch(frame, proc);
            dispatchSummary(proc, frame, "Dispatch");
            DispatchSupport.dispatchedProcs.getAndIncrement();

            return true;

        } catch (FrameReservationException fre) {
            /*
             * This usually just means another thread got the frame first, so
             * just retry on the next frame.
             */
            DispatchSupport.bookingRetries.incrementAndGet();
            String msg =
                    "frame reservation error, "
                            + "dispatchProcToJob failed to book next frame, "
                            + fre;
            logger.warn(msg);
        } catch (ResourceDuplicationFailureException rrfe) {
            /*
             * There is a resource already assigned to the frame we reserved!
             * Don't clear the frame, let it keep running and continue to the
             * next frame.
             */
            DispatchSupport.bookingErrors.incrementAndGet();
            dispatchSupport.fixFrame(frame);

            String msg =
                    "proc update error, dispatchProcToJob failed "
                            + "to assign proc to job " + frame + ", " + proc
                            + " already assigned to another frame." + rrfe;

            logger.warn(msg);
        } catch (ResourceReservationFailureException rrfe) {
            /*
             * This should technically never happen since the proc is already
             * allocated at this point, but, if it does it should be unbooked.
             */
            DispatchSupport.bookingErrors.incrementAndGet();
            String msg =
                    "proc update error, "
                            + "dispatchProcToJob failed to assign proc to job "
                            + frame + ", " + rrfe;
            logger.warn(msg);
            dispatchSupport.unbookProc(proc);
            dispatchSupport.clearFrame(frame);

            throw new DispatcherException("proc reservation error, "
                    + "unable to allocate proc " + proc + "that "
                    + "was already allocated.");
        } catch (Exception e) {
            /*
             * Everything else means that the host/frame record was updated but
             * another error occurred and the proc should be cleared. It could
             * also be running, so use the jobManagerSupprot to kill it just in
             * case.
             */
            DispatchSupport.bookingErrors.incrementAndGet();
            String msg =
                    "dispatchProcToJob failed booking proc " + proc
                            + " on job " + frame;
            logger.warn(msg);
            dispatchSupport.unbookProc(proc);
            dispatchSupport.clearFrame(frame);

            try {
                rqdClient.killFrame(proc, "An accounting error occured "
                        + "when booking this frame.");
            } catch (RqdClientException rqde) {
                /*
                 * Its almost expected that this will fail, as this is just a
                 * precaution if the frame did actually launch.
                 */
            }
            throw new DispatcherException("proc reservation error, "
                    + "unable to communicate with proc " + proc);
        }

        return false;
    }

    public boolean dispatchHost(DispatchFrame frame, VirtualProc proc) {
        try {
            dispatch(frame, proc);
            dispatchSummary(proc, frame, "Booking");
            DispatchSupport.bookedProcs.getAndIncrement();
            DispatchSupport.bookedCores.addAndGet(proc.coresReserved);
            DispatchSupport.bookedGpu.addAndGet(proc.gpuReserved);
            return true;
        } catch (FrameReservationException fre) {
            /*
             * This usually just means another thread got the frame first, so
             * just retry on the next frame.
             */
            DispatchSupport.bookingRetries.incrementAndGet();
            logger.warn("frame reservation error, "
                    + "dispatchHostToJob failed to book new frame: " + fre);
        } catch (ResourceDuplicationFailureException rrfe) {
            /*
             * There is a resource already assigned to the frame we reserved!
             * Don't clear the frame, let it keep running and continue to the
             * next frame.
             */
            DispatchSupport.bookingErrors.incrementAndGet();
            dispatchSupport.fixFrame(frame);

            String msg =
                    "proc update error, dispatchProcToJob failed "
                            + "to assign proc to job " + frame + ", " + proc
                            + " already assigned to another frame." + rrfe;

            logger.warn(msg);
        } catch (ResourceReservationFailureException rrfe) {
            /*
             * This generally means that the resources we're booked by another
             * thread. We can be fairly certain another thread is working with
             * the current host, so bail out. Also note here the proc was never
             * committed so there is not point to clearing or unbooking it.
             */
            DispatchSupport.bookingErrors.incrementAndGet();
            dispatchSupport.clearFrame(frame);

            /* Throw an exception to stop booking * */
            throw new DispatcherException("host reservation error, "
                    + "dispatchHostToJob failed to allocate a new proc " + rrfe);
        } catch (Exception e) {
            /*
             * Any other exception means that the frame/host records have been
             * updated, so, we need to clear the proc. Its possible the frame is
             * actually running, so try to kill it.
             */
            DispatchSupport.bookingErrors.incrementAndGet();
            dispatchSupport.unbookProc(proc);
            dispatchSupport.clearFrame(frame);

            try {
                rqdClient.killFrame(proc, "An accounting error occured "
                        + "when booking this frame.");
            } catch (RqdClientException rqde) {
                /*
                 * Its almost expected that this will fail, as this is just a
                 * precaution if the frame did actually launch.
                 */
            }
            /* Thrown an exception to stop booking */
            throw new DispatcherException("stopped dispatching host " + proc
                    + ", " + e);
        }

        return false;
    }

    public void dispatch(DispatchFrame frame, VirtualProc proc) {
        /*
         * The frame is reserved, the proc is created, now update the frame to
         * the running state.
         */
        dispatchSupport.startFrame(proc, frame);

        /*
         * Creates a proc to run on the specified frame. Throws a
         * ResourceReservationFailureException if the proc cannot be created due
         * to lack of resources.
         */
        dispatchSupport.reserveProc(proc, frame);

        /*
         * Communicate with RQD to run the frame.
         */
        if (!testMode) {
            dispatchSupport.runFrame(proc, frame);
        }

    }

    private static void dispatchSummary(VirtualProc p, DispatchFrame f, String type) {
        String msg = type + " summary: " +
            p.coresReserved +
            " cores / " +
            CueUtil.KbToMb(p.memoryReserved) +
            " memory / " +
            p.gpuReserved +
            " gpu / " +
            CueUtil.KbToMb(p.gpuMemoryReserved) +
            " gpu memory " +
            p.getName() +
            " to " + f.show + "/" + f.shot;
        logger.info(msg);
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public RqdClient getRqdClient() {
        return rqdClient;
    }

    public void setRqdClient(RqdClient rqdClient) {
        this.rqdClient = rqdClient;
    }

    public boolean isTestMode() {
        return testMode;
    }

    public void setTestMode(boolean testMode) {
        this.testMode = testMode;
    }
}

