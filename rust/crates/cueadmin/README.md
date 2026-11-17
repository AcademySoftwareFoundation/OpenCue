# cueadmin

Rust rewrite of the Python [`cueadmin`](../../../cueadmin) OpenCue administration tool. It ships as a
single static binary with no Python or pycue dependency.

Commands follow a `cueadmin <noun> <verb>` layout. `cueadmin --help`, `cueadmin <noun> --help` and
`cueadmin <noun> <verb> --help` document every command and option.

```bash
cargo build -r -p cueadmin
target/release/cueadmin --help
```

## Connecting

The Cuebot address is resolved in this order:

1. `--server HOST[:PORT]` (repeat it or separate addresses with commas)
2. `--facility CODE`, looked up under `cuebot.facility` in the config file
3. `CUEBOT_HOSTS`, comma separated
4. `CUEBOT_FACILITY`, then `cuebot.facility_default` from the config file

The config file is the one pycue reads: `$OPENCUE_CONFIG_FILE`, `$OPENCUE_CONF`, or
`~/.config/opencue/opencue.yaml`. The keys used are `cuebot.facility`, `cuebot.facility_default`,
`cuebot.grpc_port`, `cuebot.timeout` and `cuebot.max_message_bytes`.

Global options (`--server`, `--facility`, `-v/--verbose`, `-f/--force`, `--raw`, `--pretty`) can
go anywhere on the command line. `CUEADMIN_LOG` takes a `tracing` filter for finer logging control.

## Output

By default (`--pretty`) lists print as boxed tables with humanized values (`2.0G`, `3d 4h`), a
totals row where numbers add up, and a count footer. Commands that change something print one
`✓` line per item as it completes. Color is used only when stdout is a terminal and `NO_COLOR` is
unset. `host list`, `job list` and `proc list` take `-w/--wide` for extra columns.

`--raw` is for scripts: a header line of column keys, then tab-separated rows with every column,
nothing truncated, and exact values (memory in KB, times in epoch seconds, durations in seconds,
`true`/`false`). Mutating commands print nothing on success. `--pretty` wins when both are given,
so an alias that adds `--raw` can be overridden per call.

```bash
cueadmin host list --raw | awk -F'\t' 'NR > 1 && $2 == "DOWN" { print $1 }'
```

## Migrating from the Python tool

| Python                                        | Rust                                                 |
|-----------------------------------------------|------------------------------------------------------|
| `-ls`                                         | `show list`                                          |
| `-create-show SHOW`                           | `show create SHOW`                                   |
| `-delete-show SHOW`                           | `show delete SHOW`                                   |
| `-enable-show SHOW` / `-disable-show SHOW`    | `show enable SHOW` / `show disable SHOW`             |
| `-dispatching SHOW on\|off`                   | `show dispatching SHOW on\|off`                      |
| `-booking SHOW on\|off`                       | `show booking SHOW on\|off`                          |
| `-default-min-cores SHOW N`                   | `show default-min-cores SHOW N`                      |
| `-default-max-cores SHOW N`                   | `show default-max-cores SHOW N`                      |
| `-archive-show SHOW TARGET`                   | `show archive SHOW TARGET`                           |
| `-scheduler-managed SHOW on\|off`             | `show scheduler-managed SHOW on\|off`                |
| `-la`                                         | `alloc list`                                         |
| `-create-alloc FAC NAME TAG`                  | `alloc create FAC NAME TAG`                          |
| `-delete-alloc ALLOC`                         | `alloc delete ALLOC`                                 |
| `-rename-alloc OLD NEW`                       | `alloc rename OLD NEW`                               |
| `-transfer SRC DST`                           | `alloc transfer SRC DST`                             |
| `-tag-alloc ALLOC TAG`                        | `alloc tag ALLOC TAG`                                |
| `-lb SHOW...`                                 | `sub list SHOW...`                                   |
| `-lba ALLOC`                                  | `sub list --alloc ALLOC`                             |
| `-create-sub SHOW ALLOC SIZE BURST`           | `sub create SHOW ALLOC SIZE BURST`                   |
| `-delete-sub SHOW ALLOC`                      | `sub delete SHOW ALLOC`                              |
| `-size SHOW ALLOC SIZE`                       | `sub size SHOW ALLOC CORES` (see below)              |
| `-burst SHOW ALLOC BURST[%]`                  | `sub burst SHOW ALLOC CORES[%]` (see below)          |
| `-lh [SUBSTR...] -state S -alloc A`           | `host list [SUBSTR...] --state S --alloc A`          |
| `-lh -lock-state S -sort-idle`                | `host list --lock-state S --sort-idle`               |
| `-host H... -lock` / `-hostmatch M -lock`     | `host lock H...` / `host lock -m M`                  |
| `-host H... -unlock`                          | `host unlock H...`                                   |
| `-host H... -move ALLOC`                      | `host move ALLOC H...`                               |
| `-host H... -delete-host`                     | `host delete H...`                                   |
| `-host H... -safe-reboot`                     | `host safe-reboot H...`                              |
| `-host H... -repair` / `-fixed`               | `host repair H...` / `host up H...`                  |
| `-host H... -thread MODE`                     | `host thread-mode MODE H...`                         |
| `-lj [SUBSTR...]` / `-lji [SUBSTR...]`        | `job list [SUBSTR...]` / `job list -w [SUBSTR...]`   |
| `-pause JOB...` / `-unpause JOB...`           | `job pause JOB...` / `job resume JOB...`             |
| `-kill JOB...` / `-kill-all`                  | `job kill JOB...` / `job kill --all`                 |
| `-retry JOB...` / `-retry-all`                | `job retry JOB...` / `job retry --all`               |
| `-drop-depends JOB...`                        | `job drop-depends JOB...`                            |
| `-set-min-cores JOB N` / `-set-max-cores`     | `job min-cores JOB N` / `job max-cores JOB N`        |
| `-priority JOB N`                             | `job priority JOB N`                                 |
| `-lp [SHOW...] -host -alloc -job -memory ...` | `proc list --show ... --host ... --memory ...`       |
| `-ll [SHOW...] ...`                           | `proc logs --show ...`                               |
| `-lv [SHOW]`                                  | `service list [--show SHOW]`                         |
| `-force`                                      | `-f` / `--force` / `--yes`                           |

### Behavior changes

- Output is formatted for people by default, so scripts that parsed the Python tool's columns
  need `--raw`, which prints tab-separated values with a header (see [Output](#output)).
- `job list` prints a table instead of bare names. Use `job list --raw | cut -f1 | tail -n +2`
  for names only.

- `sub size` and `sub burst` take cores, like `sub create` and the `sub list` output. The Python
  tool sent the raw value as core units (hundredths of a core), so `-size pipe alloc 100` set one
  core. Both commands now ask for confirmation and show the old and new core counts.
- Blank `--match` values (e.g. from `-m vrack,`) are dropped instead of matching every host.
- `job retry` retries only dead frames, as documented. The Python tool sent no state filter.
- An unknown `--facility` is an error instead of silently falling back to the default facility.
- With `--server`, an unreadable config file is ignored with a warning instead of failing.
- `host` commands take either host names or `--match`, not both.
- `alloc rename` accepts the new name with or without the facility prefix.
- `service list` shows minimum memory with a unit (`3.2G`) instead of the raw KB value labelled MB,
  and minimum cores in cores instead of core units.
- `job kill` takes an optional `--reason`.
