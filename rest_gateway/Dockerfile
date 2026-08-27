FROM golang:1.25-bookworm AS build

# Install protobuf compiler
RUN apt-get update && \
    apt-get install -y protobuf-compiler && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PATH=$PATH:/root/go/bin

# Copy all of the staged files (protos plus go source)
COPY ./proto /app/proto
COPY ./rest_gateway/opencue_gateway /app/opencue_gateway
# COPY ./lib /app/lib


WORKDIR /app/opencue_gateway
RUN if [ ! -f go.mod ]; then go mod init opencue_gateway; fi && go mod tidy

RUN go install \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2 \
    github.com/golang-jwt/jwt/v5 \
    google.golang.org/protobuf/cmd/protoc-gen-go \
    google.golang.org/grpc/cmd/protoc-gen-go-grpc

# Generate go grpc code
RUN mkdir -p gen/go && \
    protoc -I ../proto/src/ \
    --go_out ./gen/go/ \
    --go_opt paths=source_relative \
    --go-grpc_out ./gen/go/ \
    --go-grpc_opt paths=source_relative \
    ../proto/src/*.proto

# Generate grpc-gateway handlers
RUN protoc -I ../proto/src/ --grpc-gateway_out ./gen/go \
    --grpc-gateway_opt paths=source_relative \
    --grpc-gateway_opt generate_unbound_methods=true \
    ../proto/src/*.proto

# Generate OpenAPI/Swagger definitions
RUN mkdir -p gen/openapiv2 && \
    protoc -I ../proto/src/ --openapiv2_out ./gen/openapiv2 \
    --openapiv2_opt generate_unbound_methods=true \
    --openapiv2_opt logtostderr=true \
    ../proto/src/*.proto

# Fetch swaggo/files static assets and update dependencies.
# go.mod/go.sum are not committed (see rest_gateway/.gitignore), so this pin is
# the only thing keeping the build reproducible. Keep the version in sync with
# the "Install Go dependencies" step in .github/workflows/testing-pipeline.yml.
RUN go get github.com/swaggo/files/v2@v2.0.2 && \
    go mod tidy

# Uncomment this to run go tests
# RUN go test -v

# Build project
RUN go build -o grpc_gateway main.go

FROM debian:bookworm-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/opencue_gateway/grpc_gateway /app/
COPY --from=build /app/opencue_gateway/gen/openapiv2 /app/gen/openapiv2

# Ensure logs folder is created and has correct permissions
RUN mkdir -p /logs && chmod 755 /logs

# Set default environment variables
ENV CUEBOT_ENDPOINT=localhost:8443
ENV REST_PORT=8448
ENV JWT_SECRET=default-secret-key
ENV SWAGGER_DIR=/app/gen/openapiv2
# The Swagger UI on /swagger/ is served without authentication so the API can be
# browsed. Set SWAGGER_ENABLED=false wherever the gateway is reachable beyond a
# trusted network.
ENV SWAGGER_ENABLED=true

EXPOSE 8448
ENTRYPOINT ["/app/grpc_gateway"]
