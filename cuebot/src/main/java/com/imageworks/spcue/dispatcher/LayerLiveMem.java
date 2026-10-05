
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
 * Per-layer rss ledger: the peaks of each layer's last {@link #FRAME_WINDOW} frames, fed by host
 * reports (running frames) and completions (final peak, replacing the running samples). The
 * scheduler reads the median ({@link #typicalRssKb}) to size a layer; fewer than
 * {@link #MIN_SAMPLES} frames read 0. A layer's samples expire after {@link #EXPIRE_MS}.
 */
@Component
public class LayerLiveMem {

    static final int FRAME_WINDOW = 32;
    static final int MIN_SAMPLES = 4;
    private static final long EXPIRE_MS = 12 * 60 * 60 * 1000L;
    private static final long EVICT_EVERY_MS = 60 * 60 * 1000L;
    private volatile long lastEvictMs;

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

        synchronized void fold(String frameId, long rssKb, long now, boolean replace) {
            if (replace)
                peakByFrame.put(frameId, rssKb);
            else
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

    /** Record one host report's running frames: their peaks so far. Never throws. */
    public void record(List<RunningFrameInfo> frames) {
        try {
            for (RunningFrameInfo frame : frames)
                sample(frame, false);
        } catch (RuntimeException ignored) {
            // a malformed report must never disturb report handling
        }
    }

    /** Record a finished frame's final peak, replacing its running samples. Never throws. */
    public void recordFinished(RunningFrameInfo frame) {
        try {
            sample(frame, true);
        } catch (RuntimeException ignored) {
            // a malformed report must never disturb report handling
        }
    }

    private void sample(RunningFrameInfo frame, boolean replace) {
        long now = System.currentTimeMillis();
        if (now - lastEvictMs > EVICT_EVERY_MS) {
            lastEvictMs = now;
            evictStale(now);
        }
        String layerId = frame.getLayerId();
        String frameId = frame.getFrameId();
        long rss = Math.max(frame.getMaxRss(), frame.getRss());
        if (layerId.isEmpty() || frameId.isEmpty() || rss <= 0)
            return;
        byLayerId.computeIfAbsent(layerId, k -> new LayerSamples()).fold(frameId, rss, now,
                replace);
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
