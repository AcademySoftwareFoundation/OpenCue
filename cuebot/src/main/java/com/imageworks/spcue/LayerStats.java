
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

public class LayerStats {

    private LayerDetail detail;
    private FrameStateTotals frameStateTotals;
    private ExecutionSummary executionSummary;
    private List<ThreadStats> threadStats;
    private List<String> outputs;

    private String graphUnits;
    private float conversionUnits;
    private int scale;

    public List<String> getOutputs() {
        return outputs;
    }

    public void setOutputs(List<String> outputs) {

        List<String> newOutputs = new ArrayList<String>(outputs.size());
        for (String output : outputs) {
            newOutputs.add(new File(output).getParent() + "/*");
        }
        this.outputs = newOutputs;
    }

    public List<ThreadStats> getThreadStats() {
        return threadStats;
    }

    public void setThreadStats(List<ThreadStats> threadStats) {
        this.threadStats = threadStats;
        setGraphScaleValues();
    }

    public LayerDetail getDetail() {
        return detail;
    }

    public void setDetail(LayerDetail detail) {
        this.detail = detail;
    }

    public FrameStateTotals getFrameStateTotals() {
        return frameStateTotals;
    }

    public void setFrameStateTotals(FrameStateTotals frameStateTotals) {
        this.frameStateTotals = frameStateTotals;
    }

    public ExecutionSummary getExecutionSummary() {
        return executionSummary;
    }

    public void setExecutionSummary(ExecutionSummary executionSummary) {
        this.executionSummary = executionSummary;
    }

    public int getGraphScale() {
        return scale;
    }

    public String getGraphUnits() {
        return graphUnits;
    }

    public String getFormattedHighMemory() {
        return String.format(Locale.ROOT, "%.1fGB",
                executionSummary.highMemoryKb / 1024.0 / 1024.0);
    }

    public String getFormattedProcHours() {
        return String.format(Locale.ROOT, "%.1f", executionSummary.coreTime / 3600.0);
    }

    public int getFailedFrames() {
        return frameStateTotals.waiting + frameStateTotals.dead + frameStateTotals.eaten;
    }

    public String getGraphLegend() {
        StringBuilder sb = new StringBuilder(128);
        List<ThreadStats> reversed = new ArrayList<ThreadStats>(threadStats);
        Collections.reverse(reversed);
        for (ThreadStats t : reversed) {
            sb.append("|");
            sb.append(t.getThreads());
            sb.append("+");
            sb.append("Thread ");
        }
        return sb.toString();
    }

    public String getGraphData() {

        StringBuilder sb = new StringBuilder(128);

        for (ThreadStats t : threadStats) {
            sb.append(String.format(Locale.ROOT, "%.2f", t.getAvgFrameTime() / conversionUnits));
            sb.append(",");
        }
        if (sb.length() > 1) {
            sb.deleteCharAt(sb.length() - 1);
        }
        return sb.toString();
    }

    public int getThreadAvgCount() {
        return threadStats.size();
    }

    /**
     * Since frame times vary wildly, anywhere from 1 second to 7 days, this method will set some
     * values so average frame times are displayed in units that make them easy to compare.
     *
     * Based on the highest average frame time per thread group, average frame can be displayed in
     * minutes, seconds, or hours.
     *
     */
    private void setGraphScaleValues() {

        int hightestAverageSec = 0;
        for (ThreadStats t : threadStats) {
            if (t.getAvgFrameTime() >= hightestAverageSec) {
                hightestAverageSec = t.getAvgFrameTime();
            }
        }

        if (hightestAverageSec < 60) {
            graphUnits = "Seconds";
            scale = ((hightestAverageSec / 2 + 1) * 2);
            conversionUnits = 1f;
        } else if (hightestAverageSec < 3600) {
            graphUnits = "Minutes";
            scale = ((hightestAverageSec / 60) + 1);
            conversionUnits = 60f;
        } else {
            graphUnits = "Hours";
            scale = ((hightestAverageSec / 3600) + 1);
            conversionUnits = 3600f;
        }
    }
}
