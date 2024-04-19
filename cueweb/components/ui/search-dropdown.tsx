import { Job } from "@/app/jobs/columns";
import React from "react";
import { CommandEmpty, CommandGroup, CommandItem, CommandList } from "./command";
import { PlusCircle } from "lucide-react";

type SearchDropdownProps = {
  promise: Promise<Job[]> | undefined;
  hidden: boolean;
  handleJobSearchSelect(job: Job): void;
};

export default async function SearchDropdown({ promise, hidden, handleJobSearchSelect }: SearchDropdownProps) {
  const jobs = await promise;
  return (
    <div>
      <CommandList
        className="absolute z-10 bg-stone-50 rounded-md w-100 border shadow-md dark:bg-background"
        hidden={hidden}
      >
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup>
          {jobs?.map((job) => (
            <CommandItem key={job.name} onSelect={() => handleJobSearchSelect(job)}>
              {/* For some reason adding the plus icon here causes the jobs to not show? */}
              {/* <PlusCircle strokeWidth={1.25} className="mr-2" /> */}
              {job.name}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </div>
  );
}
