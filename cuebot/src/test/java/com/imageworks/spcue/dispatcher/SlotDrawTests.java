
package com.imageworks.spcue.dispatcher;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.junit.Test;

/**
 * The slot draw's law, asserted exactly: over every unit of a draw, each candidate of the
 * lowest-tier shows is picked as many times as its weight, and no other candidate is picked. That
 * is the invariant the linear walk enforced, compared here unit by unit rather than by a sample. A
 * second test pins the picks on a fixed farm, and a third checks that removal and a moving tier
 * hand the slots on as the walk did. The show cells stand in for the tick-wide counters: one cell
 * per show, shared by its candidates, as bindCells binds them.
 */
public class SlotDrawTests {

    private static Maestro.LayerCandidate candidate(Map<String, Maestro.Cell> cells, String layer,
            String show, int size, int coresInUse, int priority, int waiting) {
        Maestro.LayerCandidate c = new Maestro.LayerCandidate();
        c.layerId = layer;
        c.showId = show;
        c.showKey = show + "@alloc";
        c.showSizeCores = size;
        c.showCoresInUse = coresInUse;
        c.showCell = cells.computeIfAbsent(c.showKey, k -> {
            Maestro.Cell x = new Maestro.Cell();
            x.used = coresInUse;
            return x;
        });
        c.priority = priority;
        c.waitingFrameCount = waiting;
        return c;
    }

    /** The linear law: weight for every candidate of a lowest-tier show still in the draw. */
    private static Map<String, Long> expectedUnits(List<Maestro.LayerCandidate> in) {
        double low = Double.POSITIVE_INFINITY;
        for (Maestro.LayerCandidate c : in)
            low = Math.min(low, Maestro.showTier(c));
        Map<String, Long> units = new HashMap<>();
        for (Maestro.LayerCandidate c : in) {
            if (Maestro.showTier(c) <= low)
                units.put(c.layerId, Maestro.lotteryWeight(c));
        }
        return units;
    }

    /** Every unit of the draw, mapped through next(u), counted per candidate. */
    private static Map<String, Long> drawnUnits(SlotDraw draw, long weightSum) {
        Map<String, Long> units = new HashMap<>();
        for (long r = 0; r < weightSum; r++) {
            Maestro.LayerCandidate c = draw.next((r + 0.5) / weightSum);
            units.merge(c.layerId, 1L, Long::sum);
        }
        return units;
    }

    private static long sum(Map<String, Long> units) {
        long s = 0;
        for (long v : units.values())
            s += v;
        return s;
    }

    @Test
    public void everyUnitLandsByWeightOnTheLowestTier() {
        Random rnd = new Random(11);
        for (int farm = 0; farm < 200; farm++) {
            int shows = 1 + rnd.nextInt(5);
            List<Maestro.LayerCandidate> all = new ArrayList<>();
            Map<String, Maestro.Cell> cells = new HashMap<>();
            for (int s = 0; s < shows; s++) {
                int size = rnd.nextInt(3) == 0 ? 0 : 100 * (1 + rnd.nextInt(4));
                int inUse = rnd.nextInt(3) == 0 ? 0 : rnd.nextInt(500);
                int layers = 1 + rnd.nextInt(6);
                for (int l = 0; l < layers; l++)
                    all.add(candidate(cells, "s" + s + "l" + l, "show" + s, size, inUse,
                            rnd.nextInt(4) == 0 ? 0 : 1 + rnd.nextInt(300), rnd.nextInt(3)));
            }
            SlotDraw draw = new SlotDraw(all);
            List<Maestro.LayerCandidate> in = new ArrayList<>();
            for (Maestro.LayerCandidate c : all)
                if (c.waitingFrameCount > 0)
                    in.add(c);
            // Remove candidates one by one; the law must hold at every step.
            while (!in.isEmpty()) {
                Map<String, Long> expected = expectedUnits(in);
                assertEquals(expected, drawnUnits(draw, sum(expected)));
                Maestro.LayerCandidate gone = in.remove(rnd.nextInt(in.size()));
                draw.remove(gone);
                // A placement moves its show's cores, so the tiers move under the draw.
                if (rnd.nextBoolean())
                    gone.showCell.used += 100;
            }
            assertTrue(draw.isEmpty());
        }
    }

    @Test
    public void pinnedPicksOnAFixedFarm() {
        Map<String, Maestro.Cell> cells = new HashMap<>();
        // showB sits under its size (tier 0.4), showA over it (1.5), showC has no size (1.0).
        Maestro.LayerCandidate a = candidate(cells, "a", "showA", 100, 150, 500, 5);
        Maestro.LayerCandidate b1 = candidate(cells, "b1", "showB", 100, 40, 1, 5);
        Maestro.LayerCandidate b2 = candidate(cells, "b2", "showB", 100, 40, 50, 5);
        Maestro.LayerCandidate b3 = candidate(cells, "b3", "showB", 100, 40, 100, 5);
        Maestro.LayerCandidate c = candidate(cells, "c", "showC", 0, 0, 900, 5);
        List<Maestro.LayerCandidate> all = List.of(a, b1, b2, b3, c);
        SlotDraw draw = new SlotDraw(all);
        // Units 0..150: b1 covers 0, b2 covers 1..50, b3 covers 51..150.
        assertSame(b1, draw.next(0.0));
        assertSame(b1, draw.next(0.5 / 151));
        assertSame(b2, draw.next(1.5 / 151));
        assertSame(b2, draw.next(50.5 / 151));
        assertSame(b3, draw.next(75.0 / 151));
        assertSame(b3, draw.next(0.999));
        // Once showB is out, showC (tier 1.0) beats showA (tier 1.5).
        draw.remove(b1);
        draw.remove(b2);
        draw.remove(b3);
        assertSame(c, draw.next(0.0));
        assertSame(c, draw.next(0.999));
        draw.remove(c);
        assertSame(a, draw.next(0.3));
        draw.remove(a);
        assertTrue(draw.isEmpty());
    }

    @Test
    public void aShowThatFillsPastItsSizeYieldsTheSlot() {
        Map<String, Maestro.Cell> cells = new HashMap<>();
        Maestro.LayerCandidate a = candidate(cells, "a", "showA", 100, 50, 10, 5);
        Maestro.LayerCandidate b = candidate(cells, "b", "showB", 100, 80, 10, 5);
        SlotDraw draw = new SlotDraw(List.of(a, b));
        assertSame(a, draw.next(0.5));
        // showA books 40 cores: tier 0.9 against showB's 0.8, so showB takes the next slot.
        a.showCell.used = 90;
        assertSame(b, draw.next(0.5));
        // showB books too: 1.2 against 0.9, back to showA.
        b.showCell.used = 120;
        assertSame(a, draw.next(0.5));
    }

    @Test
    public void candidatesWithoutFramesNeverEnterTheDraw() {
        Map<String, Maestro.Cell> cells = new HashMap<>();
        Maestro.LayerCandidate a = candidate(cells, "a", "showA", 100, 50, 10, 0);
        Maestro.LayerCandidate b = candidate(cells, "b", "showA", 100, 50, 10, 3);
        SlotDraw draw = new SlotDraw(List.of(a, b));
        assertSame(b, draw.next(0.0));
        assertSame(b, draw.next(0.999));
        draw.remove(b);
        assertTrue(draw.isEmpty());
    }
}
