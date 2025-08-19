mod dispatcher;
mod error;
mod event_handler;
mod frame_set;
mod job_consumer;

pub use error::{DispatchError, VirtualProcError};
use job_consumer::GeneralJobDispatcher;

pub async fn run() -> miette::Result<()> {
    let job_dispatcher = GeneralJobDispatcher::new().await?;

    job_dispatcher.start().await
}
