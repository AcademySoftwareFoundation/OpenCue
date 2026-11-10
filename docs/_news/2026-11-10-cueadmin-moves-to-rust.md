---
layout: default
title: "November 10, 2026: CueAdmin Moves to Rust"
---

# CueAdmin Moves to Rust

### The Python cueadmin is deprecated in favor of a single-binary Rust rewrite with subcommands

#### November 10, 2026

---

The official **CueAdmin** now lives in the Rust workspace at
[`rust/crates/cueadmin`](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/rust/crates/cueadmin).
The Python `cueadmin` module is **deprecated**. It still works and will receive critical fixes, but
new features land only in the Rust version, and the Python module will be removed in a future
release.

The Rust version does everything the Python tool does. What changes is how you call it.

## Why

**Subcommands instead of a flat flag list.** The Python tool exposes everything as single-dash flags
on one command: `-lh`, `-host H -lock`, `-size SHOW ALLOC N`. Nothing stops you from combining
flags that don't make sense together, and some combinations silently do nothing. The new tool
follows a `cueadmin <noun> <verb>` layout, so each command takes only the arguments that apply to
it, and invalid combinations are rejected before anything reaches Cuebot.

**Real `--help` at every level.** `cueadmin --help`, `cueadmin host --help` and
`cueadmin host move --help` each document exactly what that level accepts, including value formats
and which commands ask for confirmation.

**One binary, no Python.** CueAdmin is an operator tool that tends to run on admin hosts, in
containers and in automation, and bundling a Python interpreter, pycue and its gRPC dependencies
there has been a recurring pain point. The Rust version is a single binary with no runtime
dependencies.

## What it looks like

Commands are grouped by what they act on: `show`, `alloc`, `subscription` (alias `sub`), `host`,
`job`, `proc` and `service`. Some examples:

| Python                              | Rust                                 |
|-------------------------------------|--------------------------------------|
| `cueadmin -ls`                      | `cueadmin show list`                 |
| `cueadmin -lh vrack -state UP`      | `cueadmin host list vrack --state up`|
| `cueadmin -hostmatch vrack -lock`   | `cueadmin host lock -m vrack`        |
| `cueadmin -host h1 h2 -move ALLOC`  | `cueadmin host move ALLOC h1 h2`     |
| `cueadmin -lb pipe`                 | `cueadmin sub list pipe`             |
| `cueadmin -kill JOB -force`         | `cueadmin job kill JOB --force`      |
| `cueadmin -lp pipe -memory gt8`     | `cueadmin proc list --show pipe --memory gt8` |
| `cueadmin -ll -job JOB`             | `cueadmin proc logs --job JOB`       |

The crate's
[README](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/rust/crates/cueadmin#migrating-from-the-python-tool)
maps every Python flag to its new command.

Things that stay the same:

- **Connection settings.** The Rust tool reads the same pycue config file (`OPENCUE_CONFIG_FILE`,
  `OPENCUE_CONF` or `~/.config/opencue/opencue.yaml`) and the same `CUEBOT_HOSTS` and
  `CUEBOT_FACILITY` variables. `--server` and `--facility` still override them.
- **Output.** Table columns match the Python tool, so scripts that parse `show list`, `host list`
  or `proc list` output keep working.
- **Confirmations.** Destructive commands still prompt, and `--force` (or `--yes`) still skips the
  prompt.

## Behavior changes to check before migrating

A few Python behaviors were bugs, and the Rust version fixes them. Check any scripts that depend on
them:

- **`sub size` and `sub burst` take cores.** The Python `-size` and `-burst` sent the raw value in
  core units (hundredths of a core), so `-size pipe alloc 100` set **one** core, unlike
  `-create-sub`, which took cores. The Rust commands take cores everywhere, matching
  `sub create`, `sub list` and CueGUI. A ported script that still passes core units will ask for a
  100x larger subscription, so both commands now confirm and show the old and new core counts.
- **`job retry` retries only dead frames,** as its help always said. The Python tool sent no state
  filter.
- **Blank host matches are rejected.** A stray empty value such as `-m vrack,` no longer turns into
  a match on every host in the farm.
- **An unknown `--facility` is an error.** The Python tool fell back to the default facility with a
  warning, which could point an admin command at the wrong farm.
- **Host commands take host names or `--match`, not both.**

## Getting it

Build it from the Rust workspace. You need a Rust toolchain and `protoc`, as for RQD:

```bash
cd OpenCue/rust
cargo build -r -p cueadmin
target/release/cueadmin --help
```

The [Rust README](https://github.com/AcademySoftwareFoundation/OpenCue/tree/master/rust) covers
installing `protoc` on macOS and Linux.

## What this means for you

**If you use CueAdmin interactively,** switch to the Rust binary and use `--help` as you go. Most
commands map one to one.

**If you have scripts that call CueAdmin,** port them using the README's migration table, and
check them against the behavior changes above, especially any use of `-size` or `-burst`.

**If you depend on the Python `cueadmin` package,** it keeps working for now. We will announce its
removal here ahead of time.

---

Questions or feedback:

- **Slack**: #opencue on [ASWF Slack](https://slack.aswf.io)
- **GitHub Discussions**: [OpenCue Discussions](https://github.com/AcademySoftwareFoundation/OpenCue/discussions)
