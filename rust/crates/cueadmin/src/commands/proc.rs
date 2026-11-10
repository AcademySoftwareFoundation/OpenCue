// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use miette::Result;
use opencue_proto::criterion::{GreaterThanIntegerSearchCriterion, InRangeIntegerSearchCriterion};
use opencue_proto::host::{ProcGetProcsRequest, ProcSearchCriteria};

use super::Context;
use crate::cli::{ProcCommand, ProcFilter};
use crate::client::rpc_error;
use crate::criteria::RangeFilter;
use crate::output;

const GB_TO_KB: f64 = 1024.0 * 1024.0;
const HOURS_TO_SECONDS: f64 = 3600.0;

/// Runs a `proc` subcommand.
pub async fn run(ctx: &Context, cmd: ProcCommand) -> Result<()> {
    let (filter, logs_only) = match cmd {
        ProcCommand::List(filter) => (filter, false),
        ProcCommand::Logs(filter) => (filter, true),
    };
    let procs = ctx
        .cuebot
        .proc()
        .get_procs(ProcGetProcsRequest {
            r: Some(criteria(filter)),
        })
        .await
        .map_err(rpc_error("listing procs"))?
        .into_inner()
        .procs
        .unwrap_or_default()
        .procs;
    if logs_only {
        for proc in procs {
            println!("{}", proc.log_path);
        }
    } else {
        print!("{}", output::procs(&procs, chrono::Utc::now().timestamp()));
    }
    Ok(())
}

fn criteria(filter: ProcFilter) -> ProcSearchCriteria {
    let mut criteria = ProcSearchCriteria {
        hosts: filter.host,
        jobs: filter.job,
        shows: filter.show,
        allocs: filter.alloc,
        max_results: filter.limit.into_iter().collect(),
        ..Default::default()
    };
    // Cuebot reads memory_less_than as a lower bound, so upper bounds are sent as a range.
    match filter.memory {
        Some(RangeFilter::AtLeast(gb)) => {
            criteria.memory_greater_than = vec![GreaterThanIntegerSearchCriterion {
                value: (gb * GB_TO_KB) as i64,
            }];
        }
        Some(range) => criteria.memory_range = vec![in_range(range, GB_TO_KB)],
        None => {}
    }
    if let Some(range) = filter.duration {
        criteria.duration_range = vec![in_range(range, HOURS_TO_SECONDS)];
    }
    criteria
}

fn in_range(range: RangeFilter, factor: f64) -> InRangeIntegerSearchCriterion {
    let (min, max) = range.bounds(factor);
    InRangeIntegerSearchCriterion { min, max }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn filter() -> ProcFilter {
        ProcFilter {
            show: vec!["pipe".into()],
            host: vec![],
            alloc: vec![],
            job: vec![],
            memory: None,
            duration: None,
            limit: None,
        }
    }

    #[test]
    fn plain_filters() {
        let c = criteria(ProcFilter {
            limit: Some(10),
            ..filter()
        });
        assert_eq!(c.shows, ["pipe"]);
        assert_eq!(c.max_results, [10]);
        assert!(c.memory_range.is_empty() && c.memory_greater_than.is_empty());
    }

    #[test]
    fn memory_filters_in_kb() {
        let c = criteria(ProcFilter {
            memory: Some(RangeFilter::AtLeast(2.0)),
            ..filter()
        });
        assert_eq!(c.memory_greater_than[0].value, 2 * 1024 * 1024);

        let c = criteria(ProcFilter {
            memory: Some(RangeFilter::AtMost(1.0)),
            ..filter()
        });
        assert!(c.memory_greater_than.is_empty());
        assert_eq!(
            (c.memory_range[0].min, c.memory_range[0].max),
            (0, 1024 * 1024)
        );
    }

    #[test]
    fn duration_in_seconds() {
        let c = criteria(ProcFilter {
            duration: Some(RangeFilter::Between(1.0, 2.5)),
            ..filter()
        });
        assert_eq!(
            (c.duration_range[0].min, c.duration_range[0].max),
            (3600, 9000)
        );
    }
}
