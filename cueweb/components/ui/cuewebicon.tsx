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

import Image from "next/image";
import opencueIconBlack from "../../public/opencue-icon-black.png";
import opencueIconWhite from "../../public/opencue-icon-white.png";

interface CueWebIconProps {
  height?: number;
}

const CueWebIcon = ({ height = 70 }: CueWebIconProps) => {
  // Scale the text alongside the icon so callers control the overall size
  // via the single `height` prop.
  const labelStyle = { fontSize: `${Math.round(height * 0.5)}px` };
  const gapStyle = { gap: `${Math.round(height * 0.18)}px` };

  return (
    <div
      className="flex items-center text-foreground"
      style={gapStyle}
    >
      <Image
        className="block dark:hidden"
        src={opencueIconBlack}
        alt="OpenCue logo"
        height={height}
        width={height}
      />
      <Image
        className="hidden dark:block"
        src={opencueIconWhite}
        alt="OpenCue logo"
        height={height}
        width={height}
      />
      <span className="font-bold leading-none" style={labelStyle}>
        CueWeb
      </span>
    </div>
  );
};

export default CueWebIcon;
