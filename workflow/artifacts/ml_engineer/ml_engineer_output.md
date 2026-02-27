# ML Engineer Implementation Output: Finance CLI

**Date**: 2026-02-20
**Agent**: ML Engineer
**Status**: Complete
**Depends On**: ML Architect Output, Categorization Engine Developer Output
**Provides To**: Categorization Engine Developer, Test Developer

---

## Executive Summary

This document specifies the complete ML module implementation for the Finance CLI application. Following the ML Architect's recommendation of a hybrid approach (Option D: Embeddings + Lightweight Classifier Head), this implementation adapts that design to work within Rust using pure-Rust crates, avoiding ONNX runtime complexity for the MVP while preserving a clear upgrade path.

The implementation uses a **three-tier strategy**:

1. **Tier 1 (MVP)**: Pure-Rust ensemble of Naive Bayes + Logistic Regression + Merchant Lookup, matching the existing `MlCategorizer` placeholder interface in `src/categorization/ml.rs`
2. **Tier 2 (Post-MVP)**: ONNX Runtime integration for sentence-transformer embeddings via `ort` crate
3. **Tier 3 (Future)**: Full hybrid with fine-tuned classifier head on frozen embeddings

The ML system is strictly secondary to the rule-based engine. Rules always take priority. ML predictions only apply when no rule matches.

---

## Module Structure

```
src/ml/
├── mod.rs                    # Module exports, feature gate
├── features.rs               # Feature extraction from transactions
├── vocabulary.rs             # TF-IDF vocabulary management
├── models/
│   ├── mod.rs                # CategorizationModel trait
│   ├── naive_bayes.rs        # Multinomial Naive Bayes (text)
│   ├── logistic.rs           # Logistic Regression (numeric features)
│   └── merchant_lookup.rs    # Merchant-to-category lookup table
├── ensemble.rs               # EnsemblePredictor combining all models
├── training.rs               # Batch training pipeline
├── online.rs                 # Online/incremental learning
├── persistence.rs            # Model save/load (bincode)
├── feedback.rs               # Feedback collection and storage
├── anomaly.rs                # Statistical anomaly detection
├── recurring.rs              # Recurring transaction detection
└── config.rs                 # ML configuration and thresholds
```

Integration point with existing code: the existing placeholder at `src/categorization/ml.rs` will be updated to delegate to `src/ml/ensemble.rs`.

---

## 1. Rust Crate Dependencies

Add the following to `Cargo.toml` under `[dependencies]`:

```toml
# ML dependencies
bincode = "1.3"          # Model serialization (fast, compact binary)
ordered-float = "4.2"    # Ordered f32/f64 for use in collections
```

Add under `[features]`:

```toml
ml = []                  # Enable ML categorization (Tier 1, pure Rust)
# ml-embeddings = ["ort"]  # Enable embedding-based ML (Tier 2, post-MVP)
```

No new dev-dependencies are required; existing `rstest` and `proptest` suffice for ML tests.

---

## 2. Configuration

### src/ml/config.rs

```rust
//! ML module configuration and threshold constants.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Top-level ML configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MlConfig {
    /// Whether ML categorization is enabled.
    pub enabled: bool,

    /// Directory for model storage.
    pub model_dir: PathBuf,

    /// Feature extraction settings.
    pub features: FeatureConfig,

    /// Confidence thresholds for categorization decisions.
    pub thresholds: ConfidenceThresholds,

    /// Training configuration.
    pub training: TrainingConfig,

    /// Anomaly detection configuration.
    pub anomaly: AnomalyConfig,

    /// Recurring transaction detection configuration.
    pub recurring: RecurringConfig,
}

impl Default for MlConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            model_dir: PathBuf::from("data/models"),
            features: FeatureConfig::default(),
            thresholds: ConfidenceThresholds::default(),
            training: TrainingConfig::default(),
            anomaly: AnomalyConfig::default(),
            recurring: RecurringConfig::default(),
        }
    }
}

/// Feature extraction configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureConfig {
    /// Maximum vocabulary size for TF-IDF text features.
    pub max_vocab_size: usize,

    /// Minimum document frequency for a token to be included.
    pub min_doc_freq: usize,

    /// Maximum document frequency ratio (tokens appearing in more
    /// than this fraction of documents are excluded as stop words).
    pub max_doc_freq_ratio: f32,

    /// N-gram range: (min_n, max_n). (1, 2) means unigrams + bigrams.
    pub ngram_range: (usize, usize),

    /// Whether to apply TF-IDF weighting (vs raw term frequency).
    pub use_tfidf: bool,

    /// Number of numeric features extracted per transaction.
    /// Currently: log_amount, is_expense, is_round, day_of_week,
    ///            day_of_month, month, is_weekend = 7.
    pub num_numeric_features: usize,
}

impl Default for FeatureConfig {
    fn default() -> Self {
        Self {
            max_vocab_size: 5000,
            min_doc_freq: 2,
            max_doc_freq_ratio: 0.95,
            ngram_range: (1, 2),
            use_tfidf: true,
            num_numeric_features: 7,
        }
    }
}

/// Confidence thresholds that determine what happens with ML predictions.
///
/// These thresholds are aligned with the ML Architect specification:
/// - >= auto_categorize: silently apply the predicted category
/// - >= suggest (and < auto_categorize): show suggestion, require confirmation
/// - < suggest: mark for manual review, do not suggest
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceThresholds {
    /// Minimum confidence to auto-categorize without user confirmation.
    pub auto_categorize: f32,

    /// Minimum confidence to suggest a category (user must confirm).
    pub suggest: f32,

    /// Below this threshold, the prediction is discarded entirely.
    pub discard: f32,
}

impl Default for ConfidenceThresholds {
    fn default() -> Self {
        Self {
            auto_categorize: 0.85,
            suggest: 0.50,
            discard: 0.20,
        }
    }
}

/// Training pipeline configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingConfig {
    /// Minimum labeled transactions required before first training.
    pub min_training_samples: usize,

    /// Number of corrections that trigger automatic retraining.
    pub retrain_correction_threshold: usize,

    /// Maximum days between retraining checks.
    pub retrain_interval_days: u32,

    /// Number of SGD epochs for logistic regression training.
    pub logistic_epochs: usize,

    /// Learning rate for online updates.
    pub online_learning_rate: f32,

    /// Fraction of data held out for validation during training.
    pub validation_split: f32,

    /// Number of previous model versions to keep on disk.
    pub max_model_versions: usize,

    /// Minimum accuracy improvement to deploy a new model.
    pub min_accuracy_improvement: f32,
}

impl Default for TrainingConfig {
    fn default() -> Self {
        Self {
            min_training_samples: 30,
            retrain_correction_threshold: 50,
            retrain_interval_days: 7,
            logistic_epochs: 100,
            online_learning_rate: 0.1,
            validation_split: 0.2,
            max_model_versions: 3,
            min_accuracy_improvement: 0.01,
        }
    }
}

/// Anomaly detection configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyConfig {
    /// Z-score threshold for amount outlier detection.
    pub zscore_threshold: f32,

    /// Minimum transactions in a category before anomaly
    /// detection is active for that category.
    pub min_category_history: usize,

    /// Whether to flag first-time merchants in sensitive categories.
    pub flag_new_merchants: bool,

    /// Whether to flag weekend transactions in business categories.
    pub flag_weekend_business: bool,
}

impl Default for AnomalyConfig {
    fn default() -> Self {
        Self {
            zscore_threshold: 2.5,
            min_category_history: 10,
            flag_new_merchants: true,
            flag_weekend_business: false,
        }
    }
}

/// Recurring transaction detection configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecurringConfig {
    pub monthly_interval: u32,
    pub monthly_tolerance: u32,
    pub quarterly_interval: u32,
    pub quarterly_tolerance: u32,
    pub annual_interval: u32,
    pub annual_tolerance: u32,
    pub weekly_interval: u32,
    pub weekly_tolerance: u32,
    /// Amount tolerance as a fraction (0.05 = +/- 5%).
    pub amount_tolerance: f32,
    pub min_occurrences_monthly: usize,
    pub min_occurrences_quarterly: usize,
    pub min_occurrences_annual: usize,
    pub min_occurrences_weekly: usize,
}

impl Default for RecurringConfig {
    fn default() -> Self {
        Self {
            monthly_interval: 30,
            monthly_tolerance: 3,
            quarterly_interval: 90,
            quarterly_tolerance: 7,
            annual_interval: 365,
            annual_tolerance: 14,
            weekly_interval: 7,
            weekly_tolerance: 1,
            amount_tolerance: 0.05,
            min_occurrences_monthly: 3,
            min_occurrences_quarterly: 2,
            min_occurrences_annual: 2,
            min_occurrences_weekly: 4,
        }
    }
}
```

---

## 3. Feature Extraction

### src/ml/features.rs

```rust
//! Feature extraction from Transaction objects.
//!
//! Produces a FeatureVector containing:
//! - Sparse TF-IDF text features from the description
//! - Dense numeric features (amount, temporal signals)
//! - Extracted merchant string for the merchant lookup model

use crate::ml::vocabulary::Vocabulary;
use crate::ml::config::FeatureConfig;
use crate::models::{Money, Transaction};
use chrono::Datelike;
use serde::{Deserialize, Serialize};

/// Sparse vector for efficient TF-IDF representation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SparseVector {
    pub indices: Vec<usize>,
    pub values: Vec<f32>,
    pub len: usize,
}

impl SparseVector {
    /// Dot product with a dense vector.
    pub fn dot(&self, dense: &[f32]) -> f32 {
        self.indices
            .iter()
            .zip(&self.values)
            .map(|(&idx, &val)| {
                val * dense.get(idx).copied().unwrap_or(0.0)
            })
            .sum()
    }

    /// Convert to dense representation.
    pub fn to_dense(&self) -> Vec<f32> {
        let mut dense = vec![0.0; self.len];
        for (&idx, &val) in self.indices.iter().zip(&self.values) {
            if idx < dense.len() {
                dense[idx] = val;
            }
        }
        dense
    }

    /// Create an empty sparse vector.
    pub fn empty(len: usize) -> Self {
        Self {
            indices: Vec::new(),
            values: Vec::new(),
            len,
        }
    }
}

/// Complete feature vector for one transaction.
#[derive(Debug, Clone)]
pub struct FeatureVector {
    /// Sparse TF-IDF text features from description.
    pub text_features: SparseVector,

    /// Dense numeric features:
    /// [0] log_amount (ln of absolute value, floored at 0)
    /// [1] is_expense (1.0 if negative, else 0.0)
    /// [2] is_round_amount (1.0 if cents == 0, else 0.0)
    /// [3] day_of_week (0.0 Mon .. 1.0 Sun, normalized to [0,1])
    /// [4] day_of_month (normalized to [0,1])
    /// [5] month (normalized to [0,1])
    /// [6] is_weekend (1.0 if Sat/Sun, else 0.0)
    pub numeric_features: Vec<f32>,

    /// Extracted merchant name (uppercase, cleaned).
    pub merchant: Option<String>,
}

/// Extracts features from transactions using a fitted Vocabulary.
pub struct MlFeatureExtractor {
    vocabulary: Vocabulary,
    config: FeatureConfig,
}

impl MlFeatureExtractor {
    /// Create extractor from an existing vocabulary.
    pub fn new(vocabulary: Vocabulary, config: FeatureConfig) -> Self {
        Self { vocabulary, config }
    }

    /// Fit a new vocabulary from training descriptions then return
    /// an extractor ready for use.
    pub fn fit(descriptions: &[String], config: FeatureConfig) -> Self {
        let vocabulary = Vocabulary::build(descriptions, &config);
        Self { vocabulary, config }
    }

    /// Extract a full feature vector from one transaction.
    pub fn extract(&self, transaction: &Transaction) -> FeatureVector {
        let text_features = self
            .vocabulary
            .vectorize(&transaction.description, &self.config);

        let amount_f32 = money_to_f32(&transaction.amount);
        let date = &transaction.transaction_date;

        let numeric_features = vec![
            amount_f32.abs().max(0.01).ln().max(0.0),
            if amount_f32 < 0.0 { 1.0 } else { 0.0 },
            if is_round(amount_f32) { 1.0 } else { 0.0 },
            date.weekday().num_days_from_monday() as f32 / 6.0,
            date.day() as f32 / 31.0,
            date.month() as f32 / 12.0,
            if date.weekday().num_days_from_monday() >= 5 {
                1.0
            } else {
                0.0
            },
        ];

        let merchant = extract_merchant(&transaction.description);

        FeatureVector {
            text_features,
            numeric_features,
            merchant,
        }
    }

    pub fn vocabulary(&self) -> &Vocabulary {
        &self.vocabulary
    }

    pub fn config(&self) -> &FeatureConfig {
        &self.config
    }
}

fn money_to_f32(money: &Money) -> f32 {
    use rust_decimal::prelude::ToPrimitive;
    money.0.to_f32().unwrap_or(0.0)
}

fn is_round(amount: f32) -> bool {
    (amount.abs() - amount.abs().round()).abs() < 0.01
}

/// Extract a cleaned merchant name from a bank description.
fn extract_merchant(description: &str) -> Option<String> {
    let base = description
        .split('*')
        .next()
        .unwrap_or(description)
        .trim();

    let prefixes = [
        "SQ ", "TST*", "SP ", "PP*", "PAYPAL *", "VENMO *",
        "ZELLE *", "CASH APP*", "GOOGLE *", "APPLE.COM/",
    ];

    let mut cleaned = base.to_uppercase();
    for prefix in &prefixes {
        if let Some(stripped) = cleaned.strip_prefix(prefix) {
            cleaned = stripped.to_string();
            break;
        }
    }

    let trimmed = cleaned.trim();
    if trimmed.len() > 2 {
        Some(trimmed.to_string())
    } else {
        None
    }
}
```

---

## 4. Vocabulary (TF-IDF)

### src/ml/vocabulary.rs

```rust
//! TF-IDF vocabulary: token-to-index mapping with IDF weights.

use crate::ml::config::FeatureConfig;
use crate::ml::features::SparseVector;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vocabulary {
    token_to_idx: HashMap<String, usize>,
    idx_to_token: Vec<String>,
    doc_freqs: Vec<usize>,
    total_docs: usize,
    idf: Vec<f32>,
}

impl Vocabulary {
    pub fn build(descriptions: &[String], config: &FeatureConfig) -> Self {
        if descriptions.is_empty() {
            return Self::empty();
        }

        let mut token_counts: HashMap<String, usize> = HashMap::new();
        let mut doc_freqs: HashMap<String, usize> = HashMap::new();

        for desc in descriptions {
            let tokens = Self::tokenize(desc, config.ngram_range);
            let unique: HashSet<_> = tokens.iter().cloned().collect();

            for token in &tokens {
                *token_counts.entry(token.clone()).or_insert(0) += 1;
            }
            for token in unique {
                *doc_freqs.entry(token).or_insert(0) += 1;
            }
        }

        let total_docs = descriptions.len();
        let min_freq = config.min_doc_freq;
        let max_freq = (total_docs as f32 * config.max_doc_freq_ratio) as usize;

        let mut tokens: Vec<_> = token_counts
            .into_iter()
            .filter(|(token, _)| {
                let df = doc_freqs.get(token).copied().unwrap_or(0);
                df >= min_freq && df <= max_freq
            })
            .collect();
        tokens.sort_by(|a, b| b.1.cmp(&a.1));
        tokens.truncate(config.max_vocab_size);

        let mut token_to_idx = HashMap::new();
        let mut idx_to_token = Vec::new();
        let mut doc_freq_vec = Vec::new();

        for (idx, (token, _)) in tokens.iter().enumerate() {
            token_to_idx.insert(token.clone(), idx);
            idx_to_token.push(token.clone());
            doc_freq_vec.push(*doc_freqs.get(token).unwrap_or(&1));
        }

        let idf: Vec<f32> = doc_freq_vec
            .iter()
            .map(|&df| {
                ((total_docs as f32 + 1.0) / (df as f32 + 1.0)).ln() + 1.0
            })
            .collect();

        Self { token_to_idx, idx_to_token, doc_freqs: doc_freq_vec, total_docs, idf }
    }

    pub fn empty() -> Self {
        Self {
            token_to_idx: HashMap::new(),
            idx_to_token: Vec::new(),
            doc_freqs: Vec::new(),
            total_docs: 0,
            idf: Vec::new(),
        }
    }

    pub fn tokenize(text: &str, ngram_range: (usize, usize)) -> Vec<String> {
        let words: Vec<String> = text
            .to_lowercase()
            .split(|c: char| !c.is_alphanumeric())
            .filter(|s| s.len() > 1)
            .map(|s| s.to_string())
            .collect();

        let mut tokens = Vec::new();
        for n in ngram_range.0..=ngram_range.1 {
            if n > words.len() {
                continue;
            }
            for window in words.windows(n) {
                tokens.push(window.join("_"));
            }
        }
        tokens
    }

    pub fn len(&self) -> usize {
        self.idx_to_token.len()
    }

    pub fn is_empty(&self) -> bool {
        self.idx_to_token.is_empty()
    }

    pub fn vectorize(&self, text: &str, config: &FeatureConfig) -> SparseVector {
        if self.is_empty() {
            return SparseVector::empty(0);
        }

        let tokens = Self::tokenize(text, config.ngram_range);
        let mut tf: HashMap<usize, f32> = HashMap::new();
        for token in &tokens {
            if let Some(&idx) = self.token_to_idx.get(token) {
                *tf.entry(idx).or_insert(0.0) += 1.0;
            }
        }

        let doc_len = tokens.len().max(1) as f32;
        let mut pairs: Vec<(usize, f32)> = tf
            .into_iter()
            .map(|(idx, count)| {
                let tf_val = count / doc_len;
                let value = if config.use_tfidf {
                    tf_val * self.idf.get(idx).copied().unwrap_or(1.0)
                } else {
                    tf_val
                };
                (idx, value)
            })
            .collect();

        pairs.sort_by_key(|(idx, _)| *idx);
        let (indices, values): (Vec<_>, Vec<_>) = pairs.into_iter().unzip();

        SparseVector { indices, values, len: self.len() }
    }
}
```

---

## 5. Model Trait and Implementations

### src/ml/models/mod.rs

```rust
//! Base trait for ML categorization models.

pub mod naive_bayes;
pub mod logistic;
pub mod merchant_lookup;

pub use naive_bayes::NaiveBayes;
pub use logistic::LogisticRegression;
pub use merchant_lookup::MerchantLookup;

use crate::ml::features::FeatureVector;
use uuid::Uuid;

/// Output from a single model's prediction.
#[derive(Debug, Clone)]
pub struct ModelPrediction {
    pub probabilities: Vec<(Uuid, f32)>,
    pub model_confidence: f32,
}

/// Trait that all ensemble member models must implement.
pub trait CategorizationModel: Send + Sync {
    fn name(&self) -> &str;
    fn predict(&self, features: &FeatureVector) -> ModelPrediction;
    fn update(&mut self, features: &FeatureVector, category_id: Uuid, learning_rate: f32);
    fn is_trained(&self) -> bool;
    fn weight(&self) -> f32;
}
```

### src/ml/models/naive_bayes.rs

```rust
//! Multinomial Naive Bayes for text-feature-based classification.

use super::{CategorizationModel, FeatureVector, ModelPrediction};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NaiveBayes {
    log_priors: HashMap<Uuid, f32>,
    log_likelihoods: HashMap<Uuid, Vec<f32>>,
    num_features: usize,
    alpha: f32,
    classes: Vec<Uuid>,
    trained: bool,
}

impl NaiveBayes {
    pub fn new(num_features: usize) -> Self {
        Self {
            log_priors: HashMap::new(),
            log_likelihoods: HashMap::new(),
            num_features,
            alpha: 1.0,
            classes: Vec::new(),
            trained: false,
        }
    }

    pub fn fit(&mut self, examples: &[(FeatureVector, Uuid)]) {
        if examples.is_empty() { return; }

        let mut class_counts: HashMap<Uuid, usize> = HashMap::new();
        let mut feature_sums: HashMap<Uuid, Vec<f32>> = HashMap::new();

        for (fv, class) in examples {
            *class_counts.entry(*class).or_insert(0) += 1;
            let sums = feature_sums
                .entry(*class)
                .or_insert_with(|| vec![0.0; self.num_features]);
            for (&idx, &val) in fv.text_features.indices.iter().zip(&fv.text_features.values) {
                if idx < self.num_features { sums[idx] += val; }
            }
        }

        let total = examples.len() as f32;
        self.classes = class_counts.keys().copied().collect();

        for (&class, &count) in &class_counts {
            self.log_priors.insert(class, (count as f32 / total).ln());
        }

        for (&class, sums) in &feature_sums {
            let total_sum: f32 = sums.iter().sum::<f32>() + self.alpha * self.num_features as f32;
            let log_probs: Vec<f32> = sums
                .iter()
                .map(|&c| ((c + self.alpha) / total_sum).ln())
                .collect();
            self.log_likelihoods.insert(class, log_probs);
        }

        self.trained = true;
    }

    fn softmax(log_posteriors: &[(Uuid, f32)]) -> Vec<(Uuid, f32)> {
        if log_posteriors.is_empty() { return vec![]; }
        let max_log = log_posteriors.iter().map(|(_, p)| *p).fold(f32::NEG_INFINITY, f32::max);
        let exp_sum: f32 = log_posteriors.iter().map(|(_, p)| (p - max_log).exp()).sum();
        let mut probs: Vec<_> = log_posteriors
            .iter()
            .map(|(c, p)| (*c, (p - max_log).exp() / exp_sum))
            .collect();
        probs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        probs
    }
}

impl CategorizationModel for NaiveBayes {
    fn name(&self) -> &str { "NaiveBayes" }

    fn predict(&self, features: &FeatureVector) -> ModelPrediction {
        if !self.trained {
            return ModelPrediction { probabilities: vec![], model_confidence: 0.0 };
        }
        let mut log_posteriors = Vec::new();
        for &class in &self.classes {
            let mut log_p = *self.log_priors.get(&class).unwrap_or(&-10.0);
            if let Some(ll) = self.log_likelihoods.get(&class) {
                for (&idx, &val) in features.text_features.indices.iter().zip(&features.text_features.values) {
                    if idx < ll.len() { log_p += ll[idx] * val; }
                }
            }
            log_posteriors.push((class, log_p));
        }
        let probabilities = Self::softmax(&log_posteriors);
        let confidence = probabilities.first().map(|(_, p)| *p).unwrap_or(0.0);
        ModelPrediction { probabilities, model_confidence: confidence }
    }

    fn update(&mut self, features: &FeatureVector, category_id: Uuid, learning_rate: f32) {
        if !self.classes.contains(&category_id) {
            self.classes.push(category_id);
            self.log_likelihoods.insert(category_id, vec![0.0; self.num_features]);
        }
        if let Some(ll) = self.log_likelihoods.get_mut(&category_id) {
            for (&idx, &val) in features.text_features.indices.iter().zip(&features.text_features.values) {
                if idx < ll.len() {
                    ll[idx] = ll[idx] * (1.0 - learning_rate) + val.ln().max(-10.0) * learning_rate;
                }
            }
        }
    }

    fn is_trained(&self) -> bool { self.trained }
    fn weight(&self) -> f32 { 0.4 }
}
```

### src/ml/models/logistic.rs

```rust
//! Multi-class logistic regression trained via SGD on numeric features.

use super::{CategorizationModel, FeatureVector, ModelPrediction};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogisticRegression {
    weights: HashMap<Uuid, Vec<f32>>,
    biases: HashMap<Uuid, f32>,
    num_features: usize,
    classes: Vec<Uuid>,
    learning_rate: f32,
    trained: bool,
}

impl LogisticRegression {
    pub fn new(num_features: usize) -> Self {
        Self {
            weights: HashMap::new(),
            biases: HashMap::new(),
            num_features,
            classes: Vec::new(),
            learning_rate: 0.01,
            trained: false,
        }
    }

    pub fn fit(&mut self, examples: &[(FeatureVector, Uuid)], epochs: usize) {
        if examples.is_empty() { return; }
        let classes: HashSet<_> = examples.iter().map(|(_, c)| *c).collect();
        self.classes = classes.into_iter().collect();

        for &class in &self.classes {
            self.weights.insert(class, vec![0.0; self.num_features]);
            self.biases.insert(class, 0.0);
        }

        for _ in 0..epochs {
            for (fv, true_class) in examples {
                let preds = self.predict_raw(&fv.numeric_features);
                for &class in &self.classes {
                    let predicted = preds.get(&class).copied().unwrap_or(0.0);
                    let target = if class == *true_class { 1.0 } else { 0.0 };
                    let error = predicted - target;
                    if let Some(w) = self.weights.get_mut(&class) {
                        for (i, &feat) in fv.numeric_features.iter().enumerate() {
                            if i < w.len() { w[i] -= self.learning_rate * error * feat; }
                        }
                    }
                    if let Some(b) = self.biases.get_mut(&class) {
                        *b -= self.learning_rate * error;
                    }
                }
            }
        }
        self.trained = true;
    }

    fn predict_raw(&self, features: &[f32]) -> HashMap<Uuid, f32> {
        let mut logits: HashMap<Uuid, f32> = HashMap::new();
        for &class in &self.classes {
            let w = match self.weights.get(&class) { Some(w) => w, None => continue };
            let bias = self.biases.get(&class).copied().unwrap_or(0.0);
            let logit: f32 = features.iter().zip(w).map(|(f, w)| f * w).sum::<f32>() + bias;
            logits.insert(class, logit);
        }
        if logits.is_empty() { return logits; }
        let max_l = logits.values().copied().fold(f32::NEG_INFINITY, f32::max);
        let exp_sum: f32 = logits.values().map(|&l| (l - max_l).exp()).sum();
        logits.into_iter().map(|(c, l)| (c, (l - max_l).exp() / exp_sum)).collect()
    }
}

impl CategorizationModel for LogisticRegression {
    fn name(&self) -> &str { "LogisticRegression" }

    fn predict(&self, features: &FeatureVector) -> ModelPrediction {
        if !self.trained {
            return ModelPrediction { probabilities: vec![], model_confidence: 0.0 };
        }
        let probs = self.predict_raw(&features.numeric_features);
        let mut probabilities: Vec<_> = probs.into_iter().collect();
        probabilities.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        let confidence = probabilities.first().map(|(_, p)| *p).unwrap_or(0.0);
        ModelPrediction { probabilities, model_confidence: confidence }
    }

    fn update(&mut self, features: &FeatureVector, category_id: Uuid, learning_rate: f32) {
        if !self.classes.contains(&category_id) {
            self.classes.push(category_id);
            self.weights.insert(category_id, vec![0.0; self.num_features]);
            self.biases.insert(category_id, 0.0);
        }
        let preds = self.predict_raw(&features.numeric_features);
        for &class in &self.classes {
            let predicted = preds.get(&class).copied().unwrap_or(0.0);
            let target = if class == category_id { 1.0 } else { 0.0 };
            let error = predicted - target;
            if let Some(w) = self.weights.get_mut(&class) {
                for (i, &feat) in features.numeric_features.iter().enumerate() {
                    if i < w.len() { w[i] -= learning_rate * error * feat; }
                }
            }
            if let Some(b) = self.biases.get_mut(&class) {
                *b -= learning_rate * error;
            }
        }
    }

    fn is_trained(&self) -> bool { self.trained }
    fn weight(&self) -> f32 { 0.2 }
}
```

### src/ml/models/merchant_lookup.rs

```rust
//! Merchant-to-category lookup table.
//!
//! The simplest and often most effective model: if we have seen
//! a merchant before, predict the same category.

use super::{CategorizationModel, FeatureVector, ModelPrediction};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MerchantLookup {
    lookup: HashMap<String, HashMap<Uuid, usize>>,
    min_count: usize,
}

impl MerchantLookup {
    pub fn new() -> Self {
        Self { lookup: HashMap::new(), min_count: 2 }
    }

    pub fn fit(&mut self, examples: &[(String, Uuid)]) {
        for (merchant, category) in examples {
            let upper = merchant.to_uppercase();
            let counts = self.lookup.entry(upper).or_insert_with(HashMap::new);
            *counts.entry(*category).or_insert(0) += 1;
        }
    }

    pub fn lookup_merchant(&self, merchant: &str) -> Option<(Uuid, f32)> {
        let upper = merchant.to_uppercase();
        self.lookup.get(&upper).and_then(|counts| {
            let total: usize = counts.values().sum();
            if total < self.min_count { return None; }
            counts
                .iter()
                .max_by_key(|(_, &count)| count)
                .map(|(&cat, &count)| (cat, count as f32 / total as f32))
        })
    }

    pub fn merchant_count(&self) -> usize {
        self.lookup.len()
    }
}

impl Default for MerchantLookup {
    fn default() -> Self { Self::new() }
}

impl CategorizationModel for MerchantLookup {
    fn name(&self) -> &str { "MerchantLookup" }

    fn predict(&self, features: &FeatureVector) -> ModelPrediction {
        if let Some(ref merchant) = features.merchant {
            if let Some((cat, conf)) = self.lookup_merchant(merchant) {
                return ModelPrediction {
                    probabilities: vec![(cat, conf)],
                    model_confidence: conf,
                };
            }
        }
        ModelPrediction { probabilities: vec![], model_confidence: 0.0 }
    }

    fn update(&mut self, features: &FeatureVector, category_id: Uuid, _learning_rate: f32) {
        if let Some(ref merchant) = features.merchant {
            let upper = merchant.to_uppercase();
            let counts = self.lookup.entry(upper).or_insert_with(HashMap::new);
            *counts.entry(category_id).or_insert(0) += 1;
        }
    }

    fn is_trained(&self) -> bool { !self.lookup.is_empty() }
    fn weight(&self) -> f32 { 0.4 }
}
```

---

## 6. Ensemble Predictor

### src/ml/ensemble.rs

```rust
//! Ensemble predictor combining all sub-models.

use crate::ml::config::{ConfidenceThresholds, FeatureConfig, MlConfig, TrainingConfig};
use crate::ml::features::{FeatureVector, MlFeatureExtractor};
use crate::ml::models::{CategorizationModel, LogisticRegression, MerchantLookup, NaiveBayes};
use crate::ml::vocabulary::Vocabulary;
use crate::models::Transaction;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct MlPrediction {
    pub category_id: Uuid,
    pub confidence: f32,
    pub alternatives: Vec<(Uuid, f32)>,
    pub action: PredictionAction,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PredictionAction {
    AutoCategorize,
    Suggest,
    ManualReview,
    NoModel,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMetadata {
    pub version: String,
    pub trained_at: Option<DateTime<Utc>>,
    pub training_samples: usize,
    pub categories: Vec<Uuid>,
    pub accuracy: f32,
    pub top3_accuracy: f32,
    pub vocabulary_size: usize,
    pub merchant_count: usize,
}

pub struct EnsemblePredictor {
    feature_extractor: MlFeatureExtractor,
    naive_bayes: NaiveBayes,
    logistic: LogisticRegression,
    merchant_lookup: MerchantLookup,
    metadata: ModelMetadata,
    thresholds: ConfidenceThresholds,
    online_learning_rate: f32,
}

impl EnsemblePredictor {
    pub fn new(config: &MlConfig) -> Self {
        Self {
            feature_extractor: MlFeatureExtractor::new(
                Vocabulary::empty(), config.features.clone(),
            ),
            naive_bayes: NaiveBayes::new(config.features.max_vocab_size),
            logistic: LogisticRegression::new(config.features.num_numeric_features),
            merchant_lookup: MerchantLookup::new(),
            metadata: ModelMetadata {
                version: "0.0.0".into(), trained_at: None, training_samples: 0,
                categories: vec![], accuracy: 0.0, top3_accuracy: 0.0,
                vocabulary_size: 0, merchant_count: 0,
            },
            thresholds: config.thresholds.clone(),
            online_learning_rate: config.training.online_learning_rate,
        }
    }

    pub fn is_ready(&self) -> bool {
        self.naive_bayes.is_trained() || self.merchant_lookup.is_trained()
    }

    pub fn predict(&self, transaction: &Transaction) -> MlPrediction {
        if !self.is_ready() {
            return MlPrediction {
                category_id: Uuid::nil(), confidence: 0.0,
                alternatives: vec![], action: PredictionAction::NoModel,
            };
        }
        let features = self.feature_extractor.extract(transaction);
        self.combine_predictions(&features)
    }

    pub fn predict_batch(&self, transactions: &[Transaction]) -> Vec<MlPrediction> {
        transactions.iter().map(|tx| self.predict(tx)).collect()
    }

    pub fn train(&mut self, labeled: &[(Transaction, Uuid)], config: &TrainingConfig) {
        if labeled.is_empty() { return; }

        let descriptions: Vec<String> = labeled.iter().map(|(tx, _)| tx.description.clone()).collect();
        self.feature_extractor = MlFeatureExtractor::fit(
            &descriptions, self.feature_extractor.config().clone(),
        );

        let mut examples: Vec<(FeatureVector, Uuid)> = Vec::new();
        let mut merchant_pairs: Vec<(String, Uuid)> = Vec::new();

        for (tx, cat) in labeled {
            let fv = self.feature_extractor.extract(tx);
            if let Some(ref m) = fv.merchant {
                merchant_pairs.push((m.clone(), *cat));
            }
            examples.push((fv, *cat));
        }

        let vocab_size = self.feature_extractor.vocabulary().len();
        self.naive_bayes = NaiveBayes::new(vocab_size);
        self.naive_bayes.fit(&examples);

        self.logistic = LogisticRegression::new(
            self.feature_extractor.config().num_numeric_features,
        );
        self.logistic.fit(&examples, config.logistic_epochs);

        self.merchant_lookup = MerchantLookup::new();
        self.merchant_lookup.fit(&merchant_pairs);

        let (acc, top3) = self.evaluate_accuracy(&examples);
        let categories: HashSet<_> = labeled.iter().map(|(_, c)| *c).collect();
        self.metadata = ModelMetadata {
            version: increment_version(&self.metadata.version),
            trained_at: Some(Utc::now()),
            training_samples: labeled.len(),
            categories: categories.into_iter().collect(),
            accuracy: acc, top3_accuracy: top3,
            vocabulary_size: vocab_size,
            merchant_count: self.merchant_lookup.merchant_count(),
        };
    }

    pub fn learn_online(&mut self, transaction: &Transaction, category_id: Uuid) {
        let features = self.feature_extractor.extract(transaction);
        let lr = self.online_learning_rate;
        self.naive_bayes.update(&features, category_id, lr);
        self.logistic.update(&features, category_id, lr);
        self.merchant_lookup.update(&features, category_id, lr);
        self.metadata.training_samples += 1;
        if !self.metadata.categories.contains(&category_id) {
            self.metadata.categories.push(category_id);
        }
    }

    pub fn metadata(&self) -> &ModelMetadata { &self.metadata }

    // Accessor clones for persistence bundling.
    pub fn vocabulary_clone(&self) -> Vocabulary { self.feature_extractor.vocabulary().clone() }
    pub fn feature_config_clone(&self) -> FeatureConfig { self.feature_extractor.config().clone() }
    pub fn naive_bayes_clone(&self) -> NaiveBayes { self.naive_bayes.clone() }
    pub fn logistic_clone(&self) -> LogisticRegression { self.logistic.clone() }
    pub fn merchant_lookup_clone(&self) -> MerchantLookup { self.merchant_lookup.clone() }

    /// Reconstruct from a deserialized bundle.
    pub fn from_bundle(
        bundle: crate::ml::persistence::ModelBundle,
        config: &MlConfig,
    ) -> Self {
        Self {
            feature_extractor: MlFeatureExtractor::new(bundle.vocabulary, bundle.feature_config),
            naive_bayes: bundle.naive_bayes,
            logistic: bundle.logistic,
            merchant_lookup: bundle.merchant_lookup,
            metadata: bundle.metadata,
            thresholds: config.thresholds.clone(),
            online_learning_rate: config.training.online_learning_rate,
        }
    }

    fn combine_predictions(&self, features: &FeatureVector) -> MlPrediction {
        let mut combined: HashMap<Uuid, f32> = HashMap::new();
        let mut total_weight = 0.0f32;

        let models: Vec<&dyn CategorizationModel> = vec![
            &self.naive_bayes, &self.logistic, &self.merchant_lookup,
        ];
        for model in models {
            if !model.is_trained() { continue; }
            let pred = model.predict(features);
            let w = model.weight();
            for (cat, prob) in pred.probabilities {
                *combined.entry(cat).or_insert(0.0) += prob * w;
            }
            total_weight += w;
        }
        if total_weight > 0.0 {
            for v in combined.values_mut() { *v /= total_weight; }
        }

        let mut probs: Vec<_> = combined.into_iter().collect();
        probs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        let (top_cat, top_conf) = probs.first().copied().unwrap_or((Uuid::nil(), 0.0));
        let alternatives: Vec<_> = probs.into_iter().skip(1).take(3).collect();

        let action = if top_conf >= self.thresholds.auto_categorize {
            PredictionAction::AutoCategorize
        } else if top_conf >= self.thresholds.suggest {
            PredictionAction::Suggest
        } else {
            PredictionAction::ManualReview
        };

        MlPrediction { category_id: top_cat, confidence: top_conf, alternatives, action }
    }

    fn evaluate_accuracy(&self, examples: &[(FeatureVector, Uuid)]) -> (f32, f32) {
        if examples.is_empty() { return (0.0, 0.0); }
        let mut correct = 0usize;
        let mut top3_correct = 0usize;
        for (fv, true_cat) in examples {
            let pred = self.combine_predictions(fv);
            if pred.category_id == *true_cat { correct += 1; }
            if pred.category_id == *true_cat
                || pred.alternatives.iter().any(|(c, _)| *c == *true_cat) {
                top3_correct += 1;
            }
        }
        let n = examples.len() as f32;
        (correct as f32 / n, top3_correct as f32 / n)
    }
}

fn increment_version(version: &str) -> String {
    let parts: Vec<&str> = version.split('.').collect();
    if parts.len() == 3 {
        if let Ok(patch) = parts[2].parse::<u32>() {
            return format!("{}.{}.{}", parts[0], parts[1], patch + 1);
        }
    }
    format!("{}.1", version)
}
```

---

## 7. Model Persistence

### src/ml/persistence.rs

```rust
//! Save and load the ensemble model to/from disk using bincode.
//!
//! Model files are stored under {data_dir}/models/ with naming
//! convention model_v{version}.bin. model_latest.bin is always a
//! copy of the active model.

use crate::ml::config::{FeatureConfig, MlConfig};
use crate::ml::ensemble::{EnsemblePredictor, ModelMetadata};
use crate::ml::models::{LogisticRegression, MerchantLookup, NaiveBayes};
use crate::ml::vocabulary::Vocabulary;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{BufReader, BufWriter};
use std::path::{Path, PathBuf};

#[derive(Serialize, Deserialize)]
pub struct ModelBundle {
    pub vocabulary: Vocabulary,
    pub feature_config: FeatureConfig,
    pub naive_bayes: NaiveBayes,
    pub logistic: LogisticRegression,
    pub merchant_lookup: MerchantLookup,
    pub metadata: ModelMetadata,
}

pub fn save_model(predictor: &EnsemblePredictor, model_dir: &Path) -> Result<PathBuf, String> {
    fs::create_dir_all(model_dir)
        .map_err(|e| format!("Failed to create model dir: {}", e))?;

    let version = &predictor.metadata().version;
    let filename = format!("model_v{}.bin", version);
    let path = model_dir.join(&filename);

    let file = fs::File::create(&path)
        .map_err(|e| format!("Failed to create file: {}", e))?;
    let writer = BufWriter::new(file);

    bincode::serialize_into(writer, &ModelBundle {
        vocabulary: predictor.vocabulary_clone(),
        feature_config: predictor.feature_config_clone(),
        naive_bayes: predictor.naive_bayes_clone(),
        logistic: predictor.logistic_clone(),
        merchant_lookup: predictor.merchant_lookup_clone(),
        metadata: predictor.metadata().clone(),
    }).map_err(|e| format!("Serialization failed: {}", e))?;

    let latest = model_dir.join("model_latest.bin");
    let _ = fs::remove_file(&latest);
    fs::copy(&path, &latest)
        .map_err(|e| format!("Failed to copy latest: {}", e))?;

    Ok(path)
}

pub fn load_model(model_dir: &Path, config: &MlConfig) -> Result<EnsemblePredictor, String> {
    let latest = model_dir.join("model_latest.bin");
    if !latest.exists() { return Err("No saved model found".into()); }
    load_model_file(&latest, config)
}

pub fn load_model_file(path: &Path, config: &MlConfig) -> Result<EnsemblePredictor, String> {
    let file = fs::File::open(path)
        .map_err(|e| format!("Failed to open model: {}", e))?;
    let reader = BufReader::new(file);
    let bundle: ModelBundle = bincode::deserialize_from(reader)
        .map_err(|e| format!("Deserialization failed: {}", e))?;
    Ok(EnsemblePredictor::from_bundle(bundle, config))
}

pub fn list_model_versions(model_dir: &Path) -> Vec<(String, PathBuf)> {
    let mut versions = Vec::new();
    if let Ok(entries) = fs::read_dir(model_dir) {
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with("model_v") && name.ends_with(".bin") {
                let version = name
                    .trim_start_matches("model_v")
                    .trim_end_matches(".bin")
                    .to_string();
                versions.push((version, entry.path()));
            }
        }
    }
    versions.sort_by(|a, b| a.0.cmp(&b.0));
    versions
}

pub fn prune_old_models(model_dir: &Path, keep: usize) -> Result<usize, String> {
    let versions = list_model_versions(model_dir);
    if versions.len() <= keep { return Ok(0); }
    let to_remove = versions.len() - keep;
    let mut removed = 0;
    for (_, path) in versions.iter().take(to_remove) {
        if fs::remove_file(path).is_ok() { removed += 1; }
    }
    Ok(removed)
}
```

### Model Storage Layout

```
~/.finance-cli/
└── data/
    └── models/
        ├── model_v0.0.1.bin      # First trained model
        ├── model_v0.0.2.bin      # After retraining
        ├── model_v0.0.3.bin      # Current model
        └── model_latest.bin      # Copy of v0.0.3
```

Expected sizes:

| Component | Typical Size |
|-----------|-------------|
| Vocabulary (5000 tokens) | ~1.2 MB |
| NaiveBayes weights | ~2-4 MB |
| LogisticRegression weights | ~0.1 MB |
| MerchantLookup table | ~0.5-1.0 MB |
| Metadata | <1 KB |
| **Total** | **~4-6 MB** |

---

## 8. Feedback Collection

### src/ml/feedback.rs

```rust
//! Feedback collection for retraining triggers.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CategorizationFeedback {
    pub id: Uuid,
    pub timestamp: DateTime<Utc>,
    pub transaction_id: Uuid,
    pub predicted_category_id: Option<Uuid>,
    pub predicted_confidence: Option<f32>,
    pub action: FeedbackAction,
    pub final_category_id: Uuid,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FeedbackAction {
    Accepted,
    Corrected,
    ManuallyAssigned,
    Skipped,
}

pub struct FeedbackBuffer {
    records: Vec<CategorizationFeedback>,
    correction_count: usize,
}

impl FeedbackBuffer {
    pub fn new() -> Self { Self { records: Vec::new(), correction_count: 0 } }

    pub fn record(&mut self, feedback: CategorizationFeedback) {
        if feedback.action == FeedbackAction::Corrected { self.correction_count += 1; }
        self.records.push(feedback);
    }

    pub fn corrections_since_retrain(&self) -> usize { self.correction_count }

    pub fn should_retrain(&self, threshold: usize) -> bool {
        self.correction_count >= threshold
    }

    pub fn drain(&mut self) -> Vec<CategorizationFeedback> {
        self.correction_count = 0;
        std::mem::take(&mut self.records)
    }

    pub fn records(&self) -> &[CategorizationFeedback] { &self.records }
    pub fn len(&self) -> usize { self.records.len() }
    pub fn is_empty(&self) -> bool { self.records.is_empty() }
}

impl Default for FeedbackBuffer { fn default() -> Self { Self::new() } }
```

---

## 9. Training Pipeline

### src/ml/training.rs

```rust
//! Batch retraining pipeline.
//!
//! Triggered when FeedbackBuffer crosses correction threshold.
//! Pipeline:
//! 1. Export all labeled transactions
//! 2. Weight recent corrections higher (2x)
//! 3. Split into train/validation
//! 4. Train new ensemble
//! 5. Evaluate on validation set
//! 6. Deploy if improved
//! 7. Save and prune old versions

use crate::ml::config::TrainingConfig;
use crate::ml::ensemble::EnsemblePredictor;
use crate::ml::feedback::CategorizationFeedback;
use crate::models::Transaction;
use std::collections::HashSet;
use uuid::Uuid;

#[derive(Debug)]
pub struct TrainingResult {
    pub deployed: bool,
    pub new_version: Option<String>,
    pub validation_accuracy: f32,
    pub validation_top3_accuracy: f32,
    pub previous_accuracy: f32,
    pub training_samples: usize,
    pub category_count: usize,
    pub summary: String,
}

pub fn retrain(
    predictor: &mut EnsemblePredictor,
    all_labeled: &[(Transaction, Uuid)],
    _recent_corrections: &[CategorizationFeedback],
    correction_transactions: &[(Transaction, Uuid)],
    config: &TrainingConfig,
) -> TrainingResult {
    let total = all_labeled.len();
    if total < config.min_training_samples {
        return TrainingResult {
            deployed: false, new_version: None,
            validation_accuracy: 0.0, validation_top3_accuracy: 0.0,
            previous_accuracy: predictor.metadata().accuracy,
            training_samples: total, category_count: 0,
            summary: format!("Insufficient data: {} samples (need {})", total, config.min_training_samples),
        };
    }

    // Augment: include correction transactions twice for higher weight.
    let mut training_data: Vec<(Transaction, Uuid)> = all_labeled.to_vec();
    for (tx, cat) in correction_transactions {
        training_data.push((tx.clone(), *cat));
    }

    let split_idx = (training_data.len() as f32 * (1.0 - config.validation_split)) as usize;
    let (train_set, val_set) = training_data.split_at(split_idx);
    let previous_accuracy = predictor.metadata().accuracy;

    predictor.train(train_set, config);

    let mut val_correct = 0usize;
    let mut val_top3 = 0usize;
    for (tx, true_cat) in val_set {
        let pred = predictor.predict(tx);
        if pred.category_id == *true_cat { val_correct += 1; }
        if pred.category_id == *true_cat
            || pred.alternatives.iter().any(|(c, _)| *c == *true_cat) {
            val_top3 += 1;
        }
    }

    let val_n = val_set.len().max(1) as f32;
    let val_acc = val_correct as f32 / val_n;
    let val_top3_acc = val_top3 as f32 / val_n;
    let categories: HashSet<_> = all_labeled.iter().map(|(_, c)| *c).collect();

    let improved = val_acc >= previous_accuracy + config.min_accuracy_improvement
        || previous_accuracy == 0.0;

    let summary = if improved {
        format!("Model retrained: accuracy {:.1}% -> {:.1}% ({} samples, {} categories)",
            previous_accuracy * 100.0, val_acc * 100.0, total, categories.len())
    } else {
        format!("Retraining did not improve: {:.1}% vs {:.1}%",
            val_acc * 100.0, previous_accuracy * 100.0)
    };

    TrainingResult {
        deployed: improved,
        new_version: if improved { Some(predictor.metadata().version.clone()) } else { None },
        validation_accuracy: val_acc, validation_top3_accuracy: val_top3_acc,
        previous_accuracy, training_samples: total,
        category_count: categories.len(), summary,
    }
}
```

---

## 10. Anomaly Detection

### src/ml/anomaly.rs

```rust
//! Statistical anomaly detection (Tier 1 from ML Architect spec).

use crate::ml::config::AnomalyConfig;
use crate::models::Transaction;
use chrono::Datelike;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyFlag {
    pub transaction_id: Uuid,
    pub anomaly_type: AnomalyType,
    pub severity: AnomalySeverity,
    pub score: f32,
    pub description: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AnomalyType {
    AmountOutlier,
    NewMerchantSensitive,
    WeekendBusiness,
    LargeRoundAmount,
    PossibleDuplicate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AnomalySeverity { Low, Medium, High }

#[derive(Debug, Clone, Default)]
struct CategoryStats {
    amounts: Vec<f32>,
    merchants: std::collections::HashSet<String>,
}

impl CategoryStats {
    fn mean(&self) -> f32 {
        if self.amounts.is_empty() { return 0.0; }
        self.amounts.iter().sum::<f32>() / self.amounts.len() as f32
    }

    fn std_dev(&self) -> f32 {
        if self.amounts.len() < 2 { return 0.0; }
        let mean = self.mean();
        let variance = self.amounts.iter()
            .map(|&x| (x - mean).powi(2))
            .sum::<f32>() / (self.amounts.len() - 1) as f32;
        variance.sqrt()
    }

    fn zscore(&self, amount: f32) -> f32 {
        let sd = self.std_dev();
        if sd < 0.01 { return 0.0; }
        (amount - self.mean()).abs() / sd
    }
}

pub struct AnomalyDetector {
    config: AnomalyConfig,
    category_stats: HashMap<Uuid, CategoryStats>,
}

impl AnomalyDetector {
    pub fn new(config: AnomalyConfig) -> Self {
        Self { config, category_stats: HashMap::new() }
    }

    pub fn fit(&mut self, transactions: &[(Transaction, Uuid)]) {
        self.category_stats.clear();
        for (tx, cat) in transactions {
            let stats = self.category_stats.entry(*cat).or_default();
            let amount = money_to_f32(&tx.amount).abs();
            stats.amounts.push(amount);
            if let Some(ref m) = tx.merchant_name {
                stats.merchants.insert(m.to_uppercase());
            }
        }
    }

    pub fn detect(&self, transaction: &Transaction, category_id: Option<Uuid>) -> Vec<AnomalyFlag> {
        let mut flags = Vec::new();
        let amount = money_to_f32(&transaction.amount).abs();

        if let Some(cat) = category_id {
            if let Some(stats) = self.category_stats.get(&cat) {
                if stats.amounts.len() >= self.config.min_category_history {
                    let z = stats.zscore(amount);
                    if z > self.config.zscore_threshold {
                        flags.push(AnomalyFlag {
                            transaction_id: transaction.id,
                            anomaly_type: AnomalyType::AmountOutlier,
                            severity: if z > 4.0 { AnomalySeverity::High }
                                else if z > 3.0 { AnomalySeverity::Medium }
                                else { AnomalySeverity::Low },
                            score: z,
                            description: format!(
                                "Amount ${:.2} is {:.1} std devs from category mean ${:.2}",
                                amount, z, stats.mean()
                            ),
                        });
                    }
                }

                if self.config.flag_new_merchants {
                    if let Some(ref m) = transaction.merchant_name {
                        if !stats.merchants.contains(&m.to_uppercase()) && !stats.merchants.is_empty() {
                            flags.push(AnomalyFlag {
                                transaction_id: transaction.id,
                                anomaly_type: AnomalyType::NewMerchantSensitive,
                                severity: AnomalySeverity::Low,
                                score: 0.5,
                                description: format!("First transaction from '{}' in this category", m),
                            });
                        }
                    }
                }
            }
        }

        if self.config.flag_weekend_business
            && transaction.is_business_expense
            && transaction.transaction_date.weekday().num_days_from_monday() >= 5
        {
            flags.push(AnomalyFlag {
                transaction_id: transaction.id,
                anomaly_type: AnomalyType::WeekendBusiness,
                severity: AnomalySeverity::Low,
                score: 0.3,
                description: "Business expense on a weekend".to_string(),
            });
        }

        if amount >= 500.0 && (amount - amount.round()).abs() < 0.01 {
            flags.push(AnomalyFlag {
                transaction_id: transaction.id,
                anomaly_type: AnomalyType::LargeRoundAmount,
                severity: AnomalySeverity::Low,
                score: 0.4,
                description: format!("Large round amount: ${:.0}", amount),
            });
        }

        flags
    }
}

fn money_to_f32(money: &crate::models::Money) -> f32 {
    use rust_decimal::prelude::ToPrimitive;
    money.0.to_f32().unwrap_or(0.0)
}
```

---

## 11. Recurring Transaction Detection

### src/ml/recurring.rs

```rust
//! Recurring transaction detection via merchant + amount + interval analysis.

use crate::ml::config::RecurringConfig;
use crate::models::Transaction;
use chrono::NaiveDate;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecurringPattern {
    pub merchant: String,
    pub frequency: RecurringFrequency,
    pub average_amount: f32,
    pub amount_cv: f32,
    pub occurrences: usize,
    pub confidence: f32,
    pub next_expected: Option<NaiveDate>,
    pub transaction_ids: Vec<Uuid>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RecurringFrequency { Weekly, Monthly, Quarterly, Annual }

pub struct RecurringDetector { config: RecurringConfig }

impl RecurringDetector {
    pub fn new(config: RecurringConfig) -> Self { Self { config } }

    pub fn detect(&self, transactions: &[Transaction]) -> Vec<RecurringPattern> {
        let mut groups: HashMap<String, Vec<&Transaction>> = HashMap::new();
        for tx in transactions {
            let key = tx.merchant_name.as_deref()
                .unwrap_or(&tx.description).to_uppercase();
            groups.entry(key).or_default().push(tx);
        }

        let mut patterns = Vec::new();
        for (merchant, mut txs) in groups {
            if txs.len() < 2 { continue; }
            txs.sort_by_key(|tx| tx.transaction_date);
            let amount_groups = self.group_by_amount(&txs);
            for group in amount_groups {
                if group.len() < 2 { continue; }
                if let Some(p) = self.check_pattern(&merchant, &group) {
                    patterns.push(p);
                }
            }
        }
        patterns.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap_or(std::cmp::Ordering::Equal));
        patterns
    }

    fn group_by_amount<'a>(&self, txs: &[&'a Transaction]) -> Vec<Vec<&'a Transaction>> {
        let tolerance = self.config.amount_tolerance;
        let mut groups: Vec<Vec<&'a Transaction>> = Vec::new();
        for tx in txs {
            let amount = money_abs(tx);
            let mut found = false;
            for group in &mut groups {
                let avg: f32 = group.iter().map(|t| money_abs(t)).sum::<f32>() / group.len() as f32;
                if avg > 0.0 && (amount - avg).abs() / avg <= tolerance {
                    group.push(tx);
                    found = true;
                    break;
                }
            }
            if !found { groups.push(vec![tx]); }
        }
        groups
    }

    fn check_pattern(&self, merchant: &str, txs: &[&Transaction]) -> Option<RecurringPattern> {
        if txs.len() < 2 { return None; }
        let dates: Vec<NaiveDate> = txs.iter().map(|tx| tx.transaction_date).collect();
        let intervals: Vec<i64> = dates.windows(2).map(|w| (w[1] - w[0]).num_days()).collect();
        if intervals.is_empty() { return None; }

        let avg_interval = intervals.iter().sum::<i64>() as f32 / intervals.len() as f32;

        let checks = [
            (RecurringFrequency::Weekly, self.config.weekly_interval, self.config.weekly_tolerance, self.config.min_occurrences_weekly),
            (RecurringFrequency::Monthly, self.config.monthly_interval, self.config.monthly_tolerance, self.config.min_occurrences_monthly),
            (RecurringFrequency::Quarterly, self.config.quarterly_interval, self.config.quarterly_tolerance, self.config.min_occurrences_quarterly),
            (RecurringFrequency::Annual, self.config.annual_interval, self.config.annual_tolerance, self.config.min_occurrences_annual),
        ];

        for (freq, expected, tolerance, min_occ) in &checks {
            if txs.len() < *min_occ { continue; }
            let exp_f = *expected as f32;
            let tol_f = *tolerance as f32;

            if (avg_interval - exp_f).abs() <= tol_f {
                let consistent = intervals.iter()
                    .filter(|&&i| (i as f32 - exp_f).abs() <= tol_f)
                    .count();
                let ratio = consistent as f32 / intervals.len() as f32;

                if ratio >= 0.7 {
                    let amounts: Vec<f32> = txs.iter().map(|t| money_abs(t)).collect();
                    let avg_amt = amounts.iter().sum::<f32>() / amounts.len() as f32;
                    let std = if amounts.len() > 1 {
                        (amounts.iter().map(|&a| (a - avg_amt).powi(2)).sum::<f32>()
                            / (amounts.len() - 1) as f32).sqrt()
                    } else { 0.0 };
                    let cv = if avg_amt > 0.0 { std / avg_amt } else { 0.0 };
                    let confidence = ratio * 0.6 + (txs.len() as f32 / 6.0).min(1.0) * 0.4;

                    let last = dates.last().copied().unwrap_or(dates[0]);
                    let next = last + chrono::Duration::days(*expected as i64);

                    return Some(RecurringPattern {
                        merchant: merchant.to_string(),
                        frequency: *freq,
                        average_amount: avg_amt,
                        amount_cv: cv,
                        occurrences: txs.len(),
                        confidence,
                        next_expected: Some(next),
                        transaction_ids: txs.iter().map(|t| t.id).collect(),
                    });
                }
            }
        }
        None
    }
}

fn money_abs(tx: &Transaction) -> f32 {
    use rust_decimal::prelude::ToPrimitive;
    tx.amount.0.abs().to_f32().unwrap_or(0.0)
}
```

---

## 12. Module Root

### src/ml/mod.rs

```rust
//! Machine learning module for the Finance CLI.
//!
//! Provides ML-based transaction categorization as a secondary system
//! to the rule-based engine. ML predictions apply only when no rule matches.

pub mod anomaly;
pub mod config;
pub mod ensemble;
pub mod features;
pub mod feedback;
pub mod models;
pub mod online;
pub mod persistence;
pub mod recurring;
pub mod training;
pub mod vocabulary;

pub use anomaly::{AnomalyDetector, AnomalyFlag, AnomalyType};
pub use config::MlConfig;
pub use ensemble::{EnsemblePredictor, MlPrediction, PredictionAction};
pub use feedback::{CategorizationFeedback, FeedbackAction, FeedbackBuffer};
pub use recurring::{RecurringDetector, RecurringPattern, RecurringFrequency};
```

### src/ml/online.rs

```rust
//! Online learning helpers wrapping ensemble updates with feedback recording.

use crate::ml::config::MlConfig;
use crate::ml::ensemble::EnsemblePredictor;
use crate::ml::feedback::{CategorizationFeedback, FeedbackAction, FeedbackBuffer};
use crate::models::Transaction;
use chrono::Utc;
use uuid::Uuid;

/// Process a user categorization decision. Returns true if retraining should be triggered.
pub fn process_feedback(
    predictor: &mut EnsemblePredictor,
    buffer: &mut FeedbackBuffer,
    transaction: &Transaction,
    predicted_category: Option<Uuid>,
    predicted_confidence: Option<f32>,
    final_category: Uuid,
    config: &MlConfig,
) -> bool {
    let action = match predicted_category {
        Some(pred) if pred == final_category => FeedbackAction::Accepted,
        Some(_) => FeedbackAction::Corrected,
        None => FeedbackAction::ManuallyAssigned,
    };

    predictor.learn_online(transaction, final_category);

    buffer.record(CategorizationFeedback {
        id: Uuid::new_v4(),
        timestamp: Utc::now(),
        transaction_id: transaction.id,
        predicted_category_id: predicted_category,
        predicted_confidence,
        action,
        final_category_id: final_category,
    });

    buffer.should_retrain(config.training.retrain_correction_threshold)
}
```

---

## 13. Integration with Existing Categorization Engine

### Updated src/categorization/ml.rs

Replace the current placeholder with delegation to the ML module:

```rust
//! ML integration for the categorization engine.

use crate::ml::ensemble::{EnsemblePredictor, MlPrediction, PredictionAction};
use crate::ml::config::MlConfig;
use crate::ml::persistence;
use crate::models::Transaction;
use uuid::Uuid;

pub struct MlCategorizer {
    predictor: Option<EnsemblePredictor>,
    config: MlConfig,
}

impl MlCategorizer {
    pub fn new(config: MlConfig) -> Self {
        let predictor = persistence::load_model(&config.model_dir, &config).ok();
        Self { predictor, config }
    }

    pub fn disabled() -> Self {
        Self { predictor: None, config: MlConfig { enabled: false, ..MlConfig::default() } }
    }

    pub fn predict(&self, transaction: &Transaction) -> Option<MlPrediction> {
        if !self.config.enabled { return None; }
        let predictor = self.predictor.as_ref()?;
        if !predictor.is_ready() { return None; }
        let prediction = predictor.predict(transaction);
        if prediction.confidence < self.config.thresholds.discard { return None; }
        Some(prediction)
    }

    pub fn is_ready(&self) -> bool {
        self.config.enabled
            && self.predictor.as_ref().map(|p| p.is_ready()).unwrap_or(false)
    }

    pub fn predictor_mut(&mut self) -> Option<&mut EnsemblePredictor> {
        self.predictor.as_mut()
    }

    pub fn set_predictor(&mut self, predictor: EnsemblePredictor) {
        self.predictor = Some(predictor);
    }
}

impl Default for MlCategorizer { fn default() -> Self { Self::new(MlConfig::default()) } }
```

### Updated categorize() in src/categorization/engine.rs

Add optional ML fallback parameter:

```rust
pub fn categorize(
    &self,
    transaction: &Transaction,
    ml: Option<&MlCategorizer>,
) -> CategorizationResult {
    // 1. Try rules first (always priority).
    for rule in &self.rules {
        if !rule.is_active { continue; }
        if RuleMatcher::matches(rule, transaction) {
            let category = self.categories.iter()
                .find(|c| c.id == rule.target_category_id).cloned();
            return CategorizationResult {
                transaction_id: transaction.id,
                category,
                matched_rule: Some(rule.clone()),
                confidence: 1.0,
                method: CategorizationMethod::Rule,
            };
        }
    }

    // 2. If no rule matched, try ML.
    if let Some(ml_cat) = ml {
        if let Some(prediction) = ml_cat.predict(transaction) {
            if prediction.action != PredictionAction::ManualReview {
                let category = self.categories.iter()
                    .find(|c| c.id == prediction.category_id).cloned();
                return CategorizationResult {
                    transaction_id: transaction.id,
                    category,
                    matched_rule: None,
                    confidence: prediction.confidence as f64,
                    method: CategorizationMethod::MachineLearning,
                };
            }
        }
    }

    // 3. No categorization.
    CategorizationResult {
        transaction_id: transaction.id,
        category: None,
        matched_rule: None,
        confidence: 0.0,
        method: CategorizationMethod::None,
    }
}
```

---

## 14. Confidence Scoring Strategy

| Confidence Range | Action | User Experience |
|-----------------|--------|-----------------|
| >= 0.85 | `AutoCategorize` | Applied silently, shown in import summary |
| 0.50 - 0.84 | `Suggest` | Shown with "[ML]" tag, user must confirm |
| 0.20 - 0.49 | `ManualReview` | Queued for manual review, top-3 shown as hints |
| < 0.20 | Discarded | No ML prediction shown |

### Ensemble Weight Rationale

| Model | Weight | Rationale |
|-------|--------|-----------|
| Merchant Lookup | 40% | Strongest single signal; if you've seen this merchant before, predict the same category |
| Naive Bayes | 40% | Good text classification even with small data; captures description patterns |
| Logistic Regression | 20% | Captures amount/temporal signals that text models miss |

### Cold Start Behavior

1. `is_ready()` returns false until first training.
2. All transactions go to manual categorization.
3. After 30 manually categorized transactions, first model trains automatically.
4. Merchant lookup becomes useful after just 2 occurrences of the same merchant.

---

## 15. Data Flow Summary

```
Transaction Imported
        |
        v
+-------------------+
| Rule-Based Engine |  <-- Always runs first
+-------------------+
        |
   Rule matched? ---YES---> Apply category (confidence: 1.0)
        |
        NO
        |
        v
+-------------------+
| ML Predictor      |  <-- Only if no rule matched
+-------------------+
        |
   conf >= 0.85? ---YES---> Auto-categorize (CategorizedBy::Ml)
        |
   conf >= 0.50? ---YES---> Suggest to user, await confirmation
        |
   conf >= 0.20? ---YES---> Show as hint in manual review
        |
        NO
        |
        v
   Mark as Uncategorized
        |
        v
+-------------------+
| User Decision     |  <-- User accepts, corrects, or assigns
+-------------------+
        |
        v
+-------------------+
| Online Learning   |  <-- Update all models incrementally
+-------------------+
        |
   Corrections >= 50? ---YES---> Trigger batch retraining
        |
        v
+-------------------+
| Anomaly Detector  |  <-- Runs on categorized transactions
+-------------------+
        |
        v
   Flag anomalies for review
```

---

## 16. Performance Requirements

| Operation | Target | Notes |
|-----------|--------|-------|
| Single prediction | < 10ms | Feature extraction + ensemble |
| Batch prediction (100 tx) | < 500ms | Sequential |
| Online learning update | < 5ms | Single example |
| Full retraining (1K tx) | < 10s | Vocab rebuild + NB + LR SGD |
| Full retraining (10K tx) | < 30s | Linear scaling |
| Model save | < 1s | Bincode serialization |
| Model load | < 1s | Bincode deserialization |
| Anomaly detection | < 1ms | Per transaction |
| Recurring detection | < 5s | Full history scan |
| Model file size | < 10 MB | All components |
| Runtime memory | < 50 MB | Loaded model |

---

## 17. Post-MVP Embedding Upgrade Path (Tier 2)

When the `ml-embeddings` feature flag is enabled:

1. Add `ort` crate for ONNX Runtime.
2. Download `all-MiniLM-L6-v2` model (~80MB) on first use.
3. Add `EmbeddingClassifier` as fourth ensemble member.
4. MLP classifier head: 394 -> 128 (ReLU) -> 64 (ReLU) -> N_categories (Softmax).
5. Train classifier head locally; embedding model weights are frozen.

Updated ensemble weights with embeddings:

| Model | Without Embeddings | With Embeddings |
|-------|-------------------|-----------------|
| Naive Bayes | 40% | 20% |
| Logistic Regression | 20% | 10% |
| Merchant Lookup | 40% | 30% |
| Embedding Classifier | -- | 40% |

---

## 18. Files to Create

| File | Purpose |
|------|---------|
| `src/ml/mod.rs` | Module root and re-exports |
| `src/ml/config.rs` | Configuration structs with defaults |
| `src/ml/features.rs` | SparseVector, FeatureVector, MlFeatureExtractor |
| `src/ml/vocabulary.rs` | TF-IDF vocabulary |
| `src/ml/models/mod.rs` | CategorizationModel trait |
| `src/ml/models/naive_bayes.rs` | Multinomial Naive Bayes |
| `src/ml/models/logistic.rs` | Logistic Regression with SGD |
| `src/ml/models/merchant_lookup.rs` | Merchant lookup table |
| `src/ml/ensemble.rs` | EnsemblePredictor |
| `src/ml/training.rs` | Batch retraining pipeline |
| `src/ml/online.rs` | Online learning + feedback processing |
| `src/ml/persistence.rs` | Model save/load |
| `src/ml/feedback.rs` | Feedback types and buffer |
| `src/ml/anomaly.rs` | Statistical anomaly detection |
| `src/ml/recurring.rs` | Recurring transaction detection |

### Files to Modify

| File | Change |
|------|--------|
| `Cargo.toml` | Add `bincode`, `ordered-float`; add `ml` feature |
| `src/categorization/ml.rs` | Replace placeholder with ML module delegation |
| `src/categorization/engine.rs` | Add optional `MlCategorizer` param to `categorize()` |
| `src/lib.rs` or `src/main.rs` | Add `pub mod ml;` |

---

## 19. Implementation Priority

| Priority | Component | Effort |
|----------|-----------|--------|
| P0 | config, features, vocabulary | 1 day |
| P0 | models/ (all three) | 1 day |
| P0 | ensemble | 1 day |
| P0 | persistence | 0.5 day |
| P0 | feedback, online | 0.5 day |
| P1 | training (batch retraining) | 1 day |
| P1 | Integration with categorization | 0.5 day |
| P1 | Unit + integration tests | 1 day |
| P2 | anomaly detection | 0.5 day |
| P2 | recurring detection | 0.5 day |
| P3 | ONNX embedding classifier | 3-5 days |

**Total MVP (P0 + P1): ~6 days**
**Total with anomaly + recurring (P2): ~7 days**

---

## 20. Testing Plan

### Unit Tests per Module

- **vocabulary.rs**: Tokenization edge cases, vocabulary build with min/max freq, vectorize consistency.
- **features.rs**: Merchant extraction from various bank formats, numeric feature normalization, round amount detection.
- **naive_bayes.rs**: Fit/predict round-trip, softmax sums to 1.0, online update changes predictions.
- **logistic.rs**: SGD convergence on separable data, predict_raw softmax normalization.
- **merchant_lookup.rs**: Lookup with min_count threshold, multi-category merchants return majority.
- **ensemble.rs**: Untrained returns NoModel, trained returns valid predictions, weight normalization.
- **persistence.rs**: Save/load round-trip produces identical predictions.
- **anomaly.rs**: Z-score detection with known data, new merchant flagging, weekend business flagging.
- **recurring.rs**: Monthly pattern detection with 6 months of data, amount tolerance grouping.

### Property-Based Tests

- Confidence always in [0.0, 1.0].
- Softmax outputs sum to approximately 1.0.
- Serialization is lossless (save then load yields identical ModelBundle).
- Feature extraction is deterministic for the same transaction.
- Anomaly z-scores are non-negative.

### Integration Tests

1. Full pipeline: create transactions, categorize manually, train, predict, verify.
2. Online learning: correct a prediction, verify next prediction improves.
3. Retraining trigger: accumulate corrections, verify retrain fires.
4. Cold start: verify graceful degradation when no model exists.
5. Persistence: save model, create new predictor from disk, verify identical results.
