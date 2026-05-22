"use client";

/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import * as React from "react";
import { Button } from "@/components/ui/button";

type AdminEntry = {
  id: number;
  username: string;
  email: string | null;
  displayName: string | null;
  source: string;
};

export default function AdminsPage() {
  const [admins, setAdmins] = React.useState<AdminEntry[]>([]);
  const [lookup, setLookup] = React.useState("");
  const [field, setField] = React.useState<"username" | "email" | "externalId">("username");
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    const r = await fetch("/api/admin/admins").then((r) => r.json());
    setAdmins(r.admins ?? []);
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const body: Record<string, string> = {};
    body[field] = lookup;
    const res = await fetch("/api/admin/admins", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      setError(b.error || "Failed.");
      return;
    }
    setLookup("");
    refresh();
  }

  async function remove(userId: number) {
    if (!confirm("Remove admin access from this user?")) return;
    const res = await fetch(`/api/admin/admins/${userId}`, { method: "DELETE" });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      alert(b.error || "Failed.");
    }
    refresh();
  }

  return (
    <div className="space-y-4">
      <form onSubmit={add} className="flex flex-wrap items-end gap-2 p-3 rounded-md border bg-card">
        <label className="text-sm space-y-1">
          <span className="font-medium">Identify by</span>
          <select
            value={field}
            onChange={(e) => setField(e.target.value as typeof field)}
            className="block rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            <option value="username">Username</option>
            <option value="email">Email</option>
            <option value="externalId">External ID (Okta sub / LDAP DN)</option>
          </select>
        </label>
        <label className="text-sm space-y-1 flex-1 min-w-[18rem]">
          <span className="font-medium">Value</span>
          <input
            value={lookup}
            onChange={(e) => setLookup(e.target.value)}
            required
            className="block w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </label>
        <Button type="submit">Add admin</Button>
        {error && (
          <p className="text-sm text-red-600 w-full" role="alert">
            {error}
          </p>
        )}
      </form>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-foreground/5">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Username
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Email
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Source
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {admins.map((a) => (
              <tr key={a.id} className="border-t">
                <td className="px-3 py-2 align-top">{a.username}</td>
                <td className="px-3 py-2 align-top">{a.email ?? ""}</td>
                <td className="px-3 py-2 align-top">{a.source}</td>
                <td className="px-3 py-2 align-top">
                  <Button size="sm" variant="outline" onClick={() => remove(a.id)}>
                    Remove
                  </Button>
                </td>
              </tr>
            ))}
            {admins.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-foreground/60">
                  No admins. (CueWeb cannot be administered without at least one admin.)
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
