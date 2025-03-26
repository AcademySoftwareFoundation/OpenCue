# Opencue Rest Gateway

A gateway to provide a REST endpoint to the Opencue gRPC API.


## Contents

1. [Introduction](#introduction)
2. [How does it work](#how-does-it-work)
3. [REST interface](#rest-interface)
    - [Example: Getting a show](#example-getting-a-show)
    - [Example: Getting frames for a job](#example-getting-frames-for-a-job)
4. [Authentication](#authentication)
    - [What are JSON Web Tokens?](#what-are-json-web-tokens)
    - [JSON Web Tokens in a web system and the Rest Gateway](#json-web-tokens-in-a-web-system-and-the-rest-gateway)
        - [Web system](#web-system)
        - [Rest Gateway](#rest-gateway)
5. [Rest Gateway unit testing](#rest-gateway-unit-testing)


## Introduction

The Opencue Rest Gateway is a crucial component that bridges the gap between Opencue's high-performance gRPC API and the widespread, web-friendly RESTful interface. Designed with scalability and integration flexibility in mind, this gateway allows developers and systems to interact with Opencue through standard HTTP methods, making it easier to integrate Opencue into a variety of environments, including web applications, automation scripts, and third-party services.

By leveraging REST, the Opencue Rest Gateway opens up Opencue's advanced rendering and job management capabilities to a broader audience, enabling access through familiar, widely-adopted web technologies. This gateway not only simplifies interaction with Opencue but also ensures that all communications are secure, thanks to its implementation of [JSON Web Token (JWT)](https://jwt.io/) authentication.

This documentation provides detailed instructions on how to set up and use the Opencue Rest Gateway, including configuration tips, examples of API calls, and insights into the security mechanisms that protect your data and operations.

Go back to [Contents](#contents).


## How Does It Work

The Opencue Rest Gateway operates as a translator and secure access point between the RESTful world and the gRPC services provided by Opencue. Built on top of Go and the [grpc-gateway project](https://github.com/grpc-ecosystem/grpc-gateway), the gateway automatically converts Opencue's protocol buffer (proto) definitions into REST endpoints.

Here’s a step-by-step breakdown of how it works:

1. **Request Conversion**: When a client sends an HTTP request to the gateway, the request is matched against the predefined RESTful routes generated from the proto files. The gateway then converts this HTTP request into the corresponding gRPC call.

2. **gRPC Communication**: The converted request is sent to the appropriate Opencue gRPC service, where it is processed just like any other gRPC request.

3. **Response Handling**: After the gRPC service processes the request, the response is returned to the gateway, which then converts the gRPC response into a JSON format suitable for HTTP.

4. **Security Enforcement**: Before any request is processed, the gateway enforces security by requiring a JSON Web Token (JWT) in the `Authorization header`. This token is validated to ensure that the request is authenticated and authorized to access the requested resources.

5. **Final Response**: The formatted JSON response is sent back to the client via HTTP, completing the request-response cycle.

This seamless conversion and security process allows the Opencue Rest Gateway to provide a robust, secure, and user-friendly interface to Opencue's gRPC services, making it accessible to a wide range of clients and applications.

**Note:** In the examples below, the REST gateway is available at OPENCUE_REST_GATEWAY_URL. Remember to replace OPENCUE_REST_GATEWAY_URL with the appropriate URL.

Go back to [Contents](#contents).


## REST interface

All service RPC calls are accessible via the REST interface:

 * **HTTP method:** POST
 * **URI path:** Built from the service's name and method: `/<fully qualified service name>/<method name>` (e.g., `/show.ShowInterface/FindShow`)
 * **Authorization header:** Must include a JWT token as the bearer.
    ```json
    headers: {
            "Authorization": `Bearer ${jwtToken}`,
        },
    ```
 * **HTTP body:** A JSON object with the request data.
    ```proto
        message ShowFindShowRequest {
            string name = 1;
        }
    ``` 
    Becomes:
    ```json
    {
        "name": "value for name"
    }
    ```
 * **HTTP response:** A JSON object with the formatted response.

Go back to [Contents](#contents).


### Example: Getting a show

Given the following proto definition in `show.proto`:

```proto
service ShowInterface {
    // Find a show with the specified name.
    rpc FindShow(ShowFindShowRequest) returns (ShowFindShowResponse);
}

message ShowFindShowRequest {
    string name = 1;
}
message ShowFindShowResponse {
    Show show = 1;
}
message Show {
    string id = 1;
    string name = 2;
    float default_min_cores = 3;
    float default_max_cores = 4;
    string comment_email = 5;
    bool booking_enabled = 6;
    bool dispatch_enabled = 7;
    bool active = 8;
    ShowStats show_stats = 9;
    float default_min_gpus = 10;
    float default_max_gpus = 11;
}
```

You can send a request to the REST gateway running on `OPENCUE_REST_GATEWAY_URL`:

```bash
curl -i -H "Authorization: Bearer jwtToken" -X POST OPENCUE_REST_GATEWAY_URL/show.ShowInterface/FindShow -d '{"name": "testshow"}`
```

The response might look like this:

```bash
HTTP/1.1 200 OK
Content-Type: application/json
Grpc-Metadata-Content-Type: application/grpc
Grpc-Metadata-Grpc-Accept-Encoding: gzip
Date: Tue, 12 Dec 2023 18:05:18 GMT
Content-Length: 501

{"show":{"id":"00000000-0000-0000-0000-000000000000","name":"testshow","defaultMinCores":1,"defaultMaxCores":10,"commentEmail":"middle-tier@company.com","bookingEnabled":true,"dispatchEnabled":true,"active":true,"showStats":{"runningFrames":75,"deadFrames":14,"pendingFrames":1814,"pendingJobs":175,"createdJobCount":"2353643","createdFrameCount":"10344702","renderedFrameCount":"9733366","failedFrameCount":"1096394","reservedCores":252,"reservedGpus":0},"defaultMinGpus":100,"defaultMaxGpus":100000}}
```

Go back to [Contents](#contents).


### Example: Getting frames for a job

Given the following proto definition in `job.proto`:

```proto
service JobInterface {
    // Returns all frame objects that match FrameSearchCriteria
    rpc GetFrames(JobGetFramesRequest) returns (JobGetFramesResponse);
}

message JobGetFramesRequest {
    Job job = 1;
    FrameSearchCriteria req = 2;
}

message Job {
    string id = 1;
    JobState state = 2;
    string name = 3;
    string shot = 4;
    string show = 5;
    string user = 6;
    string group = 7;
    string facility = 8;
    string os = 9;
    oneof uid_optional {
        int32 uid = 10;
    }
    int32 priority = 11;
    float min_cores = 12;
    float max_cores = 13;
    string log_dir = 14;
    bool is_paused = 15;
    bool has_comment = 16;
    bool auto_eat = 17;
    int32 start_time = 18;
    int32 stop_time = 19;
    JobStats job_stats = 20;
    float min_gpus = 21;
    float max_gpus = 22;
}

// Object for frame searching
message FrameSearchCriteria {
    repeated string ids = 1;
    repeated string frames = 2;
    repeated string layers = 3;
    FrameStateSeq states = 4;
    string frame_range = 5;
    string memory_range = 6;
    string duration_range = 7;
    int32 page = 8;
    int32 limit = 9;
    int32 change_date = 10;
    int32 max_results = 11;
    int32 offset = 12;
    bool include_finished = 13;
}

message JobGetFramesResponse {
    FrameSeq frames = 1;
}

// A sequence of Frames
message FrameSeq {
    repeated Frame frames = 1;
}
```

You can send a request to the REST gateway running on `OPENCUE_REST_GATEWAY_URL`:

**Note:** It is important to include 'page' and 'limit' when getting frames for a job.

```bash
curl -i -H "Authorization: Bearer jwtToken" -X POST OPENCUE_REST_GATEWAY_URL/job.JobInterface/GetFrames -d '{"job":{"id":"00000000-0000-0000-0000-000000000001", "req": {"include_finished":true,"page":1,"limit":100}}'
```

The response might look like this:

```bash
HTTP/1.1 200 OK
content-type: application/json
grpc-metadata-content-type: application/grpc
grpc-metadata-grpc-accept-encoding: gzip
date: Tue, 13 Feb 2024 17:15:49 GMT
transfer-encoding: chunked
set-cookie: 01234567890123456789012345678901234567890123456789012345678901234; path=/; HttpOnly


{"frames":{"frames":[{"id":"00000000-0000-0000-0000-000000000002", "name":"0001-bty_tp_3d_123456", "layerName":"bty_tp_3d_123456", "number":1, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":0, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000003", "name":"0002-bty_tp_3d_123456", "layerName":"bty_tp_3d_123456", "number":2, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":1, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000004", "name":"0003-bty_tp_3d_083540", "layerName":"bty_tp_3d_123456", "number":3, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":2, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000005", "name":"0004-bty_tp_3d_083540", "layerName":"bty_tp_3d_123456", "number":4, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":3, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"00000000-0000-0000-0000-000000000006", "name":"0005-bty_tp_3d_083540", "layerName":"bty_tp_3d_123456", "number":5, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":4, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}]}}
```

Go back to [Contents](#contents).


## Authentication

Go back to [Contents](#contents).


### What are JSON Web Tokens?

The gRPC REST gateway implements JSON Web Tokens (JWT) for authentication. JWTs are a compact, URL-safe means of representing claims to be transferred between two parties. The claims in a JWT are encoded as a JSON object and are digitally signed for verification and security. In the gRPC REST gateway, all JWTs are signed using a secret. A JWT consists of the following three parts separated by dots:

1. **Header:** Contains the type of token (usually `JWT`) and the signing algorithm (like `SHA256`)

- Example:

```json
{
    "alg": "HS256",
    "typ": "JWT"
}
```

2. **Payload:** Contains the claims, which are statements about an entity (user) and additional data.

- Example:

```json
{
    "sub": "user-id-123",
    "role": "admin",
    "iat": 1609459200,  // Example timestamp (Jan 1, 2021)
    "exp": 1609462800   // Example expiration (1 hour later)
}

```
3. **Signature:** Created from the encoded header, the encoded payload, a secret, the algorithm specified in the header, and signed.

- The signature also verifies that the original message was not altered and can verify that the sender of the JWT is who they say they are (when signed with a private key).

- Example:

```
HMACSHA256(
    base64UrlEncode(header) + "." +
    base64UrlEncode(payload),
    secret
)
```
Together, these three parts form a token like `xxxxx.yyyyy.zzzzz`, which is three Base64-URL strings separated by dots that can be passed in HTML environments.

Go back to [Contents](#contents).


### JSON Web Tokens in a web system and the Rest Gateway

In a web system and Rest Gateway, the secret for the JWT must be defined and match. In Rest Gateway, the secret is defined as an environment variable called `JWT_AUTH_SECRET`.

Go back to [Contents](#contents).


#### Web system

When a web system accesses the gRPC REST gateway, `fetchObjectFromRestGateway()` will be called, which initializes a JWT with an expiration time (e.g. 1 hour). This JWT is then passed on every request to the gRPC REST gateway as the authorization bearer in the header. If this JWT is successfully authenticated by the Rest Gateway, the gRPC endpoint will be reached. If the JWT is invalid, an error will be returned, and the gRPC endpoint will not be reached.

Go back to [Contents](#contents).


#### Rest Gateway

When the gRPC REST gateway receives a request, it must first verify and authenticate it using middleware (`jwtMiddleware()`). The following requirements are checked before the gRPC REST gateway complies with the request:
- The request contains an `Authorization header` with a `Bearer token`.
- The token's signing method is Hash-based message authentication code (or HMAC).
- The token is valid.
- The token is not expired.
- The token's secret matches the Rest Gateway's secret.

Go back to [Contents](#contents).


## Rest Gateway unit testing

Unit tests for the gRPC REST gateway can be run with `go test`. To run the Rest Gateway unit testing using the Dockerfile, uncomment `RUN go test -v` in the Dockerfile. 

Unit tests currently cover the following cases for `jwtMiddleware` (used for authentication):

- Valid tokens
- Missing tokens
- Invalid tokens
- Expired tokens

Go back to [Contents](#contents).
