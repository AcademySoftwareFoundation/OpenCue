
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

import java.util.List;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.dao.DataAccessException;

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.PrometheusMetricsCollector;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryBacklog;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryDrain;

public class HistoricalSupport {
    private static final Logger logger = LogManager.getLogger(HistoricalSupport.class);

    private HistoricalManager historicalManager;
    private PrometheusMetricsCollector prometheusMetrics;
    private int frameDrainBatchSize = 5000;

    public void archiveHistoricalJobData() {
        logger.info("running historical job data transfer");
        List<JobInterface> jobs = historicalManager.getFinishedJobs();
        for (JobInterface j : jobs) {
            logger.info("transfering job " + j.getId() + "/" + j.getName());
            try {
                historicalManager.transferJob(j);
            } catch (Exception e) {
                logger.warn("failed to transfer job, " + e);
            }
        }
    }

    /**
     * Moves queued frame history events into frame_history. Drains batches until the queue is empty
     * or another Cuebot holds the drain lock. A batch that fails is retried once in safe mode,
     * which drops the failing events instead of leaving them to block the queue.
     */
    public void drainFrameHistory() {
        long start = System.nanoTime();
        int applied = 0;
        int skipped = 0;
        int merged = 0;
        try {
            FrameHistoryDrain batch;
            do {
                batch = drainBatch();
                applied += batch.drained - batch.skipped;
                skipped += batch.skipped;
                merged += batch.merged;
            } while (batch.drained >= frameDrainBatchSize);
        } catch (Exception e) {
            logger.warn("failed to drain frame history queue", e);
        }

        if (skipped > 0) {
            logger.warn("dropped " + skipped + " frame history events, see the database log");
        }

        FrameHistoryBacklog backlog = null;
        try {
            backlog = historicalManager.getFrameHistoryBacklog();
        } catch (Exception e) {
            logger.warn("failed to read frame history backlog", e);
        }
        if (prometheusMetrics != null) {
            prometheusMetrics.recordFrameHistoryDrain(applied, skipped, merged,
                    (System.nanoTime() - start) / 1e9, backlog);
        }
    }

    private FrameHistoryDrain drainBatch() {
        try {
            return historicalManager.drainFrameHistory(frameDrainBatchSize, false);
        } catch (DataAccessException e) {
            logger.warn("frame history batch failed, retrying in safe mode: " + e.getMessage());
            return historicalManager.drainFrameHistory(frameDrainBatchSize, true);
        }
    }

    public HistoricalManager getHistoricalManager() {
        return historicalManager;
    }

    public void setHistoricalManager(HistoricalManager historicalManager) {
        this.historicalManager = historicalManager;
    }

    public void setPrometheusMetrics(PrometheusMetricsCollector prometheusMetrics) {
        this.prometheusMetrics = prometheusMetrics;
    }

    public void setFrameDrainBatchSize(int frameDrainBatchSize) {
        this.frameDrainBatchSize = frameDrainBatchSize;
    }
}
