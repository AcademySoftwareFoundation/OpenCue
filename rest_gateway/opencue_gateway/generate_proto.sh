#!/bin/bash

# Generates the gateway's Go code and OpenAPI definitions from OpenCue's protos into gen/.
#
# Usage: generate_proto.sh [proto source dir]   (default: ../../proto/src)
#
# Needs protoc and, on the PATH, the plugins listed in tools/gateway.go, installed from this
# module so go.mod pins their versions (`go install <plugin package>...`).

set -euo pipefail

cd "$(dirname "$0")"
proto_dir="${1:-../../proto/src}"

mkdir -p gen/go gen/openapiv2
protoc -I "${proto_dir}" \
  --go_out ./gen/go/ \
  --go_opt paths=source_relative \
  --go-grpc_out ./gen/go/ \
  --go-grpc_opt paths=source_relative \
  "${proto_dir}"/*.proto
protoc -I "${proto_dir}" \
  --grpc-gateway_out ./gen/go \
  --grpc-gateway_opt paths=source_relative \
  --grpc-gateway_opt generate_unbound_methods=true \
  "${proto_dir}"/*.proto
protoc -I "${proto_dir}" \
  --openapiv2_out ./gen/openapiv2 \
  --openapiv2_opt generate_unbound_methods=true \
  --openapiv2_opt logtostderr=true \
  "${proto_dir}"/*.proto
