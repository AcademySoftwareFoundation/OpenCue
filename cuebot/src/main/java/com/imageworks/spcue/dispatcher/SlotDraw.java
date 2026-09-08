
package com.imageworks.spcue.dispatcher;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The draw of a group's placement slots: a priority-weighted lottery among the candidates of the
 * lowest-tier show on the allocation, with removal of the candidates that leave the draw. The
 * candidates live in one bucket per show, since the tier is a property of the show on this
 * allocation and is read once per show per slot, and each bucket keeps its weights in a Fenwick
 * tree, so the pick inside a bucket and the removal of a member are both O(log n). A slot costs
 * O(shows + log C). A draw maps one integer in [0, sum of the tied weights) to a candidate through
 * bucket order, then member order.
 */
final class SlotDraw {

    private final List<Bucket> buckets = new ArrayList<>();
    private int live;

    /**
     * One draw over the candidates with waiting frames; the tiers read the show cells.
     *
     * Bound: O(C).
     */
    SlotDraw(List<Maestro.LayerCandidate> candidates) {
        Map<String, Bucket> byShow = new HashMap<>();
        for (Maestro.LayerCandidate c : candidates) {
            if (c.waitingFrameCount <= 0)
                continue;
            Bucket b = byShow.get(c.showKey);
            if (b == null) {
                b = new Bucket(buckets.size());
                byShow.put(c.showKey, b);
                buckets.add(b);
            }
            b.members.add(c);
        }
        for (Bucket b : buckets) {
            b.seal();
            live += b.live;
        }
    }

    /** Whether any candidate is still in the draw. */
    boolean isEmpty() {
        return live == 0;
    }

    /**
     * The candidate that takes the next slot for the draw u in [0, 1).
     *
     * Bound: O(shows + log C).
     */
    Maestro.LayerCandidate next(double u) {
        double low = Double.POSITIVE_INFINITY;
        for (Bucket b : buckets) {
            if (b.live == 0)
                continue;
            b.tier = Maestro.showTier(b.members.get(0));
            low = Math.min(low, b.tier);
        }
        long weightSum = 0;
        for (Bucket b : buckets) {
            if (b.live > 0 && b.tier <= low)
                weightSum += b.weight;
        }
        long r = (long) (u * weightSum);
        Bucket last = null;
        for (Bucket b : buckets) {
            if (b.live == 0 || b.tier > low)
                continue;
            last = b;
            if (r < b.weight)
                return b.select(r);
            r -= b.weight;
        }
        return last.select(last.weight - 1);
    }

    /**
     * Take a candidate out of the draw; the slot loop calls this once per leaving candidate.
     *
     * Bound: O(log n) in the candidate's bucket.
     */
    void remove(Maestro.LayerCandidate c) {
        buckets.get(c.drawShow).remove(c.drawIx, Maestro.lotteryWeight(c));
        live--;
    }

    /** The candidates of one show on the allocation, weights in a Fenwick tree (1-based). */
    private static final class Bucket {
        final int ix;
        final List<Maestro.LayerCandidate> members = new ArrayList<>();
        long[] tree;
        long weight;
        int live;
        double tier;

        Bucket(int ix) {
            this.ix = ix;
        }

        /** Build the tree over the members in O(n) and stamp each member with its place. */
        void seal() {
            int n = members.size();
            tree = new long[n + 1];
            for (int i = 0; i < n; i++) {
                Maestro.LayerCandidate c = members.get(i);
                c.drawShow = ix;
                c.drawIx = i;
                long w = Maestro.lotteryWeight(c);
                tree[i + 1] = w;
                weight += w;
            }
            for (int i = 1; i <= n; i++) {
                int j = i + (i & -i);
                if (j <= n)
                    tree[j] += tree[i];
            }
            live = n;
        }

        /** The member whose weight covers unit r, the smallest index with prefix sum above r. */
        Maestro.LayerCandidate select(long r) {
            int n = members.size();
            int pos = 0;
            for (int step = Integer.highestOneBit(n); step > 0; step >>= 1) {
                int next = pos + step;
                if (next <= n && tree[next] <= r) {
                    pos = next;
                    r -= tree[next];
                }
            }
            return members.get(pos);
        }

        void remove(int memberIx, long w) {
            int n = members.size();
            for (int i = memberIx + 1; i <= n; i += i & -i)
                tree[i] -= w;
            weight -= w;
            live--;
        }
    }
}
