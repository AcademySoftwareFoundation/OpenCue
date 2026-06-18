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

"use server";

import { getServerSession } from "next-auth";
import { revalidatePath } from "next/cache";

import { authOptions } from "@/lib/auth";
import { getConfiguredFacilities } from "@/lib/facility";
import { writeFacilityOverride } from "@/lib/facility-store";

export interface UpdateFacilityResult {
  ok: boolean;
  message: string;
}

/**
 * Server action backing the /settings/facilities admin screen. Persists a
 * per-facility gateway URL / JWT secret override (runtime, no redeploy) and
 * records an audit entry. Admin gating: when group authorization is enabled
 * (see lib/authz.ts / middleware.ts in deployments that ship it), restrict
 * /settings/facilities to CUEWEB_ADMIN_GROUPS so only admins reach this action.
 */
export async function updateFacilityConfig(
  _prev: UpdateFacilityResult | null,
  formData: FormData,
): Promise<UpdateFacilityResult> {
  const name = String(formData.get("facility") ?? "").trim();
  if (!name || !getConfiguredFacilities().includes(name)) {
    return { ok: false, message: "Unknown facility." };
  }

  // gatewayUrl: empty string clears the override (falls back to env/default).
  const gatewayUrlRaw = formData.get("gatewayUrl");
  const gatewayUrl = gatewayUrlRaw === null ? undefined : String(gatewayUrlRaw).trim();
  if (gatewayUrl && !/^https?:\/\/.+/i.test(gatewayUrl)) {
    return { ok: false, message: "Gateway URL must start with http:// or https://" };
  }

  // jwtSecret: the value is never round-tripped to the client, so the password
  // field starts empty. A blank field means "leave unchanged"; the explicit
  // "clear" checkbox removes the override (falls back to env/default).
  const clearSecret = formData.get("clearSecret") != null;
  const secretInput = formData.get("jwtSecret");
  let jwtSecret: string | undefined;
  if (clearSecret) {
    jwtSecret = ""; // clear the override
  } else if (secretInput !== null && String(secretInput) !== "") {
    jwtSecret = String(secretInput); // set a new secret
  } else {
    jwtSecret = undefined; // unchanged
  }

  let actor = "unknown";
  try {
    const session = await getServerSession(authOptions);
    actor = session?.user?.email || session?.user?.name || "unknown";
  } catch {
    // Auth disabled / unavailable: leave actor as "unknown".
  }

  try {
    await writeFacilityOverride(name, { gatewayUrl, jwtSecret }, actor);
  } catch (err) {
    return { ok: false, message: `Could not save: ${(err as Error).message}` };
  }

  revalidatePath("/settings/facilities");
  return { ok: true, message: `Saved ${name}.` };
}
