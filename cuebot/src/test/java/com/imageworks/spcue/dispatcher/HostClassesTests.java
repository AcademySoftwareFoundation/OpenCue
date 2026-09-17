
package com.imageworks.spcue.dispatcher;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import org.junit.Test;

/**
 * The class visit picks what the scan of the group picks. Random groups whose hosts share a few
 * states and hold unique ones now and then, with warm, seated and reserved hosts among them, and
 * random candidates with and without HOST limits: the best host, the soft cap's fallback and their
 * strand-free frames from pickHost over the classes' representatives and the candidate's special
 * hosts equal those from pickHost over every host, slot after slot, as the picked host takes a
 * frame and moves class.
 */
public class HostClassesTests {

    @Test
    public void theClassVisitPicksWhatTheScanPicks() {
        Random rnd = new Random(41);
        for (int group = 0; group < 300; group++) {
            List<Maestro.BookableHost> hosts = new ArrayList<>();
            for (int i = 0; i < 1 + rnd.nextInt(40); i++)
                hosts.add(Fix.randomHost(rnd, i));
            List<Maestro.LayerCandidate> candidates = new ArrayList<>();
            for (int i = 0; i < 1 + rnd.nextInt(8); i++)
                candidates.add(Fix.randomCandidate(rnd, i));
            Set<String> seated = new HashSet<>();
            for (int i = 0; i < rnd.nextInt(4); i++)
                seated.add("host" + rnd.nextInt(hosts.size() + 4));
            List<Maestro.LimitBudget> pools = Arrays.asList(new Maestro.LimitBudget("lic", "lic",
                    true, 0, seated.size() + rnd.nextInt(2), seated));
            Map<String, Set<String>> limitSeats = new HashMap<>();
            limitSeats.put("lic", new HashSet<>(seated));

            Maestro s = new Maestro();
            s.layerHostMaxFrac = rnd.nextBoolean() ? 0.25 : 0;
            s.bindWaiting(candidates);
            s.reachNeeds = Maestro.reachNeedsOf(candidates);
            s.bindWarmClaims(hosts, candidates);
            HostClasses classes = new HostClasses(hosts);
            for (int slot = 0; slot < 25; slot++) {
                Maestro.LayerCandidate c = candidates.get(rnd.nextInt(candidates.size()));
                List<Maestro.LimitBudget> cPools = c.limitIds == null ? null : pools;
                Maestro.Pick scan = s.pickHost(c, hosts, cPools, limitSeats);
                Maestro.Pick visit = s.pickHost(c, classes.candidates(c, cPools, limitSeats),
                        cPools, limitSeats);
                assertSame(scan.best, visit.best);
                assertSame(scan.fallback, visit.fallback);
                assertEquals(scan.bestStrandFree, visit.bestStrandFree);
                assertEquals(scan.fallbackStrandFree, visit.fallbackStrandFree);
                Maestro.BookableHost best = scan.best != null ? scan.best : scan.fallback;
                if (best == null)
                    continue;
                // One frame lands as placeOnce would book it: resources, plan, frames, class.
                for (Maestro.Dim d : Maestro.Dim.values())
                    d.take(best, d.need(c));
                best.planned.put(c.layerId, new int[] {0, 1});
                best.layerFrames.merge(c.layerId, 1, Integer::sum);
                classes.move(best);
            }
        }
    }

    /** The price of a host is the credit its strongest other waiting claimant would receive. */
    @Test
    public void thePriceIsTheClaimantsCredit() {
        Maestro s = new Maestro();
        Maestro.BookableHost h = Fix.host("0", 1600, Fix.GB * 64, 0, 0);
        h.ix = 0;
        h.layersRunning.add("l1");
        h.warmth = new HashMap<>();
        h.warmth.put("l2", 10L);
        h.odometer = 26;
        Maestro.LayerCandidate c1 = Fix.candidate("l1", 100, Fix.GB, 0, 0, 3);
        Maestro.LayerCandidate c2 = Fix.candidate("l2", 100, Fix.GB, 0, 0, 3);
        Maestro.LayerCandidate c3 = Fix.candidate("l3", 100, Fix.GB, 0, 0, 3);
        List<Maestro.LayerCandidate> candidates = Arrays.asList(c1, c2, c3);
        List<Maestro.BookableHost> hosts = Arrays.asList(h);
        s.bindWarmClaims(hosts, candidates);
        double live = s.warmCredit(h, c1);
        double cache = s.warmCredit(h, c2);
        assertEquals(8.0, live, 0);
        assertEquals(8.0 * (1 - 16.0 / 64), cache, 1e-9);
        assertEquals(live, Maestro.otherClaim(h, c3), 0);
        assertEquals(live, Maestro.otherClaim(h, c2), 0);
        assertEquals(cache, Maestro.otherClaim(h, c1), 0);
        // A layer with nothing waiting holds no claim.
        c1.waitingFrameCount = 0;
        s.bindWarmClaims(hosts, candidates);
        assertEquals(cache, Maestro.otherClaim(h, c3), 0);
        assertEquals(0.0, Maestro.otherClaim(h, c2), 0);
    }

    /**
     * A cold host of equal state beats a host warm for another waiting layer; alone, the warm host
     * is taken.
     */
    @Test
    public void theColdHostOfEqualStateWins() {
        Maestro s = new Maestro();
        Maestro.BookableHost warm = Fix.host("0", 1600, Fix.GB * 64, 0, 0);
        warm.ix = 0;
        warm.layersRunning.add("l2");
        Maestro.BookableHost cold = Fix.host("1", 1600, Fix.GB * 64, 0, 0);
        cold.ix = 1;
        Maestro.LayerCandidate c1 = Fix.candidate("l1", 100, Fix.GB, 0, 0, 3);
        Maestro.LayerCandidate c2 = Fix.candidate("l2", 100, Fix.GB, 0, 0, 3);
        List<Maestro.LayerCandidate> candidates = Arrays.asList(c1, c2);
        Map<String, Set<String>> seats = new HashMap<>();
        s.bindWaiting(candidates);
        s.bindWarmClaims(Arrays.asList(warm, cold), candidates);
        assertSame(cold, s.pickHost(c1, Arrays.asList(warm, cold), null, seats).best);
        assertSame(warm, s.pickHost(c1, Arrays.asList(warm), null, seats).best);
        assertSame(warm, s.pickHost(c2, Arrays.asList(warm, cold), null, seats).best);
    }
}
