
package com.imageworks.spcue.dispatcher;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;

/**
 * The job and layer environments of one launch batch, read once per job and once per layer. The
 * environment is a property of the job and of the layer, not of the frame, so a batch keeps what it
 * has read; the maps are concurrent because the launch pool runs the batch on several threads. The
 * legacy per-frame paths hand in a fresh memo, so they read as before.
 */
final class LaunchEnv {

    private final Map<String, Map<String, String>> byJob = new ConcurrentHashMap<>();
    private final Map<String, Map<String, String>> byLayer = new ConcurrentHashMap<>();

    Map<String, String> job(DispatchFrame frame, JobDao jobDao) {
        return byJob.computeIfAbsent(frame.getJobId(), k -> jobDao.getEnvironment(frame));
    }

    Map<String, String> layer(DispatchFrame frame, LayerDao layerDao) {
        return byLayer.computeIfAbsent(frame.getLayerId(),
                k -> layerDao.getLayerEnvironment(frame));
    }
}
