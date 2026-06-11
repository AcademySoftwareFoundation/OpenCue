"use client";

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

import { Show } from "@/app/utils/show_utils";
import { Button } from "@/components/ui/button";
import { CreateShowDialog } from "@/components/ui/create-show-dialog";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";

export default function ShowsClient({ shows }: { shows: Show[] }) {
  const router = useRouter();
  const [dialogOpen, setDialogOpen] = React.useState(false);

  const handleShowCreated = (showName: string) => {
    router.push(`/shows/${showName}`);
  };

  return (
    <>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Shows</h1>
        <Button onClick={() => setDialogOpen(true)}>+ New Show</Button>
      </div>

      {shows.length === 0 ? (
        <p className="text-muted-foreground">No shows found.</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 pr-4 font-medium">Name</th>
              <th className="py-2 pr-4 font-medium">Active</th>
              <th className="py-2 pr-4 font-medium">Booking</th>
              <th className="py-2 font-medium">Dispatching</th>
            </tr>
          </thead>
          <tbody>
            {shows.map((show) => (
              <tr key={show.id} className="border-b hover:bg-muted/50">
                <td className="py-2 pr-4">
                  <Link href={`/shows/${show.name}`} className="underline underline-offset-2">
                    {show.name}
                  </Link>
                </td>
                <td className="py-2 pr-4">{show.active ? "Yes" : "No"}</td>
                <td className="py-2 pr-4">{show.bookingEnabled ? "Enabled" : "Disabled"}</td>
                <td className="py-2">{show.dispatchEnabled ? "Enabled" : "Disabled"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <CreateShowDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSuccess={handleShowCreated}
      />
    </>
  );
}
