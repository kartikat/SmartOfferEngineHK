"""
SmartOfferEngine — PostgreSQL Data Generator
Seeds all 18 C360 tables in dependency order with:
  - Real Safeway product UPCs and offer data (Dairy category, extracted from Safeway API)
  - Synthetic correlated data for all other tables

Run: python3 files/data/generate_data.py
Requires: psycopg2-binary sqlalchemy pandas numpy
"""

import os
import random
import uuid
from datetime import datetime, timedelta, date

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

random.seed(42)
np.random.seed(42)

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/smartrewards")
engine = create_engine(DB_URL)

TODAY = date.today()
NOW = datetime.now()

# ─── CONFIG ──────────────────────────────────────────────────────────────────
N_STORES = 12
N_CUSTOMERS = 300          # individual customers
N_HOUSEHOLDS = 120         # ~2.5 customers per household
N_SYNTHETIC_OFFERS = 56    # in addition to real offers
FISCAL_YEAR = 2024

# ─── REAL SAFEWAY DATA ────────────────────────────────────────────────────────
# Products extracted from Safeway API (Dairy category)
REAL_UPCS = [
    {"upc_id": "0002113007010", "upc_dsc": "Lucerne Milk Half Gallon", "brand": "Lucerne", "department_nm": "Dairy Eggs Cheese", "category_nm": "Milk", "sub_category_nm": "Whole Milk", "price": 3.89},
    {"upc_id": "0002113006010", "upc_dsc": "Lucerne Milk Gallon", "brand": "Lucerne", "department_nm": "Dairy Eggs Cheese", "category_nm": "Milk", "sub_category_nm": "Whole Milk", "price": 5.49},
    {"upc_id": "0052100054418", "upc_dsc": "Fairlife Milk 52 oz", "brand": "Fairlife", "department_nm": "Dairy Eggs Cheese", "category_nm": "Milk", "sub_category_nm": "Specialty Milk", "price": 5.99},
    {"upc_id": "0052100099518", "upc_dsc": "Fairlife 2% Reduced Fat Milk 52 oz", "brand": "Fairlife", "department_nm": "Dairy Eggs Cheese", "category_nm": "Milk", "sub_category_nm": "Reduced Fat Milk", "price": 5.99},
    {"upc_id": "0052100099418", "upc_dsc": "Fairlife Whole Milk 52 oz", "brand": "Fairlife", "department_nm": "Dairy Eggs Cheese", "category_nm": "Milk", "sub_category_nm": "Whole Milk", "price": 5.99},
    {"upc_id": "0001600085758", "upc_dsc": "Coffee Mate Original Liquid Creamer 32 oz", "brand": "Coffee Mate", "department_nm": "Dairy Eggs Cheese", "category_nm": "Creamer", "sub_category_nm": "Liquid Creamer", "price": 5.49},
    {"upc_id": "0002100000908", "upc_dsc": "Chobani Plain Greek Yogurt 32 oz", "brand": "Chobani", "department_nm": "Dairy Eggs Cheese", "category_nm": "Yogurt", "sub_category_nm": "Greek Yogurt", "price": 6.49},
    {"upc_id": "0002100003008", "upc_dsc": "Chobani Vanilla Greek Yogurt 32 oz", "brand": "Chobani", "department_nm": "Dairy Eggs Cheese", "category_nm": "Yogurt", "sub_category_nm": "Greek Yogurt", "price": 6.49},
    {"upc_id": "0004126030408", "upc_dsc": "Daisy Sour Cream 16 oz", "brand": "Daisy", "department_nm": "Dairy Eggs Cheese", "category_nm": "Sour Cream", "sub_category_nm": "Regular Sour Cream", "price": 3.29},
    {"upc_id": "0007050028108", "upc_dsc": "Challenge Butter Salted 16 oz", "brand": "Challenge", "department_nm": "Dairy Eggs Cheese", "category_nm": "Butter", "sub_category_nm": "Salted Butter", "price": 5.99},
    {"upc_id": "0007050028208", "upc_dsc": "Challenge Butter Unsalted 16 oz", "brand": "Challenge", "department_nm": "Dairy Eggs Cheese", "category_nm": "Butter", "sub_category_nm": "Unsalted Butter", "price": 5.99},
    {"upc_id": "0007278900018", "upc_dsc": "Tillamook Medium Cheddar Cheese 32 oz", "brand": "Tillamook", "department_nm": "Dairy Eggs Cheese", "category_nm": "Cheese", "sub_category_nm": "Cheddar Cheese", "price": 9.99},
    {"upc_id": "0007278900118", "upc_dsc": "Tillamook Sharp Cheddar Cheese 32 oz", "brand": "Tillamook", "department_nm": "Dairy Eggs Cheese", "category_nm": "Cheese", "sub_category_nm": "Cheddar Cheese", "price": 9.99},
    {"upc_id": "0003560020508", "upc_dsc": "FAGE Total 0% Greek Yogurt 35.3 oz", "brand": "FAGE", "department_nm": "Dairy Eggs Cheese", "category_nm": "Yogurt", "sub_category_nm": "Greek Yogurt", "price": 8.99},
    {"upc_id": "0005714700818", "upc_dsc": "Greek Gods Honey Vanilla Yogurt 24 oz", "brand": "Greek Gods", "department_nm": "Dairy Eggs Cheese", "category_nm": "Yogurt", "sub_category_nm": "Greek Yogurt", "price": 5.49},
    {"upc_id": "0085239012918", "upc_dsc": "SToK Cold Brew Coffee 48 oz", "brand": "SToK", "department_nm": "Dairy Eggs Cheese", "category_nm": "Coffee Drinks", "sub_category_nm": "Cold Brew", "price": 6.99},
    {"upc_id": "0001200012318", "upc_dsc": "Tropicana Pure Premium Orange Juice 52 oz", "brand": "Tropicana", "department_nm": "Dairy Eggs Cheese", "category_nm": "Juice", "sub_category_nm": "Orange Juice", "price": 6.49},
    {"upc_id": "0007080034218", "upc_dsc": "Frigo Cheese Heads String Cheese 12 ct", "brand": "Frigo", "department_nm": "Dairy Eggs Cheese", "category_nm": "Cheese", "sub_category_nm": "String Cheese", "price": 5.99},
    {"upc_id": "0007910301118", "upc_dsc": "O Organics Whole Milk Gallon", "brand": "O Organics", "department_nm": "Dairy Eggs Cheese", "category_nm": "Milk", "sub_category_nm": "Organic Milk", "price": 8.49},
    {"upc_id": "0008956801218", "upc_dsc": "Vital Farms Pasture-Raised Eggs 12 ct", "brand": "Vital Farms", "department_nm": "Dairy Eggs Cheese", "category_nm": "Eggs", "sub_category_nm": "Pasture-Raised Eggs", "price": 8.99},
    {"upc_id": "0002113500118", "upc_dsc": "Lucerne Large Grade A Eggs 12 ct", "brand": "Lucerne", "department_nm": "Dairy Eggs Cheese", "category_nm": "Eggs", "sub_category_nm": "Large Eggs", "price": 4.49},
    {"upc_id": "0002113500218", "upc_dsc": "Lucerne Large Grade A Eggs 18 ct", "brand": "Lucerne", "department_nm": "Dairy Eggs Cheese", "category_nm": "Eggs", "sub_category_nm": "Large Eggs", "price": 6.49},
    {"upc_id": "0007278950018", "upc_dsc": "Tillamook Colby Jack Cheese 32 oz", "brand": "Tillamook", "department_nm": "Dairy Eggs Cheese", "category_nm": "Cheese", "sub_category_nm": "Colby Jack Cheese", "price": 9.99},
    {"upc_id": "0004126060418", "upc_dsc": "Daisy Cottage Cheese 24 oz", "brand": "Daisy", "department_nm": "Dairy Eggs Cheese", "category_nm": "Cottage Cheese", "sub_category_nm": "Regular", "price": 4.49},
    {"upc_id": "0002100050018", "upc_dsc": "Chobani Oat Drink Original 52 oz", "brand": "Chobani", "department_nm": "Dairy Eggs Cheese", "category_nm": "Plant Based Milk", "sub_category_nm": "Oat Milk", "price": 5.99},
    {"upc_id": "0052100010018", "upc_dsc": "Fairlife Chocolate Milk 52 oz", "brand": "Fairlife", "department_nm": "Dairy Eggs Cheese", "category_nm": "Milk", "sub_category_nm": "Flavored Milk", "price": 5.99},
    {"upc_id": "0001600085858", "upc_dsc": "Coffee Mate French Vanilla Creamer 32 oz", "brand": "Coffee Mate", "department_nm": "Dairy Eggs Cheese", "category_nm": "Creamer", "sub_category_nm": "Liquid Creamer", "price": 5.49},
    {"upc_id": "0007050040118", "upc_dsc": "Challenge Spreadable Butter 15 oz", "brand": "Challenge", "department_nm": "Dairy Eggs Cheese", "category_nm": "Butter", "sub_category_nm": "Spreadable Butter", "price": 5.49},
    {"upc_id": "0007278900218", "upc_dsc": "Tillamook Pepper Jack Cheese 16 oz", "brand": "Tillamook", "department_nm": "Dairy Eggs Cheese", "category_nm": "Cheese", "sub_category_nm": "Pepper Jack Cheese", "price": 5.99},
    {"upc_id": "0003560049918", "upc_dsc": "FAGE Total 2% Greek Yogurt 35.3 oz", "brand": "FAGE", "department_nm": "Dairy Eggs Cheese", "category_nm": "Yogurt", "sub_category_nm": "Greek Yogurt", "price": 8.99},
]

# Synthetic products for other categories
SYNTHETIC_UPCS = [
    # Grocery / Center Store
    {"upc_id": "0001600012345", "upc_dsc": "Cheerios Original Cereal 18 oz", "brand": "General Mills", "department_nm": "Grocery", "category_nm": "Cereal", "sub_category_nm": "Oat Cereal", "price": 4.99},
    {"upc_id": "0001600023456", "upc_dsc": "Quaker Oats Old Fashioned 42 oz", "brand": "Quaker", "department_nm": "Grocery", "category_nm": "Hot Cereal", "sub_category_nm": "Oatmeal", "price": 5.49},
    {"upc_id": "0001600034567", "upc_dsc": "Coca-Cola Classic 12 pk 12 oz Cans", "brand": "Coca-Cola", "department_nm": "Grocery", "category_nm": "Carbonated Beverages", "sub_category_nm": "Cola", "price": 7.99},
    {"upc_id": "0001600045678", "upc_dsc": "Lay's Classic Potato Chips 8 oz", "brand": "Lay's", "department_nm": "Grocery", "category_nm": "Snacks", "sub_category_nm": "Potato Chips", "price": 4.29},
    {"upc_id": "0001600056789", "upc_dsc": "Oreo Chocolate Sandwich Cookies 14.3 oz", "brand": "Nabisco", "department_nm": "Grocery", "category_nm": "Cookies", "sub_category_nm": "Sandwich Cookies", "price": 4.49},
    {"upc_id": "0001600067890", "upc_dsc": "Campbell's Chicken Noodle Soup 10.75 oz", "brand": "Campbell's", "department_nm": "Grocery", "category_nm": "Soup", "sub_category_nm": "Canned Soup", "price": 2.49},
    {"upc_id": "0001600078901", "upc_dsc": "Heinz Tomato Ketchup 32 oz", "brand": "Heinz", "department_nm": "Grocery", "category_nm": "Condiments", "sub_category_nm": "Ketchup", "price": 4.99},
    {"upc_id": "0001600089012", "upc_dsc": "Skippy Creamy Peanut Butter 16.3 oz", "brand": "Skippy", "department_nm": "Grocery", "category_nm": "Nut Butters", "sub_category_nm": "Peanut Butter", "price": 4.49},
    # Produce
    {"upc_id": "0004011000018", "upc_dsc": "Bananas - per lb", "brand": "Dole", "department_nm": "Produce", "category_nm": "Fresh Fruit", "sub_category_nm": "Tropical Fruit", "price": 0.59},
    {"upc_id": "0004011000118", "upc_dsc": "Strawberries 16 oz", "brand": "Driscoll's", "department_nm": "Produce", "category_nm": "Fresh Fruit", "sub_category_nm": "Berries", "price": 4.99},
    {"upc_id": "0004011000218", "upc_dsc": "Baby Carrots 16 oz", "brand": "Grimmway", "department_nm": "Produce", "category_nm": "Fresh Vegetables", "sub_category_nm": "Carrots", "price": 1.99},
    {"upc_id": "0004011000318", "upc_dsc": "Spinach 5 oz", "brand": "Earthbound Farm", "department_nm": "Produce", "category_nm": "Fresh Vegetables", "sub_category_nm": "Leafy Greens", "price": 3.99},
    # Bakery
    {"upc_id": "0003800012345", "upc_dsc": "Nature's Own Honey Wheat Bread 20 oz", "brand": "Nature's Own", "department_nm": "Bakery", "category_nm": "Bread", "sub_category_nm": "Whole Wheat Bread", "price": 3.99},
    {"upc_id": "0003800023456", "upc_dsc": "Dave's Killer Bread 21 Whole Grains 27 oz", "brand": "Dave's Killer Bread", "department_nm": "Bakery", "category_nm": "Bread", "sub_category_nm": "Whole Grain Bread", "price": 5.99},
    {"upc_id": "0003800034567", "upc_dsc": "Thomas' English Muffins 6 ct", "brand": "Thomas'", "department_nm": "Bakery", "category_nm": "English Muffins", "sub_category_nm": "Original", "price": 4.49},
    # Meat
    {"upc_id": "0002300012345", "upc_dsc": "O Organics Chicken Breast Boneless Skinless per lb", "brand": "O Organics", "department_nm": "Meat", "category_nm": "Chicken", "sub_category_nm": "Boneless Chicken Breast", "price": 8.99},
    {"upc_id": "0002300023456", "upc_dsc": "80/20 Ground Beef per lb", "brand": "Open Nature", "department_nm": "Meat", "category_nm": "Beef", "sub_category_nm": "Ground Beef", "price": 5.99},
    # Frozen
    {"upc_id": "0005100012345", "upc_dsc": "Birds Eye Steamfresh Mixed Vegetables 10 oz", "brand": "Birds Eye", "department_nm": "Frozen", "category_nm": "Frozen Vegetables", "sub_category_nm": "Mixed Vegetables", "price": 2.49},
    {"upc_id": "0005100023456", "upc_dsc": "DiGiorno Rising Crust Pepperoni Pizza 28.2 oz", "brand": "DiGiorno", "department_nm": "Frozen", "category_nm": "Frozen Pizza", "sub_category_nm": "Rising Crust", "price": 9.99},
    # Household
    {"upc_id": "0003700012345", "upc_dsc": "Tide Original Liquid Laundry Detergent 64 oz", "brand": "Tide", "department_nm": "Household", "category_nm": "Laundry", "sub_category_nm": "Liquid Detergent", "price": 12.99},
    {"upc_id": "0003700023456", "upc_dsc": "Bounty Select-A-Size Paper Towels 6 rolls", "brand": "Bounty", "department_nm": "Household", "category_nm": "Paper Products", "sub_category_nm": "Paper Towels", "price": 11.99},
    # Seafood
    {"upc_id": "0006900012345", "upc_dsc": "Fresh Atlantic Salmon Fillet per lb", "brand": "Open Nature", "department_nm": "Seafood", "category_nm": "Fresh Fish", "sub_category_nm": "Salmon", "price": 11.99},
    {"upc_id": "0006900023456", "upc_dsc": "Wild Alaskan Cod Fillet per lb", "brand": "Open Nature", "department_nm": "Seafood", "category_nm": "Fresh Fish", "sub_category_nm": "White Fish", "price": 9.99},
    {"upc_id": "0006900034567", "upc_dsc": "Raw Shrimp 31-40 ct 16 oz", "brand": "Open Nature", "department_nm": "Seafood", "category_nm": "Shrimp", "sub_category_nm": "Raw Shrimp", "price": 9.49},
    {"upc_id": "0001480000018", "upc_dsc": "StarKist Chunk Light Tuna in Water 5 oz 4 pk", "brand": "StarKist", "department_nm": "Seafood", "category_nm": "Canned Seafood", "sub_category_nm": "Canned Tuna", "price": 6.99},
    # Deli
    {"upc_id": "0008000012345", "upc_dsc": "Safeway Rotisserie Chicken 3 lb", "brand": "Safeway", "department_nm": "Deli", "category_nm": "Rotisserie", "sub_category_nm": "Whole Chicken", "price": 8.99},
    {"upc_id": "0008000023456", "upc_dsc": "Boar's Head Oven Gold Turkey Breast per lb", "brand": "Boar's Head", "department_nm": "Deli", "category_nm": "Sliced Meats", "sub_category_nm": "Turkey", "price": 10.99},
    {"upc_id": "0008000034567", "upc_dsc": "Boar's Head Black Forest Ham per lb", "brand": "Boar's Head", "department_nm": "Deli", "category_nm": "Sliced Meats", "sub_category_nm": "Ham", "price": 9.99},
    {"upc_id": "0008000045678", "upc_dsc": "Primo Taglio Genoa Salami per lb", "brand": "Primo Taglio", "department_nm": "Deli", "category_nm": "Sliced Meats", "sub_category_nm": "Salami", "price": 8.99},
    # Additional Grocery / Pantry
    {"upc_id": "0007680012345", "upc_dsc": "Barilla Spaghetti 16 oz", "brand": "Barilla", "department_nm": "Grocery", "category_nm": "Pasta", "sub_category_nm": "Spaghetti", "price": 1.99},
    {"upc_id": "0007680023456", "upc_dsc": "Bertolli Extra Virgin Olive Oil 16.9 oz", "brand": "Bertolli", "department_nm": "Grocery", "category_nm": "Cooking Oil", "sub_category_nm": "Olive Oil", "price": 8.99},
    {"upc_id": "0007680034567", "upc_dsc": "Pace Chunky Salsa 16 oz", "brand": "Pace", "department_nm": "Grocery", "category_nm": "Condiments", "sub_category_nm": "Salsa", "price": 3.49},
    # Additional Produce
    {"upc_id": "0004011000418", "upc_dsc": "Organic Fuji Apples 3 lb bag", "brand": "O Organics", "department_nm": "Produce", "category_nm": "Fresh Fruit", "sub_category_nm": "Apples", "price": 5.99},
    {"upc_id": "0004011000518", "upc_dsc": "Avocados 4 ct", "brand": "Calavo", "department_nm": "Produce", "category_nm": "Fresh Fruit", "sub_category_nm": "Avocados", "price": 4.99},
    {"upc_id": "0004011000618", "upc_dsc": "Broccoli Crown per lb", "brand": "Fresh", "department_nm": "Produce", "category_nm": "Fresh Vegetables", "sub_category_nm": "Cruciferous", "price": 1.99},
    # Additional Meat
    {"upc_id": "0002300034567", "upc_dsc": "Pork Tenderloin per lb", "brand": "Open Nature", "department_nm": "Meat", "category_nm": "Pork", "sub_category_nm": "Tenderloin", "price": 6.99},
    {"upc_id": "0002300045678", "upc_dsc": "Beef Sirloin Steak per lb", "brand": "Open Nature", "department_nm": "Meat", "category_nm": "Beef", "sub_category_nm": "Sirloin", "price": 9.99},
    # Additional Frozen
    {"upc_id": "0005100034567", "upc_dsc": "Haagen-Dazs Vanilla Ice Cream 14 oz", "brand": "Haagen-Dazs", "department_nm": "Frozen", "category_nm": "Ice Cream", "sub_category_nm": "Premium Ice Cream", "price": 5.99},
    {"upc_id": "0005100045678", "upc_dsc": "Amy's Frozen Burrito 6 oz", "brand": "Amy's", "department_nm": "Frozen", "category_nm": "Frozen Meals", "sub_category_nm": "Burritos", "price": 3.99},
    # Additional Bakery
    {"upc_id": "0003800045678", "upc_dsc": "Semifreddi's Rustic Sourdough 24 oz", "brand": "Semifreddi's", "department_nm": "Bakery", "category_nm": "Bread", "sub_category_nm": "Sourdough", "price": 5.49},
    {"upc_id": "0003800056789", "upc_dsc": "O Organics Flour Tortillas 10 ct", "brand": "O Organics", "department_nm": "Bakery", "category_nm": "Tortillas", "sub_category_nm": "Flour Tortillas", "price": 3.99},
]

# Own-brand products (for own_brands_ind)
OWN_BRAND_UPCS = ["0007910301118"]  # O Organics

# Real offer data from Safeway API
REAL_OFFERS = [
    {
        "client_offer_id": "OFR-41758637",
        "oms_offer_id": "41758637",
        "offer_dsc": "Lucerne or Challenge Butter Club Card Price $3.99 ea",
        "title_dsc1": "Club Card Price",
        "headline_txt": "$3.99 ea when you buy 1",
        "description_txt": "Lucerne Milk Gallon or Challenge Butter Salted 16 oz. Club Card Price.",
        "offer_type": "ITEM_DISCOUNT",
        "delivery_channel_cd": "J4U",
        "delivery_channel_dsc": "Club Card",
        "program_type": "Club Card",
        "discount_type_cd": "AMT_OFF",
        "discount_value": 1.50,
        "min_purch_qty": 1,
        "target_level_cd": "ITEM",
        "is_appliable_to_j4u_ind": False,
        "is_freshpass_offer_ind": False,
        "is_in_weekly_ad": True,
        "upcs": ["0002113006010", "0007050028108"],
    },
    {
        "client_offer_id": "OFR-46066809",
        "oms_offer_id": "46066809",
        "offer_dsc": "Earn 4X Points on Participating Dairy Items",
        "title_dsc1": "4X Points",
        "headline_txt": "Earn 4X Points",
        "description_txt": "Earn 4X Points on participating Dairy, Eggs & Cheese items when you clip and redeem.",
        "offer_type": "REWARDS_ACCUMULATION",
        "delivery_channel_cd": "J4U",
        "delivery_channel_dsc": "Digital Offer",
        "program_type": "Points",
        "discount_type_cd": "POINTS_MULTIPLIER",
        "discount_value": 4.0,
        "min_purch_qty": 1,
        "target_level_cd": "CATEGORY",
        "is_appliable_to_j4u_ind": True,
        "is_freshpass_offer_ind": False,
        "is_in_weekly_ad": False,
        "upcs": ["0002113007010", "0052100054418", "0002100000908", "0007278900018", "0008956801218"],
    },
    {
        "client_offer_id": "OFR-58577250",
        "oms_offer_id": "58577250",
        "offer_dsc": "Buy Oreo Cookies, Save $0.50 on Milk",
        "title_dsc1": "Buy X Get Y",
        "headline_txt": "$0.50 off Milk when you buy Oreo",
        "description_txt": "Purchase any Oreo Sandwich Cookies and save $0.50 on any Lucerne Milk or Fairlife Milk.",
        "offer_type": "BUYX_GETY",
        "delivery_channel_cd": "J4U",
        "delivery_channel_dsc": "Digital Offer",
        "program_type": "Bundle",
        "discount_type_cd": "AMT_OFF",
        "discount_value": 0.50,
        "min_purch_qty": 1,
        "target_level_cd": "ITEM",
        "is_appliable_to_j4u_ind": False,
        "is_freshpass_offer_ind": False,
        "is_in_weekly_ad": False,
        "upcs": ["0002113007010", "0002113006010", "0052100054418", "0001600056789"],
    },
    {
        "client_offer_id": "OFR-62739257",
        "oms_offer_id": "62739257",
        "offer_dsc": "Earn 2X Points on Dairy Purchases",
        "title_dsc1": "2X Points",
        "headline_txt": "Earn 2X Points In-Store",
        "description_txt": "Earn 2X Points on all Dairy purchases in-store. No clip needed.",
        "offer_type": "REWARDS_ACCUMULATION",
        "delivery_channel_cd": "Weekly Ad",
        "delivery_channel_dsc": "In-Store",
        "program_type": "Points",
        "discount_type_cd": "POINTS_MULTIPLIER",
        "discount_value": 2.0,
        "min_purch_qty": 1,
        "target_level_cd": "CATEGORY",
        "is_appliable_to_j4u_ind": False,
        "is_freshpass_offer_ind": False,
        "is_in_weekly_ad": True,
        "upcs": [],  # category-level, no specific UPCs
    },
    {
        "client_offer_id": "OFR-64279529",
        "oms_offer_id": "64279529",
        "offer_dsc": "Schedule & Save 5% on Creamer",
        "title_dsc1": "Schedule & Save",
        "headline_txt": "5% off when you Subscribe",
        "description_txt": "Subscribe to Coffee Mate or Chobani items and save 5% on every order.",
        "offer_type": "ITEM_DISCOUNT",
        "delivery_channel_cd": "Auto Clip",
        "delivery_channel_dsc": "eCommerce Subscription",
        "program_type": "Schedule & Save",
        "discount_type_cd": "PCT_OFF",
        "discount_value": 5.0,
        "min_purch_qty": 1,
        "target_level_cd": "ITEM",
        "is_appliable_to_j4u_ind": False,
        "is_freshpass_offer_ind": True,
        "is_in_weekly_ad": False,
        "upcs": ["0001600085758", "0001600085858", "0002100000908"],
    },
    {
        "client_offer_id": "OFR-81759989",
        "oms_offer_id": "81759989",
        "offer_dsc": "FreshPass Exclusive: Free Delivery on Dairy Orders",
        "title_dsc1": "FreshPass Exclusive",
        "headline_txt": "Free Delivery on $35+ Dairy Orders",
        "description_txt": "FreshPass members get free delivery when Dairy items total $35 or more.",
        "offer_type": "ITEM_DISCOUNT",
        "delivery_channel_cd": "Auto Clip",
        "delivery_channel_dsc": "eCommerce",
        "program_type": "FreshPass",
        "discount_type_cd": "FREE_DELIVERY",
        "discount_value": 0.0,
        "min_purch_qty": 1,
        "min_purch_amt": 35.00,
        "target_level_cd": "BASKET",
        "is_appliable_to_j4u_ind": False,
        "is_freshpass_offer_ind": True,
        "is_in_weekly_ad": False,
        "upcs": [],
    },
]

# Synthetic offers for other categories
# Tuple: (category, channel, discount_type_cd, discount_value, target_level, j4u_exclusive, description, pts_threshold)
# pts_threshold is only used for GROCERY_REWARD / DEPT_REWARD / FREE_ITEM offers
SYNTHETIC_OFFER_TEMPLATES = [
    # ── Standard category discounts ───────────────────────────────────────────
    ("Grocery", "J4U", "AMT_OFF", 1.00, "ITEM", False, "Save $1 on Cheerios Original Cereal", None),
    ("Grocery", "J4U", "PCT_OFF", 10.0, "CATEGORY", False, "10% off Snacks when you buy 2", None),
    ("Grocery", "Weekly Ad", "AMT_OFF", 2.00, "ITEM", False, "Save $2 on Coca-Cola 12 Pack", None),
    ("Produce", "J4U", "PCT_OFF", 20.0, "CATEGORY", False, "20% off Fresh Berries", None),
    ("Produce", "Weekly Ad", "AMT_OFF", 1.50, "ITEM", False, "Save $1.50 on Organic Strawberries", None),
    ("Bakery", "J4U", "AMT_OFF", 1.00, "ITEM", False, "Save $1 on Dave's Killer Bread", None),
    ("Bakery", "Weekly Ad", "AMT_OFF", 2.00, "CATEGORY", False, "$2 off any 2 Bread items", None),
    ("Meat", "Weekly Ad", "PCT_OFF", 15.0, "ITEM", False, "15% off O Organics Chicken Breast", None),
    ("Meat", "J4U", "AMT_OFF", 3.00, "ITEM", True, "4U+ Exclusive: Save $3 on Organic Beef", None),
    ("Frozen", "J4U", "PCT_OFF", 25.0, "CATEGORY", False, "25% off any Frozen Pizza", None),
    ("Household", "J4U", "AMT_OFF", 2.00, "ITEM", False, "Save $2 on Tide Detergent", None),
    ("Household", "Weekly Ad", "PCT_OFF", 10.0, "CATEGORY", False, "10% off Paper Products", None),
    ("Grocery", "J4U", "POINTS_MULTIPLIER", 3.0, "CATEGORY", True, "4U+ Earn 3X Points on Cereal", None),
    ("Dairy Eggs Cheese", "J4U", "POINTS_MULTIPLIER", 2.0, "CATEGORY", False, "Earn 2X Points on Eggs", None),
    ("Fuel", "J4U", "FUEL_CENTS", 0.10, "BASKET", False, "Save 10¢/gal on Fuel", None),
    ("Fuel", "Weekly Ad", "FUEL_CENTS", 0.20, "BASKET", True, "4U+ Save 20¢/gal on Fuel", None),
    ("Grocery", "Auto Clip", "PCT_OFF", 5.0, "BASKET", False, "Auto-Clip: 5% off Your Order", None),
    ("Produce", "J4U", "AMT_OFF", 1.00, "CATEGORY", False, "$1 off any Fresh Vegetable Purchase", None),
    # Seafood
    ("Seafood", "J4U", "AMT_OFF", 3.00, "ITEM", False, "Save $3 on Fresh Atlantic Salmon", None),
    ("Seafood", "Weekly Ad", "PCT_OFF", 20.0, "ITEM", False, "20% off Wild Caught Shrimp", None),
    ("Seafood", "J4U", "AMT_OFF", 1.00, "ITEM", False, "Buy 2 Canned Tuna, Save $1", None),
    ("Seafood", "J4U", "POINTS_MULTIPLIER", 3.0, "CATEGORY", True, "4U+ Earn 3X Points on Seafood", None),
    # Deli
    ("Deli", "Weekly Ad", "AMT_OFF", 2.00, "ITEM", False, "$2 off Rotisserie Chicken", None),
    ("Deli", "J4U", "PCT_OFF", 15.0, "CATEGORY", False, "15% off Boar's Head Deli Meats", None),
    ("Deli", "Weekly Ad", "POINTS_MULTIPLIER", 2.0, "CATEGORY", False, "Earn 2X Points on Deli Purchases", None),
    # More Produce / Meat / Frozen / Pantry
    ("Produce", "J4U", "PCT_OFF", 25.0, "ITEM", False, "25% off Organic Apples", None),
    ("Produce", "Weekly Ad", "AMT_OFF", 1.50, "ITEM", False, "Save $1.50 on Avocados", None),
    ("Meat", "J4U", "AMT_OFF", 5.00, "ITEM", False, "Save $5 on Pork Tenderloin", None),
    ("Meat", "Weekly Ad", "AMT_OFF", 2.00, "ITEM", False, "$2 off Beef Sirloin per lb", None),
    ("Frozen", "J4U", "AMT_OFF", 2.00, "CATEGORY", False, "$2 off Frozen Vegetables", None),
    ("Frozen", "Weekly Ad", "PCT_OFF", 20.0, "ITEM", False, "20% off Premium Ice Cream", None),
    ("Grocery", "J4U", "AMT_OFF", 1.50, "ITEM", False, "$1.50 off Barilla Pasta", None),
    ("Grocery", "Weekly Ad", "AMT_OFF", 2.00, "ITEM", False, "Save $2 on Extra Virgin Olive Oil", None),
    # ── Grocery Reward: Basket discounts (one per tier) ───────────────────────
    ("Grocery", "J4U", "GROCERY_REWARD",  1.00, "BASKET", False, "$1 Off Basket — Grocery Reward 100 pts",  100),
    ("Grocery", "J4U", "GROCERY_REWARD",  2.00, "BASKET", False, "$2 Off Basket — Grocery Reward 200 pts",  200),
    ("Grocery", "J4U", "GROCERY_REWARD",  4.00, "BASKET", False, "$4 Off Basket — Grocery Reward 300 pts",  300),
    ("Grocery", "J4U", "GROCERY_REWARD",  5.00, "BASKET", False, "$5 Off Basket — Grocery Reward 400 pts",  400),
    ("Grocery", "J4U", "GROCERY_REWARD",  7.00, "BASKET", False, "$7 Off Basket — Grocery Reward 500 pts",  500),
    ("Grocery", "J4U", "GROCERY_REWARD", 10.00, "BASKET", False, "$10 Off Basket — Grocery Reward 700 pts", 700),
    ("Grocery", "J4U", "GROCERY_REWARD", 15.00, "BASKET", False, "$15 Off Basket — Grocery Reward 1000 pts", 1000),
    ("Grocery", "J4U", "GROCERY_REWARD", 20.00, "BASKET", False, "$20 Off Basket — Grocery Reward 1200 pts", 1200),
    # ── Grocery Reward: Department discounts ─────────────────────────────────
    ("Bakery",  "J4U", "DEPT_REWARD", 2.00, "CATEGORY", False, "$2 Off Bakery Department — 100 pts",  100),
    ("Produce", "J4U", "DEPT_REWARD", 3.00, "CATEGORY", False, "$3 Off Produce Department — 200 pts", 200),
    ("Bakery",  "J4U", "DEPT_REWARD", 5.00, "CATEGORY", False, "$5 Off Bakery Department — 300 pts",  300),
    ("Meat",    "J4U", "DEPT_REWARD", 7.00, "CATEGORY", False, "$7 Off Meat Department — 400 pts",    400),
    ("Produce", "J4U", "DEPT_REWARD", 7.00, "CATEGORY", False, "$7 Off Produce Department — 500 pts", 500),
    # ── Grocery Reward: Free item offers (2 per tier, 100–700 pts) ────────────
    ("Grocery",          "J4U", "FREE_ITEM", 1.99,  "ITEM", False, "FREE Signature SELECT Canned Vegetables — 100 pts",    100),
    ("Seafood",          "J4U", "FREE_ITEM", 2.49,  "ITEM", False, "FREE Signature SELECT Chunk Light Tuna 5-oz — 100 pts", 100),
    ("Dairy Eggs Cheese","J4U", "FREE_ITEM", 3.49,  "ITEM", False, "FREE Lucerne Cream Cheese Brick 8-oz — 200 pts",       200),
    ("Frozen",           "J4U", "FREE_ITEM", 2.49,  "ITEM", False, "FREE Signature SELECT Frozen Vegetables 12-oz — 200 pts", 200),
    ("Grocery",          "J4U", "FREE_ITEM", 4.99,  "ITEM", False, "FREE Signature SELECT Orange Juice 59-oz — 300 pts",   300),
    ("Frozen",           "J4U", "FREE_ITEM", 5.99,  "ITEM", False, "FREE Signature SELECT Ice Cream Sandwiches 12-ct — 300 pts", 300),
    ("Deli",             "J4U", "FREE_ITEM", 8.99,  "ITEM", False, "FREE Signature Cafe Rotisserie Chicken — 400 pts",     400),
    ("Frozen",           "J4U", "FREE_ITEM", 4.99,  "ITEM", False, "FREE Signature SELECT Breakfast Sandwiches 4-ct — 400 pts", 400),
    ("Dairy Eggs Cheese","J4U", "FREE_ITEM", 9.99,  "ITEM", False, "FREE Lucerne Chunk Cheese 32-oz — 500 pts",            500),
    ("Deli",             "J4U", "FREE_ITEM", 7.99,  "ITEM", False, "FREE Signature SELECT Whole Roasted Chicken — 500 pts", 500),
    ("Meat",             "J4U", "FREE_ITEM", 14.99, "ITEM", False, "FREE Signature SELECT Bacon 48-oz — 700 pts",          700),
    ("Seafood",          "J4U", "FREE_ITEM", 12.99, "ITEM", False, "FREE Open Nature Sea Scallops 16-oz — 700 pts",        700),
]

DIVISIONS = [
    {"division_id": "DIV01", "division_nm": "Northern California", "banner_nm": "Safeway"},
    {"division_id": "DIV02", "division_nm": "Southern California", "banner_nm": "Vons"},
    {"division_id": "DIV03", "division_nm": "Pacific Northwest", "banner_nm": "Safeway"},
    {"division_id": "DIV04", "division_nm": "Texas", "banner_nm": "Tom Thumb"},
    {"division_id": "DIV05", "division_nm": "Mountain", "banner_nm": "Albertsons"},
]

CITIES = [
    ("San Francisco", "CA", "94105", "DIV01"), ("Oakland", "CA", "94601", "DIV01"),
    ("San Jose", "CA", "95101", "DIV01"), ("Los Angeles", "CA", "90001", "DIV02"),
    ("San Diego", "CA", "92101", "DIV02"), ("Seattle", "WA", "98101", "DIV03"),
    ("Portland", "OR", "97201", "DIV03"), ("Dallas", "TX", "75201", "DIV04"),
    ("Houston", "TX", "77001", "DIV04"), ("Denver", "CO", "80201", "DIV05"),
    ("Phoenix", "AZ", "85001", "DIV05"), ("Boise", "ID", "83701", "DIV05"),
]

FIRST_NAMES = ["James", "Maria", "David", "Sarah", "Michael", "Jennifer", "Robert", "Emily",
               "William", "Jessica", "John", "Ashley", "Christopher", "Amanda", "Daniel",
               "Melissa", "Matthew", "Nicole", "Joshua", "Stephanie", "Andrew", "Rachel",
               "Kevin", "Samantha", "Brian", "Brittany", "Timothy", "Elizabeth", "Ryan", "Lauren"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
              "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

SHOPSTYLES = ["Convenience", "Health-Conscious", "Value-Seeker", "Brand-Loyal", "Variety-Seeker"]
MYNEED = ["Stock Up", "Daily Essentials", "Special Occasion", "Healthy Living", "Quick Meal"]
CHURN_SEGMENTS = ["Low Risk", "Medium Risk", "High Risk", "Already Churned"]
TRIBES = ["Healthy Families", "Budget Shoppers", "Convenience Seekers", "Gourmet Explorers", "Senior Savers"]
DIET_PREFS = ["None", "Vegetarian", "Vegan", "Gluten-Free", "Kosher", "Halal", "Organic"]
INCOME_BANDS = ["<$30k", "$30k-$60k", "$60k-$100k", "$100k-$150k", ">$150k"]
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

ALL_CATEGORIES = ["Dairy Eggs Cheese", "Grocery", "Produce", "Bakery", "Meat", "Frozen", "Household", "Fuel", "Seafood", "Deli"]
CATEGORY_IDS = {cat: f"CAT{i+1:03d}" for i, cat in enumerate(ALL_CATEGORIES)}


def rnd_date(days_back_min=0, days_back_max=730):
    return TODAY - timedelta(days=random.randint(days_back_min, days_back_max))


def rnd_ts(days_back_min=0, days_back_max=730):
    d = rnd_date(days_back_min, days_back_max)
    return datetime.combine(d, datetime.min.time()) + timedelta(
        hours=random.randint(6, 22), minutes=random.randint(0, 59)
    )


def new_uuid():
    return str(uuid.uuid4())


# ─── GENERATORS ──────────────────────────────────────────────────────────────

def gen_stores():
    rows = []
    for i, (city, state, zip_, div_id) in enumerate(CITIES[:N_STORES]):
        div = next(d for d in DIVISIONS if d["division_id"] == div_id)
        store_id = f"STR{i+1:04d}"
        rows.append({
            "store_id": store_id,
            "store_nm": f"{div['banner_nm']} {city}",
            "city": city, "state": state, "zip": zip_,
            "address": f"{random.randint(100, 9999)} Main St",
            "division_id": div_id,
            "division_nm": div["division_nm"],
            "banner_nm": div["banner_nm"],
            "b4u_region_id": f"REG{div_id[-2:]}",
            "b4u_region_nm": div["division_nm"],
            "latitude": round(random.uniform(25, 48), 6),
            "longitude": round(random.uniform(-122, -80), 6),
            "ecom_ind": random.random() > 0.2,
            "dug_ind": random.random() > 0.4,
            "grocery_rewards_program_ind": True,
            "gas_rewards_program_ind": random.random() > 0.3,
            "fuel_partner_nm": random.choice(["Shell", "Chevron", None, "Exxon"]),
            "pharmacy_ind": random.random() > 0.3,
            "starbucks_ind": random.random() > 0.5,
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_upcs():
    rows = []
    all_upcs = REAL_UPCS + SYNTHETIC_UPCS
    for p in all_upcs:
        dept = p["department_nm"]
        rows.append({
            "upc_id": p["upc_id"],
            "upc_dsc": p["upc_dsc"],
            "department_id": CATEGORY_IDS.get(dept, "CAT001"),
            "department_nm": dept,
            "category_id": f"CAT{abs(hash(p['category_nm'])) % 900 + 100:03d}",
            "category_nm": p["category_nm"],
            "sub_category_id": f"SUB{abs(hash(p.get('sub_category_nm', ''))) % 900 + 100:03d}",
            "sub_category_nm": p.get("sub_category_nm", ""),
            "brand": p.get("brand", ""),
            "vendor_nm": p.get("brand", ""),
            "own_brands_ind": p["upc_id"] in OWN_BRAND_UPCS or p.get("brand", "") == "O Organics",
            "fresh_vs_center_flag": "Fresh" if dept in ["Produce", "Meat", "Dairy Eggs Cheese", "Seafood", "Deli"] else "Center Store",
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_customers_and_households(stores_df):
    store_ids = stores_df["store_id"].tolist()
    household_ids = [f"HH{i+1:05d}" for i in range(N_HOUSEHOLDS)]
    rows = []
    used_hh = {}

    for i in range(N_CUSTOMERS):
        hh_id = household_ids[i % N_HOUSEHOLDS]
        is_head = hh_id not in used_hh
        if is_head:
            used_hh[hh_id] = True

        tier = random.choice(["Standard", "Standard", "Standard", "4U+"])
        points = random.randint(0, 3000)
        expiring = random.randint(0, min(points, 500)) if points > 50 else 0
        reg_store = random.choice(store_ids)
        city_state = next((c for c in CITIES if c[0] == stores_df.loc[stores_df.store_id == reg_store, "city"].values[0]), CITIES[0])
        eng_mode = random.choice(["In-Store", "In-Store", "eCommerce", "Both"])
        fav_channel = "J4U" if eng_mode in ["eCommerce", "Both"] else "Weekly Ad"
        days_last_txn = random.randint(0, 120)
        churn_score = round(random.uniform(0, 1), 4)
        churn_seg = "Low Risk" if churn_score < 0.3 else ("Medium Risk" if churn_score < 0.6 else "High Risk")
        income = random.choice(INCOME_BANDS)
        hh_size = random.randint(1, 6)
        n_children = random.randint(0, min(3, hh_size - 1))

        fuel_user = random.random() > 0.5
        grocery_user = random.random() > 0.2

        rows.append({
            "retail_customer_uuid": new_uuid(),
            "club_card_nbr": f"CC{random.randint(10**11, 10**12 - 1)}",
            "household_id": hh_id,
            "head_household_ind": is_head,
            "first_nm": random.choice(FIRST_NAMES),
            "last_nm": random.choice(LAST_NAMES),
            "email_id": f"user{i+1}@example.com",
            "birth_dt": rnd_date(365*18, 365*70),
            "birth_month": random.randint(1, 12),
            "zipcode": city_state[2],
            "city": city_state[0],
            "state": city_state[1],
            "b4u_profile_ind": tier == "4U+",
            "b4u_sign_up_dt": rnd_date(30, 1825) if tier == "4U+" else None,
            "current_point_balance": points,
            "points_expiring_next_month": expiring,
            "lifetime_savings_amt": round(random.uniform(50, 5000), 2),
            "clv_tier_level_id": tier,
            "tier": tier,
            "eng_mode_p3m": eng_mode,
            "eng_mode_p6m": eng_mode,
            "eng_mode_p12m": eng_mode,
            "fav_channel": fav_channel,
            "fav_departments": random.choice(["Grocery,Dairy", "Produce,Meat", "Bakery,Dairy", "Grocery,Frozen"]),
            "shopping_days": random.choice(["Weekday", "Weekend", "Both"]),
            "deal_engagement": random.choice(["High", "Medium", "Low"]),
            "customer_most_used_store_id": reg_store,
            "customer_last_used_store_id": reg_store,
            "prim_b4u_region_id": f"REG{random.randint(1, 5):02d}",
            "pref_division_id": random.choice([d["division_id"] for d in DIVISIONS]),
            "gas_rewards_ind_6m": fuel_user,
            "fuel_station_purchase_ind_6m": fuel_user,
            "grocery_purchase_ind_6m": grocery_user,
            "dairy_purchase_ind_6m": random.random() > 0.3,
            "bakery_purchase_ind_6m": random.random() > 0.4,
            "produce_purchase_ind_6m": random.random() > 0.35,
            "meat_purchase_ind_6m": random.random() > 0.4,
            "seafood_purchase_ind_6m": random.random() > 0.6,
            "pharmacy_purchase_ind_6m": random.random() > 0.5,
            "alcohol_purchase_ind_6m": random.random() > 0.5,
            "pet_product_purchase_ind_6m": random.random() > 0.6,
            "baby_product_purchase_ind_6m": n_children > 0 and random.random() > 0.3,
            "frozen_grocery_purchase_ind_6m": random.random() > 0.4,
            "own_brand_ind_6m": random.random() > 0.5,
            "starbucks_purchase_ind_6m": random.random() > 0.6,
            "doordash_txn_ind_6m": eng_mode in ["eCommerce", "Both"] and random.random() > 0.5,
            "instacart_txn_ind_6m": eng_mode in ["eCommerce", "Both"] and random.random() > 0.5,
            "uber_txn_ind_6m": eng_mode in ["eCommerce", "Both"] and random.random() > 0.6,
            "customer_age": random.choice(AGE_BANDS),
            "household_size": hh_size,
            "num_of_children": n_children,
            "pet_owner": random.random() > 0.5,
            "customer_income": income,
            "diet_preference": random.choice(DIET_PREFS),
            "snap_customers": income == "<$30k" and random.random() > 0.4,
            "email_opt_in": random.random() > 0.3,
            "sms_opt_in": random.random() > 0.5,
            "push_enabled_ind": random.random() > 0.4,
            "mobile_app_download_flg": eng_mode in ["eCommerce", "Both"] or random.random() > 0.4,
            "customer_created_dt": rnd_date(30, 3650),
            "reg_store_id": reg_store,
            "customer_status_cd": "ACTIVE",
            "shopstyles_segment_cd": random.choice(SHOPSTYLES),
            "myneed_segment_cd": random.choice(MYNEED),
            "churn_risk_score_nbr": churn_score,
            "churn_segment_cd": churn_seg,
            "tribe": random.choice(TRIBES),
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_offers():
    rows = []
    offer_upcs = {}  # client_offer_id -> list of upc_ids

    # Real offers
    for offer in REAL_OFFERS:
        start = rnd_date(90, 180)
        end = start + timedelta(days=random.randint(14, 60))
        o = {
            "client_offer_id": offer["client_offer_id"],
            "oms_offer_id": offer["oms_offer_id"],
            "incentive_id": f"INC-{offer['oms_offer_id']}",
            "offer_nbr": offer["oms_offer_id"],
            "offer_dsc": offer["offer_dsc"],
            "title_dsc1": offer["title_dsc1"],
            "headline_txt": offer["headline_txt"],
            "description_txt": offer["description_txt"],
            "categories_txt": "Dairy",
            "start_dt": start, "end_dt": end,
            "display_start_dt": start, "display_end_dt": end,
            "offer_type": offer["offer_type"],
            "offer_type_dsc": offer["offer_type"],
            "offer_form": "Digital",
            "delivery_channel_cd": offer["delivery_channel_cd"],
            "delivery_channel_dsc": offer.get("delivery_channel_dsc", ""),
            "program_type": offer.get("program_type", "Standard"),
            "program_subtype": None,
            "program_cd": offer.get("program_type", "STD").upper()[:3],
            "program_cd_dsc": offer.get("program_type", "Standard"),
            "discount_type_cd": offer["discount_type_cd"],
            "discount_dsc": offer["offer_dsc"],
            "discount_value": offer["discount_value"],
            "savings_value_txt": str(offer["discount_value"]),
            "min_purch_qty": offer.get("min_purch_qty", 1),
            "min_purch_amt": offer.get("min_purch_amt", None),
            "tier_1_discount": None, "tier_1_threshold": None,
            "tier_2_discount": None, "tier_2_threshold": None,
            "tier_3_discount": None, "tier_3_threshold": None,
            "points_program_id": "PTS001" if "POINTS" in offer["discount_type_cd"] or "REWARD" in offer["offer_type"] else None,
            "points_program_nm": "Albertsons Rewards" if "POINTS" in offer["discount_type_cd"] else None,
            "tier_1_points": int(offer["discount_value"]) if "POINTS" in offer["discount_type_cd"] else None,
            "tier_2_points": None, "tier_3_points": None,
            "tier_1_points_threshold": None, "tier_2_points_threshold": None, "tier_3_points_threshold": None,
            "target_level_cd": offer["target_level_cd"],
            "is_appliable_to_j4u_ind": offer["is_appliable_to_j4u_ind"],
            "is_freshpass_offer_ind": offer["is_freshpass_offer_ind"],
            "customer_segment_dsc": "All" if not offer["is_appliable_to_j4u_ind"] else "4U+",
            "is_employee_offer_ind": False,
            "allocation_cd": "ALL",
            "allocation_nm": "All Customers",
            "offer_status_cd": "ACTIVE",
            "is_in_weekly_ad": offer.get("is_in_weekly_ad", False),
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        }
        rows.append(o)
        offer_upcs[offer["client_offer_id"]] = offer.get("upcs", [])

    # Synthetic offers
    for i, template in enumerate(SYNTHETIC_OFFER_TEMPLATES):
        cat, channel, disc_type, disc_val, target_lvl, exclusive_j4u, dsc = template[:7]
        pts_threshold = template[7] if len(template) > 7 else None
        offer_id = f"OFR-SYN{i+1:03d}"
        start = rnd_date(30, 150)
        end = start + timedelta(days=random.randint(7, 45))
        is_grocery_reward = disc_type in ("GROCERY_REWARD", "DEPT_REWARD", "FREE_ITEM")
        o = {
            "client_offer_id": offer_id,
            "oms_offer_id": f"SYN{80000000 + i}",
            "incentive_id": f"INC-SYN{i+1:03d}",
            "offer_nbr": f"SYN{i+1:04d}",
            "offer_dsc": dsc,
            "title_dsc1": dsc.split(":")[0] if ":" in dsc else dsc[:40],
            "headline_txt": dsc,
            "description_txt": dsc,
            "categories_txt": cat,
            "start_dt": start, "end_dt": end,
            "display_start_dt": start, "display_end_dt": end,
            "offer_type": "ITEM_DISCOUNT" if not is_grocery_reward else "GROCERY_REWARD",
            "offer_type_dsc": disc_type,
            "offer_form": "Digital",
            "delivery_channel_cd": channel,
            "delivery_channel_dsc": channel,
            "program_type": "Grocery Reward" if is_grocery_reward else ("Fuel Reward" if disc_type == "FUEL_CENTS" else "Standard"),
            "program_subtype": "Department" if disc_type == "DEPT_REWARD" else ("Free Item" if disc_type == "FREE_ITEM" else None),
            "program_cd": "GRW" if is_grocery_reward else "STD",
            "program_cd_dsc": "Grocery Reward" if is_grocery_reward else "Standard",
            "discount_type_cd": disc_type,
            "discount_dsc": dsc,
            "discount_value": disc_val,
            "savings_value_txt": "FREE" if disc_type == "FREE_ITEM" else (f"${disc_val}" if disc_type in ["AMT_OFF", "GROCERY_REWARD", "DEPT_REWARD"] else f"{disc_val}%"),
            "min_purch_qty": 1, "min_purch_amt": None,
            "tier_1_discount": disc_val if is_grocery_reward else None,
            "tier_1_threshold": None,
            "tier_2_discount": disc_val * 2 if is_grocery_reward else None,
            "tier_2_threshold": None,
            "tier_3_discount": disc_val * 3 if is_grocery_reward else None,
            "tier_3_threshold": None,
            "points_program_id": "PTS001" if "POINTS" in disc_type else None,
            "points_program_nm": "Albertsons Rewards" if "POINTS" in disc_type else None,
            "tier_1_points": int(disc_val) if "POINTS" in disc_type else None,
            "tier_2_points": None, "tier_3_points": None,
            "tier_1_points_threshold": pts_threshold if is_grocery_reward else None,
            "tier_2_points_threshold": None,
            "tier_3_points_threshold": None,
            "target_level_cd": target_lvl,
            "is_appliable_to_j4u_ind": exclusive_j4u,
            "is_freshpass_offer_ind": False,
            "customer_segment_dsc": "4U+" if exclusive_j4u else "All",
            "is_employee_offer_ind": False,
            "allocation_cd": "ALL",
            "allocation_nm": "All Customers",
            "offer_status_cd": "ACTIVE",
            "is_in_weekly_ad": channel == "Weekly Ad",
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        }
        rows.append(o)
        offer_upcs[offer_id] = []  # will be assigned below

    return pd.DataFrame(rows), offer_upcs


def gen_offer_upcs(offers_df, offer_upcs_map, upcs_df):
    rows = []
    upc_ids_by_dept = upcs_df.groupby("department_nm")["upc_id"].apply(list).to_dict()
    all_upc_ids = upcs_df["upc_id"].tolist()

    for _, offer in offers_df.iterrows():
        oid = offer["client_offer_id"]
        explicit_upcs = offer_upcs_map.get(oid, [])

        # For ITEM-level offers with no explicit UPCs, pick 1-3 matching-category UPCs
        if offer["target_level_cd"] == "ITEM" and not explicit_upcs:
            dept = offer["categories_txt"]
            pool = upc_ids_by_dept.get(dept, all_upc_ids)
            explicit_upcs = random.sample(pool, min(random.randint(1, 3), len(pool)))

        for upc_id in explicit_upcs:
            if upc_id in upcs_df["upc_id"].values:
                rows.append({
                    "client_offer_id": oid,
                    "oms_offer_id": offer["oms_offer_id"],
                    "incentive_id": offer["incentive_id"],
                    "upc_id": upc_id,
                    "dept_section_id": offer.get("categories_txt", ""),
                    "any_product_ind": offer["target_level_cd"] == "BASKET",
                    "dw_create_ts": NOW, "dw_last_update_ts": NOW,
                })
    return pd.DataFrame(rows).drop_duplicates(subset=["client_offer_id", "upc_id"])


def gen_freshpass(customers_df):
    # ~20% of customers have FreshPass
    rows = []
    freshpass_customers = customers_df[customers_df["eng_mode_p6m"].isin(["eCommerce", "Both"])].sample(
        frac=0.4, random_state=42
    )
    for _, c in freshpass_customers.iterrows():
        sub_dt = rnd_date(30, 730)
        rows.append({
            "retail_customer_uuid": c["retail_customer_uuid"],
            "household_id": c["household_id"],
            "freshpass_status": random.choice(["ACTIVE", "ACTIVE", "ACTIVE", "CANCELLED"]),
            "subscription_plan_type_nm": random.choice(["Monthly", "Annual"]),
            "fp_subscription_dt": sub_dt,
            "fp_renewal_dt": sub_dt + timedelta(days=365),
            "fp_cancellation_dt": None,
            "life_delivery_order_cnt": random.randint(1, 100),
            "life_pickup_order_cnt": random.randint(0, 50),
            "lifetime_total_savings_amt": round(random.uniform(20, 500), 2),
            "lifetime_delivery_fee_savings": round(random.uniform(10, 200), 2),
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_j4u_hh_attributes(customers_df):
    run_id = f"RUN-{TODAY.strftime('%Y%m%d')}"
    attributes = [
        "HAS_CHILDREN", "PET_OWNER", "ORGANIC_SHOPPER", "HEALTH_CONSCIOUS",
        "DEAL_SEEKER", "FUEL_REDEEMER", "FRESHPASS_ELIGIBLE", "HIGH_CLV",
    ]
    rows = []
    hh_ids = customers_df["household_id"].unique()
    for hh_id in hh_ids:
        cust = customers_df[customers_df["household_id"] == hh_id].iloc[0]
        flags = {
            "HAS_CHILDREN": cust["num_of_children"] > 0,
            "PET_OWNER": cust["pet_owner"],
            "ORGANIC_SHOPPER": cust["own_brand_ind_6m"],
            "HEALTH_CONSCIOUS": cust["diet_preference"] in ["Vegetarian", "Vegan", "Organic"],
            "DEAL_SEEKER": cust["deal_engagement"] == "High",
            "FUEL_REDEEMER": cust["gas_rewards_ind_6m"],
            "FRESHPASS_ELIGIBLE": cust["eng_mode_p6m"] in ["eCommerce", "Both"],
            "HIGH_CLV": cust["clv_tier_level_id"] == "4U+",
        }
        for attr in attributes:
            rows.append({
                "run_id": run_id,
                "household_id": hh_id,
                "attribute_id": attr,
                "attribute_nm": attr.replace("_", " ").title(),
                "attribute_flag": flags[attr],
                "is_current_ind": True,
                "dw_create_ts": NOW, "dw_last_update_ts": NOW,
            })
    return pd.DataFrame(rows)


def gen_transactions(customers_df, stores_df, upcs_df):
    store_ids = stores_df["store_id"].tolist()
    upc_rows = upcs_df.to_dict("records")
    upc_by_dept = {}
    for u in upc_rows:
        upc_by_dept.setdefault(u["department_nm"], []).append(u["upc_id"])

    txn_rows = []
    txn_upc_rows = []

    for _, cust in customers_df.iterrows():
        n_txns = random.randint(5, 25)
        hh_id = cust["household_id"]
        ecom = cust["eng_mode_p6m"] in ["eCommerce", "Both"]
        store = cust["customer_most_used_store_id"]

        for _ in range(n_txns):
            txn_id = f"TXN-{new_uuid()[:8].upper()}"
            is_ecom = ecom and random.random() > 0.5
            txn_ts = rnd_ts(0, 365)
            fulfillment = random.choice(["DELIVERY", "PICKUP"]) if is_ecom else None
            n_items = random.randint(2, 15)

            # Biased category selection based on customer flags
            dept_weights = {
                "Dairy Eggs Cheese": 3 if cust["dairy_purchase_ind_6m"] else 1,
                "Grocery": 4 if cust["grocery_purchase_ind_6m"] else 1,
                "Produce": 3 if cust["produce_purchase_ind_6m"] else 1,
                "Bakery": 2 if cust["bakery_purchase_ind_6m"] else 1,
                "Meat": 2 if cust["meat_purchase_ind_6m"] else 1,
                "Seafood": 2 if cust["seafood_purchase_ind_6m"] else 0,
                "Deli": 2,
                "Frozen": 2 if cust["frozen_grocery_purchase_ind_6m"] else 1,
                "Household": 1,
                "Fuel": 3 if cust["fuel_station_purchase_ind_6m"] else 0,
            }
            depts = [d for d in dept_weights if upc_by_dept.get(d)]
            weights = [dept_weights[d] for d in depts]
            total_w = sum(weights)
            dept_probs = [w / total_w for w in weights]

            item_lines = []
            total_sales = 0
            for line in range(1, n_items + 1):
                dept = np.random.choice(depts, p=dept_probs)
                pool = upc_by_dept.get(dept, [])
                if not pool:
                    continue
                upc_id = random.choice(pool)
                upc_info = next((u for u in upc_rows if u["upc_id"] == upc_id), None)
                price = upc_info.get("price", 5.0) if upc_info else 5.0
                qty = random.randint(1, 3)
                line_sales = round(price * qty, 2)
                total_sales += line_sales
                item_lines.append({
                    "txn_id": txn_id,
                    "upc_id": upc_id,
                    "plu_cd": upc_id[-6:],
                    "store_id": store,
                    "txn_dte": txn_ts.date(),
                    "household_id": hh_id,
                    "card_nbr": cust["club_card_nbr"],
                    "net_sales": line_sales,
                    "gross_amt": round(line_sales * 1.05, 2),
                    "item_qty": qty,
                    "markdown_amt": 0,
                    "ecom_ind": is_ecom,
                    "fulfillment_type_cd": fulfillment,
                    "division_id": stores_df.loc[stores_df.store_id == store, "division_id"].values[0],
                    "b4u_region_id": stores_df.loc[stores_df.store_id == store, "b4u_region_id"].values[0],
                    "dw_create_ts": NOW, "dw_last_update_ts": NOW,
                    "receipt_line_nbr": line,
                })

            if not item_lines:
                continue

            txn_rows.append({
                "txn_id": txn_id,
                "store_id": store,
                "txn_dte": txn_ts.date(),
                "txn_ts": txn_ts,
                "division_id": stores_df.loc[stores_df.store_id == store, "division_id"].values[0],
                "b4u_region_id": stores_df.loc[stores_df.store_id == store, "b4u_region_id"].values[0],
                "household_id": hh_id,
                "card_nbr": cust["club_card_nbr"],
                "net_sales": round(total_sales, 2),
                "gross_amt": round(total_sales * 1.05, 2),
                "item_qty": sum(l["item_qty"] for l in item_lines),
                "markdown_amt": 0,
                "item_mkdn_amt": 0,
                "wod_mkdn_amt": 0,
                "pod_mkdn_amt": 0,
                "ecom_ind": is_ecom,
                "fulfillment_type_cd": fulfillment,
                "tender_type": random.choice(["Credit", "Debit", "Cash", "EBT"]),
                "device_type_nm": "Mobile" if is_ecom else "POS",
                "slot_type_nm": None,
                "order_id": new_uuid() if is_ecom else None,
                "dw_create_ts": NOW, "dw_last_update_ts": NOW,
            })
            txn_upc_rows.extend(item_lines)

    return pd.DataFrame(txn_rows), pd.DataFrame(txn_upc_rows)


def gen_clips_and_redemptions(customers_df, offers_df, txn_df, txn_upc_df, stores_df):
    clip_rows = []
    redemption_rows = []
    rewards_rows = []

    hh_txns = txn_df.groupby("household_id")
    offer_list = offers_df.to_dict("records")

    for _, cust in customers_df[customers_df["head_household_ind"]].iterrows():
        hh_id = cust["household_id"]
        store = cust["customer_most_used_store_id"]
        div_id = stores_df.loc[stores_df.store_id == store, "division_id"].values[0]
        region_id = stores_df.loc[stores_df.store_id == store, "b4u_region_id"].values[0]

        # Pick 3-10 offers to clip
        eligible_offers = [o for o in offer_list if
                           not o["is_appliable_to_j4u_ind"] or cust["clv_tier_level_id"] == "4U+"]
        eligible_offers = [o for o in eligible_offers if
                           not o["is_freshpass_offer_ind"] or
                           cust.get("eng_mode_p6m", "") in ["eCommerce", "Both"]]

        n_clips = random.randint(3, min(10, len(eligible_offers)))
        clipped_offers = random.sample(eligible_offers, n_clips)

        hh_txn_list = hh_txns.get_group(hh_id)["txn_id"].tolist() if hh_id in hh_txns.groups else []

        for offer in clipped_offers:
            clip_dt_obj = rnd_date(0, 60)
            clip_ts = datetime.combine(clip_dt_obj, datetime.min.time()) + timedelta(hours=random.randint(8, 21))
            clip_source = random.choice(["MOBILE", "MOBILE", "WEB", "AUTO"])
            clip_id = f"CLIP-{new_uuid()[:8].upper()}"

            clip_rows.append({
                "clip_id": clip_id,
                "client_offer_id": offer["client_offer_id"],
                "oms_offer_id": offer["oms_offer_id"],
                "incentive_id": offer["incentive_id"],
                "household_id": hh_id,
                "retail_customer_uuid": cust["retail_customer_uuid"],
                "card_nbr": cust["club_card_nbr"],
                "customer_guid": cust["retail_customer_uuid"],
                "clip_ts": clip_ts,
                "clip_dt": clip_dt_obj,
                "clip_tm": clip_ts.time(),
                "clip_source_cd": clip_source,
                "clip_source_application_id": "MOBILE_APP" if clip_source == "MOBILE" else "WEB",
                "mobile_ind": clip_source == "MOBILE",
                "clip_type_cd": "STANDARD",
                "store_id": store,
                "b4u_region_id": region_id,
                "b4u_region_nm": stores_df.loc[stores_df.store_id == store, "b4u_region_nm"].values[0],
                "division_id": div_id,
                "division_nm": stores_df.loc[stores_df.store_id == store, "division_nm"].values[0],
                "postal_cd": cust["zipcode"],
                "offer_type": offer["offer_type"],
                "dw_create_ts": NOW, "dw_last_update_ts": NOW,
            })

            # 55% redemption rate
            if hh_txn_list and random.random() < 0.55:
                txn_id = random.choice(hh_txn_list)
                txn_row = txn_df[txn_df.txn_id == txn_id].iloc[0]
                receipt_line = random.randint(1, 10)
                upc_rows_for_txn = txn_upc_df[txn_upc_df.txn_id == txn_id]
                upc_id = upc_rows_for_txn["upc_id"].iloc[0] if len(upc_rows_for_txn) > 0 else ""

                markdown = round(float(offer["discount_value"]) if offer["discount_type_cd"] in ["AMT_OFF", "GROCERY_REWARD"] else
                                 txn_row["net_sales"] * float(offer["discount_value"]) / 100, 2)

                redemption_rows.append({
                    "txn_id": txn_id,
                    "txn_dte": txn_row["txn_dte"],
                    "store_id": store,
                    "household_id": hh_id,
                    "card_nbr": cust["club_card_nbr"],
                    "receipt_line": receipt_line,
                    "client_offer_id": offer["client_offer_id"],
                    "oms_offer_id": offer["oms_offer_id"],
                    "incentive_id": offer["incentive_id"],
                    "coupon_id": None, "promotion_id": None,
                    "net_sales": txn_row["net_sales"],
                    "markdown_amt": markdown,
                    "item_mkdn_amt": markdown,
                    "offer_type": offer["offer_type"],
                    "offer_form": offer["offer_form"],
                    "program_type": offer["program_type"],
                    "program_subtype": None,
                    "discount_dsc": offer["discount_dsc"],
                    "upc_id": upc_id,
                    "category_id": "",
                    "department_nm": offer["categories_txt"],
                    "brand": "",
                    "vendor_nm": "",
                    "rwds_points_issued": random.randint(0, 100),
                    "redemptions": 1,
                    "b4u_region_id": region_id,
                    "division_id": div_id,
                    "dw_create_ts": NOW, "dw_last_update_ts": NOW,
                })

                # Grocery Reward → also write rewards_redeemed
                if offer["program_type"] in ["Grocery Reward", "Fuel Reward"]:
                    rewards_rows.append({
                        "txn_id": txn_id,
                        "txn_dte": txn_row["txn_dte"],
                        "store_id": store,
                        "household_id": hh_id,
                        "card_nbr": cust["club_card_nbr"],
                        "incentive_id": offer["incentive_id"],
                        "rewards_redeemed": float(offer["discount_value"]),
                        "mkdn_amt": markdown,
                        "gallons_redeemed": round(random.uniform(5, 15), 3) if offer["program_type"] == "Fuel Reward" else None,
                        "net_sales": txn_row["net_sales"],
                        "src": "Fuel" if offer["program_type"] == "Fuel Reward" else "Grocery",
                        "division_id": div_id,
                        "b4u_region_id": region_id,
                        "dw_create_ts": NOW, "dw_last_update_ts": NOW,
                    })

    clips_df = pd.DataFrame(clip_rows)
    redemptions_df = pd.DataFrame(redemption_rows).drop_duplicates(subset=["txn_id", "receipt_line", "client_offer_id"])
    rewards_df = pd.DataFrame(rewards_rows).drop_duplicates(subset=["txn_id", "incentive_id"])
    return clips_df, redemptions_df, rewards_df


def gen_cat_affinity(customers_df, txn_upc_df, upcs_df):
    rows = []
    upc_to_dept = dict(zip(upcs_df["upc_id"], upcs_df["department_nm"]))
    txn_upc_df = txn_upc_df.copy()
    txn_upc_df["department_nm"] = txn_upc_df["upc_id"].map(upc_to_dept)

    spend_by_hh_dept = (
        txn_upc_df.groupby(["household_id", "department_nm"])["net_sales"]
        .sum()
        .reset_index()
    )
    total_by_hh = txn_upc_df.groupby("household_id")["net_sales"].sum().reset_index()
    total_by_hh.columns = ["household_id", "total_spend"]

    merged = spend_by_hh_dept.merge(total_by_hh, on="household_id")
    merged["affinity_score"] = (merged["net_sales"] / merged["total_spend"]).round(4)
    merged = merged.sort_values(["household_id", "affinity_score"], ascending=[True, False])
    merged["affinity_rank"] = merged.groupby("household_id").cumcount() + 1

    for _, row in merged.iterrows():
        dept = row["department_nm"]
        if pd.isna(dept):
            continue
        rows.append({
            "household_id": row["household_id"],
            "category_id": CATEGORY_IDS.get(dept, "CAT001"),
            "category_nm": dept,
            "affinity_score": row["affinity_score"],
            "affinity_rank": row["affinity_rank"],
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_customer_ltv(customers_df, txn_upc_df, upcs_df):
    rows = []
    upc_to_dept = dict(zip(upcs_df["upc_id"], upcs_df["department_nm"]))
    txn_upc_df = txn_upc_df.copy()
    txn_upc_df["department_nm"] = txn_upc_df["upc_id"].map(upc_to_dept)

    for _, cust in customers_df.iterrows():
        hh_id = cust["household_id"]
        hh_txns = txn_upc_df[txn_upc_df["household_id"] == hh_id]
        dept_spend = hh_txns.groupby("department_nm")["net_sales"].sum()

        in_store = hh_txns[~hh_txns["ecom_ind"]]["net_sales"].sum()
        online = hh_txns[hh_txns["ecom_ind"]]["net_sales"].sum()

        rows.append({
            "retail_customer_uuid": cust["retail_customer_uuid"],
            "household_id": hh_id,
            "grocery_sales_amt": round(dept_spend.get("Grocery", 0), 2),
            "dairy_sales_amt": round(dept_spend.get("Dairy Eggs Cheese", 0), 2),
            "bakery_sales_amt": round(dept_spend.get("Bakery", 0), 2),
            "produce_sales_amt": round(dept_spend.get("Produce", 0), 2),
            "meat_sales_amt": round(dept_spend.get("Meat", 0), 2),
            "seafood_sales_amt": round(dept_spend.get("Seafood", 0), 2),
            "pharmacy_sales_amt": 0,
            "fuel_station_sales_amt": round(dept_spend.get("Fuel", 0), 2),
            "floral_sales_amt": 0,
            "deli_sales_amt": round(dept_spend.get("Deli", 0), 2),
            "frozen_sales_amt": round(dept_spend.get("Frozen", 0), 2),
            "in_store_sales_amt": round(in_store, 2),
            "in_store_txn_cnt": len(hh_txns[~hh_txns["ecom_ind"]]["txn_id"].unique()),
            "online_sales_amt": round(online, 2),
            "online_txn_cnt": len(hh_txns[hh_txns["ecom_ind"]]["txn_id"].unique()),
            "total_sales_amt": round(hh_txns["net_sales"].sum(), 2),
            "total_txn_cnt": len(hh_txns["txn_id"].unique()),
            "total_item_qty": int(hh_txns["item_qty"].sum()),
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_hh_weekly_cat_txns(txn_upc_df, upcs_df):
    rows = []
    upc_to_dept = dict(zip(upcs_df["upc_id"], upcs_df["department_nm"]))
    df = txn_upc_df.copy()
    df["department_nm"] = df["upc_id"].map(upc_to_dept)
    df["txn_dte"] = pd.to_datetime(df["txn_dte"])
    df["fiscal_week_id"] = df["txn_dte"].dt.isocalendar().week.astype(int)
    df["fiscal_year_id"] = df["txn_dte"].dt.isocalendar().year.astype(int)

    grouped = df.groupby(["fiscal_year_id", "fiscal_week_id", "household_id", "department_nm"]).agg(
        net_sales=("net_sales", "sum"),
        item_qty=("item_qty", "sum"),
        txn_cnt=("txn_id", "nunique"),
        primary_store_id=("store_id", "first"),
    ).reset_index()

    for _, row in grouped.iterrows():
        dept = row["department_nm"]
        if pd.isna(dept):
            continue
        rows.append({
            "fiscal_year_id": int(row["fiscal_year_id"]),
            "fiscal_week_id": int(row["fiscal_week_id"]),
            "household_id": row["household_id"],
            "category_id": CATEGORY_IDS.get(dept, "CAT001"),
            "category_nm": dept,
            "department_nm": dept,
            "primary_store_id": row["primary_store_id"],
            "net_sales": round(row["net_sales"], 2),
            "item_qty": int(row["item_qty"]),
            "txn_cnt": int(row["txn_cnt"]),
            "digital_engaged_last_12_weeks_ind": random.random() > 0.5,
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_offer_summary(offers_df, clips_df, redemptions_df):
    rows = []
    for _, offer in offers_df.iterrows():
        oid = offer["client_offer_id"]
        clips = len(clips_df[clips_df.client_offer_id == oid]) if len(clips_df) > 0 else 0
        reds = len(redemptions_df[redemptions_df.client_offer_id == oid]) if len(redemptions_df) > 0 else 0
        red_pct = round(reds / clips, 4) if clips > 0 else 0
        rows.append({
            "client_offer_id": oid,
            "oms_offer_id": offer["oms_offer_id"],
            "clips": clips,
            "redeeming_hhs": reds,
            "redemptions": reds,
            "red_pct": red_pct,
            "hh_clip_red_pct": red_pct,
            "markdown_amt": round(reds * float(offer["discount_value"]) if offer["discount_value"] else 0, 2),
            "promo_sales": round(reds * random.uniform(10, 50), 2),
            "rep_category_id": CATEGORY_IDS.get(offer["categories_txt"], "CAT001"),
            "rep_category_nm": offer["categories_txt"],
            "rep_brand": "",
            "repeat_hhs": int(reds * random.uniform(0.1, 0.3)),
            "dw_create_ts": NOW, "dw_last_update_ts": NOW,
        })
    return pd.DataFrame(rows)


def gen_deals_engagement(clips_df, redemptions_df, stores_df):
    rows = []
    periods = ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]
    for period in periods:
        for _, store in stores_df.iterrows():
            rows.append({
                "fiscal_period_id": period,
                "division_id": store["division_id"],
                "b4u_region_id": store["b4u_region_id"],
                "households_clipped_any_deals": random.randint(500, 5000),
                "clipped_and_redeemed_count": random.randint(200, 2000),
                "clipped_not_redeemed_count": random.randint(100, 1000),
                "households_redeemed_instore": random.randint(100, 1500),
                "households_redeemed_online": random.randint(50, 500),
                "total_redemptions": random.randint(500, 5000),
                "total_markdown_amt": round(random.uniform(5000, 50000), 2),
                "dw_create_ts": NOW, "dw_last_update_ts": NOW,
            })
    return pd.DataFrame(rows).drop_duplicates(subset=["fiscal_period_id", "division_id", "b4u_region_id"])


# ─── LOAD TO POSTGRES ─────────────────────────────────────────────────────────

def load(df, table, engine, if_exists="append"):
    if df.empty:
        print(f"  ⚠️  {table}: empty, skipping")
        return
    df.to_sql(table, engine, if_exists=if_exists, index=False, method="multi", chunksize=500)
    print(f"  ✅  {table}: {len(df)} rows")


def truncate_all(engine):
    tables = [
        "c360_deals_engagement_aggr", "c360_offer_summary", "c360_rewards_redeemed",
        "c360_redemptions", "c360_clips", "c360_cat_affinity", "c360_hh_weekly_cat_txns",
        "c360_customer_ltv_txn_agg", "c360_j4u_hh_attributes", "c360_freshpass",
        "c360_txn_upc", "c360_txn", "c360_offer_upcs", "c360_scored_offers",
        "c360_customer_profile", "c360_offer", "c360_upc", "c360_store",
    ]
    with engine.connect() as conn:
        conn.execute(text("SET session_replication_role = replica;"))
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE {t} CASCADE;"))
        conn.execute(text("SET session_replication_role = DEFAULT;"))
        conn.commit()
    print("🗑️  All tables truncated")


# ─── MAIN ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 SmartOfferEngine Data Generator")
    print(f"   DB: {DB_URL}\n")

    truncate_all(engine)

    print("📦 Generating...")

    stores_df = gen_stores()
    upcs_df = gen_upcs()
    customers_df = gen_customers_and_households(stores_df)
    offers_df, offer_upcs_map = gen_offers()
    offer_upcs_df = gen_offer_upcs(offers_df, offer_upcs_map, upcs_df)
    freshpass_df = gen_freshpass(customers_df)
    j4u_df = gen_j4u_hh_attributes(customers_df)
    txn_df, txn_upc_df = gen_transactions(customers_df, stores_df, upcs_df)
    clips_df, redemptions_df, rewards_df = gen_clips_and_redemptions(
        customers_df, offers_df, txn_df, txn_upc_df, stores_df
    )
    affinity_df = gen_cat_affinity(customers_df, txn_upc_df, upcs_df)
    ltv_df = gen_customer_ltv(customers_df, txn_upc_df, upcs_df)
    weekly_df = gen_hh_weekly_cat_txns(txn_upc_df, upcs_df)
    offer_summary_df = gen_offer_summary(offers_df, clips_df, redemptions_df)
    deals_df = gen_deals_engagement(clips_df, redemptions_df, stores_df)

    print("\n💾 Loading to PostgreSQL (dependency order)...")
    load(stores_df, "c360_store", engine)
    load(upcs_df, "c360_upc", engine)
    load(customers_df, "c360_customer_profile", engine)
    load(offers_df.drop(columns=["categories_txt"], errors="ignore"), "c360_offer", engine)
    load(offer_upcs_df, "c360_offer_upcs", engine)
    load(freshpass_df, "c360_freshpass", engine)
    load(j4u_df, "c360_j4u_hh_attributes", engine)
    load(txn_df, "c360_txn", engine)
    load(txn_upc_df, "c360_txn_upc", engine)
    load(clips_df, "c360_clips", engine)
    load(redemptions_df, "c360_redemptions", engine)
    load(rewards_df, "c360_rewards_redeemed", engine)
    load(affinity_df, "c360_cat_affinity", engine)
    load(ltv_df, "c360_customer_ltv_txn_agg", engine)
    load(weekly_df, "c360_hh_weekly_cat_txns", engine)
    load(offer_summary_df, "c360_offer_summary", engine)
    load(deals_df, "c360_deals_engagement_aggr", engine)

    print("\n✅ Data generation complete!")
    print(f"   {len(stores_df)} stores")
    print(f"   {len(upcs_df)} products ({len(REAL_UPCS)} real Safeway UPCs + {len(SYNTHETIC_UPCS)} synthetic)")
    print(f"   {len(customers_df)} customers in {customers_df['household_id'].nunique()} households")
    print(f"   {len(offers_df)} offers ({len(REAL_OFFERS)} real + {len(SYNTHETIC_OFFER_TEMPLATES)} synthetic)")
    print(f"   {len(txn_df)} transactions / {len(txn_upc_df)} line items")
    print(f"   {len(clips_df)} clips / {len(redemptions_df)} redemptions")
    print(f"   {len(affinity_df)} category affinity rows")
