---
title: "Filter Development"
nav_order: 89
parent: Developer Guide
layout: default
date: 2025-10-15
description: >
  Developer guide for extending OpenCue filters, implementing new actions, and understanding the filter architecture
---

# Filter Development

## Overview

This guide is for developers who want to extend OpenCue's filter system, implement new filter actions, or understand the filter architecture for custom integrations. It covers the filter implementation across the OpenCue stack from protobuf definitions to UI components.

## Filter Architecture

### System Components

The filter system spans multiple OpenCue components:

```
┌─────────────────────────────────────────────────┐
│                  CueGUI                         │
│  ┌──────────────────────────────────────────┐  │
│  │  FilterDialog - UI for filter management │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                      ↓ gRPC
┌─────────────────────────────────────────────────┐
│                  PyCue                          │
│  ┌──────────────────────────────────────────┐  │
│  │  Filter, Action, Matcher wrappers        │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                      ↓ gRPC
┌─────────────────────────────────────────────────┐
│                  Cuebot                         │
│  ┌──────────────────────────────────────────┐  │
│  │  FilterManagerService                    │  │
│  │  - Filter execution                      │  │
│  │  - Action handlers                       │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│               PostgreSQL                        │
│  ┌──────────────────────────────────────────┐  │
│  │  filter, matcher, action tables          │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Key Files and Locations

**Protocol Buffers:**
```
proto/src/filter.proto              # Filter message definitions
```

**Cuebot (Java):**
```
cuebot/src/main/java/com/imageworks/spcue/service/FilterManagerService.java
cuebot/src/main/java/com/imageworks/spcue/dispatcher/commands/
```

**PyCue (Python):**
```
pycue/opencue/wrappers/filter.py    # Filter, Action, and Matcher wrappers
```

**CueGUI (Python/Qt):**
```
cuegui/cuegui/FilterDialog.py       # Filter management UI (includes ActionWidgetItem, ActionMonitorTree)
```

## Filter Execution Flow

Understanding the filter execution lifecycle:

### 1. Job Submission

```
Job submitted to Cuebot
         ↓
FilterManager.runFiltersOnJob(job)
         ↓
Load filters from database (ordered by order field)
         ↓
For each filter (in order):
    ├─ Evaluate matchers
    ├─ If all/any matchers match:
    │   ├─ Execute actions
    │   └─ If STOP_PROCESSING: break
    └─ Continue to next filter
```

### 2. Matcher Evaluation

Matchers evaluate job properties using various comparison types (CONTAINS, IS, BEGINS_WITH, REGEX, etc.). The Cuebot implementation extracts the relevant job property based on the matcher subject and compares it against the matcher input using the specified match type.

### 3. Action Execution

Actions are executed sequentially for each matched filter. Each action type has a handler that modifies the job or its layers. The STOP_PROCESSING action returns a signal to halt further filter evaluation without processing remaining filters.

## API Integration

### Python API

Use the PyCue API to programmatically manage filters:
- Find a show: `show = opencue.api.findShow("show-name")`
- Create filter on show: `filter = show.createFilter("filter-name")`
- Find existing filter: `filter = opencue.api.findFilter("show-name", "filter-name")`
- Add matchers: `filter.createMatcher(subject, match_type, query)`
- Add actions: `filter.createAction(action_type, value)`
- Test filters: `filter.runFilterOnJobs([job1, job2])`

See `pycue/opencue/wrappers/filter.py` for complete API documentation.

### REST API

The REST gateway provides HTTP endpoints for filter management. Check the REST API documentation for available endpoints and request formats.

## Performance Considerations

### Filter Optimization

**1. Matcher Performance:**
```java
// Fast: Simple string comparison
matcher.setType(MatchType.IS);
matcher.setInput("exact_match");

// Slower: Regex compilation and matching
matcher.setType(MatchType.REGEX);
matcher.setInput("^complex_.*_pattern$");
```

**Best Practice:** Use simple match types when possible. Reserve REGEX for complex patterns.

**2. Filter Ordering:**
```
Order 5:  Most specific (matches 1% of jobs)
Order 10: Moderately specific (matches 10% of jobs)
Order 20: General (matches 50% of jobs)
```

**Best Practice:** Order from specific to general. Use STOP_PROCESSING to skip unnecessary evaluations.

**3. Action Efficiency:**
```java
// Efficient: Single database operation
job.setPriority(800);

// Less efficient: Multiple database operations
for (Layer layer : job.getLayers()) {
    layer.setTags("gpu");  // N database calls
}
```

**Best Practice:** Batch operations when possible.

### Database Indexing

Ensure proper indexes for filter queries:

```sql
-- Index on filter order for efficient retrieval
CREATE INDEX idx_filter_order ON filter(f_order);

-- Index on filter show for show-specific filters
CREATE INDEX idx_filter_show ON filter(pk_show);

-- Compound index for filter lookups
CREATE INDEX idx_filter_show_enabled ON filter(pk_show, f_enabled);
```

## Custom Filter Extensions

### Custom Matcher Types

To add new matcher types, you would need to:
1. Add new enum value to `MatchSubject` in `filter.proto`
2. Implement matcher evaluation logic in Cuebot's FilterManagerService
3. Update PyCue wrapper enum in `filter.py`
4. Add UI support in CueGUI's FilterDialog

### Custom Action Handlers

Custom actions follow the same pattern as adding standard actions (see "Adding a New Filter Action" section above). The key is implementing the handler logic in Cuebot that performs the desired operation on jobs or layers.

## Debugging Filters

### Enable Debug Logging

Configure Cuebot's logging to debug filter execution:
- Configure Cuebot's logging framework to set FilterManagerService logger to DEBUG level
- Check Cuebot logs for filter evaluation and action execution details
- Monitor log output for matcher evaluation and action application

### Filter Testing

Test filters programmatically using PyCue:
- Load filter with `opencue.api.findFilter()`
- Get matchers and actions
- Test against specific jobs with `filter.runFilterOnJobs()`
- Check Cuebot logs for execution details

## Contributing Filter Actions

### Contribution Checklist

When contributing new filter actions:

- [ ] Protobuf enum updated
- [ ] Cuebot handler implemented
- [ ] PyCue wrapper updated
- [ ] CueGUI support added
- [ ] CueAdmin integration added
- [ ] Unit tests written
- [ ] Integration tests written
- [ ] Documentation updated
- [ ] Migration script (if needed)
- [ ] VERSION.in updated

## Related Resources

- **[Protocol Buffers Guide](https://developers.google.com/protocol-buffers)** - Protobuf documentation
- **[Contributing to OpenCue](/docs/developer-guide/contributing/)** - Contribution guidelines
- **[Sandbox Testing](/docs/developer-guide/sandbox-testing/)** - Local development environment

## What's Next?

To learn more about filters:

- **[Filters and Actions](/docs/concepts/filters-and-actions/)** - Concepts: Filters and Actions
- **[Using Filters User Guide](/docs/user-guides/using-filters/)** - User Guides: Practical filter usage
- **[Filter Actions Reference](/docs/reference/filter-actions-reference/)** - Reference: Complete filter actions documentation
- **[Filter Tutorial](/docs/tutorials/filter-tutorial/)** - Tutorials: Step-by-step filter examples

## Summary

Key takeaways for filter development:

1. **Architecture spans multiple components** - Proto, Cuebot, PyCue, CueGUI
2. **Follow existing patterns** - Study similar actions for guidance
3. **Test thoroughly** - Unit, integration, and UI tests
4. **Document completely** - Code comments, concepts, user guide, reference, developer guide
5. **Performance matters** - Optimize matchers and actions
6. **Contribute back** - Share improvements with the community

Filter actions are a powerful extension point for customizing OpenCue job automation. Well-designed actions enable sophisticated pipeline workflows while maintaining system performance and reliability.
