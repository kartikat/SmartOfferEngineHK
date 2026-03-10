# SmartRewards — Offer Ranking Engine

AI-powered personalised rewards offer engine for loyalty customers.

## Project Structure

```
smartrewards/
├── data/
│   └── generate_data.py      # Synthetic customer, transaction & offer data
├── engine/
│   └── scoring.py            # Rule-based offer scoring & ranking engine
├── api/
│   └── main.py               # FastAPI REST API server
├── demo.py                   # End-to-end demo runner (no API needed)
└── README.md
```

## Quick Start

### 1. Install dependencies
```bash
pip install fastapi uvicorn pandas numpy
```

### 2. Run the demo (no API needed)
```bash
cd smartrewards
python demo.py
```

### 3. Or run step by step
```bash
python data/generate_data.py     # Generate synthetic data
python engine/scoring.py         # Run batch scoring
uvicorn api.main:app --reload    # Start API server
```

### 4. API endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/offers/{customer_id}` | Top N personalised offers for a customer |
| GET | `/customer/{customer_id}/profile` | Customer profile & loyalty attributes |
| GET | `/segments/fuel-redeemers` | All Fuel-only redeemer customers |
| GET | `/segments/4uplus` | All 4U+ subscriber customers |
| GET | `/offers` | List all available offers |
| GET | `/docs` | Interactive Swagger API docs |

## Scoring Model

Each customer-offer pair is scored using 5 weighted rules:

| Rule | Weight | Description |
|------|--------|-------------|
| Transaction Affinity | 30% | Historical spend in offer category |
| Redemption Match | 25% | Offer channel vs customer's primary channel |
| Points Eligibility | 20% | Customer has enough points to redeem |
| Cart/Browse Affinity | 15% | Online activity signal |
| Demographic Match | 10% | Age/profile fit |

### Multipliers
- **Recency Boost (1.2x):** Customer transacted in last 7 days
- **4U+ Tier Multiplier (1.5x):** 4U+ subscriber on exclusive offer

### eCommerce Nudge Logic
Fuel redeemers receive a partial score (0.6) on eCommerce offers —
intentionally nudging them online while still showing relevant fuel offers.

## Customer Segments
- **4U+ Subscribers** — High-tier, initial target segment
- **Fuel Redeemers** — Offline loyalists to be migrated to eCommerce
- **High Points Holders (1000+)** — High potential, low activation
