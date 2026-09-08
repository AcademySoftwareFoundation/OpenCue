
package com.imageworks.spcue.dispatcher;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

/**
 * Two sorted views of a group once its slot loop is done and its state is frozen, so the epilogue
 * answers "does any host fit this candidate" and "does any waiting candidate fit this host" by a
 * binary search and one compare. A cores need selects a prefix of the hosts sorted by idle cores,
 * and the prefix maximum of idle memory says whether one of them clears the memory need too; the
 * same holds the other way round for a host against the waiting candidates sorted by cores need,
 * with a prefix minimum of memory need. GPU needs are walked, only for the candidates or hosts that
 * have them.
 */
final class GroupViews {

    /**
     * The idle hosts by idle cores descending, with the prefix maximum of idle memory. Built in O(I
     * log I); a CPU candidate's fit question costs O(log I).
     */
    static final class IdleView {
        final Maestro.BookableHost[] byCores;
        final long[] prefixMaxMem;
        final long idleCoresSum;
        final List<Maestro.BookableHost> reserved = new ArrayList<>();

        IdleView(List<Maestro.BookableHost> hosts) {
            byCores = hosts.toArray(new Maestro.BookableHost[0]);
            Arrays.sort(byCores, Comparator.comparingInt((Maestro.BookableHost h) -> -h.coresIdle));
            prefixMaxMem = new long[byCores.length];
            long sum = 0;
            long max = Long.MIN_VALUE;
            for (int i = 0; i < byCores.length; i++) {
                max = Math.max(max, byCores[i].memIdle);
                prefixMaxMem[i] = max;
                sum += byCores[i].coresIdle;
                if (byCores[i].reservation != null)
                    reserved.add(byCores[i]);
            }
            idleCoresSum = sum;
        }

        /**
         * How many hosts have at least {@code coresMin} idle cores: the length of the fitting
         * prefix.
         */
        int fitPrefix(int coresMin) {
            int lo = 0;
            int hi = byCores.length;
            while (lo < hi) {
                int mid = (lo + hi) >>> 1;
                if (byCores[mid].coresIdle >= coresMin)
                    lo = mid + 1;
                else
                    hi = mid;
            }
            return lo;
        }

        /** Whether one of the first {@code k} hosts has at least {@code memMin} idle memory. */
        boolean anyMem(int k, long memMin) {
            return k > 0 && prefixMaxMem[k - 1] >= memMin;
        }
    }

    /**
     * The waiting candidates by cores need ascending, the ones without a GPU need with the prefix
     * minimum of memory need, the GPU needers apart. Built in O(W log W); a host's "can anyone buy
     * my idle cores" question costs O(log W) plus the GPU needers when the host has idle GPUs.
     */
    static final class NeedView {
        final Maestro.LayerCandidate[] byCores;
        final long[] prefixMinMem;
        final List<Maestro.LayerCandidate> gpuNeeders = new ArrayList<>();

        NeedView(List<Maestro.LayerCandidate> candidates) {
            List<Maestro.LayerCandidate> cpu = new ArrayList<>();
            for (Maestro.LayerCandidate c : candidates) {
                if (c.waitingFrameCount <= 0)
                    continue;
                if (c.layerGpusMin > 0 || c.layerGpuMemMin > 0)
                    gpuNeeders.add(c);
                else
                    cpu.add(c);
            }
            byCores = cpu.toArray(new Maestro.LayerCandidate[0]);
            Arrays.sort(byCores,
                    Comparator.comparingInt((Maestro.LayerCandidate c) -> c.layerCoresMin));
            prefixMinMem = new long[byCores.length];
            long min = Long.MAX_VALUE;
            for (int i = 0; i < byCores.length; i++) {
                min = Math.min(min, byCores[i].layerMemMin);
                prefixMinMem[i] = min;
            }
        }

        boolean isEmpty() {
            return byCores.length == 0 && gpuNeeders.isEmpty();
        }

        /**
         * Whether some waiting candidate fits the host's idle cores, memory, gpus and gpu memory.
         */
        boolean sellable(Maestro.BookableHost h) {
            int k = servedPrefix(h.coresIdle);
            if (k > 0 && prefixMinMem[k - 1] <= h.memIdle)
                return true;
            for (Maestro.LayerCandidate c : gpuNeeders) {
                if (c.layerCoresMin <= h.coresIdle && c.layerMemMin <= h.memIdle
                        && c.layerGpusMin <= h.gpusIdle && c.layerGpuMemMin <= h.gpuMemIdle)
                    return true;
            }
            return false;
        }

        /** How many CPU candidates need at most {@code coresIdle} cores: the served prefix. */
        private int servedPrefix(int coresIdle) {
            int lo = 0;
            int hi = byCores.length;
            while (lo < hi) {
                int mid = (lo + hi) >>> 1;
                if (byCores[mid].layerCoresMin <= coresIdle)
                    lo = mid + 1;
                else
                    hi = mid;
            }
            return lo;
        }
    }
}
