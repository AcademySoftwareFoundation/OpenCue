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

import React, { useEffect, useState } from "react";
import "./progressbar.css";

interface VisualPart {
  percentage: string;
  color: string;
}

interface ProgressBarProps {
  backgroundColor?: string;
  visualParts?: VisualPart[];
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  backgroundColor = "#e5e5e5",
  visualParts = [{ percentage: "0%", color: "white" }],
}) => {
  const [widths, setWidths] = useState<string[]>(visualParts.map(() => "0%"));

  useEffect(() => {
    requestAnimationFrame(() => {
      setWidths(
        visualParts.map((item) => {
          return item.percentage;
        }),
      );
    });
  }, [visualParts]);

  return (
    <>
      <div
        className="progressVisualFull"
        style={{
          backgroundColor,
        }}
      >
        {visualParts.map((item, index) => (
          <div
            key={index}
            style={{
              width: widths[index],
              backgroundColor: item.color,
            }}
            className="progressVisualPart"
          />
        ))}
      </div>
    </>
  );
};

export default ProgressBar;
