
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
}
