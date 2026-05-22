"use client";

/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import * as React from "react";
import { Button } from "@/components/ui/button";

type AdminRole = {
  id: number;
  name: string;
  description: string | null;
  builtin: 0 | 1;
  permissions: string[];
};

type PermissionEntry = { key: string; description: string };

export default function RolesPage() {
  const [roles, setRoles] = React.useState<AdminRole[]>([]);
  const [catalog, setCatalog] = React.useState<PermissionEntry[]>([]);
  const [editing, setEditing] = React.useState<Record<number, string[]>>({});
  const [newName, setNewName] = React.useState("");
  const [newDescription, setNewDescription] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    const [r, p] = await Promise.all([
      fetch("/api/admin/roles").then((r) => r.json()),
      fetch("/api/admin/permissions").then((r) => r.json()),
    ]);
    setRoles(r.roles ?? []);
    setCatalog(p.permissions ?? []);
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  function togglePerm(roleId: number, perm: string) {
    setEditing((e) => {
      const current = e[roleId] ?? roles.find((r) => r.id === roleId)?.permissions ?? [];
      const set = new Set(current);
      if (set.has(perm)) set.delete(perm);
      else set.add(perm);
      return { ...e, [roleId]: Array.from(set) };
    });
  }

  async function savePerms(roleId: number) {
    const perms =
      editing[roleId] ?? roles.find((r) => r.id === roleId)?.permissions ?? [];
    const res = await fetch(`/api/admin/roles/${roleId}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ permissions: perms }),
    });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      alert(b.error || "Failed.");
    }
    setEditing((e) => {
      const { [roleId]: _, ...rest } = e;
      return rest;
    });
    refresh();
  }

  async function deleteRole(roleId: number) {
    if (!confirm("Delete this role?")) return;
    const res = await fetch(`/api/admin/roles/${roleId}`, { method: "DELETE" });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      alert(b.error || "Failed.");
    }
    refresh();
  }

  async function createRole(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await fetch("/api/admin/roles", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        name: newName,
        description: newDescription || null,
        permissions: [],
      }),
    });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      setError(b.error || "Failed to create role.");
      return;
    }
    setNewName("");
    setNewDescription("");
    refresh();
  }

  return (
    <div className="space-y-4">
      <form onSubmit={createRole} className="flex flex-wrap items-end gap-2 p-3 rounded-md border bg-card">
        <label className="text-sm space-y-1">
          <span className="font-medium">Role name</span>
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
            className="block rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </label>
        <label className="text-sm space-y-1 flex-1 min-w-[16rem]">
          <span className="font-medium">Description</span>
          <input
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            className="block w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
        </label>
        <Button type="submit">Create custom role</Button>
        {error && (
          <p className="text-sm text-red-600 w-full" role="alert">
            {error}
          </p>
        )}
      </form>

      <div className="space-y-3">
        {roles.map((r) => {
          const draft = editing[r.id];
          const current = new Set(draft ?? r.permissions);
          const dirty = !!draft;
          return (
            <div key={r.id} className="rounded-md border p-3">
              <div className="flex items-baseline gap-2">
                <h3 className="text-lg font-semibold">{r.name}</h3>
                {r.builtin === 1 && (
                  <span className="text-xs rounded bg-foreground/10 px-1.5 py-0.5">
                    built-in
                  </span>
                )}
                <span className="text-sm text-foreground/60">{r.description}</span>
                <div className="ml-auto flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => savePerms(r.id)}
                    disabled={!dirty}
                  >
                    Save
                  </Button>
                  {r.builtin !== 1 && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => deleteRole(r.id)}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </div>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1">
                {catalog.map((p) => (
                  <label
                    key={p.key}
                    className="flex items-start gap-2 text-sm rounded p-1 hover:bg-foreground/5"
                  >
                    <input
                      type="checkbox"
                      checked={current.has(p.key)}
                      onChange={() => togglePerm(r.id, p.key)}
                      className="mt-0.5"
                    />
                    <span>
                      <span className="font-mono text-xs">{p.key}</span>
                      <span className="block text-xs text-foreground/60">
                        {p.description}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          );
        })}
        {roles.length === 0 && <p className="text-foreground/60">No roles.</p>}
      </div>
    </div>
  );
}
