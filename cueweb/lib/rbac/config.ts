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

/**
 * Centralized reading of NEXT_PUBLIC_AUTH_PROVIDER. Both server and
 * client read from here so the "auth disabled" semantics stay
 * consistent.
 *
 * Semantics:
 *   - NEXT_PUBLIC_AUTH_PROVIDER unset / empty  -> sandbox mode:
 *       no login, no menu gating, no /admin enforcement; CueWeb
 *       behaves exactly like it did before RBAC was added.
 *   - NEXT_PUBLIC_AUTH_PROVIDER=local         -> local credentials only
 *       (bootstrap admin flow active).
 *   - NEXT_PUBLIC_AUTH_PROVIDER=okta,ldap     -> any combination of
 *       `local`, `okta`, `ldap`; each runs its provider + RBAC.
 *
 * NEXT_PUBLIC_* env vars are inlined into the client bundle at build
 * time, so the client-side checks resolve at module-eval time, not
 * via process.env at request time.
 */
function rawList(): string[] {
  const raw = process.env.NEXT_PUBLIC_AUTH_PROVIDER || "";
  return raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

export function authEnabled(): boolean {
  return rawList().length > 0;
}

export function hasProvider(name: "local" | "okta" | "ldap"): boolean {
  return rawList().includes(name);
}

export function authProviderList(): string[] {
  return rawList();
}
