
package com.imageworks.spcue.dispatcher;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Random;

/**
 * Hosts and candidates for Maestro's unit tests: explicit shapes, and random groups whose hosts
 * repeat a few states and carry GPUs, running layers, plans, warmth and reservations now and then,
 * so a shadow test meets every class of host the scan does.
 */
final class Fix {

    static final long GB = 1L << 20;
    static final String[] LAYERS = {"l0", "l1", "l2", "l3", "l4", "l5"};

    /** A fully idle host of the given totals, its tick maps empty. */
    static Maestro.BookableHost host(String id, int cores, long mem, int gpus, long gpuMem) {
        Maestro.BookableHost h = new Maestro.BookableHost();
        h.hostId = id;
        h.hostName = "host" + id;
        h.coresTotal = cores;
        h.memTotal = mem;
        h.gpusTotal = gpus;
        h.gpuMemTotal = gpuMem;
        h.coresIdle = cores;
        h.memIdle = mem;
        h.gpusIdle = gpus;
        h.gpuMemIdle = gpuMem;
        h.layerFrames = new HashMap<>();
        h.layersRunning = new HashSet<>();
        h.planned = new HashMap<>();
        return h;
    }

    /** A CPU host with 64 GB and the given running procs. */
    static Maestro.BookableHost host(String id, int cores, int running) {
        Maestro.BookableHost h = host(id, cores, 64 * GB, 0, 0);
        h.runningProcs = running;
        return h;
    }

    /** A candidate of the given needs with waiting frames, its caps open and its cells fresh. */
    static Maestro.LayerCandidate candidate(String layerId, int cores, long mem, int gpus,
            long gpuMem, int waiting) {
        Maestro.LayerCandidate c = new Maestro.LayerCandidate();
        c.layerId = layerId;
        c.jobId = "j" + layerId;
        c.showId = "s";
        c.showKey = "s@a";
        c.layerCoresMin = cores;
        c.layerMemMin = mem;
        c.layerGpusMin = gpus;
        c.layerGpuMemMin = gpuMem;
        c.jobMaxCores = 100000;
        c.showBurstCores = Integer.MAX_VALUE;
        c.showSizeCores = 100;
        c.waitingFrameCount = waiting;
        c.rssProven = true;
        c.jobCell = new Maestro.Cell();
        c.showCell = new Maestro.Cell();
        return c;
    }

    /** A random host: three hardware classes, a few idle levels so classes form, one with GPUs. */
    static Maestro.BookableHost randomHost(Random rnd, int ix) {
        int cls = rnd.nextInt(3);
        Maestro.BookableHost h = host("h" + ix, 800 * (1 + cls), GB * 32 * (1 + cls),
                cls == 2 ? 2 : 0, cls == 2 ? GB * 16 : 0);
        h.coresIdle = rnd.nextInt(6) == 0 ? rnd.nextInt(h.coresTotal + 1)
                : h.coresTotal / (1 + rnd.nextInt(4));
        h.memIdle = rnd.nextInt(6) == 0 ? (long) (rnd.nextDouble() * h.memTotal)
                : h.memTotal / (1 + rnd.nextInt(4));
        h.gpusIdle = h.gpusTotal > 0 ? rnd.nextInt(h.gpusTotal + 1) : 0;
        h.gpuMemIdle = h.gpusTotal > 0 ? h.gpuMemTotal / (1 + rnd.nextInt(2)) : 0;
        for (int i = 0; i < rnd.nextInt(3); i++) {
            String l = LAYERS[rnd.nextInt(LAYERS.length)];
            h.layerFrames.merge(l, 1 + rnd.nextInt(3), Integer::sum);
            h.layersRunning.add(l);
        }
        if (rnd.nextInt(4) == 0) {
            String l = LAYERS[rnd.nextInt(LAYERS.length)];
            h.planned.put(l, new int[] {0, 4});
            h.layerFrames.merge(l, 4, Integer::sum);
        }
        if (rnd.nextInt(3) == 0) {
            h.warmth = new HashMap<>();
            for (int i = 0; i < 1 + rnd.nextInt(2); i++)
                h.warmth.put(LAYERS[rnd.nextInt(LAYERS.length)], (long) rnd.nextInt(100));
        }
        h.odometer = rnd.nextInt(120);
        if (rnd.nextInt(8) == 0) {
            h.reservation = new Maestro.Reservation(LAYERS[rnd.nextInt(LAYERS.length)], 100, 400);
            h.tReady = rnd.nextBoolean() ? rnd.nextInt(3600) : null;
        }
        return h;
    }

    /** A random candidate over the six layers: CPU or GPU needs, 0 to 4 waiting frames. */
    static Maestro.LayerCandidate randomCandidate(Random rnd, int ix) {
        boolean gpu = rnd.nextInt(4) == 0;
        Maestro.LayerCandidate c = candidate(LAYERS[ix % LAYERS.length], 100 * (1 + rnd.nextInt(8)),
                GB * (1 + rnd.nextInt(16)), gpu ? 1 : 0, gpu ? GB * 4 : 0, rnd.nextInt(5));
        c.jobId = "j" + ix;
        c.rssProven = rnd.nextInt(4) != 0;
        c.clockTimeHighSec = rnd.nextBoolean() ? 0 : rnd.nextInt(7200);
        if (rnd.nextInt(3) == 0)
            c.limitIds = Arrays.asList("lic");
        return c;
    }
}
