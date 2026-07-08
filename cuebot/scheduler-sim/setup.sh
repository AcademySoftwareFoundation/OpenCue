#!/usr/bin/env bash
#
# One-time automatic setup for the OpenCue scheduler simulator.
#
# Idempotent: safe to re-run. Creates a Python venv with the gRPC deps,
# generates the opencue_proto/ stubs from the repo's proto sources, and checks
# that a usable JDK 17 is available for the cuebot build. After this you can run
# the sim directly:
#
#     ./venv/bin/python simulate.py --mode new --jobs 30 --stats 60
#
# Everything is derived from this script's own location, so it works from a
# plain checkout with no edits. Override any piece with the SIM_* env vars that
# simulate.py documents (SIM_VENV_PY, SIM_JDK_HOME, ...).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # cuebot/scheduler-sim
REPO="$(cd "$HERE/../.." && pwd)"                       # OpenCue repo root
PROTO_SRC="$REPO/proto/src"
CUEBOT_DIR="$(cd "$HERE/.." && pwd)"                    # cuebot (has gradlew)
VENV="${SIM_VENV:-$HERE/venv}"

say() { printf '\033[1m[setup]\033[0m %s\n' "$*"; }

# 1. venv + gRPC deps -----------------------------------------------------------
if [ ! -x "$VENV/bin/python" ]; then
    say "creating venv at $VENV"
    python3 -m venv "$VENV"
fi
# Behind a TLS-intercepting proxy, pip's bundled CA rejects the proxy's
# certificate ("self-signed certificate in certificate chain"), even though the
# system trust store accepts it (apt and, via ca-certificates-java, the JDK both
# work). Point pip at the system CA bundle when present; harmless off-proxy.
if [ -z "${PIP_CERT:-}" ]; then
    for _ca in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt; do
        [ -f "$_ca" ] && { export PIP_CERT="$_ca"; break; }
    done
fi
[ -n "${PIP_CERT:-}" ] && say "using system CA bundle for pip: $PIP_CERT"
say "installing python deps (grpcio, grpcio-tools, protobuf)"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q grpcio grpcio-tools protobuf

# 2. opencue_proto/ stubs -------------------------------------------------------
if [ ! -d "$PROTO_SRC" ]; then
    echo "ERROR: proto sources not found at $PROTO_SRC" >&2
    exit 1
fi
say "generating opencue_proto/ from $PROTO_SRC"
mkdir -p "$HERE/opencue_proto"
"$VENV/bin/python" -m grpc_tools.protoc -I"$PROTO_SRC" \
    --python_out="$HERE/opencue_proto" \
    --grpc_python_out="$HERE/opencue_proto" \
    "$PROTO_SRC"/*.proto
touch "$HERE/opencue_proto/__init__.py"
say "  $(ls "$HERE"/opencue_proto/*_pb2.py | wc -l | tr -d ' ') proto modules generated"

# 3. gradlew present? -----------------------------------------------------------
if [ ! -x "$CUEBOT_DIR/gradlew" ]; then
    echo "WARNING: $CUEBOT_DIR/gradlew not found — cuebot cannot be built." >&2
fi

# 4. JDK 17 check ---------------------------------------------------------------
# cuebot's wrapper Gradle (7.6.2) needs JDK 17; the box's default JDK 21 fails
# with "Unsupported class file major version 65". simulate.py points gradle at
# SIM_JDK_HOME if it is a real dir, else the ambient JAVA_HOME.
JDK="${SIM_JDK_HOME:-/tmp/jdk-17.0.2}"
jdk_ok=""
if [ -x "$JDK/bin/java" ] && "$JDK/bin/java" -version 2>&1 | grep -q '"17'; then
    jdk_ok="$JDK"
elif command -v java >/dev/null 2>&1 && java -version 2>&1 | grep -q '"17'; then
    jdk_ok="$(dirname "$(dirname "$(command -v java)")")"
fi
if [ -n "$jdk_ok" ]; then
    say "JDK 17 found at $jdk_ok"
else
    cat >&2 <<EOF
WARNING: no JDK 17 found (checked SIM_JDK_HOME=$JDK and PATH java).
  cuebot's Gradle 7.6.2 build requires JDK 17 (JDK 21 fails: "major version 65").
  Install one and point the sim at it, e.g.:
      export SIM_JDK_HOME=/path/to/jdk-17
  Behind a TLS-intercepting proxy you must also copy the system truststore:
      cp \$JAVA_HOME/lib/security/cacerts \$SIM_JDK_HOME/lib/security/cacerts
  See BUILD.md for details.
EOF
fi

say "done. Run the sim with:"
echo "    cd $HERE && ./venv/bin/python simulate.py --mode new --jobs 30 --stats 60"
