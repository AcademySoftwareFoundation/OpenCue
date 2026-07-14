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

import { usePathname } from "next/navigation";
import * as React from "react";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  Layers3,
  PanelBottom,
  PanelLeft,
  PanelRight,
  PanelTop,
  Pin,
  X,
} from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AttributesPanelPosition,
  useAttributesPanel,
} from "@/app/utils/use_attributes_panel";
import { useAttributeSelection } from "@/app/utils/use_attribute_selection";
import { toastWarning } from "@/app/utils/notify_utils";
import { cn } from "@/lib/utils";

/** Small copy-to-clipboard icon button used for attribute keys and values. */
function CopyButton({ text, what }: { text: string; what: string }) {
  const [copied, setCopied] = React.useState(false);
  // Track the "copied" reset timer so it can be cancelled if the button
  // unmounts (e.g. the selection changes) before it fires, avoiding a state
  // update on an unmounted component.
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  React.useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);
  return (
    <button
      type="button"
      aria-label={`Copy ${what}`}
      title={`Copy ${what}`}
      onClick={async (e) => {
        e.stopPropagation();
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          if (timeoutRef.current) clearTimeout(timeoutRef.current);
          timeoutRef.current = setTimeout(() => setCopied(false), 1200);
        } catch {
          toastWarning("Could not copy to clipboard.");
        }
      }}
      className="shrink-0 rounded p-0.5 text-muted-foreground opacity-60 transition hover:bg-foreground/10 hover:text-foreground hover:opacity-100"
    >
      {copied ? (
        <Check className="h-3 w-3" aria-hidden="true" />
      ) : (
        <Copy className="h-3 w-3" aria-hidden="true" />
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Tree node - render any JSON-like value as a key/value row, with children
// for plain-object values that get a collapsible <details>-like header.
// ---------------------------------------------------------------------------

function formatScalar(value: unknown): string {
  if (value === null || value === undefined) return String(value);
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function matchesFilter(key: string, value: unknown, query: string): boolean {
  if (!query) return true;
  const haystack = `${key} ${formatScalar(value)}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function AttributeRow({
  label,
  value,
  depth,
  query,
}: {
  label: string;
  value: unknown;
  depth: number;
  query: string;
}) {
  const isObject =
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value);

  const [open, setOpen] = React.useState<boolean>(true);

  if (isObject) {
    const entries = Object.entries(value as Record<string, unknown>);
    const childRows = entries
      .filter(([k, v]) => {
        // Keep parent if any descendant matches.
        if (!query) return true;
        const stack: Array<[string, unknown]> = [[k, v]];
        while (stack.length > 0) {
          const [ck, cv] = stack.pop()!;
          if (matchesFilter(ck, cv, query)) return true;
          if (cv && typeof cv === "object" && !Array.isArray(cv)) {
            for (const [nk, nv] of Object.entries(cv as Record<string, unknown>)) {
              stack.push([nk, nv]);
            }
          }
        }
        return false;
      })
      .map(([k, v]) => (
        <AttributeRow key={k} label={k} value={v} depth={depth + 1} query={query} />
      ));

    if (childRows.length === 0) return null;

    return (
      <div>
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          aria-expanded={open}
          style={{ paddingLeft: depth * 12 }}
          className="flex w-full items-center gap-1 rounded px-2 py-1 text-left text-xs font-semibold uppercase tracking-wide text-foreground hover:bg-foreground/5"
        >
          {open ? (
            <ChevronDown className="h-3 w-3 shrink-0" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0" aria-hidden="true" />
          )}
          <span>{label}</span>
        </button>
        {open && <div>{childRows}</div>}
      </div>
    );
  }

  if (!matchesFilter(label, value, query)) return null;

  const scalar = formatScalar(value);
  return (
    <div
      style={{ paddingLeft: depth * 12 + 18 }}
      className="grid grid-cols-[minmax(0,140px)_1fr] gap-3 px-2 py-1 text-xs"
    >
      <div className="flex min-w-0 items-center gap-1">
        <span className="truncate font-mono text-foreground/70" title={label}>
          {label}
        </span>
        <CopyButton text={label} what="key" />
      </div>
      <div className="flex min-w-0 items-center gap-1">
        <span className="min-w-0 break-all font-mono text-foreground" title={scalar}>
          {scalar}
        </span>
        <CopyButton text={scalar} what="value" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Title bar - drag/dock controls + close
// ---------------------------------------------------------------------------

const POSITION_LABELS: Record<AttributesPanelPosition, string> = {
  right: "Dock Right",
  bottom: "Dock Bottom",
  left: "Dock Left",
  top: "Dock Top",
};

const POSITION_ICONS: Record<
  AttributesPanelPosition,
  (props: { className?: string }) => React.JSX.Element
> = {
  right: (p) => <PanelRight {...p} />,
  bottom: (p) => <PanelBottom {...p} />,
  left: (p) => <PanelLeft {...p} />,
  top: (p) => <PanelTop {...p} />,
};

function PanelTitleBar({
  position,
  positions,
  setPosition,
  onClose,
  title,
  subtitle,
}: {
  position: AttributesPanelPosition;
  positions: AttributesPanelPosition[];
  setPosition: (next: AttributesPanelPosition) => void;
  onClose: () => void;
  title: string;
  subtitle?: string;
}) {
  const PositionIcon = POSITION_ICONS[position];
  return (
    <div className="flex items-center gap-2 border-b border-border bg-background/60 px-3 py-2 dark:border-zinc-800 dark:bg-zinc-900/60">
      <Layers3 className="h-4 w-4 shrink-0 text-foreground/70" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-foreground">{title}</p>
        {subtitle && (
          <p
            className="truncate text-xs text-muted-foreground"
            title={subtitle}
          >
            {subtitle}
          </p>
        )}
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label="Dock position"
            title="Dock position"
            className="rounded p-1 text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
          >
            <PositionIcon className="h-4 w-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[10rem]">
          <DropdownMenuLabel>Dock</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {positions.map((p) => {
            const Icon = POSITION_ICONS[p];
            const active = p === position;
            return (
              <DropdownMenuItem
                key={p}
                onSelect={() => setPosition(p)}
                className="cursor-pointer"
              >
                <Icon className="mr-2 h-4 w-4" />
                {POSITION_LABELS[p]}
                {active && <Pin className="ml-auto h-3.5 w-3.5" aria-hidden="true" />}
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      <button
        type="button"
        onClick={onClose}
        aria-label="Close Attributes panel"
        className="rounded p-1 text-foreground/70 transition-colors hover:bg-foreground/5 hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

function positionClasses(position: AttributesPanelPosition): string {
  // Pin below the 56-px (h-14) AppHeader; let each edge own the appropriate
  // dimension. Width / height kept moderate so the panel doesn't take over
  // the whole viewport.
  switch (position) {
    case "right":
      return "fixed right-0 top-14 bottom-6 w-80 max-w-[90vw] border-l";
    case "left":
      return "fixed left-0 top-14 bottom-6 w-80 max-w-[90vw] border-r";
    case "top":
      return "fixed top-14 left-0 right-0 h-72 max-h-[60vh] border-b";
    case "bottom":
      return "fixed bottom-6 left-0 right-0 h-72 max-h-[60vh] border-t";
  }
}

export function AttributesPanel() {
  const pathname = usePathname();
  const { isOpen, position, positions, setOpen, setPosition } =
    useAttributesPanel();
  const { selection } = useAttributeSelection();
  const [query, setQuery] = React.useState<string>("");

  // Hide on /login (no app chrome there at all).
  if (pathname?.startsWith("/login")) return null;
  if (!isOpen) return null;

  const title = selection
    ? `${selection.type[0].toUpperCase()}${selection.type.slice(1)} Attributes`
    : "Attributes";
  const subtitle = selection?.name;

  return (
    <aside
      role="complementary"
      aria-label="Attributes panel"
      data-position={position}
      className={cn(
        positionClasses(position),
        "z-30 flex flex-col overflow-hidden border-border bg-background shadow-lg dark:border-zinc-800 dark:bg-zinc-900",
      )}
    >
      <PanelTitleBar
        position={position}
        positions={positions}
        setPosition={setPosition}
        onClose={() => setOpen(false)}
        title={title}
        subtitle={subtitle}
      />

      <div className="border-b border-border px-3 py-2 dark:border-zinc-800">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter attributes…"
          aria-label="Filter attributes"
          className="h-8 w-full rounded-md border border-border bg-background px-2 text-xs text-foreground placeholder:text-muted-foreground focus:border-foreground/40 focus:outline-none dark:border-zinc-800 dark:bg-zinc-900"
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-1">
        {!selection ? (
          <div className="px-4 py-6 text-xs text-muted-foreground">
            <p className="mb-1 font-semibold text-foreground">No selection</p>
            <p>
              Click a row in the jobs table (or any future host / layer / frame
              table) to inspect its attributes here.
            </p>
          </div>
        ) : (
          <AttributeRow
            label={`${selection.type}: ${selection.name}`}
            value={selection.data}
            depth={0}
            query={query}
          />
        )}
      </div>
    </aside>
  );
}
