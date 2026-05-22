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

"use client";

import { useSession } from "next-auth/react";
import { useMemo } from "react";

import { hasPermission } from "@/lib/rbac/permissions";
import { authEnabled } from "@/lib/rbac/config";

/**
 * Client-side RBAC hooks. They all hang off the NextAuth session,
 * which already carries `groups`, `roles`, `permissions`, and the
 * `isAdmin` flag (refreshed every ~60s by the JWT callback). UI
 * components hide menus and actions off these; the API enforces too.
 *
 * NB: the SessionProvider mounted in app/providers/session-provider.tsx
 * already wraps the app, so these work anywhere under it.
 */

export function useRoles(): string[] {
  const { data } = useSession();
  return useMemo(() => data?.user?.roles ?? [], [data?.user?.roles]);
}

export function usePermissions(): string[] {
  const { data } = useSession();
  return useMemo(() => data?.user?.permissions ?? [], [data?.user?.permissions]);
}

export function useFeature(name: string): boolean {
  const permissions = usePermissions();
  return useMemo(() => {
    // Sandbox mode: no auth configured -> every feature is on.
    if (!authEnabled()) return true;
    return hasPermission(permissions, name);
  }, [permissions, name]);
}

export function useIsAdmin(): boolean {
  const { data } = useSession();
  // Sandbox mode: hide the Admin shortcut (there is no auth, so the
  // admin UI is unreachable from the header by design).
  if (!authEnabled()) return false;
  return !!data?.user?.isAdmin;
}

export function useGroups(): string[] {
  const { data } = useSession();
  return useMemo(() => data?.user?.groups ?? [], [data?.user?.groups]);
}

export function useMustChangePassword(): boolean {
  const { data } = useSession();
  return !!data?.user?.mustChangePassword;
}
