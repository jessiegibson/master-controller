# ML Architecture: Finance CLI

Version: 1
Date: 2024-12-28
Status: Draft
Target Implementation: Post-MVP

## Executive Summary

This ML architecture implements local-first transaction categorization using a hybrid embedding + classifier approach that balances accuracy, privacy, and resource constraints. The system provides intelligent categorization while maintaining the application's privacy-first philosophy through local-only execution and user-controlled feedback loops.

## Design Principles

1. **Local-first**: All ML runs on user's device by default
2. **Privacy-preserving**: No transaction data leaves device without consent
3. **Incremental learning**: Models improve with user feedback
4. **Graceful degradation**: App works without ML (rules-based fallback)
5. **Resource-conscious**: Fits within hardware constraints

## Hardware Constraints

| Constraint | Limit |
|------------|-------|
| Model memory | ≤4GB |
| Inference latency | <500ms single, <5s batch |
| Disk footprint | <2GB |
| Cold start | <10s |

---

# Use Case 1: Transaction Categorization

## Problem Statement

Automatically categorize transactions to reduce manual effort while maintaining high accuracy on user's specific spending patterns.

## Approach Evaluation

### Option A: Traditional ML Classifier

**Architecture**: TF-IDF + Gradient Boosting

```
Transaction Description
        │
        ▼
┌───────────────────┐
│ Text Preprocessing │
│ (lowercase, clean) │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│    TF-IDF         │
│  Vectorization    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Feature Concat    │
│ (text + amount +  │
│  day_of_week)     │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Gradient Boosting │
│   Classifier      │
└─────────┬─────────┘
          │
          ▼
    Category + Confidence
```

**Pros**:
- Very fast inference (<10ms)
- Small memory footprint (<100MB)
- Easy to train locally
- Interpretable

**Cons**:
- Limited semantic understanding
- Requires feature engineering
- May struggle with new merchants

**Resource estimate**:
- Memory: 50-100MB
- Inference: <10ms
- Training: <1 minute on 10K transactions

---

### Option B: Embedding Similarity

**Architecture**: Sentence Transformer + Nearest Neighbor

```
Transaction Description
        │
        ▼
┌───────────────────┐
│ Sentence          │
│ Transformer       │
│ (all-MiniLM-L6)   │
└─────────┬─────────┘
          │
          ▼
    384-dim Embedding
          │
          ▼
┌───────────────────┐
│ Nearest Neighbor  │
│ (FAISS/Annoy)     │
│ against labeled   │
│ transactions      │
└─────────┬─────────┘
          │
          ▼
    Category + Confidence
```

**Pros**:
- Good semantic understanding
- Handles new merchants well
- Transfer learning from pre-trained model
- Natural similarity scores

**Cons**:
- Larger memory footprint
- Slower inference
- Requires embedding index maintenance

**Resource estimate**:
- Memory: 400MB-1GB (model + index)
- Inference: 50-200ms
- Training: Index building <5 minutes

---

### Option C: Small Local LLM

**Architecture**: Quantized 7B model with classification prompt

```
Transaction Description
        │
        ▼
┌───────────────────┐
│ Prompt Template   │
│ "Categorize this  │
│  transaction..."  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Quantized LLM     │
│ (Phi-3, Gemma 2B) │
└─────────┬─────────┘
          │
          ▼
    Category + Reasoning
```

**Pros**:
- Best semantic understanding
- Can explain categorization
- Handles edge cases well
- Zero-shot capability

**Cons**:
- Highest resource usage
- Slowest inference
- Complex deployment
- Overkill for classification

**Resource estimate**:
- Memory: 2-8GB
- Inference: 1-5s
- No local training (use pre-trained)

---

### Option D: Hybrid (Recommended)

**Architecture**: Embeddings + Lightweight Classifier Head

```
Transaction Description
        │
        ▼
┌───────────────────┐
│ Sentence          │
│ Transformer       │
│ (all-MiniLM-L6)   │
└─────────┬─────────┘
          │
          ▼
    384-dim Embedding
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌────────┐ ┌────────────┐
│ Amount │ │ Day/Month  │
│ Feature│ │ Features   │
└────┬───┘ └─────┬──────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌───────────────────┐
│ Concat Features   │
│ (384 + 10)        │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Small Neural Net  │
│ (2 hidden layers) │
└─────────┬─────────┘
          │
          ▼
    Category + Confidence
```

**Pros**:
- Balances accuracy and speed
- Semantic understanding from embeddings
- Fast inference with classifier head
- Easy to fine-tune on user data

**Cons**:
- More complex than pure traditional ML
- Requires embedding model download

**Resource estimate**:
- Memory: 400-600MB
- Inference: 50-100ms
- Fine-tuning: <5 minutes

## Recommendation

**Primary**: Option D (Hybrid) for best accuracy/resource balance
**Fallback**: Option A (Traditional ML) if resources constrained
**MVP**: Rule-based categorization (already designed)

---

## Model Specification

### Embedding Model

| Property | Value |
|----------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensions | 384 |
| Size | ~80MB |
| License | Apache 2.0 |

### Classifier Head

| Property | Value |
|----------|-------|
| Architecture | MLP (384+10 → 128 → 64 → N_categories) |
| Activation | ReLU + Softmax |
| Training | Cross-entropy loss |
| Regularization | Dropout 0.2 |

### Input Features

| Feature | Type | Preprocessing |
|---------|------|---------------|
| description | text | Lowercase, tokenize → embedding |
| amount | float | Log transform, normalize |
| day_of_week | int | One-hot encode |
| day_of_month | int | Cyclical encode |
| is_weekend | bool | Binary |

### Output

```json
{
  "category_id": "uuid",
  "category_name": "Office Supplies",
  "confidence": 0.87,
  "alternatives": [
    {"category": "Business Expenses", "confidence": 0.08},
    {"category": "Electronics", "confidence": 0.05}
  ]
}
```

### Confidence Thresholds

| Confidence | Action |
|------------|--------|
| ≥0.85 | Auto-categorize |
| 0.50-0.85 | Suggest, require confirmation |
| <0.50 | Mark for manual review |

---

# Use Case 2: Anomaly Detection

## Recommendation: Statistical + Isolation Forest Hybrid

**Problem**: Identify unusual transactions that may need review

**Approach**: Two-tier detection system

### Tier 1: Statistical Detection (Fast)

```
Transaction Amount
        │
        ▼
┌───────────────────┐
│ Category History  │
│ (mean, std, IQR)  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Z-Score & IQR     │
│ Calculations      │
└─────────┬─────────┘
          │
          ▼
    Anomaly Score
```

**Detects**:
- Unusual amounts for category (z-score > 2.5)
- First-time merchants in sensitive categories
- Weekend transactions in business categories
- Large round-number amounts

**Resource estimate**:
- Memory: <10MB
- Inference: <1ms per transaction

### Tier 2: Isolation Forest (Deep Analysis)

```
Transaction Features
        │
        ▼
┌───────────────────┐
│ Feature Vector    │
│ (amount, day,     │
│  merchant_hash)   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Isolation Forest  │
│ (pre-trained)     │
└─────────┬─────────┘
          │
          ▼
    Isolation Score
```

**Detects**:
- Complex spending pattern deviations
- Unusual merchant/amount combinations
- Temporal anomalies

**Resource estimate**:
- Memory: 50-100MB
- Training: <2 minutes on 10K transactions
- Inference: 5-10ms per transaction

## Anomaly Types

| Type | Detection Method | Threshold |
|------|------------------|-----------|
| Amount outlier | Z-score within category | \|z\| > 2.5 |
| New merchant | First occurrence + sensitive category | Boolean |
| Pattern break | Isolation forest | Score < 0.3 |
| Duplicate risk | Hash similarity + time proximity | >95% similarity |

---

# Use Case 3: Recurring Transaction Detection

## Recommendation: Rule-Based with Clustering Validation

**Problem**: Identify subscriptions and recurring payments

**Approach**: Multi-stage detection pipeline

### Stage 1: Candidate Detection

```
Transaction History
        │
        ▼
┌───────────────────┐
│ Group by Merchant │
│ + Amount Range    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Frequency Analysis│
│ (30±3, 90±7 days) │
└─────────┬─────────┘
          │
          ▼
    Recurring Candidates
```

### Stage 2: Pattern Validation

```
Candidates
        │
        ▼
┌───────────────────┐
│ Statistical Tests │
│ (regularity,      │
│  amount variance) │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Confidence Score  │
│ (frequency +      │
│  consistency)     │
└─────────┬─────────┘
          │
          ▼
    Validated Patterns
```

## Detection Criteria

| Pattern | Frequency | Amount Tolerance | Min Occurrences |
|---------|-----------|------------------|-----------------|
| Monthly | 30±3 days | ±5% | 3 |
| Quarterly | 90±7 days | ±10% | 2 |
| Annual | 365±14 days | ±5% | 2 |
| Weekly | 7±1 days | ±5% | 4 |

**Resource estimate**:
- Memory: <50MB
- Processing: <10s for full transaction history

---

# Use Case 4: Receipt/Document Parsing

## Recommendation: OCR + Local LLM (Optional Feature)

**Problem**: Extract transaction data from receipt images and PDFs

**Approach**: Two-stage pipeline (future implementation)

### Stage 1: OCR Extraction

```
Image/PDF
        │
        ▼
┌───────────────────┐
│ Tesseract OCR     │
│ (with preprocess) │
└─────────┬─────────┘
          │
          ▼
    Raw Text
```

### Stage 2: Structured Extraction

```
Raw OCR Text
        │
        ▼
┌───────────────────┐
│ Local LLM         │
│ (Phi-3 Mini 4K)   │
│ Extraction Prompt │
└─────────┬─────────┘
          │
          ▼
    Structured Data
```

**Extraction targets**:
- Merchant name
- Date
- Total amount
- Line items (optional)
- Tax amount

**Resource estimate**:
- Memory: 2-4GB (LLM loaded on demand)
- Processing: 10-30s per document
- Accuracy: 85-95% for clear receipts

**Implementation priority**: Phase 3 (after core ML features)

---

# Feedback Loop Design

## Overview

User corrections create a feedback loop that improves model accuracy over time.

```
┌─────────────────────────────────────────────────────────────────┐
│                     FEEDBACK LOOP                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Transaction imported                                         │
│         │                                                        │
│         ▼                                                        │
│  2. Model predicts category                                      │
│         │                                                        │
│         ▼                                                        │
│  3. User accepts or corrects                                     │
│         │                                                        │
│         ├──► Accepted ──► Positive feedback                     │
│         │                                                        │
│         └──► Corrected ──► Correction feedback                  │
│                   │                                              │
│                   ▼                                              │
│  4. Feedback stored in training buffer                          │
│         │                                                        │
│         ▼                                                        │
│  5. Retraining trigger check                                    │
│         │                                                        │
│         ├──► Threshold not met ──► Continue                     │
│         │                                                        │
│         └──► Threshold met ──► Retrain model                    │
│                   │                                              │
│                   ▼                                              │
│  6. Model updated, version incremented                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Feedback Data Schema

```yaml
feedback_record:
  id: uuid
  timestamp: datetime
  transaction_id: uuid
  
  # Prediction
  predicted_category: uuid
  predicted_confidence: float
  
  # User action
  action: "accepted" | "corrected" | "skipped"
  final_category: uuid  # Same as predicted if accepted
  
  # Features (for retraining)
  features:
    description: string
    amount: float
    day_of_week: int
    embedding: float[]  # Optional, can regenerate
```

## Retraining Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Correction count | 50 corrections | Queue retraining |
| Time elapsed | 7 days | Check if any corrections |
| Accuracy drop | <80% recent | Priority retraining |
| Manual request | User initiated | Immediate retraining |

## Retraining Process

1. **Export training data**: All labeled transactions
2. **Include feedback buffer**: Recent corrections weighted higher
3. **Train new model version**: Classifier head only (embeddings frozen)
4. **Evaluate on holdout set**: Compare to previous version
5. **Deploy if improved**: Otherwise keep current model
6. **Clear feedback buffer**: Reset correction counter

## Rollback Capability

- Keep last 3 model