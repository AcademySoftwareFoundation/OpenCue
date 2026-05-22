/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import { NextResponse } from "next/server";

import { requireAdmin } from "@/lib/rbac/require_feature";
import { PERMISSION_CATALOG } from "@/lib/rbac/permissions";

export const runtime = "nodejs";

export async function GET() {
  const gate = await requireAdmin();
  if (!gate.ok) return gate.response;
  return NextResponse.json({ permissions: PERMISSION_CATALOG });
}
