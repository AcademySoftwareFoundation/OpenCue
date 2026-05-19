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
import iconlight from "../../app/iconlight.png";
import icondark from "../../app/icondark.png";

interface CueWebIconProps {
  height?: number;
}

const CueWebIcon = ({ height = 70 }: CueWebIconProps) => {
  return (
    <div>
      <Image className="hidden dark:block" src={icondark} alt="dark-mode-image" height={height} />
      <Image className="mb-4 block dark:hidden" src={iconlight} alt="light-mode-image" height={height} />
    </div>
  );
};

export default CueWebIcon;
