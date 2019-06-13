
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

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DataRetrievalFailureException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.BuildableDependency;
import com.imageworks.spcue.DependencyManagerException;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.dao.DependDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.depend.DependException;
import com.imageworks.spcue.depend.FrameByFrame;
import com.imageworks.spcue.depend.FrameOnFrame;
import com.imageworks.spcue.depend.FrameOnJob;
import com.imageworks.spcue.depend.FrameOnLayer;
import com.imageworks.spcue.depend.JobOnFrame;
import com.imageworks.spcue.depend.JobOnJob;
import com.imageworks.spcue.depend.JobOnLayer;
import com.imageworks.spcue.depend.LayerOnFrame;
import com.imageworks.spcue.depend.LayerOnJob;
import com.imageworks.spcue.depend.LayerOnLayer;
import com.imageworks.spcue.depend.LayerOnSimFrame;
import com.imageworks.spcue.depend.PreviousFrame;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;

@Service
@Transactional
public class DependManagerService implements DependManager {

    private static final Logger logger = Logger.getLogger(DependManagerService.class);

    @Autowired
    private DependDao dependDao;

    @Autowired
    private JobDao jobDao;

    @Autowired
    private LayerDao layerDao;

    @Autowired
    private FrameDao frameDao;

    @Autowired
    private FrameSearchFactory frameSearchFactory;

    /** Job Depends **/
    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(JobOnJob depend) {
        if (jobDao.isJobComplete(depend.getDependOnJob())) {
            throw new DependException(
                    "The job you are depending on is already complete.");
        }
        dependDao.insertDepend(depend);
        updateDependCount(depend.getDependErJob());
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(JobOnLayer depend) {
        if (layerDao.isLayerComplete(depend.getDependOnLayer())) {
            depend.setActive(false);
        }
        dependDao.insertDepend(depend);
        if (depend.isActive()) {
            updateDependCount(depend.getDependErJob());
        }
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(JobOnFrame depend) {
        if (frameDao.isFrameComplete(depend.getDependOnFrame())) {
            depend.setActive(false);
        }
        dependDao.insertDepend(depend);
        if (depend.isActive()) {
            updateDependCount(depend.getDependErJob());
        }
    }

    /** Layer Depends **/
    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(LayerOnJob depend) {
        if (jobDao.isJobComplete(depend.getDependOnJob())) {
            throw new DependException(
                    "The job you are depending on is already complete.");
        }
        dependDao.insertDepend(depend);
        updateDependCount(depend.getDependErLayer());
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(LayerOnLayer depend) {
        if (layerDao.isLayerComplete(depend.getDependOnLayer())) {
            depend.setActive(false);
        }
        dependDao.insertDepend(depend);
        if (depend.isActive()) {
            updateDependCount(depend.getDependErLayer());
        }
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(LayerOnFrame depend) {
        if (frameDao.isFrameComplete(depend.getDependOnFrame())) {
            depend.setActive(false);
        }
        dependDao.insertDepend(depend);
        if (depend.isActive()) {
            updateDependCount(depend.getDependErLayer());
        }
    }

    /** Frame Depends **/
    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(FrameOnJob depend) {
        if (jobDao.isJobComplete(depend.getDependOnJob())) {
            throw new DependException(
                    "The job you are depending on is already complete.");
        }
        dependDao.insertDepend(depend);
        if (depend.isActive()) {
            updateDependCounts(depend.getDependErFrame());
        }
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(FrameOnLayer depend) {
        if (layerDao.isLayerComplete(depend.getDependOnLayer())) {
            depend.setActive(false);
        }
        dependDao.insertDepend(depend);
        if (depend.isActive()) {
            updateDependCounts(depend.getDependErFrame());
        }
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(FrameOnFrame depend) {
        if (frameDao.isFrameComplete(depend.getDependOnFrame())) {
            depend.setActive(false);
        }
        dependDao.insertDepend(depend);
        if (depend.isActive()) {
            updateDependCounts(depend.getDependErFrame());
        }
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(LayerOnSimFrame depend) {

        /*
         * Need the frame range to make all the dependencies.
         */
        LayerDetail dependErLayer = layerDao.getLayerDetail(
                depend.getDependErLayer().getLayerId());

        /*
         * A normalized list of frames.
         */
        List<Integer> dependErFrameSet = CueUtil.normalizeFrameRange(
                dependErLayer.range, dependErLayer.chunkSize);

        int dependErFrameSetSize = dependErFrameSet.size();
        for (int idx = 0; idx < dependErFrameSetSize; idx = idx +1) {
            /*
             * Lookup the frame we need out of our depend-er layer.
             */
            int frameNum = dependErFrameSet.get(idx);

            FrameInterface dependErFrame = frameDao.findFrame(dependErLayer, frameNum);
            FrameOnFrame fofDepend = new FrameOnFrame(dependErFrame,
                    depend.getDependOnFrame());
            createDepend(fofDepend);
        }
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(FrameByFrame depend) {

        /*
         * Obtain the full layer record so we have access
         * to the frame range and other properties.
         */
        LayerDetail dependErLayer = layerDao.getLayerDetail(
                depend.getDependErLayer().getLayerId());

        LayerDetail dependOnLayer = layerDao.getLayerDetail(
                depend.getDependOnLayer().getLayerId());

        /*
         * Do not create external dependencies on tile layers.
         */
        if (depend.getTarget().equals(DependTarget.EXTERNAL)
                && dependOnLayer.getName().contains("_tile_")) {
            return;
        }

        /*
         * Please note.  The job frame ranges are not normalized in
         * any way, there is going to be duplicates. (why a "Set"
         * would allow dups is unknown).  Anyways, When iterating
         * over these frame sets, you must do so by chunk size and
         * ignore duplicate frames.
         */

        List<Integer> dependErFrameSet = CueUtil.normalizeFrameRange(
                dependErLayer.range, dependErLayer.chunkSize);

        List<Integer> dependOnFrameSet = CueUtil.normalizeFrameRange(
                dependOnLayer.range, dependOnLayer.chunkSize);

        /*
         * When a layer is chunked so large it contains only a single frame,
         * any FrameByFrame depends to/from that that layer are converted
         * to LayerOnLayer depends.
         */
        if ((dependOnFrameSet.size() == 1 && dependOnLayer.chunkSize > 1)
                || (dependErFrameSet.size() == 1 && dependErLayer.chunkSize > 1)) {

            LayerOnLayer lolDepend = new LayerOnLayer(depend.getDependErLayer(),
                    depend.getDependOnLayer());

            createDepend(lolDepend);
            depend.setId(lolDepend.getId());
            return;
        }

        /*
         * Create the parent depends.
         */
        try {
            dependDao.insertDepend(depend);
        }
        catch (DataIntegrityViolationException e) {
            LightweightDependency originalDep =
                dependDao.getDependBySignature(depend.getSignature());
            depend.setId(originalDep.getId());
            if (!depend.isActive()) {
                unsatisfyDepend(originalDep);
            }
            else {
                return;
            }
        }

        int dependErFrameSetSize = dependErFrameSet.size();
        for (int idx = 0; idx < dependErFrameSetSize; idx = idx +1) {

            Set<Integer> dependOnFrames = new HashSet<Integer>(dependOnFrameSet.size());

            int dependErFrameNum = dependErFrameSet.get(idx);
            /* The frame always depends on the corresponding frame. */
            int dependOnFrameNum = dependErFrameNum;

            /*
             * Finds any additional frames the dependErFrame might need to
             * depend on.
             */
            if (dependOnLayer.chunkSize > dependErLayer.chunkSize) {
                dependOnFrameNum = CueUtil.findChunk(dependOnFrameSet, dependErFrameNum);
                dependOnFrames.add(dependOnFrameNum);
            }
            else if (dependOnLayer.chunkSize < dependErLayer.chunkSize) {
                dependOnFrameNum = CueUtil.findChunk(dependOnFrameSet, dependErFrameNum);
                dependOnFrames.add(dependOnFrameNum);

                for(int i=0; i <= dependErLayer.chunkSize - dependOnLayer.chunkSize; i++) {
                    int nextFrameIdx = dependOnFrameSet.indexOf(dependOnFrameNum) + i;
                    try {
                        dependOnFrames.add(dependOnFrameSet.get(nextFrameIdx));
                    } catch (java.lang.IndexOutOfBoundsException e) {
                        continue;
                    }
                }
            }
            else if (!dependErFrameSet.equals(dependOnFrameSet)) {
                if (dependOnFrameSet.contains(dependErFrameNum)) {
                    dependOnFrames.add(dependErFrameNum);
                }
                else {
                    continue;
                }
            }
            else {
                dependOnFrames.add(dependErFrameNum);
            }

            /*
             * Now we can finally start adding child dependencies.
             */
            try {
                FrameInterface dependErFrame = frameDao.findFrame(dependErLayer,
                        dependErFrameNum);
                for (int frameNum: dependOnFrames) {
                    FrameInterface dependOnFrame = frameDao.findFrame(dependOnLayer,
                            frameNum);
                    FrameOnFrame fofDepend = new FrameOnFrame(dependErFrame,
                            dependOnFrame, depend);

                    createDepend(fofDepend);

                }
            } catch (DataRetrievalFailureException dre) {
                logger.warn("failed to create frame by frame depend, " +
                		"part of frame on frame depend: "+
                        depend.getId() + " reason: " + dre);
            }
        }
    }

    @Override
    public void createDepend(PreviousFrame depend) {

        /*
         * Obtain the full layer record so we have access
         * to the frame range and other properties.
         */
        LayerDetail dependErLayer = layerDao.getLayerDetail(
                depend.getDependErLayer().getLayerId());

        LayerDetail dependOnLayer = layerDao.getLayerDetail(
                depend.getDependOnLayer().getLayerId());

        FrameSet dependErFrameSet = new FrameSet(dependErLayer.range);
        FrameSet dependOnFrameSet = new FrameSet(dependOnLayer.range);

        dependDao.insertDepend(depend);
        int dependErFrameSetSize = dependErFrameSet.size();
        for (int idx = 1; idx < dependErFrameSetSize; idx = idx + 1) {

            try {
                FrameInterface dependErFrame = frameDao.findFrame(dependErLayer,
                        dependErFrameSet.get(idx));

                FrameInterface dependOnFrame = frameDao.findFrame(dependOnLayer,
                        dependOnFrameSet.get(idx - 1));

                createDepend(new FrameOnFrame(dependErFrame,
                        dependOnFrame, depend));
            } catch (DataRetrievalFailureException dre) {
                logger.warn("failed to create frame by frame depend, " +
                        "part of a previous frame depend: " +
                        depend.getId() + " reason: " + dre);
            }
        }
    }


    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void createDepend(BuildableDependency depend) {

        JobInterface onJob = null;
        JobInterface erJob = null;

        try {
            onJob = jobDao.findJob(depend.getDependOnJobName());
            erJob = jobDao.findJob(depend.getDependErJobName());
        }
        catch (Exception e) {
            throw new DependencyManagerException("failed to setup new dependency: " +
                    depend.getType().toString() + ", was unable to find job info for " +
                    depend.getDependOnJobName() + " or " + depend.getDependErJobName() +
                    "," + e);
        }

        switch (depend.getType()) {

            case FRAME_BY_FRAME:
                createDepend(new FrameByFrame(
                        layerDao.findLayer(erJob,
                                depend.getDependErLayerName()),
                        layerDao.findLayer(onJob,
                                depend.getDependOnLayerName()))
                );
                break;

            case JOB_ON_JOB:
                createDepend(new JobOnJob(erJob, onJob));
                break;

            case JOB_ON_LAYER:
                createDepend(new JobOnLayer(erJob,
                        layerDao.findLayer(onJob,
                                depend.getDependOnLayerName())));
                break;

            case JOB_ON_FRAME:
                createDepend(new JobOnFrame(erJob,
                        frameDao.findFrame(onJob, depend
                                .getDependOnFrameName())));
                break;

            case LAYER_ON_JOB:
                createDepend(new LayerOnJob(
                        layerDao.findLayer(erJob,
                                depend.getDependErLayerName()),
                        onJob));
                break;

            case LAYER_ON_LAYER:
                LayerOnLayer lol = new LayerOnLayer(
                        layerDao.findLayer(erJob, depend
                                .getDependErLayerName()),
                        layerDao.findLayer(onJob, depend
                                .getDependOnLayerName()));
                lol.setAnyFrame(depend.anyFrame);
                createDepend(lol);
                break;

            case LAYER_ON_FRAME:
                createDepend(new LayerOnFrame(
                        layerDao.findLayer(erJob,
                                depend.getDependErLayerName()),
                        frameDao.findFrame(onJob,
                                depend.getDependOnLayerName())));
                break;

            case FRAME_ON_JOB:
                createDepend(new FrameOnJob(
                        frameDao.findFrame(erJob, depend
                                .getDependErFrameName()),
                        onJob));
                break;

            case FRAME_ON_LAYER:
                createDepend(new FrameOnLayer(
                        frameDao.findFrame(erJob,
                                depend.getDependErFrameName()),
                        layerDao.findLayer(onJob,
                                depend.getDependOnLayerName())));
                break;

            case FRAME_ON_FRAME:
                createDepend(new FrameOnFrame(
                        frameDao.findFrame(erJob, depend
                                .getDependErFrameName()),
                        frameDao.findFrame(onJob, depend
                                .getDependOnFrameName())));
                break;

            case PREVIOUS_FRAME:
                createDepend(new PreviousFrame(
                        layerDao.findLayer(erJob, depend
                                .getDependErLayerName()),
                        layerDao.findLayer(onJob, depend
                                .getDependOnLayerName())));
                break;

            case LAYER_ON_SIM_FRAME:
                createDepend(new LayerOnSimFrame(
                        layerDao.findLayer(erJob,
                                depend.getDependErLayerName()),
                        frameDao.findFrame(onJob,
                                depend.getDependOnFrameName())));
                break;
        }
    }

    @Transactional(propagation=Propagation.SUPPORTS)
    private void updateDependCount(LayerInterface layer) {
        FrameSearchInterface r = frameSearchFactory.create(layer);
        for (FrameInterface f: frameDao.findFrames(r)) {
            updateDependCounts(f);
        }
    }

    @Transactional(propagation=Propagation.SUPPORTS)
    private void updateDependCount(JobInterface job) {
        FrameSearchInterface r = frameSearchFactory.create(job);
        for (FrameInterface f: frameDao.findFrames(r)) {
            updateDependCounts(f);
        }
    }

    @Transactional(propagation = Propagation.SUPPORTS)
    private void updateDependCounts(FrameInterface f) {
        dependDao.incrementDependCount(f);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public LightweightDependency getDepend(String id) {
        return dependDao.getDepend(id);
    }

    @Override
    @Transactional(propagation=Propagation.SUPPORTS)
    public void unsatisfyDepend(LightweightDependency depend) {

        // Currently only handles FrameOnFrame and LayerOnLayer.
        if (dependDao.setActive(depend)) {

            switch(depend.type) {

                case FRAME_ON_FRAME:
                    FrameInterface frame = frameDao.getFrame(depend.dependErFrameId);
                    updateDependCounts(frame);
                    break;

                case LAYER_ON_LAYER:
                    updateDependCount(layerDao.getLayer(depend.dependErLayerId));
                    break;
            }
        }
    }

    @Transactional(propagation=Propagation.SUPPORTS)
    public void satisfyDepend(LightweightDependency depend) {
        /*
         * Before setting the depend to in-active, obtain a list
         * of frames and decrement the depend count on them.
         */
        if (DependType.FRAME_BY_FRAME.equals(depend.type)) {
            List<LightweightDependency> children =
                dependDao.getChildDepends(depend);

            for (LightweightDependency lwd: children) {
                satisfyDepend(lwd);
            }
            return;
        }

        /*
         * Only decrement the depend counts if the depend is
         * actually set to inactive.
         */
        if (dependDao.setInactive(depend)) {
            logger.info("satisfied depend: " + depend.getId());
            for (FrameInterface f: frameDao.getDependentFrames(depend)) {
                if (!dependDao.decrementDependCount(f)) {
                    logger.warn("warning, depend count for " +
                            depend.getId() + "was not decremented " +
                            "for frame " + f + "because the count is " +
                            "already 0.");
                }
            }
        }
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatThisDependsOn(JobInterface job, DependTarget target) {
        return dependDao.getWhatThisDependsOn(job, target);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatThisDependsOn(LayerInterface layer, DependTarget target) {
        return dependDao.getWhatThisDependsOn(layer, target);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatThisDependsOn(FrameInterface frame, DependTarget target) {
        return dependDao.getWhatThisDependsOn(frame, target);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public LightweightDependency getCurrentDepend(String id) {
        return dependDao.getDepend(id);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatDependsOn(JobInterface job) {
        return dependDao.getWhatDependsOn(job);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatDependsOn(JobInterface job, DependTarget target) {
        return dependDao.getWhatDependsOn(job, target);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatDependsOn(FrameInterface frame) {
        return dependDao.getWhatDependsOn(frame);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatDependsOn(FrameInterface frame, boolean active) {
        return dependDao.getWhatDependsOn(frame, active);
    }

    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatDependsOn(LayerInterface layer) {
        return dependDao.getWhatDependsOn(layer);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public List<LightweightDependency> getWhatDependsOn(LayerInterface layer, boolean active) {
        return dependDao.getWhatDependsOn(layer, active);
    }

    @Transactional(propagation=Propagation.REQUIRED)
    public void deleteDepend(LightweightDependency depend) {
        dependDao.deleteDepend(depend);
    }
}

