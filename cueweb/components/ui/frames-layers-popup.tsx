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


import { Frame, frameColumns } from "@/app/frames/frame-columns";
import { Job } from "@/app/jobs/columns";
import { Layer, layerColumns } from "@/app/layers/layer-columns";
import { getFramesForJob, getLayersForJob } from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ExternalLink } from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { SimpleDataTable } from "./simple-data-table";
import { JobDependencyGraph } from "./job-dependency-graph";

type FramesLayersPopupProps = {
  job: Job;
  username: string;
};

// Component for the Frames and Layers pop-up for a given job
// Contains a pop-up window that shows layers and frames tables
export function FramesLayersPopup({ job, username }: FramesLayersPopupProps) {
  const [layers, setLayers] = React.useState<Layer[]>([]);
  const [frames, setFrames] = React.useState<Frame[]>([]);
  const [isOpen, setIsOpen] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState<"tables" | "graph">("tables");
  const isAvailable = React.useRef(false);

  const handleDialogPopup = async (job: Job) => {
    setIsLoading(true);
    try {
      const newLayers = await getLayersForJob(job);
      const newFrames = await getFramesForJob(job);
      setLayers(newLayers);
      setFrames(newFrames);
      isAvailable.current = newLayers.length > 0 || newFrames.length > 0;
    } catch (error) {
      handleError(error, "Error fetching layers and frames");
    }
    setIsLoading(false);
  };

  // Updates the layers and frames in the table every 5 seconds
  React.useEffect(() => {
    let interval: NodeJS.Timeout | undefined;
    let layersWorker: Worker | undefined;
    let framesWorker: Worker | undefined;
    const updateTables = () => {
      try {
        if (!layersWorker) layersWorker = new Worker(new URL('/public/workers/updateLayersTableDataWorker.tsx', import.meta.url));
        if (!framesWorker) framesWorker = new Worker(new URL('/public/workers/updateFramesTableDataWorker.tsx', import.meta.url));

        layersWorker.postMessage({ job });
        framesWorker.postMessage({ job });
        
        layersWorker.onmessage = (e) => {
          if (e.data.error) {
            isAvailable.current = false;
          } else {
            const newData = e.data.updatedLayers;
            if (JSON.stringify(newData) !== JSON.stringify(layers)) {
              setLayers(newData);
            }
          }
        };

        framesWorker.onmessage = (e) => {
          if (e.data.error) {
            isAvailable.current = false;
          } else {
            const newData = e.data.updatedFrames;
            if (JSON.stringify(newData) !== JSON.stringify(frames)) {
              setFrames(newData);
            }
          }
        };
      } catch (error) {
        handleError(error, "Error updating table");
      }
    };

    if (isOpen && isAvailable.current) {
      interval = setInterval(updateTables, 5000);
    }

    return () => {
      clearInterval(interval);
      layersWorker?.terminate();
      framesWorker?.terminate();
    };
  }, [isOpen, layers, frames, job]);

  const renderSkeleton = (count: number) => {
    return Array.from({ length: count }).map((_, index) => (
      <Skeleton key={`skeleton-${index}`} className="h-5 w-full" />
    ));
  };

  return (
    <Dialog onOpenChange={setIsOpen}>
      <DialogTrigger
        className="h-10 px-4 py-2 hover:bg-accent hover:text-accent-foreground"
        onClick={() => handleDialogPopup(job)}
      >
        <ExternalLink />
      </DialogTrigger>
      {isLoading ? (
        <DialogContent className="flex max-w-[95%] max-h-[95%] flex-col">
          <DialogHeader>
            <DialogTitle>Loading...</DialogTitle>
            <DialogDescription>
              Fetching layers and frames for this job.
            </DialogDescription>
          </DialogHeader>
          <div className="w-full space-y-4">
            {renderSkeleton(5)}
            <div className="h-2"></div>
            {renderSkeleton(10)}
          </div>
        </DialogContent>
      ) : (
        <DialogContent className="max-h-[95%] max-w-[95%] overflow-y-scroll">
          <DialogHeader>
            <DialogTitle className="truncate">{job.name}</DialogTitle>
            <DialogDescription className="flex flex-wrap items-center gap-2">
              <span>Layers and frames for this job.</span>
              <Link
                href={`/jobs/${encodeURIComponent(job.name)}?jobId=${encodeURIComponent(job.id)}`}
                className="underline underline-offset-2 hover:text-foreground"
              >
                Open full page
              </Link>
            </DialogDescription>
          </DialogHeader>

          <div className="flex space-x-2 my-4">
            <button
              className={`px-3 py-1 rounded text-sm ${activeTab === "tables" ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}
              onClick={() => setActiveTab("tables")}
            >
              Layers & Frames
            </button>
            <button
              className={`px-3 py-1 rounded text-sm ${activeTab === "graph" ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`}
              onClick={() => setActiveTab("graph")}
            >
              Dependency Graph
            </button>
          </div>

         
          {activeTab === "tables" ? (
            <div className="flex flex-col gap-4">
              <SimpleDataTable data={layers} columns={layerColumns} username={username} />
              <SimpleDataTable data={frames} columns={frameColumns} job={job} isFramesTable={true} username={username} />
            </div>
          ) : (
            <JobDependencyGraph job={job} onNavigate={() => setActiveTab("tables")} />
          )}
        </DialogContent>
      )}
    </Dialog>
  );
}