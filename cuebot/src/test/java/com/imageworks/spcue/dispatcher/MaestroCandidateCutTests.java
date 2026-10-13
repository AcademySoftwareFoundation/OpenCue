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
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.regex.Pattern;

import org.junit.Test;

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
}
