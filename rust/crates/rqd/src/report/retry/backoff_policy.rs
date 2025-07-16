use std::pin::Pin;

use super::{
    Outcome, Policy,
    backoff::{Backoff, ExponentialBackoff},
    policy::ClonedRequest,
};
use futures::{FutureExt, TryStreamExt};
use http::{Request, StatusCode, request::Parts};
use http_body_util::{BodyExt, Full};
use prost::bytes::Bytes;
use tonic::body::Body;
use tracing::warn;

type Req = http::Request<Body>;
type Res = http::Response<Body>;

#[derive(Clone)]
/// Policy for implementing retry with backoff strategies.
///
/// # Warning
///
/// This policy should only be used for relatively small requests as the entire
/// request body has to be buffered and stored in memory for retry purposes.
/// Large request bodies could lead to excessive memory usage.
pub struct BackoffPolicy {
    /// Maximum number of retry attempts.
    /// If `None`, will retry indefinitely based on the policy logic.
    pub attempts: Option<usize>,

    /// The backoff strategy to use between retry attempts.
    /// Determines how long to wait before the next retry.
    pub backoff: ExponentialBackoff,
}

impl BackoffPolicy {
    /// Checks if there are still retry attempts left.
    ///
    /// This function determines whether more retry attempts can be made based on
    /// the configured maximum number of attempts.
    ///
    /// Returns:
    ///   - `true` if more retry attempts are allowed
    ///   - `false` if maximum attempts have been reached
    pub fn has_attempts_left(&mut self) -> bool {
        match self.attempts {
            Some(0) => false,
            Some(ref mut attemps_left) => {
                *attemps_left -= 1;
                true
            }
            None => true,
        }
    }
}

impl<E> Policy<Req, Res, E> for BackoffPolicy {
    type Future = tokio::time::Sleep;
    type ClonedOutput = ClonedReq<Req>;
    type ClonedFuture = Pin<Box<dyn std::future::Future<Output = Self::ClonedOutput> + Send>>;

    fn retry(&mut self, _req: &mut Req, result: Result<Res, E>) -> Outcome<Self::Future, Res, E> {
        match &result {
            Ok(response) => {
                if matches!(
                    response.status(),
                    StatusCode::INTERNAL_SERVER_ERROR
                        | StatusCode::BAD_GATEWAY
                        | StatusCode::SERVICE_UNAVAILABLE
                ) {
                    if self.has_attempts_left() {
                        warn!("Retrying for StatusCode={}", response.status());
                        Outcome::Retry(self.backoff.next_backoff())
                    } else {
                        Outcome::Return(result)
                    }
                } else {
                    Outcome::Return(result)
                }
            }
            Err(_err) => {
                if self.has_attempts_left() {
                    warn!("Retrying for Transport error.");
                    // Retry all transport errors
                    Outcome::Retry(self.backoff.next_backoff())
                } else {
                    Outcome::Return(result)
                }
            }
        }
    }

    fn clone_request(&mut self, req: Req) -> Self::ClonedFuture {
        // Convert body to Bytes so it can be cloned
        let (parts, original_body) = req.into_parts();

        Box::pin(consume_unsync_body(original_body).then(|bytes| async move {
            // Re-create the request with the captured bytes in a new BoxBody
            let original_req = create_request(parts.clone(), bytes.clone());
            let cloned_req = create_request(parts, bytes);
            ClonedReq {
                original_req,
                cloned_req,
            }
        }))
    }
}

pub struct ClonedReq<Req> {
    pub original_req: Req,
    pub cloned_req: Req,
}

impl ClonedRequest<Req> for ClonedReq<Req> {
    fn inner(self) -> (Req, Req) {
        (self.original_req, self.cloned_req)
    }
}

/// Consume body stream and return its bytes
async fn consume_unsync_body(body: Body) -> Vec<u8> {
    body.into_data_stream()
        .try_fold(Vec::new(), |mut acc, chunk| async move {
            acc.extend_from_slice(&chunk);
            Ok(acc)
        })
        .await
        .unwrap_or_else(|e| {
            warn!(
                "Failed to consume body stream on grpc backoff policy. {}",
                e
            );
            Vec::new()
        })
}

/// Creates a new HTTP request using the provided parts and body data.
///
/// # Arguments
///
/// * `parts` - The HTTP request parts containing method, URI, headers, etc.
/// * `body` - The bytes that will form the body of the request
///
/// # Returns
///
/// A complete HTTP request with the specified parts and body.
fn create_request(parts: Parts, body: Vec<u8>) -> http::Request<Body> {
    let bytes = Bytes::from(body);
    let full_body = Full::new(bytes);
    let mut request = Request::builder()
        .method(parts.method)
        .uri(parts.uri)
        .version(parts.version)
        .body(Body::new(
            full_body
                .map_err(|_err| tonic::Status::internal("Body error"))
                .boxed(),
        ))
        .expect("Failed to build grpc request from body and parts");

    *request.headers_mut() = parts.headers;

    request
}

#[cfg(test)]
mod tests {
    use crate::report::retry::backoff::MakeBackoff;

    use super::super::backoff::ExponentialBackoffMaker;
    use super::*;
    use http::{Request, StatusCode};
    use http_body_util::Empty;
    use std::time::Duration;
    use tower::util::rng::HasherRng;

    fn create_test_policy() -> BackoffPolicy {
        let mut backoff_maker = ExponentialBackoffMaker::new(
            Duration::from_millis(10),
            Duration::from_millis(100),
            2.0,
            HasherRng::default(),
        )
        .unwrap();

        BackoffPolicy {
            attempts: Some(3),
            backoff: backoff_maker.make_backoff(),
        }
    }

    fn create_test_request() -> Req {
        Request::builder()
            .method("POST")
            .uri("http://example.com")
            .body(Body::new(Empty::new().boxed()))
            .unwrap()
    }

    fn create_response(status: StatusCode) -> Res {
        http::Response::builder()
            .status(status)
            .body(Body::new(Empty::new().boxed()))
            .unwrap()
    }

    #[test]
    fn test_has_attempts_left() {
        // Test with Some(n) attempts
        let mut policy = BackoffPolicy {
            attempts: Some(2),
            backoff: create_test_policy().backoff,
        };

        assert!(policy.has_attempts_left());
        assert!(policy.has_attempts_left());
        assert!(!policy.has_attempts_left());

        // Test with None (unlimited) attempts
        let mut policy = BackoffPolicy {
            attempts: None,
            backoff: create_test_policy().backoff,
        };

        for _ in 0..10 {
            assert!(policy.has_attempts_left());
        }
    }

    #[tokio::test]
    async fn test_retry_success_response() {
        let mut policy = create_test_policy();
        let mut req = create_test_request();

        // Test with 200 OK response
        let res: Result<Res, &str> = Ok(create_response(StatusCode::OK));
        let outcome = policy.retry(&mut req, res);

        match outcome {
            Outcome::Return(_) => {}
            _ => panic!("Expected Outcome::Return for OK response"),
        }
    }

    #[tokio::test]
    async fn test_retry_error_response() {
        let mut policy = create_test_policy();
        let mut req = create_test_request();

        // Test with server error response
        let res: Result<Res, &str> = Ok(create_response(StatusCode::INTERNAL_SERVER_ERROR));
        let outcome = policy.retry(&mut req, res);

        match outcome {
            Outcome::Retry(_) => {}
            _ => panic!("Expected Outcome::Retry for server error response"),
        }
    }

    #[tokio::test]
    async fn test_retry_transport_error() {
        let mut policy = create_test_policy();
        let mut req = create_test_request();

        // Test with transport error
        let res: Result<Res, &str> = Err("transport error");
        let outcome = policy.retry(&mut req, res);

        match outcome {
            Outcome::Retry(_) => {}
            _ => panic!("Expected Outcome::Retry for transport error"),
        }
    }

    #[tokio::test]
    async fn test_no_attempts_left() {
        let mut policy = BackoffPolicy {
            attempts: Some(0),
            backoff: create_test_policy().backoff,
        };
        let mut req = create_test_request();

        // Test with server error but no attempts left
        let res: Result<Res, &str> = Ok(create_response(StatusCode::INTERNAL_SERVER_ERROR));
        let outcome = policy.retry(&mut req, res);

        match outcome {
            Outcome::Return(_) => {}
            _ => panic!("Expected Outcome::Return when no attempts left"),
        }
    }

    #[tokio::test]
    async fn test_clone_request() {
        let mut policy = create_test_policy();
        let req = create_test_request();

        let (new_req, cloned_req) = <BackoffPolicy as Policy<
            http::Request<tonic::body::Body>,
            http::Response<tonic::body::Body>,
            &str,
        >>::clone_request(&mut policy, req)
        .await
        .inner();

        assert_eq!(new_req.method(), cloned_req.method());
        assert_eq!(new_req.uri(), cloned_req.uri());
        assert_eq!(new_req.version(), cloned_req.version());
        assert_eq!(new_req.headers(), cloned_req.headers());
    }
}
