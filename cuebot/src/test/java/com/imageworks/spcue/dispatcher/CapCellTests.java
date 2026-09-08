
package com.imageworks.spcue.dispatcher;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.util.List;

import org.junit.Test;

/**
 * The cap cells' invariant: every cap counter is tick-wide, seeded once from the first row seen,
 * and every later read sees every earlier spend, in the same group or a later one.
 */
public class CapCellTests {

    private static Maestro.LayerCandidate candidate(String layer, String job, String show,
            int jobInUse, int jobMax, String folder, int folderMax, int folderRunning,
            List<String> limitIds) {
        Maestro.LayerCandidate c = new Maestro.LayerCandidate();
        c.layerId = layer;
        c.jobId = job;
        c.showId = show;
        c.showKey = show + "@alloc";
        c.layerCoresMin = 100;
        c.jobCoresInUse = jobInUse;
        c.jobMaxCores = jobMax;
        c.showCoresInUse = 0;
        c.showBurstCores = Integer.MAX_VALUE;
        c.showSizeCores = 100;
        c.folderId = folder;
        c.folderMax = folderMax;
        c.folderRunning = folderRunning;
        c.limitIds = limitIds;
        c.waitingFrameCount = 10;
        return c;
    }

    @Test
    public void candidatesOfOneKeyShareOneCellSeededFromTheFirstRow() {
        Maestro s = new Maestro();
        s.limitBudgets.put("nuke", frameBudget("nuke", 5));
        Maestro.LayerCandidate a =
                candidate("a", "job", "show", 300, 500, "f", 1000, 200, List.of("nuke"));
        Maestro.LayerCandidate b =
                candidate("b", "job", "show", 300, 500, "f", 1000, 200, List.of("nuke", "maya"));
        s.bindCells(a);
        s.bindCells(b);
        assertSame(a.jobCell, b.jobCell);
        assertSame(a.showCell, b.showCell);
        assertSame(a.folderCell, b.folderCell);
        assertSame(a.limitCells[0], b.limitCells[0]);
        assertEquals(300, a.jobCell.used);
        assertEquals(200, a.folderCell.used);
        assertEquals(0, b.limitCells[1].used);
        // A limit without a budget entry is bound but never gates.
        assertNull(b.limitBound[1]);
        // A spend on a is a spend on b: b's job cap closes when a takes the last 200 cores.
        assertTrue(Maestro.openToPlace(b));
        a.jobCell.used += 200;
        assertFalse(Maestro.openToPlace(b));
        // A candidate bound later, as in a later group of the same tick, sees the spend too.
        Maestro.LayerCandidate c = candidate("c", "job", "show", 300, 500, "f", -1, 0, null);
        s.bindCells(c);
        assertSame(a.jobCell, c.jobCell);
        assertEquals(500, c.jobCell.used);
        assertNull(c.folderCell);
        assertNull(c.limitCells);
    }

    @Test
    public void theLimitCellClosesTheCandidateAtItsBudget() {
        Maestro s = new Maestro();
        s.limitBudgets.put("lim", frameBudget("lim", 1));
        Maestro.LayerCandidate a =
                candidate("a", "jobA", "show", 0, 1000, "f", -1, 0, List.of("lim"));
        Maestro.LayerCandidate b =
                candidate("b", "jobB", "show", 0, 1000, "f", -1, 0, List.of("lim"));
        s.bindCells(a);
        s.bindCells(b);
        assertTrue(Maestro.openToPlace(b));
        a.limitCells[0].used += 1;
        assertFalse(Maestro.openToPlace(b));
    }

    /** A FRAME limit that still has {@code usable} frames to give this tick. */
    private static Maestro.LimitBudget frameBudget(String id, int usable) {
        return new Maestro.LimitBudget(id, id, false, usable, 0, java.util.Collections.emptySet());
    }
}
