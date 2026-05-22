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

import type { Source } from "../db/types";

/**
 * What a resolver returns after a successful sign-in: the canonical
 * identity (used to upsert the user row) and the list of group names
 * the user belongs to.
 */
export type ResolvedIdentity = {
  source: Exclude<Source, "imported">;
  externalId: string;
  username: string;
  email: string | null;
  displayName: string | null;
  groups: ReadonlyArray<string>;
};

export interface GroupsResolver {
  /** Short name, e.g. "okta" / "ldap" / "none". */
  readonly id: string;

  /**
   * Resolve groups for the just-signed-in user. The arguments mirror the
   * NextAuth jwt callback shape; resolvers extract whatever they need.
   */
  resolve(args: {
    profile: any;
    account: any;
    user: any;
    token: any;
  }): Promise<ResolvedIdentity | null>;
}
