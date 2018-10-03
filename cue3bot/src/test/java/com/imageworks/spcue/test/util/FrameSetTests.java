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
}
