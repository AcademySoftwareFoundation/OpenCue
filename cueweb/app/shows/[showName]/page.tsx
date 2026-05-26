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

import { findShow } from "@/app/utils/show_utils";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function ShowPage({ params }: { params: { showName: string } }) {
  const show = await findShow(params.showName);

  if (!show) notFound();

  return (
    <div className="container mx-auto py-10 max-w-[90%]">
      <div className="mb-4">
        <Link href="/shows" className="text-sm underline underline-offset-2 text-muted-foreground">
          ← All Shows
        </Link>
      </div>

      <h1 className="text-2xl font-bold mb-6">{show.name}</h1>

      <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm max-w-sm">
        <dt className="font-medium">Active</dt>
        <dd>{show.active ? "Yes" : "No"}</dd>

        <dt className="font-medium">Booking</dt>
        <dd>{show.bookingEnabled ? "Enabled" : "Disabled"}</dd>

        <dt className="font-medium">Dispatching</dt>
        <dd>{show.dispatchEnabled ? "Enabled" : "Disabled"}</dd>
      </dl>
    </div>
  );
}
