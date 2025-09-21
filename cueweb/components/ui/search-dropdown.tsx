import { Job } from "@/app/jobs/columns";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import React, { CSSProperties, useEffect } from "react";
import { FixedSizeList } from "react-window";

type SearchDropdownProps = {
  jobs: Job[];
  hidden: boolean;
  maxListWidth: number;
  tableData: Job[];
  setMaxListWidth(width: number): void;
  handleJobSearchSelect(job: Job): void;
};

// SearchDropdown component to display a list of jobs in a virtualized dropdown
export default function SearchDropdown({
  jobs,
  hidden,
  tableData,
  maxListWidth,
  setMaxListWidth,
  handleJobSearchSelect,
}: SearchDropdownProps) {
  const itemHeight = 40;
  const maxListHeight = 400;
  const listHeight = Math.min(itemHeight * jobs.length + 5, maxListHeight);
  const listRef = React.useRef<FixedSizeList | null>(null);
  const style: CSSProperties = {
    position: "absolute",
    top: "100%",
    left: 0,
    right: 0,
    background: "white",
    border: "1px solid #ccc",
    borderRadius: "4px",
    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)",
    zIndex: 1000,
  };

  // Calculates the max width for a job and sets the lists width to that size
  useEffect(() => {
    if (jobs.length > 0) {
      const tempDiv = document.createElement("div");
      tempDiv.style.position = "absolute";
      tempDiv.style.visibility = "hidden";
      tempDiv.style.whiteSpace = "nowrap";
      document.body.appendChild(tempDiv);

      let maxWidth = 0;
      jobs.forEach((job) => {
        tempDiv.innerText = job.name;
        maxWidth = Math.max(maxWidth, tempDiv.clientWidth);
      });
      document.body.removeChild(tempDiv);

      setMaxListWidth(maxWidth + 100);
    }
  }, [jobs]);

  // Auto scroll to the top when jobs change (when filtering)
  useEffect(() => {
    if (listRef && listRef.current) {
      listRef.current.scrollTo(0);
    }
  }, [jobs]);

  return (
    <Box sx={{ position: "relative", width: "auto" }}>
      {!hidden && (
        <FixedSizeList
          height={listHeight}
          itemCount={jobs.length}
          itemSize={itemHeight}
          width={maxListWidth}
          ref={listRef}
          style={style}
        >
          {({ index, style }: { index: number; style: React.CSSProperties }) => {
            const job = jobs[index];
            const isJobAdded = tableData.some((existingJob: Job) => existingJob.name === job.name);

            return (
              <React.Fragment key={index}>
                <ListItem
                  button
                  style={{
                    ...style,
                    backgroundColor: isJobAdded ? "lightgreen" : "white",
                  }}
                  onMouseOver={(e: React.MouseEvent<HTMLDivElement, MouseEvent>) =>
                    (e.currentTarget.style.backgroundColor = isJobAdded ? "#1ec71e" : "lightgrey")
                  }
                  onMouseOut={(e: React.MouseEvent<HTMLDivElement, MouseEvent>) =>
                    (e.currentTarget.style.backgroundColor = isJobAdded ? "lightgreen" : "white")
                  }
                  key={index}
                  onClick={() => handleJobSearchSelect(job)}
                >
                  <ListItemText primary={jobs[index].name} />
                </ListItem>
                <Divider />
              </React.Fragment>
            );
          }}
        </FixedSizeList>
      )}
    </Box>
  );
}
