package com.imageworks.spcue.test.util;

import com.imageworks.spcue.util.FrameSet;
import org.junit.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;

public class FrameSetTests {
    @Test
    public void shouldSplitListAndMaintainOrder() {
        FrameSet result = new FrameSet("57,1-3,4-2,12-15x2,76-70x-3,5-12y3,1-7:5");

        assertThat(result.getAll()).containsExactly(57, 1, 2, 3, 4, 3, 2, 12, 14, 76, 73, 70, 6, 7,
                9, 10, 12, 1, 6, 3, 5, 7, 2, 4);
    }

    @Test
    public void shouldReturnCorrectSize() {
        FrameSet result = new FrameSet("1-7");

        assertEquals(7, result.size());
    }

    @Test
    public void shouldReturnSingleFrame() {
        FrameSet result = new FrameSet("1-7");

        assertEquals(5, result.get(4));
    }

    @Test
    public void shouldReturnCorrectIndexes() {
        FrameSet result = new FrameSet("1-7");

        assertEquals(5, result.index(6));
        assertEquals(-1, result.index(22));
    }

    @Test
    public void shouldReconstructSteppedRange() {
        FrameSet result = new FrameSet("1-10x2,11-100x20,103-108");

        // int[] intArray = {1, 3, 5, 7, 9, 11, 31, 51, 71, 91, 103, 104, 105, 106, 107,
        // 108};

        assertEquals("11-91x20", result.getChunk(5, 5));
    }

    @Test
    public void shouldCreateNewSteppedRangeAndNextFrame() {
        FrameSet result = new FrameSet("1-10x2,11-100x20,103-108");

        // int[] intArray = {1, 3, 5, 7, 9, 11, 31, 51, 71, 91, 103, 104, 105, 106, 107,
        // 108};

        assertEquals("5-11x2,31", result.getChunk(2, 5));
    }

    @Test
    public void shouldReturnCommaSeparatedList() {
        FrameSet result = new FrameSet("1-10x2,11-100x20,103-108");

        // int[] intArray = {1, 3, 5, 7, 9, 11, 31, 51, 71, 91, 103, 104, 105, 106, 107,
        // 108};

        assertEquals("91,103,104", result.getChunk(9, 3));
    }

    @Test
    public void shouldReturnSubsetOfSteppedRange() {
        FrameSet result = new FrameSet("1-100x3");

        assertEquals("28-34x3", result.getChunk(9, 3));
    }

    @Test
    public void shouldReturnSubsetOfRange() {
        FrameSet result = new FrameSet("1-100");

        assertEquals("10-12", result.getChunk(9, 3));
    }

    @Test
    public void shouldStopBeforeTheEndOfTheRange() {
        FrameSet result = new FrameSet("55-60");

        assertEquals("55-60", result.getChunk(0, 10));
    }

    @Test
    public void shouldReturnLastFrame() {
        FrameSet result1 = new FrameSet("1-10x2");

        FrameSet chunk1 = new FrameSet(result1.getChunk(0, 3));
        FrameSet chunk2 = new FrameSet(result1.getChunk(3, 3));

        assertEquals(5, chunk1.get(chunk1.size() - 1));
        assertEquals(9, chunk2.get(chunk2.size() - 1));

        FrameSet result2 = new FrameSet("1");
        FrameSet chunk3 = new FrameSet(result2.getChunk(0, 3));

        assertEquals(1, chunk3.get(chunk3.size() - 1));
    }
}
