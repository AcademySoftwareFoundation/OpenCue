"use client";

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

import * as React from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  getPlugin,
  getRegisteredSettings,
  getSettingValue,
  PLUGIN_SETTINGS_CHANGED_EVENT,
  setSettingValue,
  type SettingChangeDetail,
  type SettingDefinition,
  type SettingValue,
} from "@/lib/plugins";

/**
 * Generic plugin settings dialog. Mounted once (see `app/layout.tsx`) and
 * opened by dispatching {@link OPEN_PLUGIN_SETTINGS_EVENT}. It persists edits to
 * `localStorage` (keys `cueweb.plugin-settings.<key>`), so values survive a
 * reload.
 *
 * The event's `detail.plugin` scopes the dialog to a single plugin's settings;
 * omit it to show every registered setting. Use {@link openPluginSettings}:
 *
 *   openPluginSettings(manifest.name); // just this plugin's settings
 *   openPluginSettings();              // all registered settings
 */
export const OPEN_PLUGIN_SETTINGS_EVENT = "cueweb:open-plugin-settings";

/** Detail payload for {@link OPEN_PLUGIN_SETTINGS_EVENT}. */
interface OpenPluginSettingsDetail {
  /** Owning plugin name to scope to; undefined shows all settings. */
  plugin?: string;
}

/** Read the current value of every registered setting into a draft map. */
function readDraft(definitions: SettingDefinition[]): Record<string, SettingValue> {
  const draft: Record<string, SettingValue> = {};
  for (const definition of definitions) {
    draft[definition.key] = getSettingValue(definition);
  }
  return draft;
}

export function PluginSettingsDialog() {
  const [open, setOpen] = React.useState(false);
  // Snapshot of the registry taken when the dialog opens. The registry is a
  // plain module-level map, so we re-read it on every open to pick up settings
  // registered by plugins that have since loaded.
  const [definitions, setDefinitions] = React.useState<SettingDefinition[]>([]);
  const [draft, setDraft] = React.useState<Record<string, SettingValue>>({});
  // Title reflects the scope: a single plugin's name, or generic when showing
  // all settings.
  const [title, setTitle] = React.useState("Plugin Settings");

  React.useEffect(() => {
    function handleOpen(event: Event) {
      const plugin = (event as CustomEvent<OpenPluginSettingsDetail>).detail?.plugin;
      const registered = getRegisteredSettings();
      const scoped = plugin ? registered.filter((s) => s.plugin === plugin) : registered;
      setDefinitions(scoped);
      setDraft(readDraft(scoped));
      setTitle(plugin ? `${getPlugin(plugin)?.manifest.title ?? plugin} Settings` : "Plugin Settings");
      setOpen(true);
    }
    window.addEventListener(OPEN_PLUGIN_SETTINGS_EVENT, handleOpen);
    return () => window.removeEventListener(OPEN_PLUGIN_SETTINGS_EVENT, handleOpen);
  }, []);

  function updateDraft(key: string, value: SettingValue) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function handleSave() {
    for (const definition of definitions) {
      setSettingValue(definition.key, draft[definition.key]);
    }
    setOpen(false);
  }

  function handleResetToDefaults() {
    const reset: Record<string, SettingValue> = {};
    for (const definition of definitions) {
      reset[definition.key] = definition.default;
    }
    setDraft(reset);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Preferences registered by plugins. Changes are saved to this browser.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[60vh] space-y-5 overflow-y-auto py-2">
          {definitions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No plugin settings are registered yet.</p>
          ) : (
            definitions.map((definition) => (
              <SettingField
                key={definition.key}
                definition={definition}
                value={draft[definition.key]}
                onChange={(value) => updateDraft(definition.key, value)}
              />
            ))
          )}
        </div>

        <DialogFooter className="sm:justify-between">
          <Button
            type="button"
            variant="ghost"
            onClick={handleResetToDefaults}
            disabled={definitions.length === 0}
          >
            Reset to defaults
          </Button>
          <div className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="button" onClick={handleSave} disabled={definitions.length === 0}>
              Save
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Renders the appropriate control for a single setting's `kind`. */
function SettingField({
  definition,
  value,
  onChange,
}: {
  definition: SettingDefinition;
  value: SettingValue;
  onChange: (value: SettingValue) => void;
}) {
  const controlId = `plugin-setting-${definition.key}`;

  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <Label htmlFor={controlId}>{definition.label}</Label>
        {definition.description && (
          <p className="mt-0.5 text-xs text-muted-foreground">{definition.description}</p>
        )}
      </div>

      <div className="shrink-0">
        {definition.kind === "boolean" && (
          <Switch
            id={controlId}
            checked={Boolean(value)}
            onCheckedChange={(checked) => onChange(checked)}
          />
        )}

        {definition.kind === "string" && (
          <Input
            id={controlId}
            className="w-48"
            value={String(value ?? "")}
            onChange={(event) => onChange(event.target.value)}
          />
        )}

        {definition.kind === "number" && (
          <Input
            id={controlId}
            type="number"
            className="w-28 text-right font-mono"
            value={Number.isFinite(Number(value)) ? String(value) : ""}
            onChange={(event) => {
              const next = Number(event.target.value);
              onChange(Number.isFinite(next) ? next : (definition.default as number));
            }}
          />
        )}

        {definition.kind === "select" && (
          <Select value={String(value ?? "")} onValueChange={(next) => onChange(next)}>
            <SelectTrigger id={controlId} className="w-48">
              <SelectValue placeholder="Select…" />
            </SelectTrigger>
            <SelectContent>
              {(definition.options ?? []).map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
    </div>
  );
}

/**
 * Imperatively open the shared plugin settings dialog. Pass a plugin name (its
 * manifest `name`) to scope the dialog to that plugin's settings; omit it to
 * show every registered setting.
 */
export function openPluginSettings(plugin?: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<OpenPluginSettingsDetail>(OPEN_PLUGIN_SETTINGS_EVENT, {
      detail: { plugin },
    }),
  );
}

/**
 * Subscribe to a single setting's persisted value. Returns the current value
 * and re-renders when it changes (in this or another tab). Plugins use this to
 * read their settings reactively.
 */
export function usePluginSetting(definition: SettingDefinition): SettingValue {
  const [value, setValue] = React.useState<SettingValue>(definition.default);

  React.useEffect(() => {
    // Hydrate from localStorage on mount (avoids an SSR/client mismatch since
    // the initial render uses the default).
    setValue(getSettingValue(definition));

    function handleChange(event: Event) {
      const detail = (event as CustomEvent<SettingChangeDetail>).detail;
      if (detail?.key === definition.key) setValue(detail.value);
    }
    // `storage` fires for changes made in other tabs.
    function handleStorage(event: StorageEvent) {
      if (event.key === `cueweb.plugin-settings.${definition.key}`) {
        setValue(getSettingValue(definition));
      }
    }
    window.addEventListener(PLUGIN_SETTINGS_CHANGED_EVENT, handleChange);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener(PLUGIN_SETTINGS_CHANGED_EVENT, handleChange);
      window.removeEventListener("storage", handleStorage);
    };
    // definition is module-stable; key/default are what matter.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [definition.key]);

  return value;
}
