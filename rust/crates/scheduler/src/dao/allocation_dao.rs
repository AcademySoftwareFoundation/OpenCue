use miette::{Context, IntoDiagnostic, Result};
use sqlx::{Pool, Postgres};
use std::sync::Arc;
use std::{cmp, collections::HashMap};
use uuid::Uuid;

use crate::{
    dao::helpers::parse_uuid,
    models::{Allocation, CoreSize, Subscription},
    pgpool::connection_pool,
};

pub type ShowId = Uuid;
pub type AllocationName = String;

/// Database model for a subscription.
///
/// Maps directly to the database schema with raw column names.
/// Should be converted to `Subscription` for business logic use.
#[derive(sqlx::FromRow)]
pub struct SubscriptionModel {
    pub pk_subscription: String,
    pub pk_alloc: String,
    pub str_alloc_name: String,
    pub pk_show: String,
    pub int_size: i64,
    pub int_burst: i64,
    pub int_cores: i32,
    pub int_gpus: i32,
}

impl From<SubscriptionModel> for Subscription {
    fn from(val: SubscriptionModel) -> Self {
        // There was a condition on cuebot in the past that would allow negative core values on
        // the subscription table. If bookedcores is negative, use 0.
        let booked_cores = cmp::max(val.int_cores, 0);

        Subscription {
            id: parse_uuid(&val.pk_subscription),
            allocation_id: parse_uuid(&val.pk_alloc),
            allocation_name: val.str_alloc_name,
            show_id: parse_uuid(&val.pk_show),
            size: val.int_size,
            burst: CoreSize::from_multiplied(
                val.int_burst.try_into().expect("int_burst should fit i32"),
            ),
            booked_cores: CoreSize::from_multiplied(booked_cores),
            gpus: val.int_gpus.try_into().expect("int_gpus should fit in u32"),
        }
    }
}

/// Database model for an allocation.
///
/// Maps directly to the database schema with raw column names.
/// Should be converted to `Allocation` for business logic use.
#[derive(sqlx::FromRow)]
pub struct AllocationModel {
    pub pk_alloc: String,
    pub str_name: String,
    pub b_allow_edit: bool,
    pub b_default: bool,
    pub str_tag: Option<String>,
    pub b_billable: bool,
    pub pk_facility: String,
    pub b_enabled: Option<bool>,
}

impl From<AllocationModel> for Allocation {
    fn from(val: AllocationModel) -> Self {
        Allocation {
            id: parse_uuid(&val.pk_alloc),
            name: val.str_name,
            allow_edit: val.b_allow_edit,
            is_default: val.b_default,
            tag: val.str_tag,
            billable: val.b_billable,
            facility_id: parse_uuid(&val.pk_facility),
            enabled: val.b_enabled.unwrap_or(true),
        }
    }
}

/// Data Access Object for allocation and subscription operations.
///
/// An allocation represents a pool of compute resources within a facility that can be
/// assigned to shows through subscriptions. This DAO provides methods to query allocation
/// and subscription data from the database.
///
/// # Purpose
///
/// The `AllocationDao` is responsible for:
/// - Retrieving subscription information organized by show
/// - Querying allocation details and their associated subscriptions
/// - Supporting resource allocation and capacity planning queries
pub struct AllocationDao {
    /// Shared connection pool for database operations.
    #[allow(dead_code)]
    connection_pool: Arc<Pool<Postgres>>,
}

/// SQL query to retrieve all subscriptions with their complete data.
///
/// Returns all columns from the subscription table, which will be used to
/// organize subscriptions by show_id for efficient lookup.
///
/// # Returns
///
/// All subscription records with columns:
/// - pk_subscription, pk_alloc, pk_show, int_size, int_burst,
///   int_cores, float_tier, int_gpus
static SELECT_ALL_SUBSCRIPTIONS: &str = r#"
    SELECT
        s.pk_subscription,
        s.pk_alloc,
        a.str_name as str_alloc_name,
        s.pk_show,
        s.int_size,
        s.int_burst,
        s.int_cores,
        s.float_tier,
        s.int_gpus
    FROM subscription s
    JOIN alloc a ON s.pk_alloc = a.pk_alloc
    ORDER BY pk_show, pk_alloc
"#;

impl AllocationDao {
    /// Creates a new `AllocationDao` instance with a connection pool.
    ///
    /// This constructor initializes the DAO by obtaining a shared database connection pool.
    /// The connection pool is reused across all operations for efficiency.
    ///
    /// # Returns
    ///
    /// Returns `Ok(AllocationDao)` on success, or an error if the connection pool cannot be obtained.
    ///
    /// # Errors
    ///
    /// This function will return an error if:
    /// - The database connection pool cannot be created
    /// - Database connection parameters are invalid
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(AllocationDao {
            connection_pool: pool,
        })
    }

    /// Retrieves all subscriptions organized by show_id and allocation_name.
    ///
    /// This method fetches all subscription records from the database and organizes them
    /// into a nested HashMap structure. The outer HashMap is keyed by show_id (pk_show),
    /// and each value is an inner HashMap keyed by allocation_name (alloc.str_name) containing
    /// the Subscription object. This structure enables efficient lookup of specific
    /// subscriptions by both show and allocation during scheduling operations.
    ///
    /// # Returns
    ///
    /// Returns `Ok(HashMap<String, HashMap<String, Subscription>>)` where:
    /// - Outer Key: `pk_show` - The show identifier
    /// - Inner Key: `pk_alloc` - The allocation identifier
    /// - Inner Value: `Subscription` object containing all subscription data
    ///
    /// # Errors
    ///
    /// This function will return an error if:
    /// - The SQL query execution fails (e.g., connection issues)
    /// - The database schema doesn't match the expected structure
    /// - Data type conversions fail
    pub async fn get_subscriptions_by_show(
        &self,
    ) -> Result<HashMap<ShowId, HashMap<AllocationName, Subscription>>> {
        // Fetch all subscriptions from the database as models
        let subscription_models: Vec<SubscriptionModel> = sqlx::query_as(SELECT_ALL_SUBSCRIPTIONS)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to fetch subscriptions")?;

        // Organize subscriptions by show_id and allocation_name, converting models to business objects
        let mut subscriptions_by_show: HashMap<Uuid, HashMap<String, Subscription>> =
            HashMap::new();

        for subs_model in subscription_models {
            let show_id = parse_uuid(&subs_model.pk_show);
            let allocation_name = subs_model.str_alloc_name.clone();
            let subscription = Subscription::from(subs_model);
            subscriptions_by_show
                .entry(show_id)
                .or_default()
                .insert(allocation_name, subscription);
        }

        Ok(subscriptions_by_show)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    #[ignore] // Requires database setup
    async fn test_get_subscriptions_by_show() -> Result<()> {
        let dao = AllocationDao::new().await?;
        let subscriptions = dao.get_subscriptions_by_show().await?;

        // Verify the structure is correct
        for (show_id, allocation_map) in subscriptions.iter() {
            assert!(
                !allocation_map.is_empty(),
                "Should have at least one subscription"
            );

            for (allocation_name, subscription) in allocation_map {
                assert_eq!(
                    &subscription.show_id, show_id,
                    "Subscription show_id should match the outer HashMap key"
                );
                assert_eq!(
                    &subscription.allocation_id.to_string(),
                    allocation_name,
                    "Subscription allocation_id should match the inner HashMap key"
                );
            }
        }

        Ok(())
    }
}
