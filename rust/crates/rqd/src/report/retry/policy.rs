use std::future::Future;

/// A "retry policy" to classify if a request should be retried.
///
/// # Example
///
/// ```
/// use crate::report::retry::{Outcome, Policy, ClonedRequest};
/// use futures_util::future;
///
/// type Req = String;
/// type Res = String;
///
/// struct MyClonedRequest(Req, Req);
///
/// impl ClonedRequest<Req> for MyClonedRequest {
///     fn inner(self) -> (Req, Req) {
///         (self.0, self.1)
///     }
/// }
///
/// struct Attempts(usize);
///
/// impl<E> Policy<Req, Res, E> for Attempts {
///     type Future = future::Ready<()>;
///     type ClonedOutput = MyClonedRequest;
///     type ClonedFuture = future::Ready<Self::ClonedOutput>;
///
///     fn retry(&mut self, req: &mut Req, result: Result<Res, E>) -> Outcome<Self::Future, Res, E> {
///         match &result {
///             Ok(_) => {
///                 // Treat all `Response`s as success,
///                 // so don't retry...
///                 Outcome::Return(result)
///             },
///             Err(_) => {
///                 // Treat all errors as failures...
///                 // But we limit the number of attempts...
///                 if self.0 > 0 {
///                     // Try again!
///                     self.0 -= 1;
///                     Outcome::Retry(future::ready(()))
///                 } else {
///                     // Used all our attempts, no retry...
///                     Outcome::Return(result)
///                 }
///             }
///         }
///     }
///
///     fn clone_request(&mut self, req: Req) -> Self::ClonedFuture {
///         let cloned = req.clone();
///         future::ready(MyClonedRequest(req, cloned))
///     }
/// }
/// ```
pub trait Policy<Req, Res, E> {
    /// The [`Future`] type returned by [`Policy::retry`].
    type Future: Future<Output = ()>;

    type ClonedOutput: ClonedRequest<Req>;
    type ClonedFuture: Future<Output = Self::ClonedOutput>;

    /// Check the policy if a certain request should be retried.
    ///
    /// This method is passed a mutable reference to the original request, and the
    /// result (either success or error) from the inner service.
    ///
    /// If the request should **not** be retried, return `Outcome::Return` with
    /// the result to be returned by the middleware.
    ///
    /// If the request *should* be retried, return `Outcome::Retry` with a future that will delay
    /// the next retry of the request. This can be used to sleep for a certain
    /// duration, to wait for some external condition to be met before retrying,
    /// or resolve right away, if the request should be retried immediately.
    ///
    /// ## Mutating Requests
    ///
    /// The policy MAY choose to mutate the `req`: if the request is mutated, the
    /// mutated request will be sent to the inner service in the next retry.
    /// This can be helpful for use cases like tracking the retry count in a
    /// header.
    ///
    /// ## Mutating Results
    ///
    /// The policy MAY choose to mutate the result. This enables the retry
    /// policy to convert a failure into a success and vice versa. For example,
    /// if the policy is used to poll while waiting for a state change, the
    /// policy can switch the result to emit a specific error when retries are
    /// exhausted.
    ///
    /// The policy can also record metadata on the request to include
    /// information about the number of retries required or to record that a
    /// failure failed after exhausting all retries.
    ///
    /// [`Service::Response`]: crate::Service::Response
    /// [`Service::Error`]: crate::Service::Error
    fn retry(&mut self, req: &mut Req, result: Result<Res, E>) -> Outcome<Self::Future, Res, E>;
    /// Tries to clone a request before being passed to the inner service.
    ///
    /// If the request cannot be cloned, return [`None`]. Moreover, the retry
    /// function will not be called if the [`None`] is returned.
    fn clone_request(&mut self, req: Req) -> Self::ClonedFuture;
}

pub trait ClonedRequest<Req> {
    fn inner(self) -> (Req, Req);
}

/// Outcome from [`Policy::retry`] with two choices:
/// * don retry, and just return result
/// * or retry by specifying future that might be used to control delay before next call.
#[derive(Debug)]
pub enum Outcome<Fut, Resp, Err> {
    /// Future which will allow delay retry
    Retry(Fut),
    /// Result that will be returned from middleware.
    Return(Result<Resp, Err>),
}

// Ensure `Policy` is object safe
#[cfg(test)]
fn _obj_safe(
    _: Box<
        dyn Policy<
                (),
                (),
                (),
                Future = futures::future::Ready<()>,
                ClonedOutput = (),
                ClonedFuture = futures::future::Ready<()>,
            >,
    >,
) {
}
