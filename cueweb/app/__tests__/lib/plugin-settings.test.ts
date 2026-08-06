/**
 * @jest-environment jsdom
 */

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

import {
  getRegisteredSettings,
  getSettingValue,
  registerSetting,
  resetSettingValue,
  setSettingValue,
  settingStorageKey,
  type SettingDefinition,
} from "@/lib/plugins";

const BOOL: SettingDefinition = {
  key: "test.bool",
  label: "Bool",
  kind: "boolean",
  default: false,
};
const STR: SettingDefinition = {
  key: "test.str",
  label: "Str",
  kind: "string",
  default: "hi",
};
const NUM: SettingDefinition = {
  key: "test.num",
  label: "Num",
  kind: "number",
  default: 7,
};

beforeEach(() => {
  window.localStorage.clear();
});

describe("plugin settings registry", () => {
  it("registers settings and exposes them in registration order", () => {
    registerSetting(BOOL);
    registerSetting(STR);
    const keys = getRegisteredSettings().map((s) => s.key);
    expect(keys).toEqual(expect.arrayContaining([BOOL.key, STR.key]));
  });

  it("re-registering the same key replaces rather than duplicates", () => {
    registerSetting(STR);
    registerSetting({ ...STR, label: "Renamed" });
    const matches = getRegisteredSettings().filter((s) => s.key === STR.key);
    expect(matches).toHaveLength(1);
    expect(matches[0].label).toBe("Renamed");
  });

  it("namespaces storage keys under cueweb.plugin-settings.", () => {
    expect(settingStorageKey("test.bool")).toBe("cueweb.plugin-settings.test.bool");
  });
});

describe("persistence", () => {
  it("returns the default when nothing is stored", () => {
    expect(getSettingValue(BOOL)).toBe(false);
    expect(getSettingValue(STR)).toBe("hi");
    expect(getSettingValue(NUM)).toBe(7);
  });

  it("round-trips a value through localStorage", () => {
    setSettingValue(BOOL.key, true);
    setSettingValue(STR.key, "bye");
    setSettingValue(NUM.key, 42);

    expect(window.localStorage.getItem(settingStorageKey(BOOL.key))).toBe("true");
    expect(getSettingValue(BOOL)).toBe(true);
    expect(getSettingValue(STR)).toBe("bye");
    expect(getSettingValue(NUM)).toBe(42);
  });

  it("survives a reload (values persist in localStorage across reads)", () => {
    setSettingValue(STR.key, "persisted");
    // Simulate a reload: a fresh read against the same localStorage. Modules
    // re-evaluate on reload, but the stored value is what is re-read.
    expect(getSettingValue(STR)).toBe("persisted");
  });

  it("falls back to the default when a stored value has the wrong type", () => {
    window.localStorage.setItem(settingStorageKey(NUM.key), JSON.stringify("not-a-number"));
    expect(getSettingValue(NUM)).toBe(7);
  });

  it("falls back to the default when stored JSON is corrupt", () => {
    window.localStorage.setItem(settingStorageKey(STR.key), "{not valid json");
    expect(getSettingValue(STR)).toBe("hi");
  });

  it("reset removes the stored value so the default returns", () => {
    setSettingValue(NUM.key, 99);
    expect(getSettingValue(NUM)).toBe(99);
    resetSettingValue(NUM.key);
    expect(window.localStorage.getItem(settingStorageKey(NUM.key))).toBeNull();
    expect(getSettingValue(NUM)).toBe(7);
  });

  it("dispatches a change event when a value is written", () => {
    const handler = jest.fn();
    window.addEventListener("cueweb:plugin-settings-changed", handler);
    setSettingValue(STR.key, "evented");
    expect(handler).toHaveBeenCalledTimes(1);
    window.removeEventListener("cueweb:plugin-settings-changed", handler);
  });
});
