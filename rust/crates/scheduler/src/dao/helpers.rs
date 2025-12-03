use uuid::Uuid;

/// Parses a UUID string with case-insensitive handling.
///
/// The database stores UUIDs as character varying(36) which may contain
/// uppercase or lowercase hex digits. This function normalizes the case
/// before parsing.
///
/// # Arguments
///
/// * `uuid_str` - String representation of a UUID
///
/// # Returns
///
/// * `Uuid` - Parsed UUID
///
/// # Panics
///
/// Panics if the string is not a valid UUID format. This is intentional
/// as invalid UUIDs in the database represent a data integrity issue.
pub fn parse_uuid(uuid_str: &str) -> Uuid {
    // Uuid::parse_str is case-insensitive by default, but let's be explicit
    Uuid::parse_str(&uuid_str.to_lowercase())
        .unwrap_or_else(|_| panic!("Invalid UUID in database: {}", uuid_str))
}
