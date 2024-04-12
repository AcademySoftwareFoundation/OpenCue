# Opencue Rest Gateway

A gateway to provide a REST endpoint to opencue gRPC API.

## How does it work

This is a go serviced based on the official [grpc-gateway project](https://github.com/grpc-ecosystem/grpc-gateway) 
that compiles opencue's proto files into a go service that provides a REST interface and redirect calls to the  
grpc endpoint.

The service is available at http://opencue-gateway.apps.spi-eat-dev-01.spimageworks.com

## REST interface

All service rpc calls are accessible:
 * HTTP method is POST
 * URI path is built from the service’s name and method: /<fully qualified service name>/<method name> (e.g.: /show.ShowInterface/FindShow)
 * HTTP body is a JSON with the request object: e.g.: 
    ```proto
        message ShowFindShowRequest {
            string name = 1;
        }
    ``` 
    becomes:
    ```json
    {
        "name": "value for name"
    }
    ```
 * HTTP response is a JSON object with the formatted response

### Example:
show.proto:
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
request (gateway running on `http://opencue-gateway.apps.spi-eat-dev-01.spimageworks.com`):
```bash
curl -i -X POST http://opencue-gateway.apps.spi-eat-dev-01.spimageworks.com/show.ShowInterface/FindShow -d '{"name": "pipe"}`
```
response
```bash
HTTP/1.1 200 OK
Content-Type: application/json
Grpc-Metadata-Content-Type: application/grpc
Grpc-Metadata-Grpc-Accept-Encoding: gzip
Date: Tue, 12 Dec 2023 18:05:18 GMT
Content-Length: 501

{"show":{"id":"00000000-0000-0000-0000-000000000000","name":"pipe","defaultMinCores":1,"defaultMaxCores":10,"commentEmail":"middle-tier@imageworks.com","bookingEnabled":true,"dispatchEnabled":true,"active":true,"showStats":{"runningFrames":75,"deadFrames":14,"pendingFrames":1814,"pendingJobs":175,"createdJobCount":"2353643","createdFrameCount":"10344702","renderedFrameCount":"9733366","failedFrameCount":"1096394","reservedCores":252,"reservedGpus":0},"defaultMinGpus":100,"defaultMaxGpus":100000}}
```

