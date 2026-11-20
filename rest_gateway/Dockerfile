FROM golang:1.27-bookworm AS build

# Install protobuf compiler
RUN apt-get update && \
    apt-get install -y protobuf-compiler && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/opencue_gateway
ENV PATH=$PATH:/root/go/bin

# Dependencies and the protoc plugins (go.mod's tool block)
COPY ./rest_gateway/opencue_gateway/go.mod ./rest_gateway/opencue_gateway/go.sum ./
RUN go mod download && go install tool

# Generate the gRPC, grpc-gateway and OpenAPI code from the protos
COPY ./proto /app/proto
COPY ./rest_gateway/opencue_gateway/generate_proto.sh ./
RUN ./generate_proto.sh ../proto/src

# Copy the go source
COPY ./rest_gateway/opencue_gateway /app/opencue_gateway

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
