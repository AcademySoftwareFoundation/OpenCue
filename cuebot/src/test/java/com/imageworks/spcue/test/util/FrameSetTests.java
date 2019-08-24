package com.imageworks.spcue.test.util;

import com.imageworks.spcue.util.FrameSet;
import org.junit.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;

public class FrameSetTests {
    @Test
    public void testMultipleSegments() {
        FrameSet result = new FrameSet("57,1-3,4-2,12-15x2,76-70x-3,5-12y3,1-7:5");

        assertThat(result.getAll()).containsExactly(
            57, 1, 2, 3, 4, 3, 2, 12, 14, 76, 73, 70, 6, 7, 9, 10, 12, 1, 6, 2, 4, 3, 5, 7);
    }

    @Test
    public void testSize() {
        FrameSet result = new FrameSet("1-7");

        assertEquals(7, result.size());
    }

    @Test
    public void testGet() {
        FrameSet result = new FrameSet("1-7");

        assertEquals(5, result.get(4));
    }

    @Test
    public void testIndex() {
        FrameSet result = new FrameSet("1-7");
        
        assertEquals(5, result.index(6));
        assertEquals(-1, result.index(22));
    }

    @Test
    public void testFramesToFrameRanges00() {
        FrameSet result = new FrameSet("1-10x2,11-100x20,103-108");

        // int[] intArray = {1, 3, 5, 7, 9, 11, 31, 51, 71, 91, 103, 104, 105, 106, 107, 108};

        assertEquals("11-91x20", result.getChunk(5, 5));
    }

    @Test
    public void testFramesToFrameRanges01() {
        FrameSet result = new FrameSet("1-10x2,11-100x20,103-108");

        // int[] intArray = {1, 3, 5, 7, 9, 11, 31, 51, 71, 91, 103, 104, 105, 106, 107, 108};

        assertEquals("5-11x2,31", result.getChunk(2, 5));
    }

    @Test
    public void testFramesToFrameRanges02() {
        FrameSet result = new FrameSet("1-10x2,11-100x20,103-108");

        // int[] intArray = {1, 3, 5, 7, 9, 11, 31, 51, 71, 91, 103, 104, 105, 106, 107, 108};

        assertEquals("91,103,104", result.getChunk(9, 3));
    }

    @Test
    public void testFramesToFrameRanges03() {
        FrameSet result = new FrameSet("1-100x3");

        assertEquals("28-34x3", result.getChunk(9, 3));
    }

    @Test
    public void testFramesToFrameRanges04() {
        FrameSet result = new FrameSet("1-100");

        assertEquals("10-12", result.getChunk(9, 3));
    }
}
