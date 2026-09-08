
package com.imageworks.spcue.dispatcher;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import org.junit.Test;

/**
 * Two invariants of the reservation index. A layer holds a reservation exactly when some host's
 * Reservation names it, through any sequence of reserves, releases and sweeps. The targets a layer
 * claims are the free fitting hosts with the fewest running procs, in group order among equals,
 * exactly the hosts a repeated argmin with exclusion picks.
 */
public class ReservationIndexTests {

    @Test
    public void theIndexAgreesWithAScanOfTheMap() {
        Random rnd = new Random(17);
        Maestro s = new Maestro();
        Map<String, String> layerOf = new HashMap<>(); // the shadow map: host -> layer
        String[] hosts = new String[40];
        for (int i = 0; i < hosts.length; i++)
            hosts[i] = "h" + i;
        String[] layers = {"a", "b", "c", "d", "e"};
        for (int step = 0; step < 2000; step++) {
            int op = rnd.nextInt(10);
            if (op < 6) {
                String h = hosts[rnd.nextInt(hosts.length)];
                String l = layers[rnd.nextInt(layers.length)];
                if (layerOf.containsKey(h))
                    continue; // a held host is never re-reserved, as in the reconcile
                s.reserve(h, new Maestro.Reservation(l, 100, 800));
                layerOf.put(h, l);
            } else if (op < 9) {
                String h = hosts[rnd.nextInt(hosts.length)];
                s.release(h);
                layerOf.remove(h);
            } else {
                Set<String> seen = new HashSet<>();
                for (String l : layers)
                    if (rnd.nextBoolean())
                        seen.add(l);
                s.sweepStaleReservationState(seen);
                layerOf.values().removeIf(l -> !seen.contains(l));
            }
            for (String l : layers) {
                List<String> expected = new ArrayList<>();
                for (Map.Entry<String, String> e : layerOf.entrySet())
                    if (e.getValue().equals(l))
                        expected.add(e.getKey());
                assertEquals(!expected.isEmpty(), s.layerHoldsReservation(l));
                assertEquals(new HashSet<>(expected), new HashSet<>(s.hostsReservedFor(l)));
            }
        }
    }

    /** The loop the one-sort claim replaced: the first free fitting host with the fewest procs. */
    private static Maestro.BookableHost argmin(Maestro.LayerCandidate c,
            List<Maestro.BookableHost> hosts, Set<String> taken) {
        Maestro.BookableHost best = null;
        int bestProcs = Integer.MAX_VALUE;
        for (Maestro.BookableHost h : hosts) {
            if (!Maestro.hostCanEverFit(c, h) || taken.contains(h.hostId))
                continue;
            if (h.runningProcs < bestProcs) {
                bestProcs = h.runningProcs;
                best = h;
            }
        }
        return best;
    }

    @Test
    public void targetsMatchTheRepeatedArgmin() {
        Random rnd = new Random(23);
        for (int trial = 0; trial < 300; trial++) {
            Maestro s = new Maestro();
            List<Maestro.BookableHost> hosts = new ArrayList<>();
            for (int i = 0; i < 30; i++)
                hosts.add(Fix.host("h" + i, 800 * (1 + rnd.nextInt(4)), rnd.nextInt(5)));
            Set<String> taken = new HashSet<>();
            for (Maestro.BookableHost h : hosts) {
                if (rnd.nextInt(4) == 0) {
                    s.reserve(h.hostId, new Maestro.Reservation("other", 100, 800));
                    taken.add(h.hostId);
                }
            }
            Maestro.LayerCandidate c =
                    Fix.candidate("wide", 800 * (1 + rnd.nextInt(4)), Fix.GB, 0, 0, 0);
            int want = rnd.nextInt(8);
            List<Maestro.BookableHost> got = s.reservationTargets(c, hosts, want);
            List<Maestro.BookableHost> expected = new ArrayList<>();
            Set<String> excluded = new HashSet<>(taken);
            for (int i = 0; i < want; i++) {
                Maestro.BookableHost t = argmin(c, hosts, excluded);
                if (t == null)
                    break;
                expected.add(t);
                excluded.add(t.hostId);
            }
            assertEquals(expected, got);
        }
        Maestro s = new Maestro();
        assertNull(argmin(Fix.candidate("x", 800, Fix.GB, 0, 0, 0), new ArrayList<>(),
                new HashSet<>()));
        assertEquals(0,
                s.reservationTargets(Fix.candidate("x", 800, Fix.GB, 0, 0, 0), new ArrayList<>(), 3)
                        .size());
    }
}
