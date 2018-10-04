package com.imageworks.spcue.util;

import com.google.common.collect.ImmutableList;

/**
 * Represents an ordered sequence of FrameRanges.
 */
public class FrameSet {
    private ImmutableList<Integer> frameList;

    /**
     * Construct a FrameSet object by parsing a spec.
     *
     * See FrameRange for the supported syntax. A FrameSet follows the same syntax,
     * with the addition that it may be a comma-separated list of different FrameRanges.
     */
    public FrameSet(String frameRange) {
        frameList = parseFrameRange(frameRange);
    }

    /**
     * Gets the number of frames contained in this sequence.
     * @return
     */
    public int size() {
        return frameList.size();
    }

    /**
     * Gets an individual entry in the sequence, by numerical position.
     * @param idx
     * @return
     */
    public int get(int idx) {
        return frameList.get(idx);
    }

    /**
     * Query index of frame number in frame set.
     * @param idx
     * @return Index of frame. -1 if frame set does not contain frame.
     */
    public int index(int idx) {
        return frameList.indexOf(idx);
    }

    /**
     * Gets the full numerical sequence.
     * @return
     */
    public ImmutableList<Integer> getAll() {
        return frameList;
    }

    private ImmutableList<Integer> parseFrameRange(String frameRange) {
        ImmutableList.Builder<Integer> builder = ImmutableList.builder();
        for (String frameRangeSection : frameRange.split(",")) {
            builder.addAll(FrameRange.parseFrameRange(frameRangeSection));
        }
        return builder.build();
    }
}
