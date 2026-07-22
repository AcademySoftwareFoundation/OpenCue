# Building & running cuebot in this dev box (hard-won notes)

This box has a toolchain trap. These are the exact steps that work.

## The toolchain trap
- The repo pins **Gradle 7.6.2** (cuebot/gradle/wrapper). It does NOT run on the
  box's default **JDK 21** ("Unsupported class file major version 65" — bundled
  ASM too old). The standalone **Gradle 8.14.3** in /opt runs on 21 but is too
  new for the Spring Boot 2.2.1 plugin ("ArchivePublishArtifact").
- Correct combo: **wrapper Gradle 7.6.2 + JDK 17**.

## JDK 17 (with the proxy CA)
A vanilla JDK 17 download can't fetch deps: the env's outbound proxy uses a TLS
CA that vanilla cacerts don't trust (Gradle reports "plugin not found"). Fix:
copy the managed JDK 21 truststore into the JDK 17.
```
# /tmp/jdk-17.0.2 was unpacked from openjdk-17.0.2_linux-x64; then:
cp /usr/lib/jvm/java-21-openjdk-amd64/lib/security/cacerts /tmp/jdk-17.0.2/lib/security/cacerts
```

## Repos: drop the dead ones (build-time only, do NOT commit)
cuebot/settings.gradle (pluginManagement) and build.gradle list `jcenter()` and
`repo.spring.io/plugins-snapshot`, which are dead and break resolution on 7.6.2.
Strip them before building:
```
# in cuebot/: remove the 'maven { url ".../plugins-snapshot" }' line and 'jcenter()' lines
```

## Postgres (must run as non-root; refuses root)
```
# run these as your own (non-root) user; postgres refuses root, no sudo needed
PGBIN=/usr/lib/postgresql/16/bin
rm -rf /tmp/pgdata && mkdir -p /tmp/pgdata /tmp/pgrun
$PGBIN/initdb -D /tmp/pgdata -U cue --auth=trust
$PGBIN/pg_ctl -D /tmp/pgdata -o "-p 5433 -k /tmp/pgrun -c listen_addresses=127.0.0.1" -l /tmp/pg.log start
$PGBIN/psql -h127.0.0.1 -p5433 -Ucue -dpostgres -c "CREATE DATABASE cuebot;"
# apply migrations in version order:
cd cuebot/src/main/resources/conf/ddl/postgres/migrations
for f in $(ls *.sql | sort -t_ -k1.2 -n); do $PGBIN/psql -h127.0.0.1 -p5433 -Ucue -dcuebot -v ON_ERROR_STOP=1 -q -f "$f"; done
# base data: dept/services/config from seed_data.sql + scheduler-sim/sim_seed.sql
```

## Build / run cuebot (as your own user, JDK 17, wrapper 7.6.2)
A dedicated gradle home /tmp/ghome-$USER holds the resolved deps. Build as the
user that owns the checkout (a fresh `git clone` already is); no specific account
is required. Remove cuebot/.gradle if you hit `checksums.lock (Permission denied)`.
```
cd cuebot && env \
  CUEBOT_DB_URL="jdbc:postgresql://127.0.0.1:5433/cuebot" CUEBOT_DB_USER=cue CUEBOT_DB_PASSWORD= \
  SCHEDULER_ENABLED=true SCHEDULER_INTERVAL_MS=250 SCHEDULER_RESERVATIONS_ENABLED=false \
  ./gradlew bootRun -g /tmp/ghome-$USER -Dorg.gradle.java.home=/tmp/jdk-17.0.2 --console=plain >/tmp/cuebot.log 2>&1
```
gRPC serves on **8443**. Compile-only check: swap `bootRun` for `compileJava`
(note `-Werror -Xlint:all` is on — warnings fail the build). Unit tests:
`./gradlew test --tests "...SchedulerTests"`.

## CRITICAL launch pattern (process management)
Launch long-running procs (cuebot, pinger, fake_rqd) with the Bash tool's
`run_in_background: true` and **NO inner `&`**. An inner `&` double-backgrounds
and the JVM/Python gets SIGKILLed when the wrapper shell exits.
After a cuebot restart, restart status_pinger.py too (its gRPC channel goes
stale -> all ReportStatus fail -> hosts age to DOWN).

## Reset the farm between runs
```
psql ... -c "DELETE FROM proc;"
psql ... -c "UPDATE host SET int_cores_idle=int_cores,int_mem_idle=int_mem,int_gpus_idle=int_gpus,int_gpu_mem_idle=int_gpu_mem;"
psql ... -c "UPDATE subscription SET int_cores=0,int_gpus=0;"
# clear the job backlog (frames then layers) for the sim show:
psql ... -c "DELETE FROM frame f USING job j WHERE f.pk_job=j.pk_job AND j.pk_show='10000000-0000-0000-0000-000000000003';"
psql ... -c "DELETE FROM layer l USING job j WHERE l.pk_job=j.pk_job AND j.pk_show='10000000-0000-0000-0000-000000000003';"
```

## Gotcha: "unable to allocate additional memory"
That is NOT a Postgres OOM. It's `trigger__verify_host_resources` raising when a
booking pushes a host's int_*_idle below 0 (overbooking protection). Treat it as
an overbooking/accounting signal, not a memory problem.
```
