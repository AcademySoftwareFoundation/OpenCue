---
layout: default
title: "August 6, 2026: Log-Based Exit-Status Rules in Rust RQD"
parent: News
nav_order: 2
---

# Log-Based Exit-Status Rules in Rust RQD

### Reclassify failed frames by scanning their log output

#### August 6, 2026

---

The Rust RQD can now **reclassify a failed frame's exit status based on what appears in its log**. When a frame exits non-zero, RQD scans the tail of the frame log against a list of operator-defined regular expressions and, on the first match, reports a substitute exit status to Cuebot instead of the process's real exit code.

## The Challenge

Some failures are worth handling differently from a generic crash, but the render process doesn't always expose that intent through its exit code. A classic example is a **Houdini license shortage**: `hython` fails with a plain exit status `3`, and the only signal that it was a licensing problem is a message buried in the log:

```
A usable license to run the application is installed but they are all in use.
Please contact your companies license administrator to create availability
for your use or wait until there is availability to try again.
```

To Cuebot, that looks identical to any other exit-3 failure. Distinguishing it previously required editing the render wrapper on every show to translate the message into a dedicated exit code — brittle, and easy to get wrong across a large studio.

## The Solution

RQD now does the classification itself, driven entirely by configuration. When a frame fails, RQD reads the last `log_scan_last_lines` lines of the frame log and evaluates them top-to-bottom against `log_exit_status_rules`. The first rule whose `regex` matches wins, and its `exit_status` is what Cuebot receives — so operators can route license shortages (or any other recognizable failure) to different dispatcher handling without touching the render command.

### Configuration

Add the following to the `runner` section of your `rqd.yaml`:

```yaml
runner:
  # Number of trailing log lines scanned on failure (default: 50).
  log_scan_last_lines: 50

  # Ordered list of regex -> exit-status rules. First match wins.
  log_exit_status_rules:
    - name: "HOUDINI_LICENSE_ERROR"
      regex: "A usable license to run the application is installed but they are all in use"
      exit_status: 330
```

Key behaviors:

- **Opt-in and safe by default** — the feature is disabled when `log_exit_status_rules` is empty or `log_scan_last_lines` is `0`.
- **Only failed frames are scanned** — a successful (exit `0`) frame is never read, so there is no cost on the happy path.
- **First match wins** — rules are evaluated in order, letting you place more specific patterns above general ones.
- **Typo-tolerant** — an invalid regex is skipped with a warning rather than disabling the whole rule set.
- **Human-readable `name`** — used only in RQD's log messages to make matches easy to trace.

### Efficient by Design

The log tail is read **backward in fixed-size chunks**, stopping as soon as enough lines have been collected. For the default 50-line scan RQD typically touches only a few kilobytes near the end of the file — even for multi-megabyte frame logs — with a hard 1 MiB cap that guarantees a pathologically large log is never read in full. Scanning a failed frame's log adds negligible overhead to the completion path.

## Availability

Log-based exit-status rules are available now in the Rust RQD (`rust/crates/rqd/`). See the [Rust RQD reference](/docs/reference/rust-rqd/) for full configuration details, and the sample `rust/config/rqd.yaml` for a commented example.
