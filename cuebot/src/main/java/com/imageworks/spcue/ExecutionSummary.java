
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



package com.imageworks.spcue;

/**
 * Commonly used statisitcal properties of a job or layer.
 */
public class ExecutionSummary {

    public double standardDeviation;
    public long coreTime;
    public long coreTimeSuccess;
    public long coreTimeFail;
    public long gpuTime;
    public long gpuTimeSuccess;
    public long gpuTimeFail;
    public long highMemoryKb;

    public long getHighMemoryKb() {
        return highMemoryKb;
    }

    public void setHighMemoryKb(long highMemoryKb) {
        this.highMemoryKb = highMemoryKb;
    }

    public double getStandardDeviation() {
        return standardDeviation;
    }

    public void setStandardDeviation(double standardDeviation) {
        this.standardDeviation = standardDeviation;
    }

    public long getCoreTime() {
        return coreTime;
    }

    public void setCoreTime(long coreTime) {
        this.coreTime = coreTime;
    }

    public long getCoreTimeSuccess() {
        return coreTimeSuccess;
    }

    public void setCoreTimeSuccess(long coreTimeSuccess) {
        this.coreTimeSuccess = coreTimeSuccess;
    }

    public long getCoreTimeFail() {
        return coreTimeFail;
    }

    public void setCoreTimeFail(long coreTimeFail) {
        this.coreTimeFail = coreTimeFail;
    }

    public long getGpuTime() {
        return gpuTime;
    }

    public void setGpuTime(long gpuTime) {
        this.gpuTime = gpuTime;
    }

    public long getGpuTimeSuccess() {
        return gpuTimeSuccess;
    }

    public void setGpuTimeSuccess(long gpuTimeSuccess) {
        this.gpuTimeSuccess = gpuTimeSuccess;
    }

    public long getGpuTimeFail() {
        return gpuTimeFail;
    }

    public void setGpuTimeFail(long gpuTimeFail) {
        this.gpuTimeFail = gpuTimeFail;
    }
}

