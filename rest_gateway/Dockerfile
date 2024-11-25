# Use the official CentOS 7 image
FROM registry.access.redhat.com/ubi9/ubi:latest AS build

RUN dnf -y update && \
    dnf install -y git \
    golang \
    dnf-plugins-core \
    unzip

RUN curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v25.1/protoc-25.1-linux-x86_64.zip && \
    unzip protoc-25.1-linux-x86_64.zip -d /usr/local && \
    rm protoc-25.1-linux-x86_64.zip

WORKDIR /app
ENV PATH=$PATH:/root/go/bin:/opt/protobuf3/usr/bin/

# Copy all of the staged files (protos plus go source)
COPY ./proto /app/proto
COPY ./rest_gateway/opencue_gateway /app/opencue_gateway
# COPY ./lib /app/lib


WORKDIR /app/opencue_gateway
RUN go mod init opencue_gateway && go mod tidy

RUN go install \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2 \
    github.com/golang-jwt/jwt/v5 \
    google.golang.org/protobuf/cmd/protoc-gen-go \
    google.golang.org/grpc/cmd/protoc-gen-go-grpc

# Generate go grpc code
RUN mkdir -p gen/go && \
    protoc -I ../proto/ \
    --go_out ./gen/go/ \
    --go_opt paths=source_relative \
    --go-grpc_out ./gen/go/ \
    --go-grpc_opt paths=source_relative \
    ../proto/*.proto

# Generate grpc-gateway handlers
RUN protoc -I ../proto/ --grpc-gateway_out ./gen/go \
    --grpc-gateway_opt paths=source_relative \
    --grpc-gateway_opt generate_unbound_methods=true \
    ../proto/*.proto

# Environment variables for the rest gateway
ENV CUEBOT_ENDPOINT=tobefilledmanually
ENV REST_PORT=tobefilledmanually
ENV JWT_AUTH_SECRET=tobefilledmanually

# Uncomment this to run go tests
# RUN go test -v

# Build project
RUN go build -o grpc_gateway main.go

FROM registry.access.redhat.com/ubi9/ubi:latest
COPY --from=build /app/opencue_gateway/grpc_gateway /app/

# Ensure logs folder is created and has correct permissions
RUN mkdir -p /logs && chmod 755 /logs

EXPOSE 8448
ENTRYPOINT ["/app/grpc_gateway"]
