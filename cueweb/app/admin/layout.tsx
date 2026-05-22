/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import * as React from "react";
import Link from "next/link";

import { Breadcrumbs } from "@/components/ui/breadcrumbs";

import { AdminTabs } from "./tabs";

export const dynamic = "force-dynamic";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="container mx-auto py-6 max-w-7xl">
      <Breadcrumbs
        items={[{ label: "Home", href: "/" }, { label: "Admin" }]}
        className="mb-4"
      />
      <header className="mb-4">
        <h1 className="text-2xl font-semibold">CueWeb administration</h1>
        <p className="text-sm text-foreground/70">
          Manage users, groups, roles, permissions, admins, and view the
          audit log.
        </p>
      </header>
      <AdminTabs />
      <div className="mt-6">{children}</div>
    </div>
  );
}
