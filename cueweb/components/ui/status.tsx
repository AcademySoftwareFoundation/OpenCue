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

type StatusProps = {
  status: string;
};

// prettier-ignore
const STATUS_COLORS = {
  SUCCEEDED: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  FINISHED: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  RUNNING: "bg-yellow-100 text-yellow-800 dark:bg-yellow-700 dark:text-yellow-300",
  WAITING: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  PAUSED: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  DEPEND: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  DEPENDENCY: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  DEAD: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  FAILING: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  DEFAULT: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
};

export function Status({ status }: StatusProps) {
  const colors = STATUS_COLORS[status.toUpperCase() as keyof typeof STATUS_COLORS] || STATUS_COLORS.DEFAULT;

  return (
    <span className={`inline-flex items-center text-xs px-1.5 py-0.5 rounded hover:cursor-pointer ${colors}`}>
      {status}
    </span>
  );
}
