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
  buildBlenderCommand,
  buildLayerCommand,
  buildMayaCommand,
  buildNukeCommand,
  buildShellCommand,
} from "@/app/cuesubmit/lib/commands";
import { isSimpleRange, isValidFrameSpec } from "@/app/cuesubmit/lib/frame_spec";
import { buildJobSpecXml } from "@/app/cuesubmit/lib/spec_xml";
import type { LayerInput } from "@/app/cuesubmit/lib/schemas";

function blankLayer(over: Partial<LayerInput> = {}): LayerInput {
  return {
    name: "L1",
    frameSpec: "1-10",
    chunkSize: 1,
    jobType: "Shell",
    services: [],
    limits: [],
    overrideCores: false,
    cores: 0,
    memory: "",
    dependencyType: "",
    shell: { command: "" },
    maya: { mayaFile: "", camera: "" },
    nuke: { nukeFile: "", writeNodes: "" },
    blender: { blenderFile: "", outputPath: "", outputFormat: "" },
    ...over,
  };
}

describe("isValidFrameSpec", () => {
  test("accepts the common cuebot forms", () => {
    for (const ok of [
      "1",
      "1-10",
      "1-10x2",
      "1-10y3",
      "1-100:2",
      "1,2,3,4",
      "1-10,20-30",
      "1-50,75-100x5",
    ]) {
      expect(isValidFrameSpec(ok)).toBe(true);
    }
  });

  test("rejects malformed specs", () => {
    for (const bad of [
      "",
      " ",
      "abc",
      "1-10-20",
      "1-10x",
      "10-1", // start > end
      "1,-5",
      "1..3",
    ]) {
      expect(isValidFrameSpec(bad)).toBe(false);
    }
  });
});

describe("isSimpleRange", () => {
  test("only matches `N-M`", () => {
    expect(isSimpleRange("1-10")).toBe(true);
    expect(isSimpleRange("1-100x2")).toBe(false);
    expect(isSimpleRange("5")).toBe(false);
    expect(isSimpleRange("1,2,3")).toBe(false);
  });
});

describe("buildShellCommand", () => {
  test("returns the command verbatim, trimmed", () => {
    const layer = blankLayer({ shell: { command: "  echo hi  " } });
    expect(buildShellCommand(layer)).toBe("echo hi");
  });
});

describe("buildMayaCommand", () => {
  test("includes scene + frame range tokens, optional camera", () => {
    const layer = blankLayer({
      jobType: "Maya",
      maya: { mayaFile: "/path/scene.ma", camera: "renderCam" },
    });
    const cmd = buildMayaCommand(layer);
    expect(cmd).toContain("Render");
    expect(cmd).toContain("-r file");
    expect(cmd).toContain("-s #FRAME_START#");
    expect(cmd).toContain("-e #FRAME_END#");
    expect(cmd).toContain("-cam renderCam");
    expect(cmd).toContain("/path/scene.ma");
  });

  test("omits camera when not set", () => {
    const layer = blankLayer({
      jobType: "Maya",
      maya: { mayaFile: "/path/scene.ma", camera: "" },
    });
    expect(buildMayaCommand(layer)).not.toContain("-cam");
  });
});

describe("buildNukeCommand", () => {
  test("includes per-frame token + optional write nodes", () => {
    const layer = blankLayer({
      jobType: "Nuke",
      nuke: { nukeFile: "/path/script.nk", writeNodes: "Write1,Write2" },
    });
    const cmd = buildNukeCommand(layer);
    expect(cmd).toContain("nuke");
    expect(cmd).toContain("-F #IFRAME#");
    expect(cmd).toContain("-X Write1,Write2");
    expect(cmd).toContain("-x /path/script.nk");
  });
});

describe("buildBlenderCommand", () => {
  test("simple range uses -s/-e/-a", () => {
    const layer = blankLayer({
      jobType: "Blender",
      frameSpec: "1-10",
      blender: { blenderFile: "/path/scene.blend", outputPath: "/out/####", outputFormat: "PNG" },
    });
    const cmd = buildBlenderCommand(layer);
    expect(cmd).toContain("blender -b -noaudio");
    expect(cmd).toContain("/path/scene.blend");
    expect(cmd).toContain("-o /out/####");
    expect(cmd).toContain("-F PNG");
    expect(cmd).toContain("-s #FRAME_START#");
    expect(cmd).toContain("-e #FRAME_END#");
    expect(cmd).toContain("-a");
    expect(cmd).not.toContain("-f #IFRAME#");
  });

  test("non-simple range falls back to per-frame -f token", () => {
    const layer = blankLayer({
      jobType: "Blender",
      frameSpec: "1-100x2",
      blender: { blenderFile: "/path/scene.blend", outputPath: "", outputFormat: "" },
    });
    const cmd = buildBlenderCommand(layer);
    expect(cmd).toContain("-f #IFRAME#");
    expect(cmd).not.toContain("-a");
  });
});

describe("buildLayerCommand silent vs strict", () => {
  test("strict throws on Shell layer with empty command", () => {
    expect(() =>
      buildLayerCommand(blankLayer({ jobType: "Shell" }), { silent: false }),
    ).toThrow(/missing a command/);
  });

  test("silent does not throw on missing fields", () => {
    // Maya in silent mode still builds the command; missing scene
    // file surfaces as an empty scene-file slot rather than an
    // exception. The live preview in the page depends on this.
    const out = buildLayerCommand(
      blankLayer({ jobType: "Maya", maya: { mayaFile: "", camera: "" } }),
      { silent: true },
    );
    expect(typeof out).toBe("string");
  });

  test("Shell silent mirrors Command To Run verbatim (or empty)", () => {
    // Mirrors cuesubmit Python: the Final command box just echoes the
    // Command To Run text. Empty in -> empty out, no sentinel.
    expect(
      buildLayerCommand(blankLayer({ jobType: "Shell" }), { silent: true }),
    ).toBe("");
    expect(
      buildLayerCommand(
        blankLayer({ jobType: "Shell", shell: { command: "  sleep 10  " } }),
        { silent: true },
      ),
    ).toBe("sleep 10");
  });
});

describe("buildJobSpecXml", () => {
  function baseJob() {
    return {
      name: "test_job",
      show: "test_show",
      shot: "test_shot",
      facility: "local",
      user: "tester",
    };
  }

  test("emits the standard cjsl preamble + job element", () => {
    const xml = buildJobSpecXml(baseJob(), [
      blankLayer({ shell: { command: "echo hi" } }),
    ]);
    expect(xml).toMatch(/^<\?xml version="1\.0"\?>/);
    expect(xml).toContain('<!DOCTYPE spec');
    expect(xml).toContain('<job name="test_job">');
    expect(xml).toContain("<show>test_show</show>");
    expect(xml).toContain("<shot>test_shot</shot>");
    expect(xml).toContain("<user>tester</user>");
    expect(xml).toContain("<facility>local</facility>");
  });

  test("uid is non-zero and stable per username (cuebot rejects root)", () => {
    // Two submissions by the same user share a UID; different users
    // get different UIDs; never zero. Guards against the regression
    // where cuebot rejected our spec with "Cannot launch jobs as root".
    const xmlA = buildJobSpecXml(baseJob(), [
      blankLayer({ shell: { command: "echo a" } }),
    ]);
    const xmlB = buildJobSpecXml(baseJob(), [
      blankLayer({ shell: { command: "echo b" } }),
    ]);
    const uidA = /<uid>(\d+)<\/uid>/.exec(xmlA)?.[1];
    const uidB = /<uid>(\d+)<\/uid>/.exec(xmlB)?.[1];
    expect(uidA).toBeDefined();
    expect(uidA).toBe(uidB);
    expect(Number(uidA)).toBeGreaterThanOrEqual(1000);

    const xmlC = buildJobSpecXml(
      { ...baseJob(), user: "different_user" },
      [blankLayer({ shell: { command: "echo c" } })],
    );
    const uidC = /<uid>(\d+)<\/uid>/.exec(xmlC)?.[1];
    expect(uidC).not.toBe(uidA);
    expect(Number(uidC)).not.toBe(0);
  });

  test("each layer block has cmd, range, chunk, services", () => {
    const xml = buildJobSpecXml(baseJob(), [
      blankLayer({
        name: "render",
        frameSpec: "1-10",
        chunkSize: 5,
        services: ["arnold"],
        shell: { command: "echo hi" },
      }),
    ]);
    expect(xml).toContain('<layer name="render" type="Render">');
    expect(xml).toContain("<cmd>echo hi</cmd>");
    expect(xml).toContain("<range>1-10</range>");
    expect(xml).toContain("<chunk>5</chunk>");
    expect(xml).toContain("<service>arnold</service>");
  });

  test("defaults to the `default` service when none picked", () => {
    const xml = buildJobSpecXml(baseJob(), [
      blankLayer({ services: [], shell: { command: "echo hi" } }),
    ]);
    expect(xml).toContain("<service>default</service>");
  });

  test("overrideCores emits <cores> with one decimal place", () => {
    const xml = buildJobSpecXml(baseJob(), [
      blankLayer({
        overrideCores: true,
        cores: 4,
        shell: { command: "echo hi" },
      }),
    ]);
    expect(xml).toContain("<cores>4.0</cores>");
    // 4 cores >= 2 -> threadable True (mirrors cuesubmit's heuristic)
    expect(xml).toContain("<threadable>True</threadable>");
  });

  test("escapes XML-special characters in user-supplied strings", () => {
    const xml = buildJobSpecXml(
      { ...baseJob(), shot: 'shot<"&\'>' },
      [blankLayer({ shell: { command: "echo hi" } })],
    );
    expect(xml).toContain("shot&lt;&quot;&amp;&apos;&gt;");
  });

  test("defaults facility to 'local' when the form is set to [Default]", () => {
    // Empty form facility -> we still emit <facility>local</facility>.
    // Omitting the element entirely makes cuebot fall back to "cloud"
    // in the seeded sandbox, which never matches the RQD's local
    // allocation - so frames sit in WAITING. Regression guard.
    const xml = buildJobSpecXml({ ...baseJob(), facility: "" }, [
      blankLayer({ shell: { command: "echo hi" } }),
    ]);
    expect(xml).toContain("<facility>local</facility>");
  });

  test("respects an explicit non-default facility", () => {
    const xml = buildJobSpecXml({ ...baseJob(), facility: "cloud" }, [
      blankLayer({ shell: { command: "echo hi" } }),
    ]);
    expect(xml).toContain("<facility>cloud</facility>");
  });

  test("memory is emitted when set, omitted when empty", () => {
    // Empty memory -> no <memory> element (cuebot inherits the
    // service's int_mem_min). This is the path that historically left
    // jobs stuck in WAITING because the default service requires 3.2GB.
    const xmlEmpty = buildJobSpecXml(baseJob(), [
      blankLayer({ shell: { command: "echo hi" } }),
    ]);
    expect(xmlEmpty).not.toContain("<memory>");

    // With a real value it shows up verbatim so cuebot can parse "256m"
    // or "1g" without us trying to normalize units.
    const xml = buildJobSpecXml(baseJob(), [
      blankLayer({
        memory: "256m",
        shell: { command: "echo hi" },
      }),
    ]);
    expect(xml).toContain("<memory>256m</memory>");
  });

  test("emits a depend block for layers with dependencyType set", () => {
    const xml = buildJobSpecXml(baseJob(), [
      blankLayer({ name: "preview", shell: { command: "echo a" } }),
      blankLayer({
        name: "final",
        shell: { command: "echo b" },
        dependencyType: "Layer",
      }),
    ]);
    expect(xml).toContain("<depend ");
    expect(xml).toContain('type="LAYER_ON_LAYER"');
    expect(xml).toContain("<deplayer>preview</deplayer>");
    expect(xml).toContain("<onlayer>final</onlayer>");
  });

  test("omits <depends> body when no layer has dependencyType set", () => {
    const xml = buildJobSpecXml(baseJob(), [
      blankLayer({ shell: { command: "echo hi" } }),
    ]);
    expect(xml).toContain("<depends/>");
  });
});
