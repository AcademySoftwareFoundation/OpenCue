package com.imageworks.spcue.util;

import java.util.ArrayList;
import java.lang.StringBuilder;
import com.google.common.collect.ImmutableList;
import com.google.common.base.Strings;
import com.imageworks.spcue.SpcueRuntimeException;

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
     * Return a string representation of a subset of a frame range.
     *
     * This approach was adapted from https://pypi.org/project/Fileseq/
     * @param startFrame Start frame
     * @param endFrame   End frame
     * @param stride     The step between frames
     * @param zFill      Left pad each frame ID with zeroes to make it this width.
     * @return           String representation of the frame range, e.g. 1-1001x3
     */
    private String buildFrangePart(int startFrame, int endFrame, int stride, int zFill) {
        String padStart = pad(startFrame, zFill);
        String padStop  = pad(endFrame, zFill);
        if (startFrame == endFrame) {
            return padStart;
        } else if (stride == 1) {
            return String.format("%s-%s", padStart, padStop);
        } else {
            return String.format("%s-%sx%d", padStart, padStop, stride);
        }
    }

    /**
     * Left pad 'number' with zeroes to make it 'width' characters wide.
     * @param number An integer to pad
     * @param width  The required width of the resulting String.
     * @return       A left-padded string, e.g 0047
     */
    private String pad(int number, int width){
        return Strings.padStart(String.valueOf(number), width, '0');
    }

    /**
     * Return a String representation of a frame range based on a list of literal integer frame IDs.
     * @param frames  A list of integers representing frame IDs,
     * @return        A representation of a frameset, e.g. '1-10,12-100x2'
     */
    private String framesToFrameRanges(ImmutableList frames) {
        return framesToFrameRanges(frames, 0);
    }

    /**
     * Return a String representation of a frame range based on a list of literal integer frame IDs.
     * @param frames  A list of integers representing frame IDs,
     * @param zFill   The required width of each left-padded frame ID, e.g. 4 if ID '1' should become '0001'
     * @return        A representation of a frameset, e.g. '1-10,12-100x2'
     */
    private String framesToFrameRanges(ImmutableList<Integer> frames, int zFill) {

        int l = frames.size();
        if (l == 0) {
            return "";
        } else if (l == 1) {
            return pad(frames.get(0), zFill);
        }

        ArrayList<String> resultBuilder = new ArrayList<String>();

        int curr_count = 1;
        int curr_stride = 0;
        int new_stride = 0;
        int curr_start = frames.get(0);
        int curr_frame = frames.get(0);
        int last_frame = frames.get(0);

        for (int i = 1; i < frames.size(); i++) {
            curr_frame = frames.get(i);

            if (curr_stride == 0) {
                curr_stride = curr_frame - curr_start;
            }
            new_stride = curr_frame - last_frame;
            if (curr_stride == new_stride) {
                last_frame = curr_frame;
                curr_count += 1;
                continue;
            } else if (curr_count == 2 && curr_stride != 1) {
                resultBuilder.add(pad(curr_start, zFill));
                curr_stride = 0;
                curr_start = last_frame;
                last_frame = curr_frame;
                continue;
            } else {
                resultBuilder.add(buildFrangePart(curr_start, last_frame, curr_stride, zFill));
                curr_stride = 0;
                curr_start = curr_frame;
                last_frame = curr_frame;
                curr_count = 1;
                continue;
            }
        }
        if (curr_count == 2 && curr_stride != 1) {
            resultBuilder.add(pad(curr_start, zFill));
            resultBuilder.add(pad(curr_frame, zFill));
        } else {
            resultBuilder.add(buildFrangePart(curr_start, curr_frame, curr_stride, zFill));
        }

        StringBuilder sb = new StringBuilder();
        l = resultBuilder.size()-1;
        for (int j = 0; j < l; j++) {
            sb.append(resultBuilder.get(j)).append(",");
        }
        sb.append(resultBuilder.get(l));
        return sb.toString();
    }

    /**
     * Return a sub-FrameSet object starting at startFrame with max chunkSize members
     * @param idx
     * @return FrameSet
     */
    public String getChunk(int startFrameIndex, int chunkSize) {
        if (frameList.size() <= startFrameIndex || startFrameIndex < 0) {
            String sf = String.valueOf(startFrameIndex);
            String sz = String.valueOf(frameList.size() - 1);
            throw new SpcueRuntimeException("startFrameIndex " + sf + " is not in range 0-" + sz);
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

        ImmutableList<Integer> sl = frameList.subList(startFrameIndex, endFrameIndex);

        return framesToFrameRanges(sl);
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
