"use client";

/*
 * Copyright Contributors to the OpenCue Project
 * SPDX-License-Identifier: Apache-2.0
 */

import * as React from "react";
import { Button } from "@/components/ui/button";

type AdminUser = {
  id: number;
  username: string;
  email: string | null;
  display_name: string | null;
  source: string;
  active: 0 | 1;
  must_change_password: 0 | 1;
  groups: string[];
  directRoles: string[];
};

type AdminRole = { id: number; name: string };

export default function UsersPage() {
  const [users, setUsers] = React.useState<AdminUser[]>([]);
  const [roles, setRoles] = React.useState<AdminRole[]>([]);
  const [q, setQ] = React.useState("");
  const [createOpen, setCreateOpen] = React.useState(false);

  const refresh = React.useCallback(async () => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    const [u, r] = await Promise.all([
      fetch(`/api/admin/users?${params}`).then((r) => r.json()),
      fetch(`/api/admin/roles`).then((r) => r.json()),
    ]);
    setUsers(u.users ?? []);
    setRoles(r.roles ?? []);
  }, [q]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  async function toggleActive(u: AdminUser) {
    await fetch(`/api/admin/users/${u.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ active: u.active !== 1 }),
    });
    refresh();
  }

  async function attachRole(userId: number, roleName: string) {
    if (!roleName) return;
    await fetch(`/api/admin/users/${userId}/roles`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ roleName }),
    });
    refresh();
  }

  async function detachRole(userId: number, roleName: string) {
    const sp = new URLSearchParams({ roleName });
    await fetch(`/api/admin/users/${userId}/roles?${sp}`, { method: "DELETE" });
    refresh();
  }

  async function resetPassword(userId: number) {
    const pw = window.prompt(
      "New password (12+ characters). The user will be forced to change it on next sign-in.",
    );
    if (!pw) return;
    const res = await fetch(`/api/admin/users/${userId}/password`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password: pw }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      window.alert(body.error || "Failed to reset password.");
    } else {
      refresh();
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <input
          type="search"
          placeholder="Search users..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm w-64"
        />
        <Button onClick={() => setCreateOpen((v) => !v)} variant="outline" size="sm">
          {createOpen ? "Cancel" : "Create local user"}
        </Button>
      </div>

      {createOpen && (
        <CreateUserForm
          onCreated={() => {
            setCreateOpen(false);
            refresh();
          }}
        />
      )}

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-foreground/5">
            <tr>
              <Th>Username</Th>
              <Th>Email</Th>
              <Th>Source</Th>
              <Th>Active</Th>
              <Th>Groups</Th>
              <Th>Direct roles</Th>
              <Th>Actions</Th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t">
                <Td>
                  {u.username}
                  {u.must_change_password === 1 && (
                    <span
                      className="ml-2 inline-block rounded-sm bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900"
                      title="User must change password on next sign-in"
                    >
                      must change pw
                    </span>
                  )}
                </Td>
                <Td>{u.email ?? ""}</Td>
                <Td>{u.source}</Td>
                <Td>{u.active === 1 ? "yes" : "no"}</Td>
                <Td>{u.groups.join(", ")}</Td>
                <Td>
                  <div className="flex flex-wrap gap-1">
                    {u.directRoles.map((r) => (
                      <span
                        key={r}
                        className="inline-flex items-center gap-1 rounded-md bg-foreground/10 px-1.5 py-0.5 text-xs"
                      >
                        {r}
                        <button
                          onClick={() => detachRole(u.id, r)}
                          className="text-foreground/60 hover:text-red-600"
                          aria-label={`Remove role ${r}`}
                          type="button"
                        >
                          x
                        </button>
                      </span>
                    ))}
                    <select
                      defaultValue=""
                      onChange={(e) => {
                        attachRole(u.id, e.target.value);
                        e.currentTarget.value = "";
                      }}
                      className="rounded-md border border-input bg-background px-1.5 py-0.5 text-xs"
                    >
                      <option value="">+ attach...</option>
                      {roles
                        .filter((r) => !u.directRoles.includes(r.name))
                        .map((r) => (
                          <option key={r.id} value={r.name}>
                            {r.name}
                          </option>
                        ))}
                    </select>
                  </div>
                </Td>
                <Td>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => toggleActive(u)}
                    >
                      {u.active === 1 ? "Deactivate" : "Activate"}
                    </Button>
                    {u.source === "local" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => resetPassword(u.id)}
                      >
                        Reset password
                      </Button>
                    )}
                  </div>
                </Td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-4 text-center text-foreground/60">
                  No users.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CreateUserForm({ onCreated }: { onCreated: () => void }) {
  const [username, setUsername] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [displayName, setDisplayName] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch("/api/admin/users", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username, email, displayName, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || "Failed to create user.");
        return;
      }
      onCreated();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-3 rounded-md border bg-card">
      <Field label="Username" value={username} onChange={setUsername} required />
      <Field label="Display name" value={displayName} onChange={setDisplayName} />
      <Field label="Email" value={email} onChange={setEmail} type="email" />
      <Field
        label="Initial password (12+ chars)"
        value={password}
        onChange={setPassword}
        type="password"
        required
        minLength={12}
      />
      {error && (
        <p className="text-sm text-red-600 sm:col-span-2" role="alert">
          {error}
        </p>
      )}
      <div className="sm:col-span-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Creating..." : "Create user"}
        </Button>
      </div>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  minLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  minLength?: number;
}) {
  return (
    <label className="text-sm space-y-1">
      <span className="font-medium">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        minLength={minLength}
        className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
      />
    </label>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide">{children}</th>;
}
function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-3 py-2 align-top">{children}</td>;
}
