# SmartOfferEngine — Productionalization Roadmap

> What needs to change to take this hackathon proof-of-concept to a production system serving millions of Albertsons customers.

---

## TL;DR

The algorithms, data model, and scoring logic are production-grade — they mirror the real Albertsons C360 schema and use industry-standard ML (XGBoost). What needs replacing is the **infrastructure layer**: single-node database → distributed cloud, Python scripts → scheduled pipelines, Streamlit demo → real frontend.

---

## 1. Data Infrastructure

### Current
- PostgreSQL 16 on a developer laptop (Homebrew)
- 120 synthetic households, 64 offers, 71 UPCs
- Data seeded once manually

### Production
- **Move to BigQuery** (Albertsons C360 already lives here)
  - All 18 tables exist in C360 BigQuery — no schema changes needed
  - Replace `postgresql://localhost/smartrewards` connection string with BigQuery client
  - `c360_scored_offers` becomes a BigQuery output table written by the scoring pipeline
- **Real customer data** — millions of households, thousands of offers, real transaction history
- **Data freshness SLA** — define how stale scores are acceptable (daily? hourly?)

### Effort: Low
The schema is already designed around C360 BigQuery. It's a connection string change + BigQuery client library swap.

---

## 2. Batch Scoring Pipeline

### Current
- `scoring.py` and `scoring_ml.py` run as single Python processes
- Loads all data into Pandas DataFrames in memory (~MB at 120 customers)
- Run manually on a laptop

### Production
- **Scale problem:** 1M customers × 64 offers = 64M pairs per scoring run. A single Pandas process needs ~67GB RAM — not viable.
- **Solution: Distributed batch scoring on GCP**

```
BigQuery (C360 tables)
        ↓
Cloud Composer (Airflow DAG) — triggers nightly
        ↓
Dataflow / Spark (partitioned by customer segment)
   ├── Shard 1: HH00001–HH250000  →  score in parallel
   ├── Shard 2: HH250001–HH500000 →  score in parallel
   ├── Shard 3: HH500001–HH750000 →  score in parallel
   └── Shard 4: HH750001–HH999999 →  score in parallel
        ↓
BigQuery: c360_scored_offers (15M rows written per run)
```

- **Scoring frequency:** Nightly batch is standard for loyalty programs. Near-real-time (hourly) is possible for high-value triggers (points expiry, lapsed customers).
- **Business rules** (FreshPass gate, 4U+ exclusive, GR eligibility) stay as pre-filters — they're cheap SQL, not ML.

### Effort: High
Requires GCP Dataflow/Spark job rewrite, Airflow DAG, IAM permissions, BigQuery write access.

---

## 3. ML Model Training

### Current
- XGBoost trained on ~1,200 synthetic examples
- `scoring_ml.py --retrain` runs on laptop in ~10 seconds
- Models saved as `.pkl` files in the repo
- CV AUC: 0.626 (standard), 0.572 (GR) — acceptable for synthetic data, will improve significantly on real data

### Production
- **Training data:** Real `c360_redemptions` + `c360_clips` — millions of labelled examples
- **Training platform:** Vertex AI (GCP) or SageMaker (AWS)
  - Managed training jobs, GPU support, hyperparameter tuning
  - Model registry for versioning (model v1.2 → v1.3 with AUC comparison before promotion)
- **Retraining schedule:** Weekly or on data drift triggers
- **Model validation gate:** New model must beat current AUC by ≥0.5% before promotion to production
- **Feature store:** Pre-materialise customer features (affinity scores, days since txn, points balance) so scoring jobs don't recompute from raw tables every run

```
Weekly trigger (Cloud Scheduler)
        ↓
Vertex AI Training Job
   ├── Pull labelled examples from BigQuery
   ├── Train XGBoost (standard + GR models)
   ├── Evaluate: new AUC vs current AUC
   └── Promote if AUC improves → push to model registry
        ↓
Next scoring run picks up new model automatically
```

### Effort: Medium
XGBoost code is portable. Main work is Vertex AI job config, model registry integration, and the promotion gate.

---

## 4. API Layer

### Current
- FastAPI on `localhost:8000`
- 7 endpoints, reads directly from PostgreSQL
- No auth, no rate limiting, single process

### Production
- **FastAPI is production-ready** — keep it, scale it
- Deploy on **Cloud Run** (GCP) or **ECS** (AWS) — serverless, auto-scales to zero
- Add authentication: OAuth2 / JWT for customer-facing endpoints, API key for internal services
- Rate limiting per customer session
- Cache hot reads (top offers per household) in **Redis** — avoid BigQuery round-trips for repeat page loads
- CDN for static assets

```
Customer App / Web
        ↓
API Gateway (rate limiting, auth)
        ↓
FastAPI (Cloud Run — auto-scales)
   ├── GET /offers/{hid}     → Redis cache → BigQuery fallback
   ├── POST /clip/{hid}/{oid} → BigQuery write + cache invalidation
   └── GET /customer/{hid}   → BigQuery
```

### Effort: Medium
FastAPI code is already clean. Main work is containerisation (Dockerfile), Cloud Run deployment, Redis setup, and auth middleware.

---

## 5. Frontend / UI

### Current
- Streamlit — single-threaded, not designed for concurrent users
- Runs on `localhost:8501`
- Two personas (Customer / Analyst) in one app

### Production
- **Split into two separate apps:**

| Persona | Technology | Hosting |
|---|---|---|
| Customer (for U app) | React Native / Swift / Kotlin | Mobile app stores |
| Analyst (internal tool) | React + internal dashboard framework (Retool, Looker, or custom) | Internal VPN only |

- The Streamlit demo becomes a **sales/demo tool only** — not customer-facing
- Customer app calls the production FastAPI for offers, clips, profile
- Analyst dashboard calls internal BigQuery views directly or via a read-only API

### Effort: High
Full frontend rebuild. Streamlit is not salvageable for production customer traffic.

---

## 6. Real-Time Triggers (New Capability)

The batch model scores nightly, but some events should trigger immediate re-scoring:

| Trigger | Action |
|---|---|
| Points about to expire (≤7 days) | Push notification with best GR offer |
| Customer hits new points tier | Unlock new GR offers immediately |
| Lapsed customer (30 days no txn) | Win-back offer surfaced at next app open |
| FreshPass subscription activated | FreshPass offers unlocked in real-time |
| Large basket transaction | Instant cashback offer (post-purchase) |

- **Implementation:** Pub/Sub event stream from transaction system → Cloud Function → update `c360_scored_offers` for that household only → push notification via FCM
- Avoids full batch re-run for single-customer events

### Effort: Medium
Requires transaction event streaming (teammate build) + Cloud Functions.

---

## 7. Monitoring & Observability

Not built yet. Required for production:

| Metric | Tool | Alert threshold |
|---|---|---|
| Scoring pipeline success/failure | Cloud Monitoring | Any failure |
| Model AUC drift | Vertex AI Model Monitoring | AUC drops >2% week-over-week |
| Offer redemption rate | BigQuery dashboard | <50% of baseline |
| API latency (p99) | Cloud Trace | >500ms |
| Cache hit rate | Redis metrics | <70% |
| Clip-to-redemption funnel | Looker / Data Studio | Drop >10% MoM |

### Effort: Medium
Standard GCP monitoring stack. Most metrics come from existing tables.

---

## 8. Privacy & Compliance

| Requirement | Action |
|---|---|
| Customer data access control | Household data scoped to authenticated session only |
| Offer personalisation disclosure | "Why am I seeing this?" explainability (SHAP values — Phase 4e) |
| Data retention | Scored offers expire after `end_dt`; purge per Albertsons retention policy |
| CCPA compliance | Customer opt-out of personalisation → fall back to rule-based generic offers |
| PII in model features | Audit feature list — no raw PII (name, email) in training data |

### Effort: Low–Medium
Most of this is policy + configuration. The CCPA opt-out fallback is the only code change (already have rule-based as a fallback model).

---

## 9. Phased Delivery Plan

| Phase | What | Effort | Dependency |
|---|---|---|---|
| **P1** | BigQuery migration (connection swap) | Low | C360 BigQuery access |
| **P1** | FastAPI → Cloud Run deployment | Medium | GCP project, Dockerfile |
| **P2** | Distributed batch scoring (Dataflow) | High | BigQuery write access |
| **P2** | Vertex AI model training + registry | Medium | Real `c360_redemptions` data |
| **P3** | Redis caching layer | Low | Cloud Run deployed |
| **P3** | Airflow DAG for nightly scoring | Medium | Dataflow job ready |
| **P3** | Monitoring & alerting | Medium | All above deployed |
| **P4** | Real-time trigger engine | Medium | Transaction event stream |
| **P4** | Customer mobile app (React Native) | High | API stable |
| **P4** | Analyst dashboard (Retool/Looker) | Medium | BigQuery views ready |
| **P5** | Embedding model (Phase 4c) | High | >10k real redemption events |
| **P5** | Blended ranking (Phase 4d) | Medium | Embedding model ready |
| **P5** | SHAP explainability in UI (Phase 4e) | Medium | Team familiar with SHAP theory |

---

## What Stays Unchanged

- **C360 schema** — all 18 tables already mirror production BigQuery
- **Scoring formulas** — rule-based weights, GR path, business rules
- **XGBoost feature set** — 16 standard features, 12 GR features
- **Separate scoring pools** — `TOP_N_STANDARD=10` + `TOP_N_GR=5` per household
- **API contract** — same endpoints, same response shapes
- **The core idea** — pre-score nightly, serve from a ranked table, personalise at household level
