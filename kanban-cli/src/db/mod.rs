//! Database module for SQLite connection and schema management

mod connection;
mod schema;

pub use connection::Database;
pub use schema::SCHEMA_SQL;
