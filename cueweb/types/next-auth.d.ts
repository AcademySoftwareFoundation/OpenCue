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

import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface Session {
    user: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      source?: "local" | "okta" | "ldap" | "google" | "github" | null;
      groups?: string[];
      roles?: string[];
      permissions?: string[];
      isAdmin?: boolean;
      mustChangePassword?: boolean;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    cuewebUserId?: number;
    cuewebSource?: "local" | "okta" | "ldap" | "google" | "github";
    cuewebGroups?: string[];
    cuewebRoles?: string[];
    cuewebPermissions?: string[];
    cuewebIsAdmin?: boolean;
    cuewebMustChangePassword?: boolean;
    cuewebRefreshedAt?: number;
  }
}
