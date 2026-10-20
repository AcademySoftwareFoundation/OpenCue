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

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.regex.Pattern;

import org.junit.Test;

import com.imageworks.spcue.grpc.host.ThreadMode;

/**
 * The in-memory group cut of the tick's candidate read: the per-group SQL's predicates and lottery,
 * in Java. The database parity of the whole cut is MaestroCandidateParityTests; these pin the pure
 * pieces.
 */
public class MaestroCandidateCutTests {

    private static final Maestro.TagMatcher PLAIN = (group, layer) -> {
        Pattern p = Maestro.compileTagPattern(layer);
        return p != null && p.matcher(group).find();
    };

    private static Maestro.HostSpecKey spec(String alloc, String facility, String tags, String os,
            boolean allThreadMode) {
        return new Maestro.HostSpecKey(alloc, facility, tags, os, false, allThreadMode);
    }

    private static Maestro.CandidateRow row(String layer, String show, String facility,
            String jobOs, String tags, int cores, boolean threadable, int priority) {
        Maestro.LayerCandidate c = new Maestro.LayerCandidate();
        c.layerId = layer;
        c.jobId = "job-" + layer;
        c.showId = show;
        c.layerCoresMin = cores;
        c.threadable = threadable;
        c.priority = priority;
        c.waitingFrameCount = 5;
        return new Maestro.CandidateRow(c, facility, jobOs, tags);
    }

    private static Maestro.TickCandidates tick(List<Maestro.CandidateRow> rows, Object... subs) {
        Map<String, long[]> s = new HashMap<>();
        for (int i = 0; i < subs.length; i += 5)
            s.put(Maestro.subKey((String) subs[i], (String) subs[i + 1]),
                    new long[] {((Number) subs[i + 2]).longValue(),
                            ((Number) subs[i + 3]).longValue(),
                            ((Number) subs[i + 4]).longValue()});
        return new Maestro.TickCandidates(rows, s);
    }

    private static Set<String> ids(List<Maestro.LayerCandidate> cs) {
        Set<String> out = new HashSet<>();
        for (Maestro.LayerCandidate c : cs)
            out.add(c.layerId);
        return out;
    }

    // ---- the tag regex, as Postgres ran it ---------------------------------

    @Test
    public void tagPatternMatchesAnAlternationAgainstTheGroupTags() {
        assertTrue(PLAIN.matches("desktop general linux", "general|desktop"));
        assertTrue(PLAIN.matches("desktop general linux", "linux"));
        assertFalse(PLAIN.matches("desktop general linux", "gpu"));
    }

    @Test
    public void tagPatternEndsOnAWordBoundaryLikePostgresBackslashY() {
        // (?x)gen\y: "gen" must end a word; "general" does not qualify.
        assertFalse(PLAIN.matches("general linux", "gen"));
        assertTrue(PLAIN.matches("gen linux", "gen"));
        // No boundary at the start, exactly like the SQL's clause.
        assertTrue(PLAIN.matches("mygen linux", "gen"));
    }

    @Test
    public void tagPatternIgnoresCaseAndWhitespaceLikeExpandedMode() {
        assertTrue(PLAIN.matches("desktop general", "General | Desktop"));
        assertTrue(PLAIN.matches("DESKTOP", "desktop"));
    }

    @Test
    public void tagPatternTranslatesPostgresWordEscapes() {
        assertTrue(PLAIN.matches("general linux", "\\mlinux\\M"));
        assertTrue(PLAIN.matches("general linux", "linux\\y"));
        assertFalse(PLAIN.matches("general linuxx", "linux\\y"));
    }

    @Test
    public void aPatternJavaCannotCompileExcludesItsLayerInsteadOfFailingTheGroup() {
        assertNull(Maestro.compileTagPattern("general|("));
        assertFalse(PLAIN.matches("general", "general|("));
    }

    @Test
    public void jobOsMatchesAnyAdvertisedOs() {
        assertTrue(Maestro.jobOsAllowed(null, "rhel7"));
        assertTrue(Maestro.jobOsAllowed("", "rhel7"));
        assertTrue(Maestro.jobOsAllowed("rhel9", "rhel7,rhel9"));
        assertFalse(Maestro.jobOsAllowed("rhel8", "rhel7,rhel9"));
        assertFalse(Maestro.jobOsAllowed("rhel7", null));
    }

    // ---- the group cut --------------------------------------------------------

    @Test
    public void theCutAppliesEveryGroupPredicate() {
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("fits", "show", "fac", "", "general", 100, true, 50));
        rows.add(row("otherFacility", "show", "fac2", "", "general", 100, true, 50));
        rows.add(row("otherOs", "show", "fac", "rhel8", "general", 100, true, 50));
        rows.add(row("osListed", "show", "fac", "rhel9", "general", 100, true, 50));
        rows.add(row("notThreadable", "show", "fac", "", "general", 100, false, 50));
        rows.add(row("tooWide", "show", "fac", "", "general", 1600, true, 50));
        rows.add(row("noTag", "show", "fac", "", "gpu", 100, true, 50));
        rows.add(row("noSub", "unsubscribed", "fac", "", "general", 100, true, 50));
        rows.add(row("atBurst", "full", "fac", "", "general", 100, true, 50));
        Maestro.TickCandidates t =
                tick(rows, "show", "alloc", 100, 1000, 500, "full", "alloc", 1000, 1000, 500);

        List<Maestro.LayerCandidate> cut =
                Maestro.groupCandidates(spec("alloc", "fac", "general linux", "rhel7,rhel9", true),
                        800, t, 2000, PLAIN, new Random(1));

        Set<String> expect = new HashSet<>();
        expect.add("fits");
        expect.add("osListed");
        assertEquals(expect, ids(cut));
        for (Maestro.LayerCandidate c : cut) {
            assertEquals("the group's subscription figures ride on the candidate", 100,
                    c.showCoresInUse);
            assertEquals(1000, c.showBurstCores);
            assertEquals(500, c.showSizeCores);
        }
    }

    @Test
    public void aVariableThreadModeGroupTakesNonThreadableLayers() {
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("single", "show", "fac", "", "general", 100, false, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 0, 1000, 500);
        assertEquals(1, Maestro.groupCandidates(spec("alloc", "fac", "general", "", false), 800, t,
                2000, PLAIN, new Random(1)).size());
    }

    @Test
    public void eachGroupGetsItsOwnCandidateCopy() {
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("shared", "show", "fac", "", "general", 100, true, 50));
        Maestro.TickCandidates t =
                tick(rows, "show", "a", 10, 1000, 500, "show", "b", 20, 1000, 500);
        Maestro.LayerCandidate onA = Maestro.groupCandidates(spec("a", "fac", "general", "", true),
                800, t, 2000, PLAIN, new Random(1)).get(0);
        Maestro.LayerCandidate onB = Maestro.groupCandidates(spec("b", "fac", "general", "", true),
                800, t, 2000, PLAIN, new Random(1)).get(0);
        assertTrue("distinct objects, so one group's sizing never leaks into another",
                onA != onB && onA != rows.get(0).row);
        assertEquals(10, onA.showCoresInUse);
        assertEquals(20, onB.showCoresInUse);
        onA.layerCoresMin = 400;
        assertEquals("the template is untouched", 100, rows.get(0).row.layerCoresMin);
    }

    @Test
    public void theCapKeepsTheHighestDrawsAndFavoursPriority() {
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        for (int i = 0; i < 200; i++)
            rows.add(row("hi" + i, "show", "fac", "", "general", 100, true, 90));
        for (int i = 0; i < 200; i++)
            rows.add(row("lo" + i, "show", "fac", "", "general", 100, true, 10));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 0, 100000, 500);
        List<Maestro.LayerCandidate> cut = Maestro.groupCandidates(
                spec("alloc", "fac", "general", "", true), 800, t, 100, PLAIN, new Random(7));
        assertEquals("the cap binds", 100, cut.size());
        int hi = 0;
        for (Maestro.LayerCandidate c : cut)
            if (c.priority == 90)
                hi++;
        assertTrue("priority 90 wins most of the capped slots over priority 10, not all: " + hi,
                hi > 60 && hi < 100);
        assertEquals("one candidate per layer", 100, ids(cut).size());
    }

    // ---- the pins, resolved from the same read ------------------------------

    private static Maestro.BookableHost host(String name, String alloc, String facility,
            String tags, String os, int cores, boolean allThreadMode) {
        Maestro.BookableHost h = new Maestro.BookableHost();
        h.hostId = "id-" + name;
        h.hostName = name;
        h.pkAlloc = alloc;
        h.pkFacility = facility;
        h.tagsRaw = tags + " " + name;
        h.os = os;
        h.coresTotal = cores;
        h.coresIdle = cores;
        h.threadMode = allThreadMode ? ThreadMode.ALL_VALUE : ThreadMode.AUTO_VALUE;
        return h;
    }

    private static Maestro.BookableHost general(String name) {
        return host(name, "alloc", "fac", "general", "rhel9", 800, false);
    }

    private static Map<String, List<Maestro.BookableHost>> byName(Maestro.BookableHost... hosts) {
        Map<String, List<Maestro.BookableHost>> m = new HashMap<>();
        for (Maestro.BookableHost h : hosts)
            m.computeIfAbsent(h.hostName.toLowerCase(), x -> new ArrayList<>()).add(h);
        return m;
    }

    private static Set<String> specTags(String... tags) {
        return new HashSet<>(Arrays.asList(tags));
    }

    /** The one candidate of the group the host belongs to, or null when the group has none. */
    private static Maestro.LayerCandidate pinIn(
            Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins, Maestro.BookableHost h) {
        List<Maestro.LayerCandidate> group = pins.get(Maestro.hostSpecKey(h));
        if (group == null)
            return null;
        assertEquals(1, group.size());
        return group.get(0);
    }

    @Test
    public void aNameResolvesCaseBlindOncePerHostAndATrailingBarIsNotAHost() {
        Maestro.BookableHost a = general("hosta");
        Maestro.BookableHost b = general("hostb");
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("L1", "show", "fac", "", "HostA | hosta | hostb |", 100, true, 50));
        rows.add(row("spec", "show", "fac", "", "general", 100, true, 50));
        rows.add(row("blank", "show", "fac", "", "", 100, true, 50));
        rows.add(row("spaces", "show", "fac", "", "  ", 100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 100, 1000, 500);
        Map<String, String> reason = new HashMap<>();
        Map<String, Integer> frames = new HashMap<>();

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins = Maestro.resolvePins(t,
                byName(a, b), specTags("general"), 2000, new Random(1), reason, frames);

        assertEquals("one group", 1, pins.size());
        Maestro.LayerCandidate pin = pinIn(pins, a);
        assertEquals("L1", pin.layerId);
        assertEquals("a name repeated in the tags adds its host once", Arrays.asList(a, b),
                pin.pinnedHosts);
        assertEquals(new HashSet<>(Arrays.asList("id-hosta", "id-hostb")), pin.pinnedIds);
        assertTrue("the pin is a copy, not the tick's template", pin != rows.get(0).row);
        assertEquals("the host's subscription figures ride on the pin", 100, pin.showCoresInUse);
        assertEquals(1000, pin.showBurstCores);
        assertEquals(500, pin.showSizeCores);
        assertTrue("a layer whose tags are all spec tags, or empty, is no pin and not dead",
                reason.isEmpty() && frames.isEmpty());
    }

    /** host.str_name is unique raw, not lower-cased, so "foo" and "FOO" can both exist. */
    @Test
    public void hostsWhoseNamesDifferOnlyByCaseAllAnswerToTheName() {
        Maestro.BookableHost lower = general("hostx");
        Maestro.BookableHost upper = general("HOSTX");
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("L1", "show", "fac", "", "hostx", 100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 100, 1000, 500);

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins =
                Maestro.resolvePins(t, byName(lower, upper), specTags("general"), 2000,
                        new Random(1), new HashMap<>(), new HashMap<>());

        assertEquals("the SQL's lower(str_name) matched both", Arrays.asList(lower, upper),
                pinIn(pins, lower).pinnedHosts);
    }

    @Test
    public void aSpecTagBesideANameIsAPinThereAndNeverNoHost() {
        Maestro.BookableHost a = general("hosta");
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("alive", "show", "fac", "", "general | hosta", 100, true, 50));
        rows.add(row("stale", "show", "fac", "", "general | nosuchhost", 100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 100, 1000, 500);
        Map<String, String> reason = new HashMap<>();

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins = Maestro.resolvePins(t,
                byName(a), specTags("general"), 2000, new Random(1), reason, new HashMap<>());

        assertEquals("alive", pinIn(pins, a).layerId);
        assertTrue("a spec-tagged layer is a group candidate, not dead", reason.isEmpty());
    }

    @Test
    public void anUnknownNameWithNoSpecTagWaitsAsNoHost() {
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("dead", "show", "fac", "", "nosuchhost | neither", 100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 100, 1000, 500);
        Map<String, String> reason = new HashMap<>();
        Map<String, Integer> frames = new HashMap<>();

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins = Maestro.resolvePins(t,
                byName(general("hosta")), specTags("general"), 2000, new Random(1), reason, frames);

        assertTrue(pins.isEmpty());
        assertEquals("no host", reason.get("dead"));
        assertEquals(Integer.valueOf(5), frames.get("dead"));
    }

    @Test
    public void aFittingButSubscriptionBlockedHostYieldsNoPinAndNoWaitlistEntry() {
        Maestro.BookableHost atBurst =
                host("hostfull", "full", "fac", "general", "rhel9", 800, false);
        Maestro.BookableHost unsubscribed =
                host("hostnosub", "nosub", "fac", "general", "rhel9", 800, false);
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("blocked", "show", "fac", "", "hostfull | hostnosub", 100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "full", 1000, 1000, 500);
        Map<String, String> reason = new HashMap<>();

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins =
                Maestro.resolvePins(t, byName(atBurst, unsubscribed), specTags("general"), 2000,
                        new Random(1), reason, new HashMap<>());

        assertTrue("the SQL dropped the row: no pin", pins.isEmpty());
        assertTrue("and no null-host row either: not dead", reason.isEmpty());
    }

    @Test
    public void aHostThatDoesNotFitTheLayerIsNoPin() {
        Maestro.BookableHost otherFacility =
                host("hostfac", "alloc", "fac2", "general", "rhel9", 800, false);
        Maestro.BookableHost otherOs =
                host("hostos", "alloc", "fac", "general", "rhel8", 800, false);
        Maestro.BookableHost allMode =
                host("hostall", "alloc", "fac", "general", "rhel9", 800, true);
        Maestro.BookableHost small =
                host("hostsmall", "alloc", "fac", "general", "rhel9", 50, false);
        Maestro.BookableHost listed =
                host("hostlisted", "alloc", "fac", "general", "rhel7,rhel9", 800, false);
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("facility", "show", "fac", "", "hostfac", 100, true, 50));
        rows.add(row("os", "show", "fac", "rhel9", "hostos", 100, true, 50));
        rows.add(row("osListed", "show", "fac", "rhel9", "hostlisted", 100, true, 50));
        rows.add(row("thread", "show", "fac", "", "hostall", 100, false, 50));
        rows.add(row("threadable", "show", "fac", "", "hostall", 100, true, 50));
        rows.add(row("cores", "show", "fac", "", "hostsmall", 100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 100, 1000, 500);
        Map<String, String> reason = new HashMap<>();

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins =
                Maestro.resolvePins(t, byName(otherFacility, otherOs, allMode, small, listed),
                        specTags("general"), 2000, new Random(1), reason, new HashMap<>());

        assertEquals("osListed", pinIn(pins, listed).layerId);
        assertEquals("threadable", pinIn(pins, allMode).layerId);
        assertEquals(2, pins.size());
        assertEquals("every misfit names no fitting host and has no spec tag",
                new HashSet<>(Arrays.asList("facility", "os", "thread", "cores")), reason.keySet());
    }

    @Test
    public void aListSpanningTwoSpecsBecomesOneCandidatePerGroup() {
        Maestro.BookableHost a = general("hosta");
        Maestro.BookableHost b = general("hostb");
        Maestro.BookableHost c = host("hostc", "alloc", "fac", "general capb", "rhel9", 800, false);
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        rows.add(row("L1", "show", "fac", "", "hosta | hostb | hostc", 100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 100, 1000, 500);

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins =
                Maestro.resolvePins(t, byName(a, b, c), specTags("general", "capb"), 2000,
                        new Random(1), new HashMap<>(), new HashMap<>());

        assertEquals(2, pins.size());
        Maestro.LayerCandidate inA = pinIn(pins, a);
        Maestro.LayerCandidate inC = pinIn(pins, c);
        assertEquals(Arrays.asList(a, b), inA.pinnedHosts);
        assertEquals(Arrays.asList(c), inC.pinnedHosts);
        assertTrue("distinct copies per group", inA != inC);
    }

    @Test
    public void theCapAndLotteryApplyToPinsPerGroup() {
        Maestro.BookableHost a = general("hosta");
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        for (int i = 0; i < 200; i++)
            rows.add(row("hi" + i, "show", "fac", "", "hosta", 100, true, 90));
        for (int i = 0; i < 200; i++)
            rows.add(row("lo" + i, "show", "fac", "", "hosta", 100, true, 10));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 0, 100000, 500);

        List<Maestro.LayerCandidate> pins = Maestro.resolvePins(t, byName(a), specTags("general"),
                100, new Random(7), new HashMap<>(), new HashMap<>()).get(Maestro.hostSpecKey(a));

        assertEquals("the cap binds per group", 100, pins.size());
        int hi = 0;
        for (Maestro.LayerCandidate c : pins)
            if (c.priority == 90)
                hi++;
        assertTrue("priority 90 wins most of the capped slots over priority 10, not all: " + hi,
                hi > 60 && hi < 100);
        assertEquals("one candidate per layer", 100, ids(pins).size());
    }

    @Test
    public void aFailedCandidateReadResolvesNoPins() {
        Maestro.TickCandidates failed = new Maestro.TickCandidates(new RuntimeException("db"));
        Map<String, String> reason = new HashMap<>();
        assertTrue(Maestro.resolvePins(failed, byName(general("hosta")), specTags("general"), 2000,
                new Random(1), reason, new HashMap<>()).isEmpty());
        assertTrue(reason.isEmpty());
    }

    /**
     * A guard on the bound, not a benchmark: the resolution is one name lookup per tag token of
     * each participating row, whatever the host count. The SQL this replaced was layers x hosts.
     */
    @Test
    public void resolvingThousandsOfRowsCostsOneLookupPerTagTokenWhateverTheHostCount() {
        Maestro.BookableHost[] hosts = new Maestro.BookableHost[5000];
        for (int i = 0; i < hosts.length; i++)
            hosts[i] = general("host" + i);
        int[] lookups = new int[1];
        Map<String, List<Maestro.BookableHost>> names =
                new HashMap<String, List<Maestro.BookableHost>>(byName(hosts)) {
                    @Override
                    public List<Maestro.BookableHost> get(Object key) {
                        lookups[0]++;
                        return super.get(key);
                    }
                };
        List<Maestro.CandidateRow> rows = new ArrayList<>();
        for (int i = 0; i < 3000; i++)
            rows.add(
                    row("L" + i, "show", "fac", "",
                            i % 3 == 0 ? "general | rhel75"
                                    : "host" + (i % 5000) + " | host" + ((i * 7) % 5000),
                            100, true, 50));
        Maestro.TickCandidates t = tick(rows, "show", "alloc", 0, 100000, 500);

        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> pins = Maestro.resolvePins(t, names,
                specTags("general"), 2000, new Random(1), new HashMap<>(), new HashMap<>());

        assertEquals(2000, pins.get(Maestro.hostSpecKey(hosts[0])).size());
        assertEquals("two tokens per row, every row participates (rhel75 is no spec tag)", 3000 * 2,
                lookups[0]);
    }
}
