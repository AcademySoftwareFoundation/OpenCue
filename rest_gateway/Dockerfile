FROM centos7.6-go1.21:latest AS build

RUN yum install -y \
    git \ 
    protobuf3-compiler \ 
    && yum clean all
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

# Uncomment this to run go tests
# RUN go test -v

# Build project
RUN go build -o grpc_gateway main.go

FROM centos-7.6.1810:latest
COPY --from=build /app/opencue_gateway/grpc_gateway /app/

# Ensure logs folder is created and has correct permissions
RUN mkdir -p /logs && chmod 755 /logs

EXPOSE 8448
ENTRYPOINT ["/app/grpc_gateway"]
