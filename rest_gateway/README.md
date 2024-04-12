# Opencue Rest Gateway

A gateway to provide a REST endpoint to opencue gRPC API.

## How does it work

This is a go serviced based on the official [grpc-gateway project](https://github.com/grpc-ecosystem/grpc-gateway) 
that compiles opencue's proto files into a go service that provides a REST interface and redirect calls to the  
grpc endpoint.

The service is available at http://opencue-gateway.apps.com

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

### Example (getting a show):
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
request (gateway running on `http://opencue-gateway.apps.com`):
```bash
curl -i -X POST http://opencue-gateway.apps.com/show.ShowInterface/FindShow -d '{"name": "ashow"}`
```
response
```bash
HTTP/1.1 200 OK
Content-Type: application/json
Grpc-Metadata-Content-Type: application/grpc
Grpc-Metadata-Grpc-Accept-Encoding: gzip
Date: Tue, 12 Dec 2023 18:05:18 GMT
Content-Length: 501

{"show":{"id":"00000000-0000-0000-0000-99999999999999","name":"ashow","defaultMinCores":1,"defaultMaxCores":10,"commentEmail":"middle-tier@imageworks.com","bookingEnabled":true,"dispatchEnabled":true,"active":true,"showStats":{"runningFrames":75,"deadFrames":14,"pendingFrames":1814,"pendingJobs":175,"createdJobCount":"2353643","createdFrameCount":"10344702","renderedFrameCount":"9733366","failedFrameCount":"1096394","reservedCores":252,"reservedGpus":0},"defaultMinGpus":100,"defaultMaxGpus":100000}}
```

### Example (getting frames for a job):
job.proto:
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
request (gateway running on `http://opencue-gateway.apps.com`):

Note: it is important to include 'page' and 'limit' when getting frames for a job.
```bash
curl -i -X POST http://opencue-gateway.apps.com/job.JobInterface/GetFrames -d '{"job":{"id":"9999999999-b8d7-9999-a29c-99999999999999"}, "req": {"include_finished":true,"page":1,"limit":100}}'
```
response
```bash
HTTP/1.1 200 OK
content-type: application/json
grpc-metadata-content-type: application/grpc
grpc-metadata-grpc-accept-encoding: gzip
date: Tue, 13 Feb 2024 17:15:49 GMT
transfer-encoding: chunked
set-cookie: 3d3a38cc45d028e42e93031e0ccc9b1e=534d34fde72242856a7fdadc27260929; path=/; HttpOnly

{"frames":{"frames":[{"id":"9999999", "name":"0001-some_frame_0999990", "layerName":"h", "number":1, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":0, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"10fa17d4-9313-4924-86f5-380c5b2a25d8", "name":"0002-some_frame_0999990", "layerName":"some_frame_0999990", "number":2, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":1, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"8d39c602-0b27-4b1e-a09b-4fa35db40e55", "name":"0003-some_frame_0999990", "layerName":"some_frame_0999990", "number":3, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":2, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"d418a837-e974-4716-9105-296f495bc407", "name":"0004-some_frame_0999990", "layerName":"some_frame_0999990", "number":4, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":3, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}, {"id":"d2113372-99999-4c05-8100-9999999", "name":"0005-some_frame_0999990", "layerName":"some_frame_0999990", "number":5, "state":"WAITING", "retryCount":0, "exitStatus":-1, "dispatchOrder":4, "startTime":0, "stopTime":0, "maxRss":"0", "usedMemory":"0", "reservedMemory":"0", "reservedGpuMemory":"0", "lastResource":"/0.00/0", "checkpointState":"DISABLED", "checkpointCount":0, "totalCoreTime":0, "lluTime":1707842141, "totalGpuTime":0, "maxGpuMemory":"0", "usedGpuMemory":"0", "frameStateDisplayOverride":null}]}}
```