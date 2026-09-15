
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

package com.imageworks.spcue.dispatcher;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Component;

import com.imageworks.spcue.grpc.report.RunningFrameInfo;

/**
 * Live per-layer memory ledger fed by every RQD host report, so the scheduler can size a layer's
 * frames from what they REALLY use, not from what the layer declared. {@link HostReportHandler}
 * records each report's running frames as they land; the scheduler reads {@link #typicalRssKb} when
 * it sizes threadable layers before placement.
 *
 * The figure is the MEDIAN of the last {@link #FRAME_WINDOW} frames' rss peaks, not a high-water:
 * one process going haywire is one sample and cannot resize the whole layer. A layer with fewer
 * than {@link #MIN_SAMPLES} frames seen reads 0, so its frames book at their ask until the farm has
 * real evidence (the production workflow: a script watches each task's rss and adjusts core usage;
 * this is that loop, inside the scheduler). Entries age out so a finished or re-scened layer does
 * not pin its old appetite forever.
 */
@Component
public class LayerLiveMem {

    static final int FRAME_WINDOW = 32;
    static final int MIN_SAMPLES = 4;
    private static final long EXPIRE_MS = 30 * 60 * 1000L;
    private static final int MAX_LAYERS = 100_000;

    /** The rss peaks of one layer's most recent frames (insertion-ordered, oldest evicted). */
    static final class LayerSamples {
        private final LinkedHashMap<String, Long> peakByFrame =
                new LinkedHashMap<String, Long>(FRAME_WINDOW, 0.75f, false) {
                    @Override
                    protected boolean removeEldestEntry(Map.Entry<String, Long> eldest) {
                        return size() > FRAME_WINDOW;
                    }
                };
        volatile long atMs;

        synchronized void fold(String frameId, long rssKb, long now) {
            peakByFrame.merge(frameId, rssKb, Math::max);
            atMs = now;
        }

        synchronized long median() {
            int n = peakByFrame.size();
            if (n < MIN_SAMPLES)
                return 0;
            long[] v = new long[n];
            int i = 0;
            for (long kb : peakByFrame.values())
                v[i++] = kb;
            Arrays.sort(v);
            return v[n / 2];
        }
    }

    private final Map<String, LayerSamples> byLayerId = new ConcurrentHashMap<>();

    /** Record one host report's running frames. Never throws into the report path. */
    public void record(List<RunningFrameInfo> frames) {
        try {
            long now = System.currentTimeMillis();
            if (byLayerId.size() > MAX_LAYERS)
                evictStale(now);
            for (RunningFrameInfo f : frames) {
                String layerId = f.getLayerId();
                String frameId = f.getFrameId();
                if (layerId == null || layerId.isEmpty() || frameId == null || frameId.isEmpty())
                    continue;
                long rss = Math.max(f.getMaxRss(), f.getRss());
                if (rss <= 0)
                    continue;
                byLayerId.computeIfAbsent(layerId, k -> new LayerSamples()).fold(frameId, rss, now);
            }
        } catch (RuntimeException ignored) {
            // a malformed report must never disturb report handling
        }
    }

    /**
     * The layer's typical frame rss in KB (median over its recent frames), or 0 when the farm has
     * fewer than {@link #MIN_SAMPLES} fresh samples for it.
     */
    public long typicalRssKb(String layerId) {
        LayerSamples s = byLayerId.get(layerId);
        if (s == null)
            return 0;
        if (s.atMs < System.currentTimeMillis() - EXPIRE_MS) {
            byLayerId.remove(layerId);
            return 0;
        }
        return s.median();
    }

    private void evictStale(long now) {
        long cut = now - EXPIRE_MS;
        for (Map.Entry<String, LayerSamples> e : byLayerId.entrySet()) {
            if (e.getValue().atMs < cut)
                byLayerId.remove(e.getKey());
        }
    }
}
