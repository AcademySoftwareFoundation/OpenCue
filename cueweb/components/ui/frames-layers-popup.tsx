"use client";

import { Frame, frameColumns } from "@/app/frames/frame-columns";
import { Job } from "@/app/jobs/columns";
import { Layer, layerColumns } from "@/app/layers/layer-columns";
import { getFramesForJob, getLayersForJob } from "@/app/utils/get_utils";
import { handleError } from "@/app/utils/notify_utils";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import Skeleton from "@mui/material/Skeleton";
import { ExternalLink } from "lucide-react";
import * as React from "react";
import { SimpleDataTable } from "./simple-data-table";

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
      <Skeleton
        key={`skeleton-${index}`}
        variant="rounded"
        width="100%"
        height="20px"
        className="animate-pulse"
      />
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
        <DialogContent className="flex max-w-[95%] max-h-[95%] flex-col p-6">
          <DialogTitle>Loading...</DialogTitle>
          <div className="space-y-4 w-full">
            {renderSkeleton(5)}
            <div className="h-2"></div>
            {renderSkeleton(10)}
          </div>
        </DialogContent>
      ) : (
        <DialogContent className="max-h-[95%] max-w-[95%] overflow-y-scroll">
          <DialogTitle>{job.name}</DialogTitle>
          <SimpleDataTable data={layers} columns={layerColumns} username={username} />
          <SimpleDataTable data={frames} columns={frameColumns} job={job} isFramesTable={true} username={username} />
        </DialogContent>
      )}
    </Dialog>
  );
}
