package com.imageworks.spcue.test.util;

import com.imageworks.spcue.util.FrameRange;
import org.junit.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

public class FrameRangeTests {
    @Test
    public void testSingleFrame() {
        Integer frame = 4927;

        FrameRange result = new FrameRange(frame.toString());

        assertThat(result.getAll()).containsExactly(frame);
    }

    @Test
    public void testNegativeSingleFrame() {
        Integer frame = -4982;

        FrameRange result = new FrameRange(frame.toString());

        assertThat(result.getAll()).containsExactly(frame);
    }

    @Test
    public void testFrameRange() {
        FrameRange result = new FrameRange("1-7");

        assertThat(result.getAll()).containsExactly(1, 2, 3, 4, 5, 6, 7);
    }

    @Test
    public void testNegativeFrameRange() {
        FrameRange result = new FrameRange("-20--13");

        assertThat(result.getAll()).containsExactly(-20, -19, -18, -17, -16, -15, -14, -13);
    }

    @Test
    public void testNegativeToPositiveFrameRange() {
        FrameRange result = new FrameRange("-5-3");

        assertThat(result.getAll()).containsExactly(-5, -4, -3, -2, -1, 0, 1, 2, 3);
    }

    @Test
    public void testReverseFrameRange() {
        FrameRange result = new FrameRange("6-2");

        assertThat(result.getAll()).containsExactly(6, 5, 4, 3, 2);
    }

    @Test
    public void testReverseNegativeFrameRange() {
        FrameRange result = new FrameRange("-2--6");

        assertThat(result.getAll()).containsExactly(-2, -3, -4, -5, -6);
    }

    @Test
    public void testStep() {
        FrameRange result = new FrameRange("1-8x2");

        assertThat(result.getAll()).containsExactly(1, 3, 5, 7);
    }

    @Test
    public void testNegativeStep() {
        FrameRange result = new FrameRange("8-1x-2");

        assertThat(result.getAll()).containsExactly(8, 6, 4, 2);
    }

    @Test
    public void testNegativeStepInvalidRange() {
        try {
            new FrameRange("1-8x-2");
            fail("negative frame step should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }
    }

    @Test
    public void testInvertedStep() {
        FrameRange result = new FrameRange("1-8y2");

        assertThat(result.getAll()).containsExactly(2, 4, 6, 8);
    }

    @Test
    public void testNegativeInvertedStep() {
        FrameRange result = new FrameRange("8-1y-2");

        assertThat(result.getAll()).containsExactly(7, 5, 3, 1);
    }

    @Test
    public void testInterleave() {
        FrameRange result = new FrameRange("1-10:5");

        assertThat(result.getAll()).containsExactly(1, 6, 3, 5, 7, 9, 2, 4, 8, 10);
    }

    @Test
    public void testNegativeInterleave() {
        FrameRange result = new FrameRange("10-1:-5");

        assertThat(result.getAll()).containsExactly(10, 5, 8, 6, 4, 2, 9, 7, 3, 1);
    }

    @Test
    public void testNonNumericalInput() {
        try {
            new FrameRange("a");
            fail("non-numerical frame should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameRange("a-b");
            fail("non-numerical frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameRange("1-5xc");
            fail("non-numerical step size should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameRange("1-5:c");
            fail("non-numerical interleave size should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }
    }

    @Test
    public void testInvalidRange() {
        try {
            new FrameRange("1-10-20");
            fail("invalid frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameRange("1x10-20");
            fail("invalid frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }

        try {
            new FrameRange("1:10-20");
            fail("invalid frame range should have been rejected");
        } catch (IllegalArgumentException e) {
            // pass
        }
    }

    @Test
    public void testSize() {
        FrameRange result = new FrameRange("1-7");

        assertEquals(7, result.size());
    }

    @Test
    public void testGet() {
        FrameRange result = new FrameRange("1-7");

        assertEquals(5, result.get(4));
    }

    @Test
    public void testIndex() {
        FrameRange result = new FrameRange("1-7");

        assertEquals(5, result.index(6));
        assertEquals(-1, result.index(22));
    }
}
