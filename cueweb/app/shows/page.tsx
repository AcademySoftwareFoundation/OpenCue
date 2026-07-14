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

import ShowsClient from "./shows-client";

// Toasts render through the global <ToastHost /> mounted in app/layout.tsx,
// so this page does not mount its own ToastContainer. ShowsClient fetches the
// active shows on the client so the table can auto-refresh.
export default function ShowsPage() {
  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <ShowsClient />
    </div>
  );
}
