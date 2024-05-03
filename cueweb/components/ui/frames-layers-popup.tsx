"use client";

import * as React from "react";
import { Frame, frameColumns } from "@/app/frames/frame-columns";
import { Job } from "@/app/jobs/columns";
import { getFramesForJob, getLayersForJob } from "@/app/utils/utils";
import { Layer, layerColumns } from "@/app/layers/layer-columns";
import { Dialog, DialogContent, DialogTrigger, DialogTitle } from "@/components/ui/dialog";
import { ExternalLink } from "lucide-react";
import { SimpleDataTable } from "./simple-data-table";

type FramesLayersPopupProps = {
  job: Job;
};

// component for the Frames and Layers pop-up for a given job
// consists of a pop-up window that contains the layers table and then the frames table beneath it
export function FramesLayersPopup({ job }: FramesLayersPopupProps) {
  const [layers, setLayers] = React.useState<Layer[]>([]);
  const [frames, setFrames] = React.useState<Frame[]>([]);

  // when the pop-up button is pressed we retrieve the layers and frames for the given job
  const handleDialogPopup = async (job: Job) => {
    setLayers(await getLayersForJob(job));
    setFrames(await getFramesForJob(job));
  };

  return (
    <Dialog>
      <DialogTrigger
        className="h-10 px-4 py-2 hover:bg-accent hover:text-accent-foreground"
        onClick={() => handleDialogPopup(job)}
      >
        <ExternalLink />
      </DialogTrigger>
      {/* setting max height and width to 95%, and making the dialog content scrollable when there is overflow */}
      <DialogContent className="max-h-[95%] max-w-[95%] overflow-y-scroll">
        <DialogTitle>{job.name}</DialogTitle>
        <SimpleDataTable data={layers} columns={layerColumns}></SimpleDataTable>
        <SimpleDataTable data={frames} columns={frameColumns} job={job} isFramesTable={true}></SimpleDataTable>
      </DialogContent>
    </Dialog>
  );
}
