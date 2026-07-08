package com.imageworks.spcue.dispatcher;

import java.util.concurrent.TimeUnit;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;

/**
 * Transient, per-JVM tracker that keeps the OOM memory ratchet off the layer.
 *
 * <p>The legacy behaviour raised the whole layer's memory (+2GB) on every OOM and
 * disabled the layer optimizer, so a single hungry or spuriously-killed frame
 * inflated every other frame's reservation and stranded cores, permanently
 * (reservations could only ever climb). This tracker splits the two cases:
 *
 * <ul>
 * <li><b>Outlier</b> (one frame OOMs): bump the memory for just THAT frame
 * ({@link #frameBumpKb}), leave the layer alone. The hungry frame climbs on its
 * own; nothing else over-reserves; the bump is transient.</li>
 * <li><b>Systematic</b> (a layer OOMs {@code threshold} times in a row, with no
 * success in between): the layer really is under-sized, so the caller raises the
 * whole layer once. Any success of the layer resets the streak, so scattered or
 * spurious OOMs never reach the threshold and never ratchet the layer.</li>
 * </ul>
 *
 * <p>Everything is in-JVM and bounded, so it is ephemeral (a restart forgets it)
 * and cannot grow without bound. No optimizer disable is needed: escalation is a
 * real pattern, so the optimizer settles the raised layer at its true size.
 */
public final class OomMemoryTracker {

    public static final OomMemoryTracker INSTANCE = new OomMemoryTracker();

    /** pk_frame -&gt; bumped reserved memory (kB) for that frame's next booking. */
    private final Cache<String, Long> frameBump = CacheBuilder.newBuilder()
            .maximumSize(200_000)
            .expireAfterAccess(1, TimeUnit.HOURS)
            .build();

    /** pk_layer -&gt; consecutive OOM count, reset on any success of the layer. */
    private final Cache<String, Integer> layerStreak = CacheBuilder.newBuilder()
            .maximumSize(100_000)
            .expireAfterAccess(1, TimeUnit.HOURS)
            .build();

    private OomMemoryTracker() {}

    /** Reserved-memory bump (kB) recorded for this frame, or 0 if none. */
    public long frameBumpKb(String frameId) {
        Long v = frameBump.getIfPresent(frameId);
        return v == null ? 0L : v;
    }

    /**
     * Record an OOM. Returns true if the LAYER should be raised (it has OOMed
     * {@code threshold} times in a row, so it is systematically under-sized);
     * false if the OOM was handled per-frame (the outlier path).
     */
    public boolean onOom(String frameId, String layerId, long newReservedKb, int threshold) {
        // Atomic read-modify-write: several report threads can complete OOM frames
        // of the SAME layer at once, and a getIfPresent/+1/put would lose
        // increments (two OOMs counted as one). asMap() is a ConcurrentMap, so
        // merge() increments the streak atomically.
        int n = layerStreak.asMap().merge(layerId, 1, Integer::sum);
        if (n >= threshold) {
            // Escalate exactly once at the boundary: only the thread that removes
            // the at-threshold mapping raises the layer; a racing thread's remove
            // fails (value already changed/reset) and it falls through to the
            // per-frame outlier path instead of raising the layer a second time.
            if (layerStreak.asMap().remove(layerId, n)) {
                return true;
            }
        }
        frameBump.put(frameId, newReservedKb); // outlier: bump just this frame
        return false;
    }

    /**
     * A frame of the layer succeeded: the layer is not systematically broken right
     * now, so forget the streak and this frame's bump.
     */
    public void onSuccess(String frameId, String layerId) {
        layerStreak.invalidate(layerId);
        frameBump.invalidate(frameId);
    }
}
