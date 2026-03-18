"""
Unit tests for files/engine/scoring.py — pure scoring functions only.
No database required.

Run: python3 -m pytest tests/test_scoring.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from files.engine.scoring import (
    WEIGHTS,
    RECENCY_BOOST,
    TIER_MULTIPLIER,
    TOP_N_STANDARD,
    TOP_N_GR,
    score_transaction_affinity,
    score_redemption_match,
    score_points_eligibility,
    score_cart_affinity,
    score_demographic_match,
    score_standard_offer,
    score_grocery_reward,
    passes_business_rules,
    run_batch_scoring,
)
import pandas as pd


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

def make_customer(**overrides):
    base = {
        "household_id":             "HH00001",
        "retail_customer_uuid":     "uuid-001",
        "clv_tier_level_id":        "Standard",
        "current_point_balance":    500,
        "points_expiring_next_month": 0,
        "fav_channel":              "J4U",
        "eng_mode_p6m":             "eCommerce",
        "customer_age":             "35-44",
        "num_of_children":          0,
        "household_size":           2,
        "diet_preference":          None,
        "gas_rewards_ind_6m":       False,
        "fuel_station_purchase_ind_6m": False,
        "doordash_txn_ind_6m":      False,
        "instacart_txn_ind_6m":     False,
        "uber_txn_ind_6m":          False,
        "dairy_purchase_ind_6m":    False,
        "produce_purchase_ind_6m":  False,
        "bakery_purchase_ind_6m":   False,
        "meat_purchase_ind_6m":     False,
        "frozen_grocery_purchase_ind_6m": False,
        "own_brand_ind_6m":         False,
        "days_since_last_txn":      30,
    }
    base.update(overrides)
    return base


def make_offer(**overrides):
    base = {
        "client_offer_id":          "OFFER001",
        "offer_dsc":                "Test Offer",
        "delivery_channel_cd":      "J4U",
        "program_type":             "Standard",
        "discount_type_cd":         "AMT_OFF",
        "discount_value":           5.0,
        "target_level_cd":          "BASKET",
        "is_appliable_to_j4u_ind":  False,
        "is_freshpass_offer_ind":   False,
        "offer_category":           "Grocery",
        "tier_1_points_threshold":  None,
        "tier_2_points_threshold":  None,
        "tier_3_points_threshold":  None,
        "tier_1_discount":          None,
        "tier_2_discount":          None,
        "tier_3_discount":          None,
        "historical_red_pct":       0.1,
    }
    base.update(overrides)
    return base


def make_gr_offer(**overrides):
    base = make_offer(
        client_offer_id="GR001",
        offer_dsc="$4 Off Basket — 300 pts",
        program_type="Grocery Reward",
        discount_type_cd="GROCERY_REWARD",
        tier_1_points_threshold=300,
        tier_1_discount=4.0,
        offer_category="Grocery",
    )
    base.update(overrides)
    return base


# ─── score_transaction_affinity ───────────────────────────────────────────────

class TestScoreTransactionAffinity:
    def test_returns_affinity_score_when_present(self):
        customer = make_customer(household_id="HH00001")
        offer = make_offer(offer_category="Produce")
        lookup = {("HH00001", "Produce"): 0.85}
        assert score_transaction_affinity(customer, offer, lookup) == 0.85

    def test_returns_zero_when_no_affinity_entry(self):
        customer = make_customer(household_id="HH00001")
        offer = make_offer(offer_category="Seafood")
        assert score_transaction_affinity(customer, offer, {}) == 0.0

    def test_category_mismatch_returns_zero(self):
        customer = make_customer(household_id="HH00001")
        offer = make_offer(offer_category="Bakery")
        lookup = {("HH00001", "Produce"): 0.9}
        assert score_transaction_affinity(customer, offer, lookup) == 0.0


# ─── score_redemption_match ───────────────────────────────────────────────────

class TestScoreRedemptionMatch:
    def test_j4u_customer_on_j4u_offer_perfect_match(self):
        c = make_customer(fav_channel="J4U")
        o = make_offer(delivery_channel_cd="J4U")
        assert score_redemption_match(c, o) == 1.0

    def test_weekly_ad_customer_on_weekly_ad_perfect_match(self):
        c = make_customer(fav_channel="Weekly Ad", eng_mode_p6m="In-Store")
        o = make_offer(delivery_channel_cd="Weekly Ad")
        assert score_redemption_match(c, o) == 1.0

    def test_auto_clip_is_channel_neutral(self):
        c = make_customer(fav_channel="J4U")
        o = make_offer(delivery_channel_cd="Auto Clip")
        assert score_redemption_match(c, o) == 0.7

    def test_j4u_offer_both_mode_gets_partial_credit(self):
        c = make_customer(fav_channel="Weekly Ad", eng_mode_p6m="Both")
        o = make_offer(delivery_channel_cd="J4U")
        assert score_redemption_match(c, o) == 0.7

    def test_fuel_redeemer_on_j4u_gets_nudge(self):
        c = make_customer(fav_channel="Weekly Ad", eng_mode_p6m="In-Store",
                          gas_rewards_ind_6m=True)
        o = make_offer(delivery_channel_cd="J4U")
        assert score_redemption_match(c, o) == 0.6

    def test_j4u_offer_mismatched_customer_low_score(self):
        c = make_customer(fav_channel="Weekly Ad", eng_mode_p6m="In-Store",
                          gas_rewards_ind_6m=False)
        o = make_offer(delivery_channel_cd="J4U")
        assert score_redemption_match(c, o) == 0.3

    def test_weekly_ad_offer_instore_customer_high_score(self):
        c = make_customer(fav_channel="J4U", eng_mode_p6m="In-Store")
        o = make_offer(delivery_channel_cd="Weekly Ad")
        assert score_redemption_match(c, o) == 0.8

    def test_unknown_channel_returns_neutral(self):
        c = make_customer()
        o = make_offer(delivery_channel_cd="Unknown")
        assert score_redemption_match(c, o) == 0.5


# ─── score_points_eligibility ─────────────────────────────────────────────────

class TestScorePointsEligibility:
    def test_no_threshold_offer_scales_with_balance(self):
        c = make_customer(current_point_balance=500)
        o = make_offer(tier_1_points_threshold=None)
        assert score_points_eligibility(c, o) == 1.0  # 500/500 = 1.0

    def test_no_threshold_capped_at_1(self):
        c = make_customer(current_point_balance=1000)
        o = make_offer(tier_1_points_threshold=None)
        assert score_points_eligibility(c, o) == 1.0

    def test_no_threshold_low_balance(self):
        c = make_customer(current_point_balance=250)
        o = make_offer(tier_1_points_threshold=None)
        assert score_points_eligibility(c, o) == 0.5

    def test_below_threshold_returns_zero(self):
        c = make_customer(current_point_balance=100)
        o = make_offer(tier_1_points_threshold=300)
        assert score_points_eligibility(c, o) == 0.0

    def test_at_threshold_returns_midrange(self):
        c = make_customer(current_point_balance=300)
        o = make_offer(tier_1_points_threshold=300, tier_2_points_threshold=None)
        assert score_points_eligibility(c, o) == 0.5

    def test_above_tier2_returns_higher(self):
        c = make_customer(current_point_balance=600)
        o = make_offer(tier_1_points_threshold=300, tier_2_points_threshold=500)
        assert score_points_eligibility(c, o) == 0.85


# ─── score_cart_affinity ──────────────────────────────────────────────────────

class TestScoreCartAffinity:
    def test_ecom_offer_heavy_ecom_user_high_score(self):
        c = make_customer(doordash_txn_ind_6m=True, instacart_txn_ind_6m=True,
                          uber_txn_ind_6m=True, eng_mode_p6m="eCommerce")
        o = make_offer(delivery_channel_cd="J4U")
        assert score_cart_affinity(c, o) == 1.0

    def test_instore_offer_ecom_user_slight_penalty(self):
        c = make_customer(doordash_txn_ind_6m=True, instacart_txn_ind_6m=True,
                          uber_txn_ind_6m=True, eng_mode_p6m="eCommerce")
        o = make_offer(delivery_channel_cd="Weekly Ad")
        score = score_cart_affinity(c, o)
        assert score < 1.0
        assert score > 0.5

    def test_no_ecom_signals_on_ecom_offer_zero(self):
        c = make_customer(doordash_txn_ind_6m=False, instacart_txn_ind_6m=False,
                          uber_txn_ind_6m=False, eng_mode_p6m="In-Store")
        o = make_offer(delivery_channel_cd="J4U")
        assert score_cart_affinity(c, o) == 0.0

    def test_auto_clip_treated_as_ecom_offer(self):
        c = make_customer(instacart_txn_ind_6m=True, eng_mode_p6m="eCommerce")
        o = make_offer(delivery_channel_cd="Auto Clip")
        assert score_cart_affinity(c, o) > 0.5


# ─── score_demographic_match ──────────────────────────────────────────────────

class TestScoreDemographicMatch:
    def test_base_score_is_half(self):
        c = make_customer(customer_age="18-24", num_of_children=0)
        o = make_offer(offer_category="Grocery")
        assert score_demographic_match(c, o) == 0.5

    def test_fuel_skews_middle_aged(self):
        c = make_customer(customer_age="45-54")
        o = make_offer(offer_category="Fuel")
        assert score_demographic_match(c, o) > 0.5

    def test_fuel_does_not_boost_young(self):
        c = make_customer(customer_age="18-24")
        o = make_offer(offer_category="Fuel")
        assert score_demographic_match(c, o) == 0.5

    def test_dairy_boosts_families(self):
        c = make_customer(customer_age="35-44", num_of_children=2)
        o = make_offer(offer_category="Dairy Eggs Cheese")
        assert score_demographic_match(c, o) > 0.5

    def test_score_capped_at_1(self):
        c = make_customer(customer_age="35-44", num_of_children=2,
                          own_brand_ind_6m=True)
        o = make_offer(offer_category="Dairy Eggs Cheese",
                       offer_dsc="Organic Milk $2 Off")
        assert score_demographic_match(c, o) <= 1.0


# ─── score_standard_offer ─────────────────────────────────────────────────────

class TestScoreStandardOffer:
    def test_returns_all_components(self):
        c = make_customer()
        o = make_offer()
        result = score_standard_offer(c, o, {})
        for key in ("transaction_affinity", "redemption_match", "points_eligibility",
                    "cart_affinity", "demographic_match", "score",
                    "recency_boost_applied", "tier_multiplier_applied"):
            assert key in result

    def test_score_between_0_and_100(self):
        c = make_customer()
        o = make_offer()
        result = score_standard_offer(c, o, {})
        assert 0 <= result["score"] <= 100

    def test_recency_boost_applied_when_transacted_within_7_days(self):
        c = make_customer(days_since_last_txn=3)
        o = make_offer()
        result = score_standard_offer(c, o, {})
        assert result["recency_boost_applied"] is True

    def test_recency_boost_not_applied_when_stale(self):
        c = make_customer(days_since_last_txn=30)
        o = make_offer()
        result = score_standard_offer(c, o, {})
        assert result["recency_boost_applied"] is False

    def test_tier_multiplier_applied_for_4uplus_exclusive(self):
        c = make_customer(clv_tier_level_id="4U+")
        o = make_offer(is_appliable_to_j4u_ind=True)
        result = score_standard_offer(c, o, {})
        assert result["tier_multiplier_applied"] is True

    def test_tier_multiplier_not_applied_for_standard_tier(self):
        c = make_customer(clv_tier_level_id="Standard")
        o = make_offer(is_appliable_to_j4u_ind=True)
        result = score_standard_offer(c, o, {})
        assert result["tier_multiplier_applied"] is False

    def test_tier_multiplier_not_applied_for_non_exclusive_offer(self):
        c = make_customer(clv_tier_level_id="4U+")
        o = make_offer(is_appliable_to_j4u_ind=False)
        result = score_standard_offer(c, o, {})
        assert result["tier_multiplier_applied"] is False

    def test_both_boosts_still_capped_at_100(self):
        c = make_customer(clv_tier_level_id="4U+", days_since_last_txn=1,
                          fav_channel="J4U", current_point_balance=9999)
        o = make_offer(is_appliable_to_j4u_ind=True, delivery_channel_cd="J4U")
        lookup = {("HH00001", "Grocery"): 1.0}
        result = score_standard_offer(c, o, lookup)
        assert result["score"] <= 100

    def test_recency_boost_increases_score(self):
        c_stale  = make_customer(days_since_last_txn=30)
        c_recent = make_customer(days_since_last_txn=2)
        o = make_offer()
        assert score_standard_offer(c_recent, o, {})["score"] > \
               score_standard_offer(c_stale,  o, {})["score"]

    def test_score_weights_sum_to_correct_base(self):
        """Verify weighted sum matches manual calculation.

        Components:  affinity=1.0, redemption=1.0, points=1.0, cart=1.0,
                     demographic=0.5 (Grocery category has no boost)
        Expected:    (0.30*1 + 0.25*1 + 0.20*1 + 0.15*1 + 0.10*0.5) * 100 = 95.0
        """
        c = make_customer(fav_channel="J4U", eng_mode_p6m="eCommerce",
                          current_point_balance=9999,
                          doordash_txn_ind_6m=True, instacart_txn_ind_6m=True,
                          uber_txn_ind_6m=True, days_since_last_txn=30)
        o = make_offer(delivery_channel_cd="J4U", is_appliable_to_j4u_ind=False,
                       tier_1_points_threshold=None)
        lookup = {("HH00001", "Grocery"): 1.0}
        result = score_standard_offer(c, o, lookup)
        assert result["score"] == pytest.approx(95.0, abs=0.01)


# ─── score_grocery_reward ─────────────────────────────────────────────────────

class TestScoreGroceryReward:
    def test_below_threshold_returns_none(self):
        c = make_customer(current_point_balance=100)
        o = make_gr_offer(tier_1_points_threshold=300)
        assert score_grocery_reward(c, o, {}, 0) is None

    def test_exactly_at_threshold_is_eligible(self):
        c = make_customer(current_point_balance=300)
        o = make_gr_offer(tier_1_points_threshold=300)
        result = score_grocery_reward(c, o, {}, 0)
        assert result is not None

    def test_score_between_0_and_100(self):
        c = make_customer(current_point_balance=600)
        o = make_gr_offer(tier_1_points_threshold=300)
        result = score_grocery_reward(c, o, {}, 3)
        assert 0 <= result["score"] <= 100

    def test_expiry_multiplier_applied_when_points_expiring(self):
        c_no_expiry  = make_customer(current_point_balance=600,
                                     points_expiring_next_month=0)
        c_expiring   = make_customer(current_point_balance=600,
                                     points_expiring_next_month=300)
        o = make_gr_offer(tier_1_points_threshold=300)
        result_no  = score_grocery_reward(c_no_expiry, o, {}, 0)
        result_exp = score_grocery_reward(c_expiring,  o, {}, 0)
        assert result_exp["recency_boost_applied"] is True
        assert result_no["recency_boost_applied"]  is False
        assert result_exp["score"] > result_no["score"]

    def test_expiry_multiplier_not_applied_when_expiring_below_threshold(self):
        c = make_customer(current_point_balance=600, points_expiring_next_month=100)
        o = make_gr_offer(tier_1_points_threshold=300)
        result = score_grocery_reward(c, o, {}, 0)
        assert result["recency_boost_applied"] is False

    def test_gr_history_floor_prevents_zero(self):
        """First-time GR customer (0 redemptions) should not be penalised to 0."""
        c = make_customer(current_point_balance=600)
        o = make_gr_offer(tier_1_points_threshold=300)
        result = score_grocery_reward(c, o, {}, 0)
        # gr_score floor is 0.3 → demographic_match column holds gr_score
        assert result["demographic_match"] >= 0.3

    def test_higher_balance_above_threshold_scores_higher(self):
        c_just  = make_customer(current_point_balance=300)
        c_2x    = make_customer(current_point_balance=600)
        o = make_gr_offer(tier_1_points_threshold=300)
        assert score_grocery_reward(c_2x, o, {}, 0)["score"] > \
               score_grocery_reward(c_just, o, {}, 0)["score"]

    def test_category_affinity_improves_score(self):
        c = make_customer(current_point_balance=600, household_id="HH00001")
        o = make_gr_offer(tier_1_points_threshold=300, offer_category="Produce")
        lookup_none = {}
        lookup_high = {("HH00001", "Produce"): 0.95}
        assert score_grocery_reward(c, o, lookup_high, 0)["score"] > \
               score_grocery_reward(c, o, lookup_none, 0)["score"]

    def test_score_capped_at_100(self):
        """Expiry multiplier + high balance + high affinity should still cap at 100."""
        c = make_customer(current_point_balance=9999, household_id="HH00001",
                          points_expiring_next_month=9999, days_since_last_txn=0)
        o = make_gr_offer(tier_1_points_threshold=100, tier_1_discount=50.0,
                          offer_category="Produce")
        lookup = {("HH00001", "Produce"): 1.0}
        result = score_grocery_reward(c, o, lookup, 10)
        assert result["score"] <= 100.0


# ─── passes_business_rules ────────────────────────────────────────────────────

class TestPassesBusinessRules:
    def test_standard_offer_always_passes(self):
        c = make_customer(clv_tier_level_id="Standard")
        o = make_offer(is_freshpass_offer_ind=False, is_appliable_to_j4u_ind=False)
        assert passes_business_rules(c, o, set()) is True

    def test_freshpass_offer_excluded_for_non_subscriber(self):
        c = make_customer(household_id="HH00001")
        o = make_offer(is_freshpass_offer_ind=True)
        assert passes_business_rules(c, o, set()) is False

    def test_freshpass_offer_passes_for_subscriber(self):
        c = make_customer(household_id="HH00001")
        o = make_offer(is_freshpass_offer_ind=True)
        assert passes_business_rules(c, o, {"HH00001"}) is True

    def test_j4u_exclusive_excluded_for_standard_tier(self):
        c = make_customer(clv_tier_level_id="Standard")
        o = make_offer(is_appliable_to_j4u_ind=True)
        assert passes_business_rules(c, o, set()) is False

    def test_j4u_exclusive_passes_for_4uplus(self):
        c = make_customer(clv_tier_level_id="4U+")
        o = make_offer(is_appliable_to_j4u_ind=True)
        assert passes_business_rules(c, o, set()) is True


# ─── run_batch_scoring ────────────────────────────────────────────────────────

class TestRunBatchScoring:
    def _make_inputs(self, n_standard=3, n_gr=2, n_customers=2):
        customers_data = [
            make_customer(household_id=f"HH{i:05d}",
                          retail_customer_uuid=f"uuid-{i}")
            for i in range(1, n_customers + 1)
        ]
        customers = pd.DataFrame(customers_data)

        standard_offers = [
            {**make_offer(client_offer_id=f"STD{i:03d}",
                          offer_dsc=f"Standard Offer {i}",
                          program_type="Standard",
                          discount_type_cd="AMT_OFF")}
            for i in range(n_standard)
        ]
        gr_offers = [
            {**make_gr_offer(client_offer_id=f"GR{i:03d}",
                             offer_dsc=f"GR Offer {i}")}
            for i in range(n_gr)
        ]
        offers = pd.DataFrame(standard_offers + gr_offers)

        affinity = pd.DataFrame(columns=["household_id", "category_nm", "affinity_score"])
        gr_history = pd.DataFrame(columns=["household_id", "gr_redemption_count"])
        freshpass_hhs = pd.DataFrame(columns=["household_id"])

        return customers, offers, affinity, gr_history, freshpass_hhs

    def test_returns_dataframe(self):
        inputs = self._make_inputs()
        result = run_batch_scoring(*inputs)
        assert isinstance(result, pd.DataFrame)

    def test_each_customer_gets_scored_rows(self):
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=3, n_gr=2, n_customers=2
        )
        # Give customers enough points for GR offers
        customers["current_point_balance"] = 1000
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        for hid in customers["household_id"]:
            assert hid in result["household_id"].values

    def test_standard_and_gr_ranked_separately(self):
        """Standard rank 1 and GR rank 1 both exist — separate pools."""
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=3, n_gr=2, n_customers=1
        )
        customers["current_point_balance"] = 1000
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        std = result[~result["discount_type_cd"].isin(["GROCERY_REWARD", "DEPT_REWARD", "FREE_ITEM"])]
        gr  = result[result["discount_type_cd"].isin(["GROCERY_REWARD", "DEPT_REWARD", "FREE_ITEM"])]
        assert 1 in std["rank"].values
        assert 1 in gr["rank"].values

    def test_standard_pool_capped_at_top_n(self):
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=TOP_N_STANDARD + 5, n_gr=0, n_customers=1
        )
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        assert len(result) <= TOP_N_STANDARD

    def test_gr_pool_capped_at_top_n(self):
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=0, n_gr=TOP_N_GR + 5, n_customers=1
        )
        customers["current_point_balance"] = 9999
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        assert len(result) <= TOP_N_GR

    def test_gr_offers_excluded_when_below_threshold(self):
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=2, n_gr=3, n_customers=1
        )
        customers["current_point_balance"] = 50  # below all GR thresholds (300)
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        gr_rows = result[result["discount_type_cd"] == "GROCERY_REWARD"]
        assert len(gr_rows) == 0

    def test_freshpass_offers_excluded_for_non_subscribers(self):
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=2, n_gr=0, n_customers=1
        )
        offers["is_freshpass_offer_ind"] = True  # mark all as FreshPass
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        assert len(result) == 0

    def test_rank_starts_at_1_and_is_contiguous(self):
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=3, n_gr=0, n_customers=1
        )
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        std = result[~result["discount_type_cd"].isin(["GROCERY_REWARD", "DEPT_REWARD", "FREE_ITEM"])]
        ranks = sorted(std["rank"].tolist())
        assert ranks == list(range(1, len(ranks) + 1))

    def test_result_sorted_by_score_descending(self):
        customers, offers, affinity, gr_history, freshpass = self._make_inputs(
            n_standard=5, n_gr=0, n_customers=1
        )
        result = run_batch_scoring(customers, offers, affinity, gr_history, freshpass)
        scores = result["score"].tolist()
        assert scores == sorted(scores, reverse=True)
