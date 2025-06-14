//! Future types

use super::policy::{ClonedRequest, Outcome};
use super::{Policy, Retry};
use futures_core::ready;
use pin_project_lite::pin_project;
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};
use tower_service::Service;
use tracing::trace;

pin_project! {
    /// The [`Future`] returned by a [`Retry`] service.
    #[derive(Debug)]
    pub struct ResponseFuture<P, S, Request>
    where
        P: Policy<Request, S::Response, S::Error>,
        S: Service<Request>,
    {
        request: Option<Request>,
        #[pin]
        retry: Retry<P, S>,
        #[pin]
        state: State<S::Future, P::Future, P::ClonedFuture>,
    }
}

pin_project! {
    #[project = StateProj]
    #[derive(Debug)]
    enum State<F, P, C> {
        Initialized,
        Called {
            #[pin]
            future: F
        },
        Waiting {
            #[pin]
            waiting: P
        },
        Retrying,
        Cloning {
            #[pin]
            future: C,
        }
    }
}

impl<P, S, Request> ResponseFuture<P, S, Request>
where
    P: Policy<Request, S::Response, S::Error>,
    S: Service<Request>,
{
    pub(crate) fn new(retry: Retry<P, S>, request: Request) -> ResponseFuture<P, S, Request> {
        ResponseFuture {
            request: Some(request),
            retry,
            state: State::Initialized,
        }
    }
}

impl<P, S, Request> Future for ResponseFuture<P, S, Request>
where
    P: Policy<Request, S::Response, S::Error>,
    S: Service<Request>,
{
    type Output = Result<S::Response, S::Error>;

    /// Polls the state of this future, handling the underlying retry logic.
    ///
    /// # State Machine
    ///
    /// This function implements a state machine with the following states and transitions:
    ///
    /// - `Initialized`: Starting state, takes the request and prepares for cloning
    ///   → `Cloning`
    ///
    /// - `Cloning`: Waits for the request cloning to complete
    ///   → `Called` (when cloning succeeds and service is ready)
    ///
    /// - `Called`: Waits for the service call to complete
    ///   → `Waiting` (when call finishes but policy decides to retry)
    ///   → Return result (when call finishes and policy decides not to retry)
    ///
    /// - `Waiting`: Waits for the retry policy's backoff period
    ///   → `Retrying` (when backoff completes)
    ///
    /// - `Retrying`: Checks if the service is ready for another attempt
    ///   → `Initialized` (when service is ready, to restart the retry cycle)
    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        let mut this = self.project();

        loop {
            match this.state.as_mut().project() {
                StateProj::Initialized => {
                    // Store original call response
                    trace!("Consumed request at: Initialized");
                    let req = this.request.take().expect("consuming request");
                    let clone_future = this.retry.policy.clone_request(req);
                    this.state.set(State::Cloning {
                        future: clone_future,
                    });
                }

                StateProj::Cloning { future } => {
                    let (orig_req, cloned_req) = ready!(future.poll(cx)).inner();
                    // Put back the request to the ResponseFuture as the Called state
                    // consumed original request
                    trace!("Inserted request at: Cloning");
                    this.request.replace(orig_req);
                    ready!(this.retry.as_mut().project().service.poll_ready(cx))?;
                    let future = this.retry.as_mut().project().service.call(cloned_req);
                    this.state.set(State::Called { future })
                }

                StateProj::Called { future } => {
                    let result = ready!(future.poll(cx));
                    trace!("Checked request at: Called");
                    if let Some(req) = &mut this.request {
                        match this.retry.policy.retry(req, result) {
                            Outcome::Retry(waiting) => this.state.set(State::Waiting { waiting }),
                            Outcome::Return(result) => return Poll::Ready(result),
                        }
                    } else {
                        // This branch is unreachable
                        return Poll::Ready(result);
                    }
                }

                StateProj::Waiting { waiting } => {
                    ready!(waiting.poll(cx));
                    this.state.set(State::Retrying);
                }

                StateProj::Retrying => {
                    ready!(this.retry.as_mut().project().service.poll_ready(cx))?;
                    trace!("Retrying");
                    this.state.set(State::Initialized);
                }
            }
        }
    }
}
