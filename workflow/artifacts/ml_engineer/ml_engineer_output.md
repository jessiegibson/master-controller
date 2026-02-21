# ML Engineer Output: Transaction Categorization System

Date: 2026-02-20
Status: Implementation Specification
Depends on: ML Architect output, Categorization Engine Developer output

## 1. Implementation Strategy

The ML Architect recommends a hybrid embedding + classifier approach (Option D) with a traditional ML fallback (Option A). Given the existing codebase constraints -- pure Rust, no Python runtime, local-only execution, and the current placeholder `MlCategorizer` in `src/categorization/ml.rs` -- we implement **Option A (TF-IDF + ensemble)** as the primary approach with a clear upgrade path to Option D when Rust embedding model support matures.

This is a pragmatic decision: Option A can be implemented entirely in Rust with zero external dependencies beyond `serde`/`bincode`, trains in under 1 second on typical datasets, and fits the CLI's offline-first philosophy. The ensemble of Naive Bayes + Logistic Regression + Merchant Lookup achieves strong accuracy on financial transaction data where merchant names are highly predictive.

## 2. Module Structure

```
src/categorization/ml/
  mod.rs              -- Public API, re-exports
  features.rs         -- TF-IDF vocabulary, feature extraction
  naive_bayes.rs      -- Multinomial Naive Bayes text classifier
  logistic.rs         -- Logistic regression on numeric features
  merchant_lookup.rs  -- Merchant-to-category frequency table
  ensemble.rs         -- Weighted ensemble combining all models
  training.rs         -- Training pipeline, cross-validation
  persistence.rs      -- bincode save/load of ModelBundle
  feedback.rs         -- Feedback record type, retraining triggers
```

The existing `src/categorization/ml.rs` file becomes `src/categorization/ml/mod.rs`.

## 3. Key Types and Interfaces

### 3.1 MlCategorizer (replaces placeholder)

```rust
// src/categorization/ml/mod.rs
pub mod features;
pub mod naive_bayes;
pub mod logistic;
pub mod merchant_lookup;
pub mod ensemble;
pub mod training;
pub mod persistence;
pub mod feedback;

pub use ensemble::EnsemblePredictor;
pub use features::{FeatureConfig, FeatureVector, MlFeatureExtractor, SparseVector};
pub use feedback::{FeedbackRecord, FeedbackAction};
pub use persistence::ModelBundle;
pub use training::TrainingPipeline;

use crate::models::Transaction;
use uuid::Uuid;

/// ML prediction result.
#[derive(Debug, Clone)]
pub struct MlPrediction {
    pub category_id: Uuid,
    pub confidence: f32,
    pub alternatives: Vec<(Uuid, f32)>,
    pub method: &'static str,
}

/// Upgraded MlCategorizer wrapping the ensemble.
pub struct MlCategorizer {
    predictor: Option<EnsemblePredictor>,
    model_path: std::path::PathBuf,
}

impl MlCategorizer {
    pub fn new() -> Self {
        Self {
            predictor: None,
            model_path: default_model_path(),
        }
    }

    pub fn load(path: &std::path::Path) -> Result<Self, MlError> {
        let predictor = EnsemblePredictor::load(path)?;
        Ok(Self {
            predictor: Some(predictor),
            model_path: path.to_path_buf(),
        })
    }

    pub fn predict(&self, transaction: &Transaction) -> Option<MlPrediction> {
        self.predictor.as_ref()?.predict_transaction(transaction)
    }

    pub fn is_ready(&self) -> bool {
        self.predictor.as_ref().map_or(false, |p| p.is_trained())
    }

    pub fn learn(&mut self, transaction: &Transaction, category_id: Uuid) {
        if let Some(ref mut p) = self.predictor {
            p.learn_online(transaction, category_id);
        }
    }
}
```

### 3.2 Feature Extraction

```rust
// src/categorization/ml/features.rs
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FeatureConfig {
    pub max_vocab_size: usize,      // default: 5000
    pub min_doc_freq: usize,        // default: 2
    pub max_doc_freq_ratio: f32,    // default: 0.95
    pub ngram_range: (usize, usize),// default: (1, 2)
    pub use_tfidf: bool,            // default: true
}

#[derive(Debug, Clone)]
pub struct FeatureVector {
    pub text_features: SparseVector,   // TF-IDF over description
    pub numeric_features: Vec<f32>,    // [log_amount, is_expense, is_round,
                                       //  weekday_norm, day_norm, month_norm, is_weekend]
    pub merchant: Option<String>,      // Extracted merchant name
}

pub struct MlFeatureExtractor {
    vocabulary: Vocabulary,
    config: FeatureConfig,
}
```

Text tokenization: lowercase, split on non-alphanumeric, filter tokens with length <= 1, generate unigrams and bigrams. Vocabulary is built from training descriptions, filtered by document frequency bounds, and truncated to `max_vocab_size`. IDF weights are precomputed as `ln((N+1)/(df+1)) + 1`.

Numeric features are 7 floats derived from the Transaction's `amount` and `transaction_date` fields. Merchant extraction strips common prefixes (SQ, TST*, SP, PP*, PAYPAL *) and splits on `*`.

### 3.3 Model Trait

```rust
pub trait CategorizationModel: Send + Sync {
    fn name(&self) -> &str;
    fn predict(&self, features: &FeatureVector) -> ModelPrediction;
    fn update(&mut self, features: &FeatureVector, category_id: Uuid, lr: f32);
    fn is_trained(&self) -> bool;
    fn weight(&self) -> f32;
}

pub struct ModelPrediction {
    pub probabilities: Vec<(Uuid, f32)>,  // sorted descending
    pub model_confidence: f32,
}
```

### 3.4 Ensemble Weights

| Model | Weight | Role |
|-------|--------|------|
| Merchant Lookup | 0.40 | Exact match on known merchants |
| Naive Bayes | 0.40 | Text-based classification via TF-IDF |
| Logistic Regression | 0.20 | Numeric feature patterns |

Predictions are combined by weighted sum, normalized, then sorted. The top prediction becomes the output category; the next 3 become alternatives.

## 4. Training Pipeline

### 4.1 Data Flow

```
DuckDB (transactions + feedback tables)
    |
    v
TrainingPipeline::load_training_data()
    |
    v
Vec<(Transaction, Uuid)>  -- labeled examples
    |
    +---> MlFeatureExtractor::fit(descriptions)  -- build vocabulary
    |
    +---> NaiveBayes::fit(examples)
    +---> LogisticRegression::fit(examples, epochs=100)
    +---> MerchantLookup::fit(merchant_examples)
    |
    v
EnsemblePredictor  -- ready for inference
    |
    v
persistence::save(model_path)
```

### 4.2 Training Data Sources

Training data comes from two sources:
1. **Manually categorized transactions** -- `transactions` table where `categorized_by = 'manual'` or `categorized_by = 'rule'` (confirmed by user).
2. **Feedback records** -- `ml_feedback` table storing user corrections to ML predictions.

### 4.3 Cross-Validation

K-fold (k=5) stratified cross-validation runs after training to estimate accuracy. Results are stored in `ModelMetadata` and displayed via `finance-cli ml status`.

### 4.4 Retraining Triggers

| Trigger | Threshold |
|---------|-----------|
| Correction count | 50 new corrections since last train |
| Time elapsed | 7 days with any corrections |
| Manual | User runs `finance-cli ml train` |

### 4.5 DuckDB Schema Addition

```sql
CREATE TABLE IF NOT EXISTS ml_feedback (
    id VARCHAR PRIMARY KEY,
    transaction_id VARCHAR NOT NULL REFERENCES transactions(id),
    predicted_category_id VARCHAR,
    predicted_confidence REAL,
    action VARCHAR NOT NULL,          -- 'accepted', 'corrected', 'skipped'
    final_category_id VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS ml_model_versions (
    id VARCHAR PRIMARY KEY,
    version VARCHAR NOT NULL,
    trained_at TIMESTAMP NOT NULL,
    training_samples INTEGER,
    accuracy REAL,
    model_path VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT true
);
```

## 5. Model Persistence

Models are serialized as a single `ModelBundle` using `bincode`:

```rust
#[derive(serde::Serialize, serde::Deserialize)]
pub struct ModelBundle {
    pub vocabulary: Vocabulary,
    pub naive_bayes: NaiveBayes,
    pub logistic: LogisticRegression,
    pub merchant_lookup: MerchantLookup,
    pub metadata: ModelMetadata,
    pub config: FeatureConfig,
}
```

Default path: `$DATA_DIR/models/categorization.bin` (where `$DATA_DIR` is the finance-cli data directory). Last 3 model versions are retained for rollback.

Expected model size: 1-6 MB depending on vocabulary and merchant table size. Well within the 10 MB constraint.

## 6. Integration with Categorization Engine

The `CategorizationEngine` in `src/categorization/engine.rs` currently only evaluates rules. The integration adds ML as a fallback:

```rust
// Modified CategorizationEngine::categorize
pub fn categorize(&self, transaction: &Transaction) -> CategorizationResult {
    // 1. Try rule-based first (highest priority)
    for rule in &self.rules {
        if rule.is_active && RuleMatcher::matches(rule, transaction) {
            return CategorizationResult { /* ... Rule method, confidence 1.0 */ };
        }
    }

    // 2. Try ML prediction if available
    if let Some(ref ml) = self.ml_categorizer {
        if let Some(prediction) = ml.predict(transaction) {
            let category = self.categories.iter()
                .find(|c| c.id == prediction.category_id).cloned();
            if let Some(cat) = category {
                return CategorizationResult {
                    transaction_id: transaction.id,
                    category: Some(cat),
                    matched_rule: None,
                    confidence: prediction.confidence as f64,
                    method: CategorizationMethod::MachineLearning,
                };
            }
        }
    }

    // 3. No categorization
    CategorizationResult { /* ... None method, confidence 0.0 */ }
}
```

The `CategorizationEngine` struct gains an optional `ml_categorizer: Option<MlCategorizer>` field, initialized from the stored model if one exists.

## 7. Confidence Thresholds and User Interaction

| Confidence | Action |
|------------|--------|
| >= 0.85 | Auto-categorize, no prompt |
| 0.50 - 0.85 | Suggest category, require confirmation |
| < 0.50 | Mark for manual review |

These thresholds are configurable in `settings.toml`:

```toml
[ml]
auto_categorize_threshold = 0.85
suggest_threshold = 0.50
model_path = "models/categorization.bin"
max_model_versions = 3
```

## 8. CLI Commands

```
finance-cli ml status       -- Show model info, accuracy, training date
finance-cli ml train        -- Retrain from all labeled data
finance-cli ml predict <id> -- Show prediction for a specific transaction
finance-cli ml feedback     -- Review and correct recent ML predictions
finance-cli ml rollback     -- Revert to previous model version
```

## 9. Cargo Dependencies to Add

```toml
# In [dependencies]
bincode = "1.3"          # Model serialization

# In [features]
ml = []                  # Feature gate for ML functionality
```

No external ML libraries required. The Naive Bayes, Logistic Regression, and TF-IDF implementations are self-contained Rust code (~800 lines total).

## 10. Online Learning Flow

When a user corrects an ML prediction via the CLI:

1. Correction stored in `ml_feedback` table
2. `MlCategorizer::learn()` called for immediate online update (adjusts model weights incrementally without full retrain)
3. Retraining trigger counter incremented
4. When threshold reached, background retrain queued

Online updates are approximate (SGD step for logistic regression, count adjustment for Naive Bayes, frequency update for merchant lookup) and persisted only when the model is explicitly saved. A full retrain produces a more accurate model from all data.

## 11. Testing Strategy

- **Unit tests**: Each model (NB, LR, MerchantLookup) tested independently with synthetic financial transactions
- **Integration tests**: End-to-end pipeline from raw transactions through training to prediction
- **Property tests**: Using `proptest` to verify predictions always return valid UUIDs and confidence in [0, 1]
- **Benchmark**: Using `criterion` bench `categorization_bench` to verify inference < 100ms per transaction
- **Regression**: Store golden test predictions to detect model behavior changes

## 12. Upgrade Path to Hybrid (Option D)

When Rust embedding model support is available (e.g., via `candle` or `ort` crates):

1. Add `EmbeddingModel` implementing `CategorizationModel` trait
2. Replace TF-IDF `text_features` with 384-dim dense embeddings
3. Retrain classifier head on embedding features
4. Adjust ensemble weights (embedding model gets 0.35, reduce NB to 0.15)
5. Feature-gate behind `ml-embeddings` feature flag

The `CategorizationModel` trait and `EnsemblePredictor` architecture are designed to support this swap without changing the integration layer.

## Summary

| Aspect | Decision |
|--------|----------|
| Approach | TF-IDF + Ensemble (NB + LR + Merchant Lookup) |
| Language | Pure Rust, no external ML libraries |
| Model size | 1-6 MB |
| Inference speed | < 10ms per transaction |
| Training speed | < 5s on 10K transactions |
| Persistence | bincode serialization |
| Online learning | Yes, incremental updates |
| Integration | Falls back from rules -> ML -> uncategorized |
| Feature gate | `ml` feature flag in Cargo.toml |
