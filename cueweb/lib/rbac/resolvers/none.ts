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

import "server-only";

import type { GroupsResolver, ResolvedIdentity } from "./types";

// The open-source default. No external group source - any signed-in
// user gets the explicit roles attached to them in the DB (if any) and
// nothing else. Useful when CueWeb runs without Okta/LDAP and the
// admin assigns roles by hand in the UI.
export const noneResolver: GroupsResolver = {
  id: "none",
  async resolve(): Promise<ResolvedIdentity | null> {
    // The caller decides what to do with a null identity; for "none"
    // we don't claim ownership of any sign-in. The local provider
    // upserts its own user, and the Okta/LDAP providers each map to
    // their own resolver (not this one).
    return null;
  },
};
