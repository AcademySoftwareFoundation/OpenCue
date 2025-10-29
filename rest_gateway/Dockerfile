FROM rockylinux:9 AS build

# Install Go 1.21 and dependencies
RUN dnf install -y epel-release && \
    dnf --enablerepo=crb install -y wget git protobuf protobuf-devel protobuf-compiler && \
    wget https://go.dev/dl/go1.21.13.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.13.linux-amd64.tar.gz && \
    rm go1.21.13.linux-amd64.tar.gz && \
    dnf clean all

WORKDIR /app
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin

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

# Uncomment this to run go tests
# RUN go test -v

# Build project
RUN go build -o grpc_gateway main.go

FROM rockylinux:9-minimal
COPY --from=build /app/opencue_gateway/grpc_gateway /app/

# Ensure logs folder is created and has correct permissions
RUN mkdir -p /logs && chmod 755 /logs

# Set default environment variables
ENV CUEBOT_ENDPOINT=localhost:8443
ENV REST_PORT=8448  
ENV JWT_SECRET=default-secret-key

EXPOSE 8448
ENTRYPOINT ["/app/grpc_gateway"]
