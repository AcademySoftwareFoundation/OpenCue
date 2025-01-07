package com.imageworks.spcue.util;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import com.google.common.base.Predicates;
import com.google.common.collect.Collections2;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;

import static java.lang.Math.abs;

/**
 * Represents a sequence of image frames.
 */
public class FrameRange {

    private static final Pattern SINGLE_FRAME_PATTERN = Pattern.compile("(-?)\\d+");
    private static final Pattern SIMPLE_FRAME_RANGE_PATTERN =
            Pattern.compile("(?<sf>(-?)\\d+)-(?<ef>(-?)\\d+)");
    private static final Pattern STEP_PATTERN =
            Pattern.compile("(?<sf>(-?)\\d+)-(?<ef>(-?)\\d+)(?<stepSep>[xy])(?<step>(-?)\\d+)");
    private static final Pattern INTERLEAVE_PATTERN =
            Pattern.compile("(?<sf>(-?)\\d+)-(?<ef>(-?)\\d+):(?<step>(-?)\\d+)");

    private ImmutableList<Integer> frameList;

    /**
     * Construct a FrameRange object by parsing a spec.
     *
     * FrameSet("1-10x3"); FrameSet("1-10y3"); // inverted step FrameSet("10-1x-1"); FrameSet("1");
     * // same as "1-1x1" FrameSet("1-10:5"); // interleave of 5
     *
     * A valid spec consists of:
     *
     * An inTime. An optional hyphen and outTime. An optional x or y and stepSize. Or an optional :
     * and interleaveSize. If outTime is less than inTime, stepSize must be negative.
     *
     * A stepSize of 0 produces an empty FrameRange.
     *
     * A stepSize cannot be combined with a interleaveSize.
     *
     * A stepSize designated with y creates an inverted step. Frames that would be included with an
     * x step are excluded.
     *
     * Example: 1-10y3 == 2, 3, 5, 6, 8, 9.
     *
     * An interleaveSize alters the order of frames when iterating over the FrameRange. The iterator
     * will first produce the list of frames from inTime to outTime with a stepSize equal to
     * interleaveSize. The interleaveSize is then divided in half, producing another set of frames
     * unique from the first set. This process is repeated until interleaveSize reaches 1.
     *
     * Example: 1-10:5 == 1, 6, 3, 5 ,7 ,9, 2, 4, 8, 10.
     */
    public FrameRange(String frameRange) {
        frameList = parseFrameRange(frameRange);
    }

    /**
     * Gets the number of frames contained in this sequence.
     * 
     * @return
     */
    public int size() {
        return frameList.size();
    }

    /**
     * Gets an individual entry in the sequence, by numerical position.
     * 
     * @param idx
     * @return
     */
    public int get(int idx) {
        return frameList.get(idx);
    }

    /**
     * Query index of frame number in frame set.
     * 
     * @param idx
     * @return Index of frame. -1 if frame set does not contain frame.
     */
    public int index(int idx) {
        return frameList.indexOf(idx);
    }

    /**
     * Gets the full numerical sequence.
     * 
     * @return
     */
    public ImmutableList<Integer> getAll() {
        return frameList;
    }

    protected static ImmutableList<Integer> parseFrameRange(String frameRange) {
        Matcher singleFrameMatcher = SINGLE_FRAME_PATTERN.matcher(frameRange);
        if (singleFrameMatcher.matches()) {
            return ImmutableList.of(Integer.valueOf(frameRange));
        }

        Matcher simpleRangeMatcher = SIMPLE_FRAME_RANGE_PATTERN.matcher(frameRange);
        if (simpleRangeMatcher.matches()) {
            Integer startFrame = Integer.valueOf(simpleRangeMatcher.group("sf"));
            Integer endFrame = Integer.valueOf(simpleRangeMatcher.group("ef"));
            return getIntRange(startFrame, endFrame, (endFrame >= startFrame ? 1 : -1));
        }

        Matcher rangeWithStepMatcher = STEP_PATTERN.matcher(frameRange);
        if (rangeWithStepMatcher.matches()) {
            Integer startFrame = Integer.valueOf(rangeWithStepMatcher.group("sf"));
            Integer endFrame = Integer.valueOf(rangeWithStepMatcher.group("ef"));
            Integer step = Integer.valueOf(rangeWithStepMatcher.group("step"));
            String stepSep = rangeWithStepMatcher.group("stepSep");
            return getSteppedRange(startFrame, endFrame, step, "y".equals(stepSep));
        }

        Matcher rangeWithInterleaveMatcher = INTERLEAVE_PATTERN.matcher(frameRange);
        if (rangeWithInterleaveMatcher.matches()) {
            Integer startFrame = Integer.valueOf(rangeWithInterleaveMatcher.group("sf"));
            Integer endFrame = Integer.valueOf(rangeWithInterleaveMatcher.group("ef"));
            Integer step = Integer.valueOf(rangeWithInterleaveMatcher.group("step"));
            return getInterleavedRange(startFrame, endFrame, step);
        }

        throw new IllegalArgumentException("unrecognized frame range syntax " + frameRange);
    }

    private static ImmutableList<Integer> getIntRange(Integer start, Integer end, Integer step) {
        int streamStart = (step < 0 ? end : start);
        int streamEnd = (step < 0 ? start : end);
        int streamStep = abs(step);

        List<Integer> intList = IntStream.rangeClosed(streamStart, streamEnd)
                .filter(n -> (n - start) % streamStep == 0).boxed().collect(Collectors.toList());

        if (step < 0) {
            return ImmutableList.copyOf(Lists.reverse(intList));
        }
        return ImmutableList.copyOf(intList);
    }

    private static ImmutableList<Integer> getSteppedRange(Integer start, Integer end, Integer step,
            Boolean inverseStep) {
        validateStepSign(start, end, step);
        ImmutableList<Integer> steppedRange = getIntRange(start, end, step);
        if (inverseStep) {
            ImmutableList<Integer> fullRange = getIntRange(start, end, (step < 0 ? -1 : 1));
            return ImmutableList.copyOf(
                    Collections2.filter(fullRange, Predicates.not(Predicates.in(steppedRange))));
        }
        return steppedRange;
    }

    private static ImmutableList<Integer> getInterleavedRange(Integer start, Integer end,
            Integer step) {
        validateStepSign(start, end, step);
        Set<Integer> interleavedFrames = new LinkedHashSet<>();

        while (abs(step) > 0) {
            interleavedFrames.addAll(getIntRange(start, end, step));
            step /= 2;
        }
        return ImmutableList.copyOf(interleavedFrames);
    }

    private static void validateStepSign(Integer start, Integer end, Integer step) {
        if (step > 1) {
            if (end < start) {
                throw new IllegalArgumentException(
                        "end frame may not be less than start frame when using a positive step");
            }
        } else if (step == 0) {
            throw new IllegalArgumentException("step cannot be zero");

        } else if (step < 0) {
            if (end >= start) {
                throw new IllegalArgumentException(
                        "end frame may not be greater than start frame when using a negative step");
            }
        }
    }
}
