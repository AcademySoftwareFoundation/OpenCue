package com.imageworks.spcue.util;

import java.lang.IllegalArgumentException;
import java.util.ArrayList;
import java.util.StringJoiner;
import com.google.common.collect.ImmutableList;
import com.google.common.base.Strings;

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

    /**
     * Return a sub-FrameSet object starting at startFrame with max chunkSize members
     * @param startFrameIndex Index of frame to start at; not the frame itself
     * @param chunkSize       Max number of frames per chunk
     * @return                String representation of the chunk, e.g. 1-1001x3
     */
    public String getChunk(int startFrameIndex, int chunkSize) {
        if (frameList.size() <= startFrameIndex || startFrameIndex < 0) {
            String sf = String.valueOf(startFrameIndex);
            String sz = String.valueOf(frameList.size() - 1);
            throw new IllegalArgumentException("startFrameIndex " + sf + " is not in range 0-" + sz);
        }
        if (chunkSize == 1) {
            // Chunksize of 1 so the FrameSet is just the startFrame
            return String.valueOf(frameList.get(startFrameIndex));
        }
        int finalFrameIndex = frameList.size() - 1;
        int endFrameIndex = startFrameIndex + chunkSize;
        if (endFrameIndex > finalFrameIndex) {
            // We don't have enough frames, so return the remaining frames.
            endFrameIndex = finalFrameIndex;
        }

        return framesToFrameRanges(frameList.subList(startFrameIndex, endFrameIndex));
    }

    /**
     * Return a string representation of a subset of a frame range.
     *
     * This approach was adapted from https://pypi.org/project/Fileseq/
     * @param startFrame Start frame
     * @param endFrame   End frame
     * @param step       The step between frames
     * @return           String representation of the frame range, e.g. 1-1001x3
     */
    private String buildFrangePart(int startFrame, int endFrame, int step) {
        if (startFrame == endFrame) {
            return String.valueOf(startFrame);
        } else if (step == 1) {
            return String.format("%d-%d", startFrame, endFrame);
        } else {
            return String.format("%d-%dx%d", startFrame, endFrame, step);
        }
    }

    /**
     * Return a String representation of a frame range based on a list of literal integer frame IDs.
     * @param frames  List of integers representing frame IDs,
     * @return        String representation of a frameset, e.g. '1-10,12-100x2'
     */
    private String framesToFrameRanges(ImmutableList<Integer> frames) {
        int l = frames.size();
        if (l == 0) {
            return "";
        } else if (l == 1) {
            return String.valueOf(frames.get(0));
        }

        StringJoiner resultBuilder = new StringJoiner(",");

        int curr_count = 1;
        int curr_step = 0;
        int new_step = 0;
        int curr_start = frames.get(0);
        int curr_frame = frames.get(0);
        int last_frame = frames.get(0);

        for (int i = 1; i < frames.size(); i++) {
            curr_frame = frames.get(i);

            if (curr_step == 0) {
                curr_step = curr_frame - curr_start;
            }
            new_step = curr_frame - last_frame;
            if (curr_step == new_step) {
                last_frame = curr_frame;
                curr_count += 1;
            } else if (curr_count == 2 && curr_step != 1) {
                resultBuilder.add(String.valueOf(curr_start));
                curr_step = 0;
                curr_start = last_frame;
                last_frame = curr_frame;
            } else {
                resultBuilder.add(buildFrangePart(curr_start, last_frame, curr_step));
                curr_step = 0;
                curr_start = curr_frame;
                last_frame = curr_frame;
                curr_count = 1;
            }
        }
        if (curr_count == 2 && curr_step != 1) {
            resultBuilder.add(String.valueOf(curr_start));
            resultBuilder.add(String.valueOf(curr_frame));
        } else {
            resultBuilder.add(buildFrangePart(curr_start, curr_frame, curr_step));
        }

        return resultBuilder.toString();
    }
}
