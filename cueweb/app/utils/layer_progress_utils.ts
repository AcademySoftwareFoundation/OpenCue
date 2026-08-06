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

import type { Layer } from "@/app/layers/layer-columns";

// Same palette + ordering as the job progress bar so the per-row segments
// line up visually across the Jobs and Layers tables.
const LAYER_PROGRESS_STATES = [
  { key: "succeededFrames", label: "Succeeded", color: "#4CC417" },
  { key: "runningFrames", label: "Running", color: "#F8E473" },
  { key: "waitingFrames", label: "Waiting", color: "#ADD8E6" },
  { key: "dependFrames", label: "Depend", color: "#9118C4" },
  { key: "deadFrames", label: "Dead", color: "tomato" },
] as const;

const getFramePercentage = (count: number, totalFrames: number) => {
  if (totalFrames <= 0) return 0;
  return (count / totalFrames) * 100;
};

export const getLayerProgressSegments = (layer: Layer) => {
  return LAYER_PROGRESS_STATES.map((state) => {
    const count = layer.layerStats[state.key];
    return {
      percentage: `${getFramePercentage(count, layer.layerStats.totalFrames)}%`,
      color: state.color,
    };
  });
};

export const getLayerProgressTooltipRows = (layer: Layer) => {
  return LAYER_PROGRESS_STATES.map((state) => {
    const count = layer.layerStats[state.key];
    const percentage = getFramePercentage(count, layer.layerStats.totalFrames);
    return {
      label: state.label,
      count,
      percentage: `${percentage.toFixed(1)}%`,
    };
  });
};
