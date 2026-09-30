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
 * Minimal CueWeb plugin contract.
 *
 * This is the browser equivalent of the CueGUI plugin system
 * (`cuegui/cuegui/Plugins.py` and `cuegui/cuegui/cueguiplugin/loader.py`),
 * where each plugin module declares a small set of metadata fields
 * (PLUGIN_NAME, PLUGIN_DESCRIPTION, PLUGIN_PROVIDES, ...) and exposes a
 * class the host instantiates. Here a plugin instead declares a
 * {@link PluginManifest} and a lazy loader for a React component, so the
 * component's code is only fetched when its route is actually visited.
 *
 * To add a plugin:
 *   1. Create `app/plugins/<name>/` with a component (a default-exported
 *      React component accepting {@link PluginComponentProps}).
 *   2. Add a `manifest.ts` in that folder exporting a {@link PluginModule}
 *      whose `load` does `() => import("./<component>")`.
 *   3. Register the module in {@link PLUGIN_REGISTRY} below.
 *
 * The dynamic route at `app/plugins/[plugin-name]/page.tsx` resolves the
 * manifest by `name` and renders the lazily-loaded component.
 */

import type { ComponentType } from "react";

/**
 * Static, serializable description of a plugin. Mirrors the CueGUI
 * PLUGIN_NAME / PLUGIN_DESCRIPTION metadata, plus the route the plugin
 * mounts on in CueWeb.
 */
export interface PluginManifest {
  /**
   * Unique, URL-safe identifier. Used as the `[plugin-name]` route segment,
   * e.g. `name: "hello"` is served at `/plugins/hello`.
   */
  name: string;
  /** Human-readable display name shown in menus and headings. */
  title: string;
  /** Semantic version of the plugin, e.g. `"1.0.0"`. */
  version: string;
  /** Route the plugin is mounted on. By convention `/plugins/<name>`. */
  route: string;
  /** Optional one-line description shown in the plugin index. */
  description?: string;
  /**
   * Whether the plugin appears in the Plugins menu (sidebar + header) by
   * default, before the user customizes their selection on the plugins page.
   * With potentially many plugins, the menu only lists the user's chosen ones;
   * this seeds that choice.
   */
  defaultEnabled?: boolean;
}

/** Props every plugin component receives from the host. */
export interface PluginComponentProps {
  /** The manifest that resolved to this component. */
  manifest: PluginManifest;
}

/** A loadable React component implementing a plugin's UI. */
export type PluginComponent = ComponentType<PluginComponentProps>;

/**
 * A registered plugin: its manifest plus a lazy loader for the component.
 *
 * `load` must return a dynamic `import()` of a module whose default export
 * is the plugin component, e.g. `() => import("./hello-plugin")`. Keeping it
 * a static `import()` expression lets the bundler split the plugin into its
 * own chunk that is only fetched when the route is visited.
 */
export interface PluginModule {
  manifest: PluginManifest;
  load: () => Promise<{ default: PluginComponent }>;
}

// Statically import each plugin's manifest module. The manifests are tiny
// (metadata + a lazy `load` thunk); the component code itself is *not*
// pulled into this bundle because `load` is a deferred `import()`.
import { helloPlugin } from "@/app/plugins/hello/manifest";
import { cueProgressBarPlugin } from "@/app/plugins/cue-progress-bar/manifest";

/** All plugins known to CueWeb. Append new {@link PluginModule}s here. */
export const PLUGIN_REGISTRY: readonly PluginModule[] = [helloPlugin, cueProgressBarPlugin];

/** Return every registered plugin module. */
export function getPlugins(): readonly PluginModule[] {
  return PLUGIN_REGISTRY;
}

/** Resolve a plugin module by its manifest `name`, or `undefined`. */
export function getPlugin(name: string): PluginModule | undefined {
  return PLUGIN_REGISTRY.find((plugin) => plugin.manifest.name === name);
}

/* -------------------------------------------------------------------------- */
/* Plugins-menu selection                                                     */
/* -------------------------------------------------------------------------- */

/**
 * Which plugins appear in the Plugins menu (sidebar + header) is user-chosen
 * and persisted to `localStorage`, so the menu stays manageable when many
 * plugins are registered. The set of enabled plugin names is stored under
 * {@link PLUGIN_MENU_STORAGE_KEY}; until the user customizes it, the plugins
 * flagged `defaultEnabled` are shown.
 */
export const PLUGIN_MENU_STORAGE_KEY = "cueweb.plugin-menu.enabled";

/** Dispatched after the enabled-plugins selection changes. */
export const PLUGIN_MENU_CHANGED_EVENT = "cueweb:plugin-menu-changed";

/** Names of plugins shown in the menu out of the box (manifest `defaultEnabled`). */
export function getDefaultEnabledPluginNames(): string[] {
  return PLUGIN_REGISTRY.filter((plugin) => plugin.manifest.defaultEnabled).map(
    (plugin) => plugin.manifest.name,
  );
}

/**
 * Names of plugins the user has chosen to show in the menu. Falls back to the
 * defaults when nothing is stored or during SSR. Stale names (plugins no longer
 * registered) are filtered out.
 */
export function getEnabledPluginNames(): string[] {
  if (typeof window === "undefined") return getDefaultEnabledPluginNames();
  try {
    const raw = window.localStorage.getItem(PLUGIN_MENU_STORAGE_KEY);
    if (raw === null) return getDefaultEnabledPluginNames();
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) {
      const known = new Set(PLUGIN_REGISTRY.map((plugin) => plugin.manifest.name));
      return parsed.filter((name): name is string => typeof name === "string" && known.has(name));
    }
  } catch {
    // fall through to defaults
  }
  return getDefaultEnabledPluginNames();
}

/** Show or hide a plugin in the menu, then notify listeners. No-op during SSR. */
export function setPluginMenuEnabled(name: string, enabled: boolean): void {
  if (typeof window === "undefined") return;
  const current = new Set(getEnabledPluginNames());
  if (enabled) current.add(name);
  else current.delete(name);
  window.localStorage.setItem(PLUGIN_MENU_STORAGE_KEY, JSON.stringify(Array.from(current)));
  window.dispatchEvent(new CustomEvent(PLUGIN_MENU_CHANGED_EVENT));
}

/* -------------------------------------------------------------------------- */
/* Plugin settings registry                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Generic, persisted settings any plugin can register entries into. A plugin
 * calls {@link registerSetting} (typically at module load) to declare a
 * setting; the shared settings dialog
 * (`components/ui/settings-dialog.tsx`) renders every registered entry and
 * writes its value to `localStorage` under `cueweb.plugin-settings.<key>`, so
 * values survive a reload.
 */

/** Supported widget/value kinds for a setting. */
export type SettingKind = "boolean" | "string" | "number" | "select";

/** A persisted setting value. */
export type SettingValue = boolean | string | number;

/** An option for a `kind: "select"` setting. */
export interface SettingOption {
  label: string;
  value: string;
}

/** Declarative description of a single plugin setting. */
export interface SettingDefinition {
  /** Unique key. Stored at `cueweb.plugin-settings.<key>`. */
  key: string;
  /**
   * Name of the owning plugin (its manifest `name`). Lets the settings dialog
   * be scoped to a single plugin. Optional for settings not tied to a plugin.
   */
  plugin?: string;
  /** Human-readable label shown in the settings dialog. */
  label: string;
  /** Which control to render and how to (de)serialize the value. */
  kind: SettingKind;
  /** Value used when nothing has been persisted yet. */
  default: SettingValue;
  /** Optional helper text shown beneath the control. */
  description?: string;
  /** Choices for `kind: "select"`. Ignored for other kinds. */
  options?: SettingOption[];
}

/** Detail payload for {@link PLUGIN_SETTINGS_CHANGED_EVENT}. */
export interface SettingChangeDetail {
  key: string;
  value: SettingValue;
}

/**
 * Window event dispatched after a setting is written, so open plugin views can
 * react without polling `localStorage`.
 */
export const PLUGIN_SETTINGS_CHANGED_EVENT = "cueweb:plugin-settings-changed";

const SETTINGS_STORAGE_PREFIX = "cueweb.plugin-settings.";
const SETTINGS_REGISTRY = new Map<string, SettingDefinition>();

/** The `localStorage` key a setting is persisted under. */
export function settingStorageKey(key: string): string {
  return `${SETTINGS_STORAGE_PREFIX}${key}`;
}

/**
 * Register a setting. Idempotent per `key` (re-registering replaces the prior
 * definition), so it is safe to call at plugin-module load. Returns the
 * definition for convenient inline use.
 */
export function registerSetting(definition: SettingDefinition): SettingDefinition {
  SETTINGS_REGISTRY.set(definition.key, definition);
  return definition;
}

/** Every registered setting, in registration order. */
export function getRegisteredSettings(): SettingDefinition[] {
  return Array.from(SETTINGS_REGISTRY.values());
}

/** Look up a single registered setting by key. */
export function getSettingDefinition(key: string): SettingDefinition | undefined {
  return SETTINGS_REGISTRY.get(key);
}

/** Coerce an arbitrary parsed value to the kind the definition expects. */
function coerceSettingValue(definition: SettingDefinition, parsed: unknown): SettingValue {
  switch (definition.kind) {
    case "boolean":
      return typeof parsed === "boolean" ? parsed : definition.default;
    case "number":
      return typeof parsed === "number" && Number.isFinite(parsed) ? parsed : definition.default;
    case "string":
    case "select":
      return typeof parsed === "string" ? parsed : definition.default;
    default:
      return definition.default;
  }
}

/**
 * Read a setting's persisted value, falling back to its default when nothing
 * is stored, the stored value is corrupt, or called during SSR (no `window`).
 */
export function getSettingValue(definition: SettingDefinition): SettingValue {
  if (typeof window === "undefined") return definition.default;
  const raw = window.localStorage.getItem(settingStorageKey(definition.key));
  if (raw === null) return definition.default;
  try {
    return coerceSettingValue(definition, JSON.parse(raw) as unknown);
  } catch {
    return definition.default;
  }
}

/**
 * Persist a setting value and notify listeners via
 * {@link PLUGIN_SETTINGS_CHANGED_EVENT}. No-op during SSR.
 */
export function setSettingValue(key: string, value: SettingValue): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(settingStorageKey(key), JSON.stringify(value));
  window.dispatchEvent(
    new CustomEvent<SettingChangeDetail>(PLUGIN_SETTINGS_CHANGED_EVENT, {
      detail: { key, value },
    }),
  );
}

/** Remove a persisted value so the setting reverts to its default. */
export function resetSettingValue(key: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(settingStorageKey(key));
  const definition = SETTINGS_REGISTRY.get(key);
  window.dispatchEvent(
    new CustomEvent<SettingChangeDetail>(PLUGIN_SETTINGS_CHANGED_EVENT, {
      detail: { key, value: definition ? definition.default : "" },
    }),
  );
}
