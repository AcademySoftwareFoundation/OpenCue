"use client";

/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import * as React from "react";
import { Button } from "@/components/ui/button";

type AdminGroup = {
  id: number;
  name: string;
  description: string | null;
  source: string;
  roles: string[];
};

type AdminRole = { id: number; name: string };

export default function GroupsPage() {
  const [groups, setGroups] = React.useState<AdminGroup[]>([]);
  const [roles, setRoles] = React.useState<AdminRole[]>([]);
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    const [g, r] = await Promise.all([
      fetch("/api/admin/groups").then((r) => r.json()),
      fetch("/api/admin/roles").then((r) => r.json()),
    ]);
    setGroups(g.groups ?? []);
    setRoles(r.roles ?? []);
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  async function createGroup(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await fetch("/api/admin/groups", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, description: description || null }),
    });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      setError(b.error || "Failed to create group.");
      return;
    }
    setName("");
    setDescription("");
    refresh();
  }

  async function deleteGroup(id: number) {
    if (!confirm("Delete this group?")) return;
    const res = await fetch(`/api/admin/groups/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      alert(b.error || "Failed.");
    }
    refresh();
  }

  async function attachRole(groupId: number, roleName: string) {
    if (!roleName) return;
    await fetch(`/api/admin/groups/${groupId}/roles`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ roleName }),
    });
    refresh();
  }

  async function detachRole(groupId: number, roleName: string) {
    const sp = new URLSearchParams({ roleName });
    await fetch(`/api/admin/groups/${groupId}/roles?${sp}`, {
      method: "DELETE",
    });
    refresh();
  }

  return (
    <div className="space-y-4">
      <form onSubmit={createGroup} className="flex flex-wrap items-end gap-2 p-3 rounded-md border bg-card">
        <label className="text-sm space-y-1">
          <span className="font-medium">Group name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="block rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </label>
        <label className="text-sm space-y-1 flex-1 min-w-[16rem]">
          <span className="font-medium">Description</span>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="block w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </label>
        <Button type="submit">Create local group</Button>
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
              <Th>Name</Th>
              <Th>Source</Th>
              <Th>Description</Th>
              <Th>Roles</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.id} className="border-t">
                <Td>{g.name}</Td>
                <Td>
                  <span className="rounded-md bg-foreground/10 px-1.5 py-0.5 text-xs">
                    {g.source}
                  </span>
                </Td>
                <Td>{g.description ?? ""}</Td>
                <Td>
                  <div className="flex flex-wrap gap-1">
                    {g.roles.map((r) => (
                      <span
                        key={r}
                        className="inline-flex items-center gap-1 rounded-md bg-foreground/10 px-1.5 py-0.5 text-xs"
                      >
                        {r}
                        <button
                          onClick={() => detachRole(g.id, r)}
                          className="text-foreground/60 hover:text-red-600"
                          type="button"
                          aria-label={`Remove role ${r}`}
                        >
                          x
                        </button>
                      </span>
                    ))}
                    <select
                      defaultValue=""
                      onChange={(e) => {
                        attachRole(g.id, e.target.value);
                        e.currentTarget.value = "";
                      }}
                      className="rounded-md border border-input bg-background px-1.5 py-0.5 text-xs"
                    >
                      <option value="">+ attach...</option>
                      {roles
                        .filter((r) => !g.roles.includes(r.name))
                        .map((r) => (
                          <option key={r.id} value={r.name}>
                            {r.name}
                          </option>
                        ))}
                    </select>
                  </div>
                </Td>
                <Td>
                  {g.source === "local" ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => deleteGroup(g.id)}
                    >
                      Delete
                    </Button>
                  ) : (
                    <span className="text-xs text-foreground/60">
                      Externally sourced
                    </span>
                  )}
                </Td>
              </tr>
            ))}
            {groups.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-center text-foreground/60">
                  No groups.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">{children}</th>;
}
function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-3 py-2 align-top">{children}</td>;
}
