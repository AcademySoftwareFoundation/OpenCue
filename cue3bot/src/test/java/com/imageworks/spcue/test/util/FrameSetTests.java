package com.imageworks.spcue.test.util;

import com.imageworks.spcue.util.FrameSet;
import org.junit.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

public class FrameSetTests {
    @Test
    public void testSingleFrame() {
        Integer frame = 4927;

        FrameSet result = new FrameSet(frame.toString());

        assertThat(result.getAll()).containsExactly(frame);
    }

    @Test
    public void testNegativeSingleFrame() {
        Integer frame = -4982;

        FrameSet result = new FrameSet(frame.toString());

        assertThat(result.getAll()).containsExactly(frame);
    }

    @Test
    public void testFrameRange() {
        FrameSet result = new FrameSet("1-7");

        assertThat(result.getAll()).containsExactly(1, 2, 3, 4, 5, 6, 7);
    }

    @Test
    public void testNegativeFrameRange() {
        FrameSet result = new FrameSet("-20--13");

        assertThat(result.getAll()).containsExactly(-20, -19, -18, -17, -16, -15, -14, -13);
    }

    @Test
    public void testNegativeToPositiveFrameRange() {
        FrameSet result = new FrameSet("-5-3");

        assertThat(result.getAll()).containsExactly(-5, -4, -3, -2, -1, 0, 1, 2, 3);
    }

    @Test
    public void testReverseFrameRange() {
        FrameSet result = new FrameSet("6-2");

        assertThat(result.getAll()).containsExactly(6, 5, 4, 3, 2);
    }

    @Test
    public void testReverseNegativeFrameRange() {
        FrameSet result = new FrameSet("-2--6");

        assertThat(result.getAll()).containsExactly(-2, -3, -4, -5, -6);
    }

    @Test
    public void testStep() {
        FrameSet result = new FrameSet("1-8x2");

        assertThat(result.getAll()).containsExactly(1, 3, 5, 7);
    }

    @Test
    public void testNegativeStep() {
        FrameSet result = new FrameSet("8-1x-2");

        assertThat(result.getAll()).containsExactly(8, 6, 4, 2);
    }

    @Test
    public void testNegativeStepInvalidRange() {
        try {
            new FrameSet("1-8x-2");
            fail("negative frame step should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }
    }

    @Test
    public void testInvertedStep() {
        FrameSet result = new FrameSet("1-8y2");

        assertThat(result.getAll()).containsExactly(2, 4, 6, 8);
    }

    @Test
    public void testNegativeInvertedStep() {
        FrameSet result = new FrameSet("8-1y-2");

        assertThat(result.getAll()).containsExactly(7, 5, 3, 1);
    }

    @Test
    public void testInterleave() {
        FrameSet result = new FrameSet("1-10:5");

        assertThat(result.getAll()).containsExactly(1, 6, 2, 4, 8, 10, 3, 5, 7, 9);
    }

    @Test
    public void testNegativeInterleave() {
        FrameSet result = new FrameSet("10-1:-5");

        assertThat(result.getAll()).containsExactly(10, 5, 9, 7, 3, 1, 8, 6, 4, 2);
    }

    @Test
    public void testMultipleSegments() {
        FrameSet result = new FrameSet("57,1-3,4-2,12-15x2,76-70x-3,5-12y3,1-7:5");

        assertThat(result.getAll()).containsExactly(
            57, 1, 2, 3, 4, 3, 2, 12, 14, 76, 73, 70, 6, 7, 9, 10, 12, 1, 6, 2, 4, 3, 5, 7);
    }

    @Test
    public void testNonNumericalInput() {
        try {
            new FrameSet("a");
            fail("non-numerical frame should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameSet("a-b");
            fail("non-numerical frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameSet("1-5xc");
            fail("non-numerical step size should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameSet("1-5:c");
            fail("non-numerical interleave size should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }
    }

    @Test
    public void testInvalidRange() {
        try {
            new FrameSet("1-10-20");
            fail("invalid frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameSet("1x10-20");
            fail("invalid frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameSet("1:10-20");
            fail("invalid frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }
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
