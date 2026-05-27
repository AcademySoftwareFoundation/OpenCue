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

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use pg_embed::pg_enums::PgAuthMethod;
use pg_embed::pg_fetch::{PgFetchSettings, PG_V16};
use pg_embed::postgres::{PgEmbed, PgSettings};
use sqlx::postgres::PgPoolOptions;
use sqlx::{Executor, Pool, Postgres};
use tokio::sync::OnceCell;

/// Shared embedded Postgres instance — started once, reused across all tests.
static EMBEDDED_PG: OnceCell<PgEmbed> = OnceCell::const_new();

/// Starts (or returns) the shared embedded Postgres process.
async fn shared_pg() -> &'static PgEmbed {
    EMBEDDED_PG
        .get_or_init(|| async {
            let db_dir = std::env::temp_dir()
                .join(format!("pg_embed_test_{}", std::process::id()));
            // Clean up any stale data from a previous crashed run
            let _ = std::fs::remove_dir_all(&db_dir);

            // Find an available port by binding to port 0
            let port = {
                let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
                listener.local_addr().unwrap().port()
            };

            let pg_settings = PgSettings {
                database_dir: db_dir,
                port,
                user: "postgres".to_string(),
                password: "password".to_string(),
                auth_method: PgAuthMethod::Plain,
                persistent: false,
                timeout: Some(Duration::from_secs(30)),
                migration_dir: None,
            };

            let fetch_settings = PgFetchSettings {
                version: PG_V16,
                ..Default::default()
            };

            let mut pg = PgEmbed::new(pg_settings, fetch_settings)
                .await
                .expect("Failed to create PgEmbed instance");

            pg.setup().await.expect("Failed to setup PgEmbed");
            pg.start_db().await.unwrap_or_else(|e| panic!("Failed to start embedded PG: {:?}", e));

            pg
        })
        .await
}

/// Creates a fresh database with all migrations and seed data applied.
///
/// Each call creates a uniquely named database on the shared embedded Postgres
/// instance, runs the Flyway-style migrations from the cuebot module, and loads
/// the seed data. Returns a connection pool and the full database URI.
#[allow(dead_code)]
pub async fn create_test_db(test_name: &str) -> (Arc<Pool<Postgres>>, String) {
    let pg = shared_pg().await;

    // Unique database name per test invocation
    let db_name = format!(
        "test_{}_{}",
        test_name,
        uuid::Uuid::new_v4().as_simple()
    );

    pg.create_database(&db_name)
        .await
        .unwrap_or_else(|e| panic!("Failed to create database '{}': {}", db_name, e));

    let url = pg.full_db_uri(&db_name);

    let pool = PgPoolOptions::new()
        .max_connections(5)
        .acquire_timeout(Duration::from_secs(10))
        .connect(&url)
        .await
        .unwrap_or_else(|e| panic!("Failed to connect to '{}': {}", db_name, e));

    run_migrations(&pool).await;
    load_seed_data(&pool).await;

    (Arc::new(pool), url)
}

/// Runs Flyway-style V{N}__{description}.sql migrations in version order.
async fn run_migrations(pool: &Pool<Postgres>) {
    let migrations_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("resources/migrations");

    let mut entries: Vec<_> = std::fs::read_dir(&migrations_dir)
        .unwrap_or_else(|e| panic!("Cannot read migrations dir {:?}: {}", migrations_dir, e))
        .filter_map(|e| e.ok())
        .filter(|e| {
            e.path()
                .extension()
                .map_or(false, |ext| ext == "sql")
        })
        .collect();

    // Sort by version number extracted from V{N}__... filename
    entries.sort_by_key(|e| {
        let name = e.file_name().to_string_lossy().to_string();
        let version: u32 = name
            .trim_start_matches('V')
            .split("__")
            .next()
            .expect("Migration file must have V{N}__ prefix")
            .parse()
            .expect("Version number must be a valid u32");
        version
    });

    for entry in entries {
        let sql = std::fs::read_to_string(entry.path()).unwrap_or_else(|e| {
            panic!(
                "Failed to read migration file {:?}: {}",
                entry.path(),
                e
            )
        });
        pool.execute(sql.as_str()).await.unwrap_or_else(|e| {
            panic!(
                "Migration {:?} failed: {}",
                entry.file_name(),
                e
            )
        });
    }
}

/// Loads the seed data (shows, departments, facilities, allocations, subscriptions).
///
/// Some seed data rows may already exist from migrations (e.g. task_lock entries added
/// by V35 and V38 that are also present in seed_data.sql for backwards compatibility).
/// Each statement is executed individually so that duplicate-key conflicts on specific
/// rows don't prevent the rest of the seed data from loading.
async fn load_seed_data(pool: &Pool<Postgres>) {
    let seed_path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("resources/seed_data.sql");
    let sql = std::fs::read_to_string(&seed_path)
        .unwrap_or_else(|e| panic!("Failed to read seed data {:?}: {}", seed_path, e));

    // Split on semicolons and execute each statement individually,
    // ignoring duplicate key violations (error code 23505).
    for statement in sql.split(';') {
        let trimmed = statement.trim();
        if trimmed.is_empty() {
            continue;
        }
        match pool.execute(trimmed).await {
            Ok(_) => {}
            Err(sqlx::Error::Database(db_err))
                if db_err.code().as_deref() == Some("23505") =>
            {
                // Duplicate key — row already inserted by a migration, skip.
            }
            Err(e) => panic!("Seed data statement failed: {}\nSQL: {}", e, trimmed),
        }
    }
}
