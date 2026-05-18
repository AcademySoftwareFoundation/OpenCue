"use client";

import dynamic from "next/dynamic";
import type { ColumnDef } from "@tanstack/react-table";
import type { Job } from "./columns";

const DataTable = dynamic(() => import("./data-table"), {
  ssr: false,
});

interface DataTableClientProps {
  columns: ColumnDef<Job>[];
  username: string;
}

export default function DataTableClient(props: DataTableClientProps) {
  return <DataTable {...props} />;
}
