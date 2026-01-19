//! Feature CRUD operations

use chrono::Utc;
use rusqlite::{params, Row};

use crate::db::Database;
use crate::models::{CreateFeatureRequest, Feature, FeatureStatus, FeatureSummary};

use super::{OperationError, Result};

/// Parse a feature from a database row
fn feature_from_row(row: &Row) -> rusqlite::Result<Feature> {
    Ok(Feature {
        id: row.get("id")?,
        name: row.get("name")?,
        description: row.get("description")?,
        status: row
            .get::<_, String>("status")?
            .parse()
            .unwrap_or(FeatureStatus::Active),
        color: row.get("color")?,
        created_at: parse_datetime(row.get::<_, String>("created_at")?),
        updated_at: parse_datetime(row.get::<_, String>("updated_at")?),
    })
}

fn parse_datetime(s: String) -> chrono::DateTime<Utc> {
    chrono::DateTime::parse_from_rfc3339(&s)
        .map(|dt| dt.with_timezone(&Utc))
        .unwrap_or_else(|_| {
            chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%d %H:%M:%S")
                .map(|dt| dt.and_utc())
                .unwrap_or_else(|_| Utc::now())
        })
}

/// Generate a feature ID from the name (slug format)
pub fn generate_feature_id(name: &str) -> String {
    name.to_lowercase()
        .chars()
        .map(|c| if c.is_alphanumeric() { c } else { '-' })
        .collect::<String>()
        .split('-')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("-")
}

/// Create a new feature
pub fn create_feature(db: &Database, request: CreateFeatureRequest) -> Result<Feature> {
    let feature_id = generate_feature_id(&request.name);
    let now = Utc::now().to_rfc3339();

    // Check if feature with this ID already exists
    let exists: bool = db
        .conn()
        .query_row(
            "SELECT 1 FROM features WHERE id = ?",
            params![feature_id],
            |_| Ok(true),
        )
        .unwrap_or(false);

    if exists {
        return Err(OperationError::Validation(format!(
            "Feature '{}' already exists",
            feature_id
        )));
    }

    db.conn().execute(
        r#"
        INSERT INTO features (id, name, description, status, color, created_at, updated_at)
        VALUES (?, ?, ?, 'active', ?, ?, ?)
        "#,
        params![
            feature_id,
            request.name,
            request.description,
            request.color,
            now,
            now,
        ],
    )?;

    get_feature(db, &feature_id)
}

/// Get a feature by ID
pub fn get_feature(db: &Database, feature_id: &str) -> Result<Feature> {
    db.conn()
        .query_row(
            "SELECT * FROM features WHERE id = ?",
            params![feature_id],
            feature_from_row,
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                OperationError::NotFound(format!("Feature not found: {}", feature_id))
            }
            _ => OperationError::Database(e),
        })
}

/// List all features
pub fn list_features(db: &Database, status: Option<FeatureStatus>) -> Result<Vec<Feature>> {
    let sql = if status.is_some() {
        "SELECT * FROM features WHERE status = ? ORDER BY name ASC"
    } else {
        "SELECT * FROM features ORDER BY name ASC"
    };

    let mut stmt = db.conn().prepare(sql)?;

    let features = if let Some(st) = status {
        stmt.query_map(params![st.to_string()], feature_from_row)?
    } else {
        stmt.query_map([], feature_from_row)?
    }
    .collect::<std::result::Result<Vec<_>, _>>()?;

    Ok(features)
}

/// Update feature status
pub fn update_feature_status(
    db: &Database,
    feature_id: &str,
    status: FeatureStatus,
) -> Result<Feature> {
    let now = Utc::now().to_rfc3339();

    db.conn().execute(
        "UPDATE features SET status = ?, updated_at = ? WHERE id = ?",
        params![status.to_string(), now, feature_id],
    )?;

    get_feature(db, feature_id)
}

/// Get feature summary with task counts
pub fn get_feature_summary(db: &Database, feature_id: &str) -> Result<FeatureSummary> {
    let feature = get_feature(db, feature_id)?;

    let counts: (i64, i64, i64, i64, i64, i64) = db.conn().query_row(
        r#"
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END) as todo,
            SUM(CASE WHEN status = 'in-progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
            SUM(CASE WHEN status = 'in-qa' THEN 1 ELSE 0 END) as in_qa,
            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done
        FROM tasks WHERE feature_id = ?
        "#,
        params![feature_id],
        |row| {
            Ok((
                row.get(0)?,
                row.get(1)?,
                row.get(2)?,
                row.get(3)?,
                row.get(4)?,
                row.get(5)?,
            ))
        },
    )?;

    Ok(FeatureSummary {
        feature,
        total_tasks: counts.0,
        todo_count: counts.1,
        in_progress_count: counts.2,
        blocked_count: counts.3,
        in_qa_count: counts.4,
        done_count: counts.5,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_feature_id() {
        assert_eq!(generate_feature_id("Parser Implementation"), "parser-implementation");
        assert_eq!(generate_feature_id("CLI/TUI"), "cli-tui");
        assert_eq!(generate_feature_id("  Multiple   Spaces  "), "multiple-spaces");
    }

    #[test]
    fn test_create_feature() {
        let db = Database::in_memory().unwrap();
        let request = CreateFeatureRequest {
            name: "Parser".to_string(),
            description: Some("CSV parsing functionality".to_string()),
            color: Some("#FF5733".to_string()),
        };

        let feature = create_feature(&db, request).unwrap();
        assert_eq!(feature.id, "parser");
        assert_eq!(feature.name, "Parser");
        assert_eq!(feature.status, FeatureStatus::Active);
    }

    #[test]
    fn test_list_features() {
        let db = Database::in_memory().unwrap();

        // Create two features
        for name in &["Parser", "CLI"] {
            create_feature(
                &db,
                CreateFeatureRequest {
                    name: name.to_string(),
                    description: None,
                    color: None,
                },
            )
            .unwrap();
        }

        let features = list_features(&db, None).unwrap();
        assert_eq!(features.len(), 2);
    }

    #[test]
    fn test_update_feature_status() {
        let db = Database::in_memory().unwrap();
        let feature = create_feature(
            &db,
            CreateFeatureRequest {
                name: "Test Feature".to_string(),
                description: None,
                color: None,
            },
        )
        .unwrap();

        let updated = update_feature_status(&db, &feature.id, FeatureStatus::Completed).unwrap();
        assert_eq!(updated.status, FeatureStatus::Completed);
    }
}
