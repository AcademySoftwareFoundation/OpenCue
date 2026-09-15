package com.imageworks.spcue.dispatcher;

import java.util.concurrent.TimeUnit;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;

/**
 * Transient, per-JVM tracker that keeps the OOM memory ratchet off the layer.
 *
 * <p>
 * The legacy behaviour raised the whole layer's memory (+2GB) on every OOM and disabled the layer
 * optimizer, so a single hungry or spuriously-killed frame inflated every other frame's reservation
 * and stranded cores, permanently (reservations could only ever climb). This tracker splits the two
 * cases:
 *
 * <ul>
 * <li><b>Outlier</b> (scattered OOMs): bump the memory for just THAT frame ({@link #frameBumpKb}),
 * leave the layer alone. The hungry frame climbs on its own; nothing else over-reserves; the bump
 * is transient.</li>
 * <li><b>Systematic</b> (a layer accrues {@code threshold} OOMs within the expiry window): the
 * layer really is under-sized, so the caller raises the whole layer, exactly once per window. Frame
 * successes do not clear the streak (an under-sized layer with occasional lucky frames must still
 * escalate); the streak only ages out with the cache expiry. OOMs past the threshold keep taking
 * the per-frame bump, so recurrences on the raised layer still self-correct.</li>
 * </ul>
 *
 * <p>
 * Everything is in-JVM and bounded, so it is ephemeral (a restart forgets it) and cannot grow
 * without bound. No optimizer disable is needed: escalation is a real pattern, so the optimizer
 * settles the raised layer at its true size.
 */
public final class OomMemoryTracker {

    public static final OomMemoryTracker INSTANCE = new OomMemoryTracker();

    /**
     * Default retention, in hours, of a frame's bump and a layer's streak. Memory-hungry frames
     * routinely run for several hours, so anything shorter forgets the pattern mid-render.
     */
    public static final long DEFAULT_EXPIRE_HOURS = 6;

    /** pk_frame -&gt; bumped reserved memory (kB) for that frame's next booking. */
    private volatile Cache<String, Long> frameBump = buildCache(DEFAULT_EXPIRE_HOURS, 200_000);

    /** pk_layer -&gt; OOM count within the expiry window; kept across frame successes. */
    private volatile Cache<String, Integer> layerStreak = buildCache(DEFAULT_EXPIRE_HOURS, 100_000);

    private OomMemoryTracker() {}

    private static <V> Cache<String, V> buildCache(long expireHours, long maxSize) {
        return CacheBuilder.newBuilder().maximumSize(maxSize)
                .expireAfterAccess(expireHours, TimeUnit.HOURS).build();
    }

    /**
     * Rebuild the caches with the configured expiries. Called once at startup (see
     * FrameCompleteHandler); any state tracked before the call is discarded, so configure before
     * traffic.
     */
    public synchronized void configure(long frameBumpExpireHours, long layerStreakExpireHours) {
        frameBump = buildCache(frameBumpExpireHours, 200_000);
        layerStreak = buildCache(layerStreakExpireHours, 100_000);
    }

    /** Reserved-memory bump (kB) recorded for this frame, or 0 if none. */
    public long frameBumpKb(String frameId) {
        Long v = frameBump.getIfPresent(frameId);
        return v == null ? 0L : v;
    }

    /**
     * Record an OOM. Returns true if the LAYER should be raised (it has accrued {@code threshold}
     * OOMs, so it is systematically under-sized); false if the OOM was handled per-frame (the
     * outlier path).
     */
    public boolean onOom(String frameId, String layerId, long newReservedKb, int threshold) {
        // merge() is atomic and monotonic: concurrent OOMs of the same layer each
        // get a distinct streak value, so exactly one thread ever sees == threshold.
        int n = layerStreak.asMap().merge(layerId, 1, Integer::sum);
        if (n == threshold) {
            return true; // systematic: raise the layer, exactly once
        }
        frameBump.put(frameId, newReservedKb); // outlier: bump just this frame
        return false;
    }

    /**
     * A frame of the layer succeeded: forget this frame's bump. The layer's streak is deliberately
     * kept (a success does not prove the layer is sized right) and only ages out with the cache
     * expiry.
     */
    public void onSuccess(String frameId) {
        frameBump.invalidate(frameId);
    }
}
