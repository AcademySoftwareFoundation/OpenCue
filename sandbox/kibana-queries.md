# OpenCue Monitoring - Kibana Query Reference

This document provides sample Kibana Dev Tools queries for exploring OpenCue monitoring data stored in Elasticsearch.

**Access Kibana Dev Tools:** http://localhost:5601/app/dev_tools#/console

## Index Overview

```json
# List all OpenCue indices with stats
GET /_cat/indices/opencue-*?v&s=index

# Get total document counts
GET /opencue-frame-events-*/_count
GET /opencue-job-events-*/_count
GET /opencue-layer-events-*/_count
GET /opencue-proc-events-*/_count
GET /opencue-host-events-*/_count
```

## Pickup Time Tracking

Pickup time measures how long frames wait between becoming ready (DEPEND->WAITING) and starting execution (WAITING->RUNNING).

### FRAME_STARTED Events (WAITING -> RUNNING)

These events are published when a frame is dispatched to a host and begins execution.

```json
# Count FRAME_STARTED events
GET /opencue-frame-events-*/_count
{
  "query": {
    "match": {
      "header.event_type": "FRAME_STARTED"
    }
  }
}

# Get recent FRAME_STARTED events
GET /opencue-frame-events-*/_search
{
  "query": {
    "match": {
      "header.event_type": "FRAME_STARTED"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20,
  "_source": [
    "header.timestamp",
    "frame_name",
    "job_name",
    "host_name",
    "previous_state",
    "state",
    "num_cores",
    "reserved_memory"
  ]
}

# FRAME_STARTED events in last hour
GET /opencue-frame-events-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "header.event_type": "FRAME_STARTED" } },
        { "range": { "header.timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 50
}
```

### FRAME_DISPATCHED Events (DEPEND -> WAITING)

These events are published when a frame's dependencies are satisfied and it becomes ready for dispatch.

```json
# Count FRAME_DISPATCHED events
GET /opencue-frame-events-*/_count
{
  "query": {
    "match": {
      "header.event_type": "FRAME_DISPATCHED"
    }
  }
}

# Get recent FRAME_DISPATCHED events
GET /opencue-frame-events-*/_search
{
  "query": {
    "match": {
      "header.event_type": "FRAME_DISPATCHED"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20,
  "_source": [
    "header.timestamp",
    "frame_name",
    "frame_number",
    "job_id",
    "layer_id",
    "previous_state",
    "state",
    "dispatch_order"
  ]
}
```

### Pickup Time Analysis

```json
# Both pickup time event types in last hour
GET /opencue-frame-events-*/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "terms": {
            "header.event_type": ["FRAME_STARTED", "FRAME_DISPATCHED"]
          }
        },
        {
          "range": {
            "header.timestamp": { "gte": "now-1h" }
          }
        }
      ]
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 100
}

# Pickup events histogram over time
GET /opencue-frame-events-*/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        {
          "terms": {
            "header.event_type": ["FRAME_STARTED", "FRAME_DISPATCHED"]
          }
        },
        {
          "range": {
            "header.timestamp": { "gte": "now-6h" }
          }
        }
      ]
    }
  },
  "aggs": {
    "events_over_time": {
      "date_histogram": {
        "field": "header.timestamp",
        "fixed_interval": "5m"
      },
      "aggs": {
        "by_type": {
          "terms": {
            "field": "header.event_type"
          }
        }
      }
    }
  }
}
```

## Frame Events

### Event Type Summary

```json
# Aggregate all frame events by type
GET /opencue-frame-events-*/_search
{
  "size": 0,
  "aggs": {
    "by_event_type": {
      "terms": {
        "field": "header.event_type"
      }
    }
  }
}
```

### FRAME_COMPLETED Events

```json
# Recent completed frames
GET /opencue-frame-events-*/_search
{
  "query": {
    "match": {
      "header.event_type": "FRAME_COMPLETED"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20,
  "_source": [
    "header.timestamp",
    "frame_name",
    "job_name",
    "host_name",
    "exit_status",
    "run_time",
    "max_rss",
    "reserved_memory"
  ]
}

# Completed frames runtime statistics
GET /opencue-frame-events-*/_search
{
  "size": 0,
  "query": {
    "match": {
      "header.event_type": "FRAME_COMPLETED"
    }
  },
  "aggs": {
    "runtime_stats": {
      "stats": {
        "field": "run_time"
      }
    },
    "memory_stats": {
      "stats": {
        "field": "max_rss"
      }
    }
  }
}
```

### FRAME_FAILED Events

```json
# Recent failed frames
GET /opencue-frame-events-*/_search
{
  "query": {
    "match": {
      "header.event_type": "FRAME_FAILED"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20,
  "_source": [
    "header.timestamp",
    "frame_name",
    "job_name",
    "host_name",
    "exit_status",
    "exit_signal",
    "retry_count",
    "reason"
  ]
}

# Failed frames by host (find problematic hosts)
GET /opencue-frame-events-*/_search
{
  "size": 0,
  "query": {
    "match": {
      "header.event_type": "FRAME_FAILED"
    }
  },
  "aggs": {
    "by_host": {
      "terms": {
        "field": "host_name",
        "size": 20
      }
    }
  }
}
```

### State Transitions

```json
# Frame state transitions summary
GET /opencue-frame-events-*/_search
{
  "size": 0,
  "aggs": {
    "transitions": {
      "composite": {
        "sources": [
          { "from": { "terms": { "field": "previous_state" } } },
          { "to": { "terms": { "field": "state" } } }
        ]
      }
    }
  }
}
```

## Job Events

```json
# Recent job events
GET /opencue-job-events-*/_search
{
  "query": {
    "match_all": {}
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20
}

# Job events by type
GET /opencue-job-events-*/_search
{
  "size": 0,
  "aggs": {
    "by_event_type": {
      "terms": {
        "field": "header.event_type"
      }
    }
  }
}

# Search for a specific job
GET /opencue-job-events-*/_search
{
  "query": {
    "match": {
      "job_name": "testing-testshot-rfigueiredo_load_test_job_0093"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "asc" } }
  ]
}

# Jobs by show
GET /opencue-job-events-*/_search
{
  "size": 0,
  "aggs": {
    "by_show": {
      "terms": {
        "field": "show"
      }
    }
  }
}

# Recently completed jobs
GET /opencue-job-events-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "header.event_type": "JOB_COMPLETED" } },
        { "range": { "header.timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20
}
```

## Proc Events

```json
# Proc events by type
GET /opencue-proc-events-*/_search
{
  "size": 0,
  "aggs": {
    "by_event_type": {
      "terms": {
        "field": "header.event_type"
      }
    }
  }
}

# Recent proc bookings
GET /opencue-proc-events-*/_search
{
  "query": {
    "match": {
      "header.event_type": "PROC_BOOKED"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20,
  "_source": [
    "header.timestamp",
    "host_name",
    "job_id",
    "frame_id",
    "reserved_cores",
    "reserved_memory"
  ]
}

# Proc unbookings (frames finished or killed)
GET /opencue-proc-events-*/_search
{
  "query": {
    "match": {
      "header.event_type": "PROC_UNBOOKED"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 20
}
```

## Layer Events

```json
# Layer events summary
GET /opencue-layer-events-*/_search
{
  "size": 0,
  "aggs": {
    "by_event_type": {
      "terms": {
        "field": "header.event_type"
      }
    }
  }
}

# Layers by type (Render, Util, etc.)
GET /opencue-layer-events-*/_search
{
  "size": 0,
  "aggs": {
    "by_layer_type": {
      "terms": {
        "field": "type"
      }
    }
  }
}
```

## Host Events

```json
# Recent host events
GET /opencue-host-events-*/_search
{
  "query": {
    "match_all": {}
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 10
}
```

## Time-Based Analytics

```json
# Frame events histogram (per minute, last hour)
GET /opencue-frame-events-*/_search
{
  "size": 0,
  "query": {
    "range": {
      "header.timestamp": { "gte": "now-1h" }
    }
  },
  "aggs": {
    "events_over_time": {
      "date_histogram": {
        "field": "header.timestamp",
        "fixed_interval": "1m"
      },
      "aggs": {
        "by_type": {
          "terms": {
            "field": "header.event_type"
          }
        }
      }
    }
  }
}

# Events by show over time
GET /opencue-frame-events-*/_search
{
  "size": 0,
  "query": {
    "range": {
      "header.timestamp": { "gte": "now-24h" }
    }
  },
  "aggs": {
    "by_show": {
      "terms": {
        "field": "show"
      },
      "aggs": {
        "over_time": {
          "date_histogram": {
            "field": "header.timestamp",
            "fixed_interval": "1h"
          }
        }
      }
    }
  }
}
```

## Correlation Queries

```json
# Track a job's complete frame lifecycle using correlation_id (job_id)
# Replace YOUR-JOB-ID with an actual job ID
GET /opencue-frame-events-*/_search
{
  "query": {
    "term": {
      "header.correlation_id": "YOUR-JOB-ID-HERE"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "asc" } }
  ],
  "size": 100
}

# All events for a specific frame
GET /opencue-frame-events-*/_search
{
  "query": {
    "term": {
      "frame_id": "YOUR-FRAME-ID-HERE"
    }
  },
  "sort": [
    { "header.timestamp": { "order": "asc" } }
  ]
}

# Frames dispatched to a specific host
GET /opencue-frame-events-*/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "header.event_type": "FRAME_STARTED" } },
        { "match": { "host_name": "172.19.0.11" } }
      ]
    }
  },
  "sort": [
    { "header.timestamp": { "order": "desc" } }
  ],
  "size": 50
}
```

## Index Mapping Reference

```json
# View frame events mapping
GET /opencue-frame-events-*/_mapping

# View the index template
GET /_index_template/opencue-frame-events
```

## Notes

- **Timestamp Field**: All events use `header.timestamp` as the time field (epoch_millis format)
- **Event Types**: Use `header.event_type` to filter by event type
- **Correlation**: Use `header.correlation_id` (typically the job_id) to track related events
- **Keyword Fields**: For exact matching and aggregations, use the field name directly (ES auto-detects keyword sub-fields)

## Grafana Dashboard

Access the pre-built monitoring dashboard at: http://localhost:3000/d/opencue-monitoring

The dashboard includes:
- Frames Completed/Failed stats
- Jobs Completed by Show
- Layer Runtime/Memory distributions
- **Pickup Time Metrics** (NEW):
  - Frames Started (WAITING -> RUNNING)
  - Frames Dispatchable (DEPEND -> WAITING)
  - Pickup Time Events Over Time
  - Recent FRAME_STARTED/FRAME_DISPATCHED tables
