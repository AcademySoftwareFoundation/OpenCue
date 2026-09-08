
package com.imageworks.spcue.dispatcher;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Random;

import org.junit.Test;

import com.imageworks.spcue.DispatchFrame;

/**
 * One frame window per layer delivers to every (host, layer) plan the rows its own slice read would
 * have returned: the slices of a layer tile [0, planned total) without a gap or an overlap, so the
 * window read at that total covers each of them, and a ranking shorter than the plan clips both the
 * same way. Random plans, rankings shorter and longer than the plan.
 */
public class PlanWindowTests {

    private static List<DispatchFrame> ranking(int n) {
        List<DispatchFrame> frames = new ArrayList<>();
        for (int i = 0; i < n; i++)
            frames.add(new DispatchFrame());
        return frames;
    }

    @Test
    public void layerWindowCutsToTheSameSlices() {
        Random rnd = new Random(37);
        String[] layers = {"a", "b", "c"};
        for (int tick = 0; tick < 300; tick++) {
            Maestro s = new Maestro();
            List<Maestro.BookableHost> hosts = new ArrayList<>();
            for (int i = 0; i < 1 + rnd.nextInt(12); i++) {
                Maestro.BookableHost h = new Maestro.BookableHost();
                h.hostId = "h" + i;
                h.planned = new HashMap<>();
                hosts.add(h);
            }
            for (int i = 0; i < rnd.nextInt(30); i++) {
                Maestro.BookableHost h = hosts.get(rnd.nextInt(hosts.size()));
                String layer = layers[rnd.nextInt(layers.length)];
                if (h.planned.containsKey(layer))
                    continue; // a pair plans once per tick
                s.submitCommit(h, layer, 1 + rnd.nextInt(12));
            }
            for (String layer : layers) {
                int total = s.plannedFramesByLayer.getOrDefault(layer, 0);
                int n = rnd.nextInt(total + 5); // the ranking may be shorter than the plan
                List<DispatchFrame> ranked = ranking(n);
                List<DispatchFrame> window = ranked.subList(0, Math.min(total, n));
                boolean[] covered = new boolean[total];
                for (Maestro.BookableHost h : hosts) {
                    int[] slice = h.planned.get(layer);
                    if (slice == null)
                        continue;
                    assertTrue(slice[0] + slice[1] <= total);
                    List<DispatchFrame> bySliceRead =
                            ranked.subList(Math.min(slice[0], n), Math.min(slice[0] + slice[1], n));
                    assertEquals(bySliceRead, Maestro.sliceOf(window, slice));
                    for (int k = slice[0]; k < slice[0] + slice[1]; k++) {
                        assertFalse(covered[k]);
                        covered[k] = true;
                    }
                }
                for (boolean b : covered)
                    assertTrue(b);
            }
        }
    }
}
