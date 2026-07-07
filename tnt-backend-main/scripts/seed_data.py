"""Tap N Take sample data seed script.

Run ``python scripts/seed_data.py`` to reset the local database (optional) and
populate it with a realistic dataset that exercises the complete mobile
workflow: login, vendor discovery, menu browsing, carts, orders, payments,
notifications, AI recommendations, and stationery flows.

The script is intentionally verbose so product, QA, and data teams can trace
every entity that gets created.  Prices are stored in paise to match the core
schema.  Extra vendor/stationery metadata plus AI recommendation blobs are
materialized via lightweight helper tables that mirror what the mobile app
expects to render.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Sequence
from uuid import uuid4

from sqlalchemy import (
	Boolean,
	Column,
	Float,
	ForeignKey,
	Integer,
	JSON,
	MetaData,
	String,
	Table,
	delete,
)
from sqlalchemy.orm import Session

from app.core.redis import redis_client
from app.core.time_utils import utcnow_naive
from app.database.base import Base
from app.database.init_db import init_db as create_schema
from app.database.session import DATABASE_URL, SessionLocal, engine
from app.modules.feedback.model import Feedback, VendorReview
from app.modules.ledger.model import Ledger, LedgerSource, LedgerType
from app.modules.rewards.model import (
	RedemptionRule,
	RedemptionType,
	OffPeakRewardPolicy,
	OffPeakRewardPolicyAudit,
	RewardPoints,
	RewardRedemption,
	RewardRule,
	RewardTransaction,
	RewardType,
	Voucher,
	VoucherDiscountType,
	VoucherRedemption,
)
from app.modules.menu.model import MenuItem
from app.modules.notifications.model import Notification, NotificationType
from app.modules.orders.history_model import OrderHistory
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.stationery.job_model import JobStatus, StationeryJob
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole


LOGGER = logging.getLogger("tnt.seed")


EXTRA_METADATA = MetaData()

VENDOR_PROFILE_TABLE = Table(
	"vendor_profiles",
	EXTRA_METADATA,
	Column("vendor_id", Integer, ForeignKey(User.__table__.c.id), primary_key=True),
	Column("category", String, nullable=False),
	Column("description", String, nullable=False),
	Column("rating", Float, nullable=False),
	Column("location", String, nullable=False),
	Column("logo_url", String, nullable=False),
	Column("cover_image", String, nullable=False),
	Column("is_open", Boolean, nullable=False, default=True),
)

STATIONERY_PRODUCT_TABLE = Table(
	"stationery_products",
	EXTRA_METADATA,
	Column("id", Integer, primary_key=True, autoincrement=True),
	Column("vendor_id", Integer, ForeignKey(User.__table__.c.id), nullable=False),
	Column("service_id", Integer, ForeignKey(StationeryService.__table__.c.id), nullable=True),
	Column("name", String, nullable=False),
	Column("description", String, nullable=False),
	Column("category", String, nullable=False),
	Column("image_url", String, nullable=False),
	Column("price", Integer, nullable=False),
	Column("stock", Integer, nullable=False),
)

AI_RECOMMENDATIONS_TABLE = Table(
	"ai_recommendations",
	EXTRA_METADATA,
	Column("id", Integer, primary_key=True, autoincrement=True),
	Column("user_id", Integer, ForeignKey(User.__table__.c.id), nullable=False, unique=True),
	Column("user_preferences", JSON, nullable=False),
	Column("popular_items", JSON, nullable=False),
	Column("recommended_items", JSON, nullable=False),
	Column("insight", String, nullable=True),
)


def rupees(value: float) -> int:
	"""Return integer paise for the supplied rupee price."""

	return int(round(value * 100))


NOW = utcnow_naive()


STUDENT_FIXTURES: Sequence[Dict[str, Any]] = (
	{
		"slug": "naina",
		"name": "Naina Sharma",
		"phone": "7016918103",
		"role": UserRole.STUDENT,
		"university_id": "UNIV-2024-01",
		"preferences": {
			"dietary_restrictions": ["vegetarian"],
			"cuisine_preferences": ["north_indian", "italian"],
			"spice_level": 2,
			"preferred_pickup_hour": 13,
		},
	},
	{
		"slug": "rahul",
		"name": "Rahul Verma",
		"phone": "7016918104",
		"role": UserRole.STUDENT,
		"university_id": "UNIV-2024-02",
		"preferences": {
			"dietary_restrictions": [],
			"cuisine_preferences": ["indian_street", "mexican"],
			"spice_level": 4,
			"preferred_pickup_hour": 20,
		},
	},
	{
		"slug": "ananya",
		"name": "Ananya Rao",
		"phone": "7016918105",
		"role": UserRole.STUDENT,
		"university_id": "UNIV-2024-03",
		"preferences": {
			"dietary_restrictions": ["vegan"],
			"cuisine_preferences": ["mediterranean", "fusion"],
			"spice_level": 1,
			"preferred_pickup_hour": 14,
		},
	},
	{
		"slug": "kabir",
		"name": "Kabir Malhotra",
		"phone": "7016918106",
		"role": UserRole.STUDENT,
		"university_id": "UNIV-2024-04",
		"preferences": {
			"dietary_restrictions": [],
			"cuisine_preferences": ["american", "grill"],
			"spice_level": 3,
			"preferred_pickup_hour": 19,
		},
	},
	{
		"slug": "meera",
		"name": "Meera Iyer",
		"phone": "7016918107",
		"role": UserRole.STUDENT,
		"university_id": "UNIV-2024-05",
		"preferences": {
			"dietary_restrictions": ["eggless"],
			"cuisine_preferences": ["bakery", "beverages"],
			"spice_level": 1,
			"preferred_pickup_hour": 10,
		},
	},
	{
		"slug": "arjun",
		"name": "Prof. Arjun Sen",
		"phone": "7016918108",
		"role": UserRole.FACULTY,
		"university_id": "FAC-ENG-01",
		"preferences": {
			"dietary_restrictions": [],
			"cuisine_preferences": ["south_indian"],
			"spice_level": 3,
			"preferred_pickup_hour": 9,
		},
	},
	{
		"slug": "dev",
		"name": "Dev Khanna",
		"phone": "7016918109",
		"role": UserRole.STUDENT,
		"university_id": "UNIV-2024-06",
		"preferences": {
			"dietary_restrictions": [],
			"cuisine_preferences": ["comfort_food"],
			"spice_level": 3,
			"preferred_pickup_hour": 21,
		},
	},
	{
		"slug": "sneha",
		"name": "Sneha Kulkarni",
		"phone": "7016918110",
		"role": UserRole.STUDENT,
		"university_id": "UNIV-2024-07",
		"preferences": {
			"dietary_restrictions": ["gluten_free"],
			"cuisine_preferences": ["salads", "wraps"],
			"spice_level": 2,
			"preferred_pickup_hour": 11,
		},
	},
)


FOOD_VENDOR_FIXTURES: Sequence[Dict[str, Any]] = (
	{
		"slug": "campus_cafe",
		"name": "Campus Cafe",
		"phone": "9810001001",
		"vendor_type": "food",
		"university_id": "VEN-CAF-01",
		"profile": {
			"category": "Cafe & Bakery",
			"description": "Signature grilled sandwiches, wraps, and handcrafted beverages.",
			"rating": 4.7,
			"location": "North Block Atrium",
			"logo_url": "https://cdn.tapntake.app/vendors/campus_cafe_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/campus_cafe_cover.jpg",
			"is_open": True,
		},
	},
	{
		"slug": "burger_hub",
		"name": "Burger Hub",
		"phone": "9810001002",
		"vendor_type": "food",
		"university_id": "VEN-BUR-02",
		"profile": {
			"category": "Burgers & Fries",
			"description": "Stacked burgers, loaded fries, and thick shakes for late lectures.",
			"rating": 4.5,
			"location": "Student Plaza",
			"logo_url": "https://cdn.tapntake.app/vendors/burger_hub_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/burger_hub_cover.jpg",
			"is_open": True,
		},
	},
	{
		"slug": "spice_corner",
		"name": "Spice Corner",
		"phone": "9810001003",
		"vendor_type": "food",
		"university_id": "VEN-SPC-03",
		"profile": {
			"category": "South Indian",
			"description": "Live dosa counter with homestyle filter coffee and hearty meals.",
			"rating": 4.8,
			"location": "Heritage Lane",
			"logo_url": "https://cdn.tapntake.app/vendors/spice_corner_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/spice_corner_cover.jpg",
			"is_open": True,
		},
	},
	{
		"slug": "green_bowl",
		"name": "Green Bowl",
		"phone": "9810001004",
		"vendor_type": "food",
		"university_id": "VEN-GRN-04",
		"profile": {
			"category": "Healthy Bowls",
			"description": "Seasonal salad bowls, wraps, and cold-pressed juices.",
			"rating": 4.4,
			"location": "Wellness Court",
			"logo_url": "https://cdn.tapntake.app/vendors/green_bowl_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/green_bowl_cover.jpg",
			"is_open": True,
		},
	},
	{
		"slug": "pizza_station",
		"name": "Pizza Station",
		"phone": "9810001005",
		"vendor_type": "food",
		"university_id": "VEN-PZA-05",
		"profile": {
			"category": "Pizzeria",
			"description": "Wood-fired pizzas, artisanal breads, and baked pasta trays.",
			"rating": 4.6,
			"location": "Central Courtyard",
			"logo_url": "https://cdn.tapntake.app/vendors/pizza_station_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/pizza_station_cover.jpg",
			"is_open": True,
		},
	},
)


STATIONERY_VENDOR_FIXTURES: Sequence[Dict[str, Any]] = (
	{
		"slug": "xerox_point",
		"name": "Xerox Point",
		"phone": "9810002001",
		"vendor_type": "stationery",
		"university_id": "VEN-XRX-06",
		"profile": {
			"category": "Printing & Copies",
			"description": "High throughput laser printers with instant binding support.",
			"rating": 4.3,
			"location": "Library Arcade",
			"logo_url": "https://cdn.tapntake.app/vendors/xerox_point_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/xerox_point_cover.jpg",
			"is_open": True,
		},
	},
	{
		"slug": "print_hub",
		"name": "Print Hub",
		"phone": "9810002002",
		"vendor_type": "stationery",
		"university_id": "VEN-PRT-07",
		"profile": {
			"category": "Design & Posters",
			"description": "Large-format, poster, and blueprint specialists with matte/gloss options.",
			"rating": 4.5,
			"location": "Innovation Street",
			"logo_url": "https://cdn.tapntake.app/vendors/print_hub_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/print_hub_cover.jpg",
			"is_open": True,
		},
	},
	{
		"slug": "campus_stationery",
		"name": "Campus Stationery",
		"phone": "9810002003",
		"vendor_type": "stationery",
		"university_id": "VEN-STN-08",
		"profile": {
			"category": "Campus Supplies",
			"description": "Pens, notebooks, lab records, and exam-ready kits for every semester.",
			"rating": 4.2,
			"location": "Ground Floor Arcade",
			"logo_url": "https://cdn.tapntake.app/vendors/campus_stationery_logo.png",
			"cover_image": "https://cdn.tapntake.app/vendors/campus_stationery_cover.jpg",
			"is_open": True,
		},
	},
)


MENU_FIXTURES: Sequence[Dict[str, Any]] = (
	# Campus Cafe
	{"slug": "campus-veg-burger", "vendor_slug": "campus_cafe", "name": "Veg Burger", "description": "Grilled veggie patty with chipotle mayo.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/veg_burger.jpg", "category": "Quick Bites", "prep_time": 12},
	{"slug": "campus-paneer-wrap", "vendor_slug": "campus_cafe", "name": "Paneer Wrap", "description": "Whole-wheat wrap with smoked paneer.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/paneer_wrap.jpg", "category": "Wraps", "prep_time": 10},
	{"slug": "campus-cold-coffee", "vendor_slug": "campus_cafe", "name": "Cold Coffee", "description": "Signature blended cold coffee.", "price": 99, "image_url": "https://cdn.tapntake.app/menu/cold_coffee.jpg", "category": "Beverages", "prep_time": 4},
	{"slug": "campus-masala-chai", "vendor_slug": "campus_cafe", "name": "Masala Chai Latte", "description": "Spiced Assam tea with oat milk.", "price": 79, "image_url": "https://cdn.tapntake.app/menu/masala_chai.jpg", "category": "Beverages", "prep_time": 5},
	{"slug": "campus-blueberry-muffin", "vendor_slug": "campus_cafe", "name": "Blueberry Muffin", "description": "Baked daily with crumble top.", "price": 89, "image_url": "https://cdn.tapntake.app/menu/blueberry_muffin.jpg", "category": "Bakery", "prep_time": 3},
	{"slug": "campus-garlic-toastie", "vendor_slug": "campus_cafe", "name": "Garlic Toastie", "description": "Cheesy garlic sourdough toastie.", "price": 119, "image_url": "https://cdn.tapntake.app/menu/garlic_toast.jpg", "category": "Quick Bites", "prep_time": 9},
	{"slug": "campus-choco-shake", "vendor_slug": "campus_cafe", "name": "Belgian Chocolate Shake", "description": "Thick shake with cocoa nibs.", "price": 139, "image_url": "https://cdn.tapntake.app/menu/choco_shake.jpg", "category": "Beverages", "prep_time": 6},
	{"slug": "campus-pesto-sandwich", "vendor_slug": "campus_cafe", "name": "Pesto Cottage Sandwich", "description": "Fresh basil pesto on multigrain.", "price": 159, "image_url": "https://cdn.tapntake.app/menu/pesto_sandwich.jpg", "category": "Sandwiches", "prep_time": 11},
	# Burger Hub
	{"slug": "burgerhub-classic-veg", "vendor_slug": "burger_hub", "name": "Classic Veg Burger", "description": "Crispy patty, lettuce, signature sauce.", "price": 139, "image_url": "https://cdn.tapntake.app/menu/classic_veg_burger.jpg", "category": "Burgers", "prep_time": 10},
	{"slug": "burgerhub-cheese-burst", "vendor_slug": "burger_hub", "name": "Cheese Burst Burger", "description": "Double cheese, brioche bun.", "price": 179, "image_url": "https://cdn.tapntake.app/menu/cheese_burst.jpg", "category": "Burgers", "prep_time": 12},
	{"slug": "burgerhub-paneer-spice", "vendor_slug": "burger_hub", "name": "Spicy Paneer Burger", "description": "Peri-peri paneer steak with slaw.", "price": 189, "image_url": "https://cdn.tapntake.app/menu/spicy_paneer_burger.jpg", "category": "Burgers", "prep_time": 13},
	{"slug": "burgerhub-loaded-fries", "vendor_slug": "burger_hub", "name": "Loaded Fries", "description": "Cheddar, jalapenos, and salsa.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/loaded_fries.jpg", "category": "Sides", "prep_time": 8},
	{"slug": "burgerhub-peri-peri-fries", "vendor_slug": "burger_hub", "name": "Peri Peri Fries", "description": "Spiced fries with smoked paprika.", "price": 119, "image_url": "https://cdn.tapntake.app/menu/peri_peri_fries.jpg", "category": "Sides", "prep_time": 7},
	{"slug": "burgerhub-iced-tea", "vendor_slug": "burger_hub", "name": "Lemon Iced Tea", "description": "Small batch brewed tea.", "price": 79, "image_url": "https://cdn.tapntake.app/menu/iced_tea.jpg", "category": "Beverages", "prep_time": 3},
	{"slug": "burgerhub-oreo-shake", "vendor_slug": "burger_hub", "name": "Oreo Shake", "description": "Cookie crumble with vanilla ice cream.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/oreo_shake.jpg", "category": "Beverages", "prep_time": 6},
	{"slug": "burgerhub-crispy-corn", "vendor_slug": "burger_hub", "name": "Crispy Corn Pops", "description": "Golden fried sweet corn with spice dust.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/crispy_corn.jpg", "category": "Sides", "prep_time": 9},
	# Spice Corner
	{"slug": "spice-masala-dosa", "vendor_slug": "spice_corner", "name": "Masala Dosa", "description": "Stone-ground batter, potato masala.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/masala_dosa.jpg", "category": "Meals", "prep_time": 14},
	{"slug": "spice-mysore-dosa", "vendor_slug": "spice_corner", "name": "Mysore Masala Dosa", "description": "Gunpowder chutney spread inside.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/mysore_dosa.jpg", "category": "Meals", "prep_time": 15},
	{"slug": "spice-idli-sambar", "vendor_slug": "spice_corner", "name": "Idli Sambar", "description": "Three mini idlis with tiffin sambar.", "price": 99, "image_url": "https://cdn.tapntake.app/menu/idli_sambar.jpg", "category": "Breakfast", "prep_time": 8},
	{"slug": "spice-medhu-vada", "vendor_slug": "spice_corner", "name": "Medu Vada Plate", "description": "Double fried lentil doughnuts.", "price": 109, "image_url": "https://cdn.tapntake.app/menu/medu_vada.jpg", "category": "Breakfast", "prep_time": 9},
	{"slug": "spice-upma", "vendor_slug": "spice_corner", "name": "Veg Upma Bowl", "description": "Semolina upma with veggies.", "price": 89, "image_url": "https://cdn.tapntake.app/menu/upma.jpg", "category": "Breakfast", "prep_time": 7},
	{"slug": "spice-filter-coffee", "vendor_slug": "spice_corner", "name": "Filter Coffee", "description": "Brass tumbler decoction.", "price": 69, "image_url": "https://cdn.tapntake.app/menu/filter_coffee.jpg", "category": "Beverages", "prep_time": 4},
	{"slug": "spice-lemon-rice", "vendor_slug": "spice_corner", "name": "Lemon Rice", "description": "Curry leaf tempered rice.", "price": 99, "image_url": "https://cdn.tapntake.app/menu/lemon_rice.jpg", "category": "Meals", "prep_time": 10},
	{"slug": "spice-chole-bhature", "vendor_slug": "spice_corner", "name": "Chole Bhature", "description": "Punjabi style chickpea curry.", "price": 159, "image_url": "https://cdn.tapntake.app/menu/chole_bhature.jpg", "category": "Meals", "prep_time": 16},
	# Green Bowl
	{"slug": "greenbowl-quinoa-salad", "vendor_slug": "green_bowl", "name": "Quinoa Rainbow Salad", "description": "Tricolor quinoa, avocado, citrus dressing.", "price": 199, "image_url": "https://cdn.tapntake.app/menu/quinoa_salad.jpg", "category": "Salads", "prep_time": 11},
	{"slug": "greenbowl-buddha-bowl", "vendor_slug": "green_bowl", "name": "Buddha Bowl", "description": "Roasted veggies, chickpeas, tahini.", "price": 219, "image_url": "https://cdn.tapntake.app/menu/buddha_bowl.jpg", "category": "Bowls", "prep_time": 12},
	{"slug": "greenbowl-hummus-wrap", "vendor_slug": "green_bowl", "name": "Hummus Wrap", "description": "Spinach tortilla with beet hummus.", "price": 169, "image_url": "https://cdn.tapntake.app/menu/hummus_wrap.jpg", "category": "Wraps", "prep_time": 9},
	{"slug": "greenbowl-detox-juice", "vendor_slug": "green_bowl", "name": "Detox Green Juice", "description": "Cold-pressed kale, cucumber, apple.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/detox_juice.jpg", "category": "Beverages", "prep_time": 4},
	{"slug": "greenbowl-greek-salad", "vendor_slug": "green_bowl", "name": "Greek Salad", "description": "Feta, olives, heirloom tomatoes.", "price": 189, "image_url": "https://cdn.tapntake.app/menu/greek_salad.jpg", "category": "Salads", "prep_time": 10},
	{"slug": "greenbowl-falafel-bowl", "vendor_slug": "green_bowl", "name": "Falafel Power Bowl", "description": "Baked falafel, quinoa, tzatziki.", "price": 209, "image_url": "https://cdn.tapntake.app/menu/falafel_bowl.jpg", "category": "Bowls", "prep_time": 13},
	{"slug": "greenbowl-avocado-toast", "vendor_slug": "green_bowl", "name": "Avocado Toast", "description": "Sourdough toast with microgreens.", "price": 179, "image_url": "https://cdn.tapntake.app/menu/avocado_toast.jpg", "category": "Breakfast", "prep_time": 8},
	{"slug": "greenbowl-power-smoothie", "vendor_slug": "green_bowl", "name": "Power Smoothie", "description": "Banana, spinach, chia, almond milk.", "price": 159, "image_url": "https://cdn.tapntake.app/menu/power_smoothie.jpg", "category": "Beverages", "prep_time": 5},
	# Pizza Station
	{"slug": "pizza-margherita", "vendor_slug": "pizza_station", "name": "Margherita Pizza", "description": "San Marzano tomatoes, basil, bocconcini.", "price": 249, "image_url": "https://cdn.tapntake.app/menu/margherita_pizza.jpg", "category": "Pizza", "prep_time": 15},
	{"slug": "pizza-farmhouse", "vendor_slug": "pizza_station", "name": "Farmhouse Pizza", "description": "Loaded veggies with mozzarella.", "price": 289, "image_url": "https://cdn.tapntake.app/menu/farmhouse_pizza.jpg", "category": "Pizza", "prep_time": 16},
	{"slug": "pizza-tandoori-paneer", "vendor_slug": "pizza_station", "name": "Tandoori Paneer Pizza", "description": "Smoky paneer tikka on cheese base.", "price": 309, "image_url": "https://cdn.tapntake.app/menu/tandoori_pizza.jpg", "category": "Pizza", "prep_time": 17},
	{"slug": "pizza-veggie-loaded", "vendor_slug": "pizza_station", "name": "Veggie Loaded Pizza", "description": "Peppers, corn, olives, chilli flakes.", "price": 299, "image_url": "https://cdn.tapntake.app/menu/veggie_loaded_pizza.jpg", "category": "Pizza", "prep_time": 16},
	{"slug": "pizza-garlic-breadsticks", "vendor_slug": "pizza_station", "name": "Garlic Breadsticks", "description": "Oven baked with herb butter.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/garlic_breadsticks.jpg", "category": "Sides", "prep_time": 9},
	{"slug": "pizza-pasta-alfredo", "vendor_slug": "pizza_station", "name": "Pasta Alfredo", "description": "Creamy alfredo with parmesan.", "price": 239, "image_url": "https://cdn.tapntake.app/menu/pasta_alfredo.jpg", "category": "Pasta", "prep_time": 14},
	{"slug": "pizza-pasta-arrabiata", "vendor_slug": "pizza_station", "name": "Pasta Arrabiata", "description": "Slow simmered tomato chilli sauce.", "price": 229, "image_url": "https://cdn.tapntake.app/menu/pasta_arrabiata.jpg", "category": "Pasta", "prep_time": 13},
	{"slug": "pizza-chilli-cheese-toast", "vendor_slug": "pizza_station", "name": "Chilli Cheese Toast", "description": "Open toast with cheddar and jalapeno.", "price": 159, "image_url": "https://cdn.tapntake.app/menu/chilli_cheese_toast.jpg", "category": "Snacks", "prep_time": 8},
)


STATIONERY_SERVICE_FIXTURES: Sequence[Dict[str, Any]] = (
	{"slug": "xerox-a4-bw", "vendor_slug": "xerox_point", "name": "A4 Xerox (B/W)", "description": "75 GSM B/W copies", "price": 1.5, "unit": "page", "category": "Printing", "image_url": "https://cdn.tapntake.app/stationery/a4_bw.jpg", "stock": 1200},
	{"slug": "xerox-a4-color", "vendor_slug": "xerox_point", "name": "A4 Xerox (Color)", "description": "Vivid color prints", "price": 7.0, "unit": "page", "category": "Printing", "image_url": "https://cdn.tapntake.app/stationery/a4_color.jpg", "stock": 600},
	{"slug": "xerox-a3-bw", "vendor_slug": "xerox_point", "name": "A3 Xerox (B/W)", "description": "Large format documents", "price": 4.0, "unit": "page", "category": "Printing", "image_url": "https://cdn.tapntake.app/stationery/a3_bw.jpg", "stock": 420},
	{"slug": "xerox-binding-soft", "vendor_slug": "xerox_point", "name": "Soft Binding", "description": "Thermal strip binding", "price": 40.0, "unit": "job", "category": "Binding", "image_url": "https://cdn.tapntake.app/stationery/soft_binding.jpg", "stock": 150},
	{"slug": "xerox-binding-hard", "vendor_slug": "xerox_point", "name": "Hard Binding", "description": "Hardcover thesis binding", "price": 120.0, "unit": "job", "category": "Binding", "image_url": "https://cdn.tapntake.app/stationery/hard_binding.jpg", "stock": 80},
	{"slug": "xerox-lam-a4", "vendor_slug": "xerox_point", "name": "A4 Lamination", "description": "Gloss lamination", "price": 25.0, "unit": "sheet", "category": "Lamination", "image_url": "https://cdn.tapntake.app/stationery/a4_lam.jpg", "stock": 320},
	{"slug": "xerox-id-card", "vendor_slug": "xerox_point", "name": "ID Card Print", "description": "PVC card printing", "price": 60.0, "unit": "piece", "category": "Cards", "image_url": "https://cdn.tapntake.app/stationery/id_card.jpg", "stock": 200},
	{"slug": "xerox-passport", "vendor_slug": "xerox_point", "name": "Passport Photo Set", "description": "Set of eight matte photos", "price": 70.0, "unit": "set", "category": "Photography", "image_url": "https://cdn.tapntake.app/stationery/passport_photo.jpg", "stock": 140},
	{"slug": "xerox-spiral-notes", "vendor_slug": "xerox_point", "name": "Spiral Notebook Print", "description": "Custom spiral notebooks", "price": 90.0, "unit": "book", "category": "Binding", "image_url": "https://cdn.tapntake.app/stationery/spiral_notebook.jpg", "stock": 110},
	{"slug": "xerox-blueprint", "vendor_slug": "xerox_point", "name": "Blueprint Print", "description": "Architectural plan copies", "price": 55.0, "unit": "sheet", "category": "Printing", "image_url": "https://cdn.tapntake.app/stationery/blueprint.jpg", "stock": 90},
	{"slug": "print-poster-a2", "vendor_slug": "print_hub", "name": "A2 Poster", "description": "A2 matte poster", "price": 130.0, "unit": "sheet", "category": "Posters", "image_url": "https://cdn.tapntake.app/stationery/poster_a2.jpg", "stock": 75},
	{"slug": "print-poster-a1", "vendor_slug": "print_hub", "name": "A1 Poster", "description": "Large format satin poster", "price": 260.0, "unit": "sheet", "category": "Posters", "image_url": "https://cdn.tapntake.app/stationery/poster_a1.jpg", "stock": 60},
	{"slug": "print-banner", "vendor_slug": "print_hub", "name": "Vinyl Banner", "description": "Indoor/outdoor banner", "price": 320.0, "unit": "sheet", "category": "Banners", "image_url": "https://cdn.tapntake.app/stationery/banner.jpg", "stock": 45},
	{"slug": "print-canvas", "vendor_slug": "print_hub", "name": "Photo Canvas", "description": "Gallery wrap canvas", "price": 480.0, "unit": "piece", "category": "Decor", "image_url": "https://cdn.tapntake.app/stationery/canvas.jpg", "stock": 35},
	{"slug": "print-sticker-pack", "vendor_slug": "print_hub", "name": "Sticker Pack", "description": "Die-cut stickers", "price": 60.0, "unit": "sheet", "category": "Stickers", "image_url": "https://cdn.tapntake.app/stationery/stickers.jpg", "stock": 180},
	{"slug": "print-flyer", "vendor_slug": "print_hub", "name": "Flyer Bundle", "description": "100 gsm flyers", "price": 5.0, "unit": "page", "category": "Marketing", "image_url": "https://cdn.tapntake.app/stationery/flyer.jpg", "stock": 400},
	{"slug": "print-bookmark", "vendor_slug": "print_hub", "name": "Custom Bookmark", "description": "UV coated bookmarks", "price": 15.0, "unit": "piece", "category": "Accessories", "image_url": "https://cdn.tapntake.app/stationery/bookmark.jpg", "stock": 220},
	{"slug": "print-calendar", "vendor_slug": "print_hub", "name": "Desk Calendar", "description": "Wiro desk calendar", "price": 180.0, "unit": "piece", "category": "Stationery", "image_url": "https://cdn.tapntake.app/stationery/calendar.jpg", "stock": 55},
	{"slug": "stationery-black-pen", "vendor_slug": "campus_stationery", "name": "Black Gel Pen", "description": "0.5mm gel pen", "price": 12.0, "unit": "piece", "category": "Writing", "image_url": "https://cdn.tapntake.app/stationery/black_pen.jpg", "stock": 500},
	{"slug": "stationery-blue-pen", "vendor_slug": "campus_stationery", "name": "Blue Ball Pen", "description": "Quick dry pen", "price": 10.0, "unit": "piece", "category": "Writing", "image_url": "https://cdn.tapntake.app/stationery/blue_pen.jpg", "stock": 520},
	{"slug": "stationery-highlighter", "vendor_slug": "campus_stationery", "name": "Highlighter Set", "description": "Pack of 5", "price": 80.0, "unit": "set", "category": "Writing", "image_url": "https://cdn.tapntake.app/stationery/highlighter.jpg", "stock": 150},
	{"slug": "stationery-notebook", "vendor_slug": "campus_stationery", "name": "Spiral Notebook", "description": "200 page ruled", "price": 95.0, "unit": "piece", "category": "Notebooks", "image_url": "https://cdn.tapntake.app/stationery/notebook.jpg", "stock": 200},
	{"slug": "stationery-graph", "vendor_slug": "campus_stationery", "name": "Graph Notebook", "description": "2mm grid", "price": 85.0, "unit": "piece", "category": "Notebooks", "image_url": "https://cdn.tapntake.app/stationery/graph_notebook.jpg", "stock": 160},
	{"slug": "stationery-stapler", "vendor_slug": "campus_stationery", "name": "Stapler Medium", "description": "No.10 stapler", "price": 110.0, "unit": "piece", "category": "Accessories", "image_url": "https://cdn.tapntake.app/stationery/stapler.jpg", "stock": 90},
	{"slug": "stationery-project-file", "vendor_slug": "campus_stationery", "name": "Project File", "description": "Button folder", "price": 35.0, "unit": "piece", "category": "Files", "image_url": "https://cdn.tapntake.app/stationery/project_file.jpg", "stock": 260},
	{"slug": "stationery-binder", "vendor_slug": "campus_stationery", "name": "Ring Binder", "description": "2D ring binder", "price": 140.0, "unit": "piece", "category": "Files", "image_url": "https://cdn.tapntake.app/stationery/ring_binder.jpg", "stock": 70},
	{"slug": "stationery-color-print", "vendor_slug": "campus_stationery", "name": "Instant Color Print", "description": "Quick kiosk prints", "price": 8.0, "unit": "page", "category": "Printing", "image_url": "https://cdn.tapntake.app/stationery/color_print.jpg", "stock": 350},
)


SLOT_TEMPLATES: Sequence[Dict[str, Any]] = (
	{"label": "breakfast", "start_hour": 9, "duration": 60, "max_orders": 24},
	{"label": "lunch", "start_hour": 12, "duration": 90, "max_orders": 48},
	{"label": "evening", "start_hour": 18, "duration": 90, "max_orders": 42},
)


ORDER_FIXTURES: Sequence[Dict[str, Any]] = (
	{
		"reference": "ORD-NAINA-001",
		"user": "naina",
		"vendor": "campus_cafe",
		"slot_label": "lunch",
		"items": [{"menu_slug": "campus-veg-burger", "quantity": 1}, {"menu_slug": "campus-cold-coffee", "quantity": 1}],
		"status": OrderStatus.PICKED,
		"days_ago": 1,
		"eta_minutes": 18,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY, OrderStatus.PICKED],
	},
	{
		"reference": "ORD-NAINA-002",
		"user": "naina",
		"vendor": "burger_hub",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "burgerhub-cheese-burst", "quantity": 1},
			{"menu_slug": "burgerhub-peri-peri-fries", "quantity": 1},
		],
		"status": OrderStatus.READY,
		"days_ago": 0,
		"eta_minutes": 15,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY],
	},
	{
		"reference": "ORD-NAINA-003",
		"user": "naina",
		"vendor": "pizza_station",
		"slot_label": "lunch",
		"items": [
			{"menu_slug": "pizza-margherita", "quantity": 1},
			{"menu_slug": "pizza-garlic-breadsticks", "quantity": 1},
		],
		"status": OrderStatus.CONFIRMED,
		"days_ago": 0,
		"eta_minutes": 25,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED],
	},
	{
		"reference": "ORD-RAHUL-001",
		"user": "rahul",
		"vendor": "burger_hub",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "burgerhub-cheese-burst", "quantity": 1},
			{"menu_slug": "burgerhub-peri-peri-fries", "quantity": 1},
			{"menu_slug": "burgerhub-iced-tea", "quantity": 1},
		],
		"status": OrderStatus.READY,
		"days_ago": 0,
		"eta_minutes": 22,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY],
	},
	{
		"reference": "ORD-ANANYA-001",
		"user": "ananya",
		"vendor": "green_bowl",
		"slot_label": "lunch",
		"items": [
			{"menu_slug": "greenbowl-buddha-bowl", "quantity": 1},
			{"menu_slug": "greenbowl-detox-juice", "quantity": 1},
		],
		"status": OrderStatus.CONFIRMED,
		"days_ago": 2,
		"eta_minutes": 20,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED],
	},
	{
		"reference": "ORD-KABIR-001",
		"user": "kabir",
		"vendor": "pizza_station",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "pizza-tandoori-paneer", "quantity": 1},
			{"menu_slug": "pizza-garlic-breadsticks", "quantity": 1},
		],
		"status": OrderStatus.READY,
		"days_ago": 3,
		"eta_minutes": 28,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY],
	},
	{
		"reference": "ORD-MEERA-001",
		"user": "meera",
		"vendor": "campus_cafe",
		"slot_label": "breakfast",
		"items": [
			{"menu_slug": "campus-blueberry-muffin", "quantity": 1},
			{"menu_slug": "campus-choco-shake", "quantity": 1},
		],
		"status": OrderStatus.PICKED,
		"days_ago": 4,
		"eta_minutes": 12,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY, OrderStatus.PICKED],
	},
	{
		"reference": "ORD-ARJUN-001",
		"user": "arjun",
		"vendor": "spice_corner",
		"slot_label": "breakfast",
		"items": [
			{"menu_slug": "spice-masala-dosa", "quantity": 1},
			{"menu_slug": "spice-filter-coffee", "quantity": 1},
		],
		"status": OrderStatus.PLACED,
		"days_ago": 0,
		"eta_minutes": 15,
		"payment": {"status": PaymentStatus.INITIATED, "method": "UPI"},
		"history": [OrderStatus.PLACED],
	},
	{
		"reference": "ORD-DEV-001",
		"user": "dev",
		"vendor": "burger_hub",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "burgerhub-loaded-fries", "quantity": 1},
			{"menu_slug": "burgerhub-oreo-shake", "quantity": 1},
		],
		"status": OrderStatus.CANCELLED,
		"days_ago": 1,
		"eta_minutes": 0,
		"payment": {"status": PaymentStatus.REFUNDED, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CANCELLED],
	},
	{
		"reference": "ORD-SNEHA-001",
		"user": "sneha",
		"vendor": "green_bowl",
		"slot_label": "lunch",
		"items": [
			{"menu_slug": "greenbowl-quinoa-salad", "quantity": 1},
			{"menu_slug": "greenbowl-power-smoothie", "quantity": 1},
		],
		"status": OrderStatus.PICKED,
		"days_ago": 2,
		"eta_minutes": 17,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "WALLET"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY, OrderStatus.PICKED],
	},
	{
		"reference": "ORD-NAINA-002",
		"user": "naina",
		"vendor": "pizza_station",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "pizza-farmhouse", "quantity": 1},
			{"menu_slug": "pizza-chilli-cheese-toast", "quantity": 1},
		],
		"status": OrderStatus.READY,
		"days_ago": 5,
		"eta_minutes": 25,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY],
	},
	{
		"reference": "ORD-RAHUL-002",
		"user": "rahul",
		"vendor": "spice_corner",
		"slot_label": "lunch",
		"items": [
			{"menu_slug": "spice-lemon-rice", "quantity": 1},
			{"menu_slug": "spice-medhu-vada", "quantity": 1},
		],
		"status": OrderStatus.PICKED,
		"days_ago": 6,
		"eta_minutes": 18,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY, OrderStatus.PICKED],
	},
	# Additional orders 13-20
	{
		"reference": "ORD-DEV-002",
		"user": "dev",
		"vendor": "campus_cafe",
		"slot_label": "breakfast",
		"items": [
			{"menu_slug": "campus-pesto-sandwich", "quantity": 1},
			{"menu_slug": "campus-masala-chai", "quantity": 2},
		],
		"status": OrderStatus.PREPARING,
		"days_ago": 0,
		"eta_minutes": 22,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING],
	},
	{
		"reference": "ORD-SNEHA-002",
		"user": "sneha",
		"vendor": "pizza_station",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "pizza-veggie-loaded", "quantity": 1},
			{"menu_slug": "pizza-garlic-breadsticks", "quantity": 1},
		],
		"status": OrderStatus.PLACED,
		"days_ago": 0,
		"eta_minutes": 30,
		"payment": {"status": PaymentStatus.INITIATED, "method": "UPI"},
		"history": [OrderStatus.PLACED],
	},
	{
		"reference": "ORD-ARJUN-002",
		"user": "arjun",
		"vendor": "campus_cafe",
		"slot_label": "breakfast",
		"items": [
			{"menu_slug": "campus-garlic-toastie", "quantity": 2},
			{"menu_slug": "campus-cold-coffee", "quantity": 1},
		],
		"status": OrderStatus.PREPARING,
		"days_ago": 0,
		"eta_minutes": 20,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING],
	},
	{
		"reference": "ORD-NAINA-004",
		"user": "naina",
		"vendor": "spice_corner",
		"slot_label": "lunch",
		"items": [
			{"menu_slug": "spice-chole-bhature", "quantity": 1},
			{"menu_slug": "spice-filter-coffee", "quantity": 1},
		],
		"status": OrderStatus.READY,
		"days_ago": 0,
		"eta_minutes": 25,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY],
	},
	{
		"reference": "ORD-KABIR-002",
		"user": "kabir",
		"vendor": "burger_hub",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "burgerhub-classic-veg", "quantity": 2},
			{"menu_slug": "burgerhub-crispy-corn", "quantity": 1},
			{"menu_slug": "burgerhub-iced-tea", "quantity": 1},
		],
		"status": OrderStatus.PICKED,
		"days_ago": 3,
		"eta_minutes": 16,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "WALLET"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.PICKED],
	},
	{
		"reference": "ORD-MEERA-002",
		"user": "meera",
		"vendor": "green_bowl",
		"slot_label": "lunch",
		"items": [
			{"menu_slug": "greenbowl-avocado-toast", "quantity": 1},
			{"menu_slug": "greenbowl-detox-juice", "quantity": 1},
		],
		"status": OrderStatus.CANCELLED,
		"days_ago": 2,
		"eta_minutes": 0,
		"payment": {"status": PaymentStatus.REFUNDED, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CANCELLED],
	},
	{
		"reference": "ORD-ANANYA-002",
		"user": "ananya",
		"vendor": "pizza_station",
		"slot_label": "evening",
		"items": [
			{"menu_slug": "pizza-pasta-alfredo", "quantity": 1},
			{"menu_slug": "pizza-chilli-cheese-toast", "quantity": 1},
		],
		"status": OrderStatus.PICKED,
		"days_ago": 4,
		"eta_minutes": 20,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.PICKED],
	},
	{
		"reference": "ORD-RAHUL-003",
		"user": "rahul",
		"vendor": "pizza_station",
		"slot_label": "lunch",
		"items": [
			{"menu_slug": "pizza-margherita", "quantity": 1},
		],
		"status": OrderStatus.CONFIRMED,
		"days_ago": 0,
		"eta_minutes": 18,
		"payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"},
		"history": [OrderStatus.PLACED, OrderStatus.CONFIRMED],
	},
)

NOTIFICATION_FIXTURES: Sequence[Dict[str, Any]] = (
	# 1-8: Order lifecycle notifications per user
	{"user": "naina", "title": "Order Placed", "message": "Your order #1 has been placed successfully. ETA: 18 minutes.", "notification_type": NotificationType.ORDER_PLACED, "order_ref": "ORD-NAINA-001", "minutes_after_order": 0, "is_read": True},
	{"user": "naina", "title": "Order Accepted", "message": "Campus Cafe confirmed your lunch combo.", "notification_type": NotificationType.ORDER_ACCEPTED, "order_ref": "ORD-NAINA-001", "minutes_after_order": 5, "is_read": True},
	{"user": "naina", "title": "Order Ready for Pickup", "message": "Pickup counter B is ready for your Veg Burger.", "notification_type": NotificationType.ORDER_READY, "order_ref": "ORD-NAINA-001", "minutes_after_order": 25, "is_read": True},
	{"user": "rahul", "title": "Order Accepted", "message": "Burger Hub has accepted your evening order.", "notification_type": NotificationType.ORDER_ACCEPTED, "order_ref": "ORD-RAHUL-001", "minutes_after_order": 3, "is_read": True},
	{"user": "rahul", "title": "Order Ready for Pickup", "message": "Your Cheese Burst Burger and Peri Peri Fries are ready.", "notification_type": NotificationType.ORDER_READY, "order_ref": "ORD-RAHUL-001", "minutes_after_order": 22, "is_read": False},
	{"user": "ananya", "title": "Order Accepted", "message": "Green Bowl has accepted your lunch order.", "notification_type": NotificationType.ORDER_ACCEPTED, "order_ref": "ORD-ANANYA-001", "minutes_after_order": 4, "is_read": True},
	{"user": "kabir", "title": "Order Ready for Pickup", "message": "Your Tandoori Paneer Pizza is ready at Pizza Station.", "notification_type": NotificationType.ORDER_READY, "order_ref": "ORD-KABIR-001", "minutes_after_order": 28, "is_read": True},
	{"user": "meera", "title": "Order Placed", "message": "Your Campus Cafe breakfast order has been placed.", "notification_type": NotificationType.ORDER_PLACED, "order_ref": "ORD-MEERA-001", "minutes_after_order": 0, "is_read": True},
	# 9-14: Preparing notifications
	{"user": "dev", "title": "Order Preparing", "message": "Your Pesto Sandwich and Masala Chai are being prepared at Campus Cafe.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-DEV-002", "minutes_after_order": 8, "is_read": False},
	{"user": "arjun", "title": "Order Preparing", "message": "Your Garlic Toastie order is now being prepared.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-ARJUN-002", "minutes_after_order": 7, "is_read": False},
	{"user": "naina", "title": "Order Preparing", "message": "Spice Corner is preparing your Chole Bhature.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-NAINA-004", "minutes_after_order": 10, "is_read": True},
	{"user": "kabir", "title": "Order Preparing", "message": "Your Classic Veg Burgers are being prepared at Burger Hub.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-KABIR-002", "minutes_after_order": 6, "is_read": True},
	{"user": "ananya", "title": "Order Preparing", "message": "Pizza Station is preparing your Pasta Alfredo.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-ANANYA-002", "minutes_after_order": 9, "is_read": True},
	{"user": "rahul", "title": "Order Preparing", "message": "Your Margherita Pizza is being prepared at Pizza Station.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-RAHUL-003", "minutes_after_order": 5, "is_read": False},
	# 15-20: Pickup reminders
	{"user": "naina", "title": "Pickup Reminder", "message": "Your order #2 is ready! Pickup slot opens in 10 minutes.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": "ORD-NAINA-002", "minutes_after_order": 30, "is_read": False},
	{"user": "rahul", "title": "Pickup Reminder", "message": "Head to Burger Hub — your order is waiting at counter A.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": "ORD-RAHUL-001", "minutes_after_order": 35, "is_read": False},
	{"user": "ananya", "title": "Pickup Reminder", "message": "Slot L-23 opens in 10 minutes for your bowl.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": "ORD-ANANYA-001", "minutes_after_order": 10, "is_read": True},
	{"user": "kabir", "title": "Pickup Reminder", "message": "Your Pizza Station order is ready for pickup at Central Courtyard.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": "ORD-KABIR-001", "minutes_after_order": 40, "is_read": True},
	{"user": "naina", "title": "Pickup Reminder", "message": "Don't forget! Your Spice Corner order is ready at Heritage Lane.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": "ORD-NAINA-004", "minutes_after_order": 38, "is_read": False},
	{"user": "sneha", "title": "Pickup Reminder", "message": "Your Veggie Loaded Pizza is ready — pick it up before the slot closes.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": "ORD-SNEHA-002", "minutes_after_order": 15, "is_read": False},
	# 21-25: Delay alerts
	{"user": "naina", "title": "Delay Alert", "message": "Your Burger Hub order is running 5 minutes late due to high demand.", "notification_type": NotificationType.DELAY_ALERT, "order_ref": "ORD-NAINA-002", "minutes_after_order": 20, "is_read": False},
	{"user": "rahul", "title": "Delay Alert", "message": "Burger Hub is experiencing delays. Your order may take 8 extra minutes.", "notification_type": NotificationType.DELAY_ALERT, "order_ref": "ORD-RAHUL-001", "minutes_after_order": 25, "is_read": False},
	{"user": "kabir", "title": "Delay Alert", "message": "Pizza Station delay: your order will be ready in about 10 more minutes.", "notification_type": NotificationType.DELAY_ALERT, "order_ref": "ORD-KABIR-001", "minutes_after_order": 30, "is_read": True},
	{"user": "ananya", "title": "Delay Alert", "message": "Green Bowl is running behind schedule. Updated ETA: 12 more minutes.", "notification_type": NotificationType.DELAY_ALERT, "order_ref": "ORD-ANANYA-001", "minutes_after_order": 18, "is_read": True},
	{"user": "dev", "title": "Delay Alert", "message": "Campus Cafe is busy. Your order may be delayed by 6 minutes.", "notification_type": NotificationType.DELAY_ALERT, "order_ref": "ORD-DEV-002", "minutes_after_order": 22, "is_read": False},
	# 26-30: Cancelled + promo + system
	{"user": "dev", "title": "Order Cancelled", "message": "Your Burger Hub order has been cancelled. Refund will be processed.", "notification_type": NotificationType.ORDER_CANCELLED, "order_ref": "ORD-DEV-001", "minutes_after_order": 2, "is_read": True},
	{"user": "meera", "title": "Order Cancelled", "message": "Your Green Bowl order was cancelled. Refund initiated.", "notification_type": NotificationType.ORDER_CANCELLED, "order_ref": "ORD-MEERA-002", "minutes_after_order": 3, "is_read": True},
	{"user": "rahul", "title": "Burger Hub Deal", "message": "Get 10% off on peri-peri fries before 6 PM today!", "notification_type": NotificationType.PROMO, "order_ref": None, "minutes_after_order": 60, "is_read": False},
	{"user": "sneha", "title": "Vendor Spotlight", "message": "Green Bowl introduced a new Hummus Wrap — try it today!", "notification_type": NotificationType.PROMO, "order_ref": None, "minutes_after_order": 30, "is_read": False},
	{"user": "arjun", "title": "Faculty Priority Slots", "message": "Early breakfast slots are now open for tomorrow. Book now!", "notification_type": NotificationType.SYSTEM, "order_ref": None, "minutes_after_order": 15, "is_read": False},
)


AI_FIXTURES: Sequence[Dict[str, Any]] = (
	{
		"user": "naina",
		"insight": "Users who bought Veg Burger also bought Cold Coffee",
		"popular": [
			{"menu_slug": "campus-veg-burger", "order_count": 15},
			{"menu_slug": "campus-cold-coffee", "order_count": 11},
		],
		"recommended": [
			{"menu_slug": "campus-paneer-wrap", "reason": "Similar to your burger preference"},
			{"menu_slug": "pizza-chilli-cheese-toast", "reason": "Pairs with your evening pizza picks"},
		],
	},
	{
		"user": "rahul",
		"insight": "Spicy eaters loved pairing Peri Peri Fries with Tandoori pizzas",
		"popular": [
			{"menu_slug": "burgerhub-peri-peri-fries", "order_count": 9},
			{"menu_slug": "pizza-tandoori-paneer", "order_count": 6},
		],
		"recommended": [
			{"menu_slug": "spice-chole-bhature", "reason": "High spice craving indicator"},
			{"menu_slug": "burgerhub-paneer-spice", "reason": "People who love peri-peri fries reorder this"},
		],
	},
	{
		"user": "ananya",
		"insight": "Plant-based eaters reorder Buddha Bowls every Tuesday",
		"popular": [
			{"menu_slug": "greenbowl-buddha-bowl", "order_count": 8},
			{"menu_slug": "greenbowl-detox-juice", "order_count": 7},
		],
		"recommended": [
			{"menu_slug": "greenbowl-falafel-bowl", "reason": "High protein Mediterranean pick"},
			{"menu_slug": "greenbowl-hummus-wrap", "reason": "Portable vegan lunch"},
		],
	},
	{
		"user": "kabir",
		"insight": "Late evening pizza fans often add Garlic Breadsticks",
		"popular": [
			{"menu_slug": "pizza-farmhouse", "order_count": 5},
			{"menu_slug": "pizza-garlic-breadsticks", "order_count": 5},
		],
		"recommended": [
			{"menu_slug": "pizza-pasta-alfredo", "reason": "Comfort combo suggested by AI"},
			{"menu_slug": "burgerhub-crispy-corn", "reason": "Crunchy add-on between classes"},
		],
	},
	{
		"user": "meera",
		"insight": "Sweet cravings peak at 10 AM around Campus Cafe",
		"popular": [
			{"menu_slug": "campus-blueberry-muffin", "order_count": 10},
			{"menu_slug": "campus-choco-shake", "order_count": 8},
		],
		"recommended": [
			{"menu_slug": "campus-masala-chai", "reason": "Pairs with your muffin rituals"},
			{"menu_slug": "campus-pesto-sandwich", "reason": "Balanced brunch suggestion"},
		],
	},
	{
		"user": "arjun",
		"insight": "Faculty members reorder Masala Dosa with Filter Coffee",
		"popular": [
			{"menu_slug": "spice-masala-dosa", "order_count": 12},
			{"menu_slug": "spice-filter-coffee", "order_count": 12},
		],
		"recommended": [
			{"menu_slug": "spice-mysore-dosa", "reason": "Upgrade to a spicier profile"},
			{"menu_slug": "spice-idli-sambar", "reason": "Quick weekday breakfast"},
		],
	},
	{
		"user": "dev",
		"insight": "Study group orders mix shakes with fries for sharing",
		"popular": [
			{"menu_slug": "burgerhub-loaded-fries", "order_count": 7},
			{"menu_slug": "burgerhub-oreo-shake", "order_count": 6},
		],
		"recommended": [
			{"menu_slug": "burgerhub-classic-veg", "reason": "Value meal suggestion"},
			{"menu_slug": "burgerhub-crispy-corn", "reason": "Crunchy midnight snack"},
		],
	},
	{
		"user": "sneha",
		"insight": "Gluten-free eaters enjoy pairing salads with smoothies",
		"popular": [
			{"menu_slug": "greenbowl-quinoa-salad", "order_count": 9},
			{"menu_slug": "greenbowl-power-smoothie", "order_count": 9},
		],
		"recommended": [
			{"menu_slug": "greenbowl-greek-salad", "reason": "High protein Greek option"},
			{"menu_slug": "greenbowl-avocado-toast", "reason": "Breakfast that fits your filters"},
		],
	},
)


FEEDBACK_FIXTURES: Sequence[Dict[str, Any]] = (
	# 50 feedback records across completed/picked orders
	{"user": "naina", "order_ref": "ORD-NAINA-001", "vendor": "campus_cafe", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Great food and fast service!", "days_offset": 0},
	{"user": "meera", "order_ref": "ORD-MEERA-001", "vendor": "campus_cafe", "quality_rating": 4, "time_rating": 5, "behavior_rating": 4, "comment": "Muffin was fresh, shake was thick.", "days_offset": 0},
	{"user": "rahul", "order_ref": "ORD-RAHUL-002", "vendor": "spice_corner", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Best dosa on campus!", "days_offset": 0},
	{"user": "sneha", "order_ref": "ORD-SNEHA-001", "vendor": "green_bowl", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Healthy and tasty.", "days_offset": 0},
	{"user": "kabir", "order_ref": "ORD-KABIR-002", "vendor": "burger_hub", "quality_rating": 4, "time_rating": 3, "behavior_rating": 4, "comment": "Good burgers, slight wait.", "days_offset": 0},
	{"user": "ananya", "order_ref": "ORD-ANANYA-002", "vendor": "pizza_station", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Alfredo was creamy perfection.", "days_offset": 0},
	# Campus Cafe feedback (15 more)
	{"user": "naina", "order_ref": "ORD-NAINA-001", "vendor": "campus_cafe", "quality_rating": 4, "time_rating": 4, "behavior_rating": 3, "comment": "Good wrap, okay wait time.", "days_offset": 1},
	{"user": "rahul", "order_ref": "ORD-RAHUL-002", "vendor": "campus_cafe", "quality_rating": 3, "time_rating": 3, "behavior_rating": 4, "comment": "Average experience.", "days_offset": 2},
	{"user": "dev", "order_ref": "ORD-DEV-002", "vendor": "campus_cafe", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Pesto sandwich was amazing!", "days_offset": 0},
	{"user": "arjun", "order_ref": "ORD-ARJUN-002", "vendor": "campus_cafe", "quality_rating": 4, "time_rating": 5, "behavior_rating": 5, "comment": "Quick and tasty.", "days_offset": 0},
	{"user": "meera", "order_ref": "ORD-MEERA-001", "vendor": "campus_cafe", "quality_rating": 5, "time_rating": 4, "behavior_rating": 4, "comment": "Love the muffins!", "days_offset": 1},
	{"user": "naina", "order_ref": "ORD-NAINA-001", "vendor": "campus_cafe", "quality_rating": 3, "time_rating": 2, "behavior_rating": 3, "comment": "Slow during lunch rush.", "days_offset": 3},
	{"user": "sneha", "order_ref": "ORD-SNEHA-001", "vendor": "campus_cafe", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Consistent quality.", "days_offset": 1},
	{"user": "kabir", "order_ref": "ORD-KABIR-002", "vendor": "campus_cafe", "quality_rating": 4, "time_rating": 3, "behavior_rating": 5, "comment": "Staff was very friendly.", "days_offset": 2},
	{"user": "ananya", "order_ref": "ORD-ANANYA-002", "vendor": "campus_cafe", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Best cafe on campus!", "days_offset": 0},
	{"user": "dev", "order_ref": "ORD-DEV-002", "vendor": "campus_cafe", "quality_rating": 3, "time_rating": 3, "behavior_rating": 4, "comment": "Decent for quick bites.", "days_offset": 1},
	{"user": "arjun", "order_ref": "ORD-ARJUN-002", "vendor": "campus_cafe", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Good breakfast option.", "days_offset": 1},
	{"user": "rahul", "order_ref": "ORD-RAHUL-002", "vendor": "campus_cafe", "quality_rating": 2, "time_rating": 2, "behavior_rating": 3, "comment": "Underwhelming today.", "days_offset": 3},
	# Burger Hub feedback (10)
	{"user": "rahul", "order_ref": "ORD-RAHUL-001", "vendor": "burger_hub", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Cheese burst is incredible!", "days_offset": 0},
	{"user": "naina", "order_ref": "ORD-NAINA-001", "vendor": "burger_hub", "quality_rating": 4, "time_rating": 3, "behavior_rating": 4, "comment": "Good burgers, peri peri fries rule.", "days_offset": 1},
	{"user": "dev", "order_ref": "ORD-DEV-001", "vendor": "burger_hub", "quality_rating": 3, "time_rating": 2, "behavior_rating": 3, "comment": "Loaded fries were cold.", "days_offset": 2},
	{"user": "kabir", "order_ref": "ORD-KABIR-002", "vendor": "burger_hub", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Perfect evening snack!", "days_offset": 0},
	{"user": "sneha", "order_ref": "ORD-SNEHA-001", "vendor": "burger_hub", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Solid choice always.", "days_offset": 1},
	{"user": "meera", "order_ref": "ORD-MEERA-001", "vendor": "burger_hub", "quality_rating": 3, "time_rating": 3, "behavior_rating": 4, "comment": "Oreo shake was too sweet.", "days_offset": 2},
	{"user": "arjun", "order_ref": "ORD-ARJUN-002", "vendor": "burger_hub", "quality_rating": 4, "time_rating": 4, "behavior_rating": 5, "comment": "Classic veg never disappoints.", "days_offset": 1},
	{"user": "ananya", "order_ref": "ORD-ANANYA-002", "vendor": "burger_hub", "quality_rating": 4, "time_rating": 3, "behavior_rating": 4, "comment": "Crispy corn pops are fun.", "days_offset": 1},
	{"user": "naina", "order_ref": "ORD-NAINA-001", "vendor": "burger_hub", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "My go-to for burgers!", "days_offset": 0},
	{"user": "rahul", "order_ref": "ORD-RAHUL-001", "vendor": "burger_hub", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Consistent quality.", "days_offset": 2},
	# Spice Corner feedback (8)
	{"user": "arjun", "order_ref": "ORD-ARJUN-001", "vendor": "spice_corner", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Authentic south Indian!", "days_offset": 0},
	{"user": "rahul", "order_ref": "ORD-RAHUL-002", "vendor": "spice_corner", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Chole bhature was excellent.", "days_offset": 0},
	{"user": "naina", "order_ref": "ORD-NAINA-004", "vendor": "spice_corner", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Good dosa, quick service.", "days_offset": 1},
	{"user": "dev", "order_ref": "ORD-DEV-002", "vendor": "spice_corner", "quality_rating": 4, "time_rating": 3, "behavior_rating": 4, "comment": "Lemon rice was flavorful.", "days_offset": 1},
	{"user": "sneha", "order_ref": "ORD-SNEHA-001", "vendor": "spice_corner", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Filter coffee is the best!", "days_offset": 0},
	{"user": "kabir", "order_ref": "ORD-KABIR-001", "vendor": "spice_corner", "quality_rating": 3, "time_rating": 3, "behavior_rating": 3, "comment": "Medhu vada was okay.", "days_offset": 2},
	{"user": "meera", "order_ref": "ORD-MEERA-001", "vendor": "spice_corner", "quality_rating": 4, "time_rating": 4, "behavior_rating": 5, "comment": "Idli sambar hit the spot.", "days_offset": 1},
	{"user": "ananya", "order_ref": "ORD-ANANYA-001", "vendor": "spice_corner", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Upma was comforting.", "days_offset": 1},
	# Green Bowl feedback (7)
	{"user": "ananya", "order_ref": "ORD-ANANYA-001", "vendor": "green_bowl", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Buddha bowl is my favorite!", "days_offset": 0},
	{"user": "sneha", "order_ref": "ORD-SNEHA-001", "vendor": "green_bowl", "quality_rating": 4, "time_rating": 5, "behavior_rating": 4, "comment": "Detox juice is so refreshing.", "days_offset": 0},
	{"user": "naina", "order_ref": "ORD-NAINA-001", "vendor": "green_bowl", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Quinoa salad was outstanding.", "days_offset": 1},
	{"user": "rahul", "order_ref": "ORD-RAHUL-002", "vendor": "green_bowl", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Hummus wrap is solid.", "days_offset": 1},
	{"user": "dev", "order_ref": "ORD-DEV-002", "vendor": "green_bowl", "quality_rating": 3, "time_rating": 3, "behavior_rating": 4, "comment": "Wish they had more options.", "days_offset": 2},
	{"user": "kabir", "order_ref": "ORD-KABIR-001", "vendor": "green_bowl", "quality_rating": 4, "time_rating": 4, "behavior_rating": 5, "comment": "Falafel bowl was great.", "days_offset": 1},
	{"user": "arjun", "order_ref": "ORD-ARJUN-001", "vendor": "green_bowl", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Best healthy option around.", "days_offset": 0},
	# Pizza Station feedback (10)
	{"user": "kabir", "order_ref": "ORD-KABIR-001", "vendor": "pizza_station", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Tandoori paneer pizza is fire!", "days_offset": 0},
	{"user": "naina", "order_ref": "ORD-NAINA-002", "vendor": "pizza_station", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Farmhouse was loaded.", "days_offset": 0},
	{"user": "rahul", "order_ref": "ORD-RAHUL-003", "vendor": "pizza_station", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Margherita perfection.", "days_offset": 0},
	{"user": "ananya", "order_ref": "ORD-ANANYA-002", "vendor": "pizza_station", "quality_rating": 4, "time_rating": 3, "behavior_rating": 4, "comment": "Pasta arrabiata had a kick.", "days_offset": 1},
	{"user": "dev", "order_ref": "ORD-DEV-001", "vendor": "pizza_station", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Chilli cheese toast is addictive.", "days_offset": 1},
	{"user": "sneha", "order_ref": "ORD-SNEHA-002", "vendor": "pizza_station", "quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Veggie loaded is the best!", "days_offset": 0},
	{"user": "meera", "order_ref": "ORD-MEERA-001", "vendor": "pizza_station", "quality_rating": 3, "time_rating": 3, "behavior_rating": 3, "comment": "Garlic breadsticks were burnt.", "days_offset": 2},
	{"user": "arjun", "order_ref": "ORD-ARJUN-002", "vendor": "pizza_station", "quality_rating": 4, "time_rating": 4, "behavior_rating": 5, "comment": "Good wood-fired taste.", "days_offset": 1},
	{"user": "naina", "order_ref": "ORD-NAINA-004", "vendor": "pizza_station", "quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "comment": "Never disappoints!", "days_offset": 0},
	{"user": "rahul", "order_ref": "ORD-RAHUL-001", "vendor": "pizza_station", "quality_rating": 4, "time_rating": 4, "behavior_rating": 4, "comment": "Reliable pizza joint.", "days_offset": 2},
)

VENDOR_REVIEW_FIXTURES: Sequence[Dict[str, Any]] = (
	# 20 vendor reviews for public review display
	{"user": "naina", "vendor": "campus_cafe", "rating": 5, "title": "Best Campus Cafe!", "review_text": "Always fresh, always fast. The pesto sandwich is my go-to.", "is_anonymous": False, "order_ref": "ORD-NAINA-001"},
	{"user": "rahul", "vendor": "campus_cafe", "rating": 4, "title": "Good but slow at lunch", "review_text": "Food is great but expect a wait during peak hours.", "is_anonymous": False, "order_ref": "ORD-RAHUL-002"},
	{"user": "meera", "vendor": "campus_cafe", "rating": 5, "title": "Muffin heaven", "review_text": "Blueberry muffins are baked fresh daily. Love the choco shake too.", "is_anonymous": False, "order_ref": "ORD-MEERA-001"},
	{"user": "arjun", "vendor": "campus_cafe", "rating": 4, "title": "Decent quick bites", "review_text": "Garlic toastie and chai make a good combo.", "is_anonymous": True, "order_ref": "ORD-ARJUN-002"},
	{"user": "sneha", "vendor": "campus_cafe", "rating": 3, "title": "Inconsistent", "review_text": "Sometimes great, sometimes meh. Depends on the day.", "is_anonymous": True},
	{"user": "rahul", "vendor": "burger_hub", "rating": 5, "title": "Cheese Burst Burger is elite", "review_text": "The double cheese on brioche is something else. Best burger on campus.", "is_anonymous": False, "order_ref": "ORD-RAHUL-001"},
	{"user": "naina", "vendor": "burger_hub", "rating": 4, "title": "Great fries", "review_text": "Peri peri fries are the star. Burgers are good too.", "is_anonymous": False, "order_ref": "ORD-NAINA-001"},
	{"user": "kabir", "vendor": "burger_hub", "rating": 5, "title": "Late night savior", "review_text": "Classic veg and crispy corn — perfect study break snack.", "is_anonymous": False, "order_ref": "ORD-KABIR-002"},
	{"user": "dev", "vendor": "burger_hub", "rating": 3, "title": "Cold fries once", "review_text": "Usually good but got cold fries once. Hope it was a one-off.", "is_anonymous": True, "order_ref": "ORD-DEV-001"},
	{"user": "arjun", "vendor": "spice_corner", "rating": 5, "title": "Authentic South Indian", "review_text": "The masala dosa and filter coffee remind me of home. Best on campus.", "is_anonymous": False, "order_ref": "ORD-ARJUN-001"},
	{"user": "rahul", "vendor": "spice_corner", "rating": 5, "title": "Chole Bhature heaven", "review_text": "Punjabi style chole bhature is outstanding. Must try!", "is_anonymous": False, "order_ref": "ORD-RAHUL-002"},
	{"user": "sneha", "vendor": "spice_corner", "rating": 4, "title": "Filter coffee addiction", "review_text": "That brass tumbler decoction is pure bliss.", "is_anonymous": False},
	{"user": "ananya", "vendor": "green_bowl", "rating": 5, "title": "Best healthy food", "review_text": "Buddha bowl and detox juice are my staples. Love this place!", "is_anonymous": False, "order_ref": "ORD-ANANYA-001"},
	{"user": "naina", "vendor": "green_bowl", "rating": 4, "title": "Quinoa salad is a winner", "review_text": "Fresh ingredients and great dressing. A bit pricey though.", "is_anonymous": False, "order_ref": "ORD-NAINA-001"},
	{"user": "kabir", "vendor": "green_bowl", "rating": 4, "title": "Falafel power bowl", "review_text": "Baked falafel with tzatziki is really good. Will order again.", "is_anonymous": True, "order_ref": "ORD-KABIR-001"},
	{"user": "dev", "vendor": "green_bowl", "rating": 3, "title": "Limited menu", "review_text": "Quality is good but wish they had more options for non-veg folks.", "is_anonymous": True},
	{"user": "kabir", "vendor": "pizza_station", "rating": 5, "title": "Tandoori Paneer Pizza!", "review_text": "The smoky paneer on a cheese base is incredible. Best pizza here.", "is_anonymous": False, "order_ref": "ORD-KABIR-001"},
	{"user": "naina", "vendor": "pizza_station", "rating": 4, "title": "Wood-fired goodness", "review_text": "Farmhouse pizza was loaded and fresh. Good value.", "is_anonymous": False, "order_ref": "ORD-NAINA-002"},
	{"user": "rahul", "vendor": "pizza_station", "rating": 5, "title": "Margherita perfection", "review_text": "San Marzano tomatoes and fresh basil — simple and perfect.", "is_anonymous": False, "order_ref": "ORD-RAHUL-003"},
	{"user": "sneha", "vendor": "pizza_station", "rating": 4, "title": "Veggie loaded review", "review_text": "Good variety of toppings. Chilli cheese toast is a must-try side.", "is_anonymous": False, "order_ref": "ORD-SNEHA-002"},
)


CART_FIXTURES: Sequence[Dict[str, Any]] = (
	{"user": "naina", "vendor": "campus_cafe", "items": [{"menu_slug": "campus-veg-burger", "quantity": 1}, {"menu_slug": "campus-cold-coffee", "quantity": 1}]},
	{"user": "rahul", "vendor": "burger_hub", "items": [{"menu_slug": "burgerhub-cheese-burst", "quantity": 1}, {"menu_slug": "burgerhub-iced-tea", "quantity": 1}]},
	{"user": "ananya", "vendor": "green_bowl", "items": [{"menu_slug": "greenbowl-hummus-wrap", "quantity": 1}, {"menu_slug": "greenbowl-detox-juice", "quantity": 1}]},
	{"user": "sneha", "vendor": "pizza_station", "items": [{"menu_slug": "pizza-margherita", "quantity": 1}, {"menu_slug": "pizza-garlic-breadsticks", "quantity": 1}]},
)


STATIONERY_JOB_FIXTURES: Sequence[Dict[str, Any]] = (
	{"user": "naina", "vendor": "xerox_point", "service": "xerox-a4-color", "quantity": 32, "status": JobStatus.READY, "paid": True},
	{"user": "rahul", "vendor": "print_hub", "service": "print-banner", "quantity": 2, "status": JobStatus.IN_PROGRESS, "paid": False},
	{"user": "ananya", "vendor": "campus_stationery", "service": "stationery-notebook", "quantity": 3, "status": JobStatus.COLLECTED, "paid": True},
)


def maybe_reset_database(fresh: bool) -> None:
	if not fresh:
		return

	if DATABASE_URL.startswith("sqlite:///"):
		db_path = Path(DATABASE_URL.replace("sqlite:///", "", 1)).resolve()
		if db_path.exists():
			db_path.unlink()
		create_schema()
		LOGGER.info("Recreated SQLite database at %s", db_path)
	else:
		if "postgresql" in DATABASE_URL:
			from sqlalchemy import text
			with engine.connect() as conn:
				try:
					conn.execute(text("DROP SCHEMA public CASCADE"))
					conn.execute(text("CREATE SCHEMA public"))
					conn.commit()
					LOGGER.info("Dropped and recreated public schema on PostgreSQL")
				except Exception as e:
					LOGGER.error(f"Error dropping public schema: {e}")
		else:
			Base.metadata.drop_all(bind=engine)
		create_schema()
		LOGGER.info("Dropped and recreated schema on %s", DATABASE_URL)


def ensure_extra_tables(reset: bool) -> None:
	tables = [AI_RECOMMENDATIONS_TABLE, STATIONERY_PRODUCT_TABLE, VENDOR_PROFILE_TABLE]
	if reset:
		for table in tables:
			table.drop(engine, checkfirst=True)
	EXTRA_METADATA.create_all(engine, tables=tables, checkfirst=True)


def purge_existing_data(session: Session) -> None:
	for table in (AI_RECOMMENDATIONS_TABLE, STATIONERY_PRODUCT_TABLE, VENDOR_PROFILE_TABLE):
		session.execute(table.delete())

	for model in (VoucherRedemption, Voucher, OffPeakRewardPolicyAudit, OffPeakRewardPolicy, RedemptionRule, RewardRule, RewardRedemption, RewardTransaction, RewardPoints, VendorReview, Feedback, Notification, Ledger, Payment, OrderHistory, OrderItem, Order, Slot, StationeryJob, StationeryService, MenuItem, User):
		session.execute(delete(model))


def seed_students(session: Session) -> Dict[str, User]:
	users: Dict[str, User] = {}
	for payload in STUDENT_FIXTURES:
		user = User(
			name=payload["name"],
			phone=payload["phone"],
			role=payload["role"],
			vendor_type="food",
			university_id=payload["university_id"],
			is_active=True,
			is_approved=True,
			preferences=payload["preferences"],
		)
		session.add(user)
		session.flush()
		users[payload["slug"]] = user
	return users


def seed_vendors(session: Session, vendor_fixtures: Sequence[Dict[str, Any]]) -> Dict[str, User]:
	vendors: Dict[str, User] = {}
	vendor_rows: List[Dict[str, Any]] = []
	for payload in vendor_fixtures:
		profile = payload["profile"]
		vendor = User(
			name=payload["name"],
			phone=payload["phone"],
			role=UserRole.VENDOR,
			vendor_type=payload["vendor_type"],
			university_id=payload["university_id"],
			is_active=True,
			is_approved=True,
			preferences={"vendor_profile": profile},
		)
		session.add(vendor)
		session.flush()
		vendors[payload["slug"]] = vendor
		vendor_rows.append(
			{
				"vendor_id": vendor.id,
				"category": profile["category"],
				"description": profile["description"],
				"rating": profile["rating"],
				"location": profile["location"],
				"logo_url": profile["logo_url"],
				"cover_image": profile["cover_image"],
				"is_open": profile["is_open"],
			}
		)
	session.execute(VENDOR_PROFILE_TABLE.insert(), vendor_rows)
	return vendors


def seed_menu(session: Session, vendor_map: Dict[str, User]) -> Dict[str, MenuItem]:
	items: Dict[str, MenuItem] = {}
	for payload in MENU_FIXTURES:
		vendor = vendor_map[payload["vendor_slug"]]
		description = f"{payload['description']} (Prep ~{payload['prep_time']} min / {payload['category']})"
		menu_item = MenuItem(
			vendor_id=vendor.id,
			name=payload["name"],
			description=description,
			price=rupees(payload["price"]),
			image_url=payload["image_url"],
			is_available=True,
		)
		session.add(menu_item)
		session.flush()
		items[payload["slug"]] = menu_item
	return items


def seed_stationery(session: Session, vendor_map: Dict[str, User]) -> Dict[str, StationeryService]:
	services: Dict[str, StationeryService] = {}
	rows: List[Dict[str, Any]] = []
	for payload in STATIONERY_SERVICE_FIXTURES:
		vendor = vendor_map[payload["vendor_slug"]]
		service = StationeryService(
			vendor_id=vendor.id,
			name=payload["name"],
			price_per_unit=rupees(payload["price"]),
			unit=payload["unit"],
			is_available=True,
		)
		session.add(service)
		session.flush()
		services[payload["slug"]] = service
		rows.append(
			{
				"vendor_id": vendor.id,
				"service_id": service.id,
				"name": payload["name"],
				"description": payload["description"],
				"category": payload["category"],
				"image_url": payload["image_url"],
				"price": rupees(payload["price"]),
				"stock": payload["stock"],
			}
		)
	session.execute(STATIONERY_PRODUCT_TABLE.insert(), rows)
	return services


def seed_slots(session: Session, vendor_map: Dict[str, User]) -> Dict[tuple[str, str], Slot]:
	slot_map: Dict[tuple[str, str], Slot] = {}
	base_day = NOW.replace(hour=8, minute=0, second=0, microsecond=0)
	for vendor_slug, vendor in vendor_map.items():
		if vendor.vendor_type != "food":
			continue
		for template in SLOT_TEMPLATES:
			start = base_day.replace(hour=template["start_hour"], minute=0, second=0, microsecond=0)
			end = start + timedelta(minutes=template["duration"])
			slot = Slot(
				vendor_id=vendor.id,
				start_time=start,
				end_time=end,
				max_orders=template["max_orders"],
				current_orders=0,
				status=SlotStatus.AVAILABLE,
			)
			session.add(slot)
			session.flush()
			slot_map[(vendor_slug, template["label"])] = slot
	return slot_map


def create_order_histories(session: Session, order: Order, statuses: Sequence[OrderStatus]) -> None:
	timestamp = order.created_at
	for step, status in enumerate(statuses):
		record = OrderHistory(order_id=order.id, status=status, changed_at=timestamp + timedelta(minutes=step * 5))
		session.add(record)


def seed_orders(
	session: Session,
	users: Dict[str, User],
	vendors: Dict[str, User],
	slots: Dict[tuple[str, str], Slot],
	menu_items: Dict[str, MenuItem],
) -> Dict[str, Order]:
	order_lookup: Dict[str, Order] = {}
	slot_counts: Dict[int, int] = {}
	for payload in ORDER_FIXTURES:
		user = users[payload["user"]]
		vendor = vendors[payload["vendor"]]
		slot = slots[(payload["vendor"], payload["slot_label"])]
		created_at = NOW - timedelta(days=payload["days_ago"], hours=0)
		order = Order(
			user_id=user.id,
			vendor_id=vendor.id,
			slot_id=slot.id,
			status=payload["status"],
			created_at=created_at,
			qr_code=f"TNT-{payload['reference'][-3:]}-{uuid4().hex[:6].upper()}",
			pickup_confirmed_by=vendor.id if payload["status"] == OrderStatus.PICKED else None,
			eta_minutes=payload["eta_minutes"],
		)
		session.add(order)
		session.flush()
		total = 0
		for item in payload["items"]:
			menu_item = menu_items[item["menu_slug"]]
			line_total = menu_item.price * item["quantity"]
			order_item = OrderItem(
				order_id=order.id,
				menu_item_id=menu_item.id,
				quantity=item["quantity"],
				price_at_time=menu_item.price,
			)
			session.add(order_item)
			total += line_total
		order.total_amount = total
		slot_counts[slot.id] = slot_counts.get(slot.id, 0) + 1
		create_order_histories(session, order, payload["history"])
		create_payment(session, order, payload["payment"])
		order_lookup[payload["reference"]] = order
	for slot in slots.values():
		slot.current_orders = slot_counts.get(slot.id, 0)
		utilization = slot.current_orders / slot.max_orders if slot.max_orders else 0
		if utilization >= 1:
			slot.status = SlotStatus.FULL
		elif utilization >= 0.7:
			slot.status = SlotStatus.LIMITED
		else:
			slot.status = SlotStatus.AVAILABLE
	return order_lookup


def create_payment(session: Session, order: Order, payload: Dict[str, Any]) -> None:
	payment = Payment(
		order_id=order.id,
		amount=order.total_amount,
		status=payload["status"],
		idempotency_key=f"{payload['method']}-{uuid4().hex[:8]}",
		razorpay_order_id=f"order_{uuid4().hex[:10]}",
		razorpay_payment_id=f"pay_{uuid4().hex[:10]}" if payload["status"] in {PaymentStatus.SUCCESS, PaymentStatus.REFUNDED} else None,
		razorpay_signature="demo_signature",
	)
	if payload["status"] == PaymentStatus.REFUNDED:
		payment.razorpay_refund_id = f"rfnd_{uuid4().hex[:8]}"
	session.add(payment)
	if payload["status"] in {PaymentStatus.SUCCESS, PaymentStatus.REFUNDED}:
		ledger = Ledger(
			order_id=order.id,
			payment_id=payment.id,
			amount=order.total_amount,
			entry_type=LedgerType.CREDIT if payload["status"] == PaymentStatus.SUCCESS else LedgerType.DEBIT,
			source=LedgerSource.PAYMENT,
			description=f"{payload['method']} settlement",
		)
		session.add(ledger)


def seed_notifications(session: Session, users: Dict[str, User], orders: Dict[str, Order]) -> None:
	for payload in NOTIFICATION_FIXTURES:
		user = users[payload["user"]]
		base_time = NOW
		reference_id = None
		if payload["order_ref"]:
			order = orders[payload["order_ref"]]
			base_time = order.created_at
			reference_id = order.id
		created_at = base_time + timedelta(minutes=payload["minutes_after_order"])
		notification = Notification(
			user_id=user.id,
			title=payload["title"],
			message=payload["message"],
			notification_type=payload.get("notification_type", NotificationType.SYSTEM),
			reference_id=reference_id,
			is_read=payload.get("is_read", False),
			created_at=created_at,
		)
		session.add(notification)


def seed_ai_rows(session: Session, users: Dict[str, User], menu_items: Dict[str, MenuItem]) -> None:
	rows = []
	for payload in AI_FIXTURES:
		user = users[payload["user"]]
		popular = []
		for item in payload["popular"]:
			menu_item = menu_items[item["menu_slug"]]
			popular.append({"menu_item_id": menu_item.id, "name": menu_item.name, "order_count": item["order_count"]})
		recommended = []
		for item in payload["recommended"]:
			menu_item = menu_items[item["menu_slug"]]
			recommended.append({"menu_item_id": menu_item.id, "name": menu_item.name, "reason": item["reason"]})
		rows.append(
			{
				"user_id": user.id,
				"user_preferences": user.preferences or {},
				"popular_items": popular,
				"recommended_items": recommended,
				"insight": payload["insight"],
			}
		)
	session.execute(AI_RECOMMENDATIONS_TABLE.insert(), rows)


def seed_stationery_jobs(
	session: Session,
	users: Dict[str, User],
	vendors: Dict[str, User],
	services: Dict[str, StationeryService],
) -> None:
	for payload in STATIONERY_JOB_FIXTURES:
		user = users[payload["user"]]
		vendor = vendors[payload["vendor"]]
		service = services[payload["service"]]
		amount = service.price_per_unit * payload["quantity"]
		job = StationeryJob(
			user_id=user.id,
			vendor_id=vendor.id,
			service_id=service.id,
			quantity=payload["quantity"],
			file_url=f"https://cdn.tapntake.app/uploads/{payload['service']}.pdf",
			amount=amount,
			is_paid=payload["paid"],
			status=payload["status"],
			razorpay_order_id=f"job_{uuid4().hex[:8]}",
			razorpay_payment_id=f"pay_{uuid4().hex[:8]}" if payload["paid"] else None,
		)
		session.add(job)


def build_cart_payloads(
	users: Dict[str, User],
	vendors: Dict[str, User],
	menu_items: Dict[str, MenuItem],
) -> List[Dict[str, Any]]:
	carts: List[Dict[str, Any]] = []
	for payload in CART_FIXTURES:
		user = users[payload["user"]]
		vendor = vendors[payload["vendor"]]
		items = []
		for entry in payload["items"]:
			menu_item = menu_items[entry["menu_slug"]]
			items.append(
				{
					"menu_item_id": menu_item.id,
					"name": menu_item.name,
					"price": menu_item.price,
					"quantity": entry["quantity"],
				}
			)
		carts.append({"user_id": user.id, "vendor_id": vendor.id, "items": items})
	return carts


def seed_carts(carts: Sequence[Dict[str, Any]]) -> None:
	try:
		for cart in carts:
			payload = {"vendor_id": cart["vendor_id"], "items": cart["items"]}
			redis_client.setex(f"tnt:cart:user:{cart['user_id']}", 60 * 60 * 12, json.dumps(payload))
		LOGGER.info("Prepared %s carts in Redis", len(carts))
	except Exception as exc:
		LOGGER.warning("Skipping cart seeding (redis unavailable?): %s", exc)


def seed_feedback(session: Session, users: Dict[str, User], vendors: Dict[str, User], orders: Dict[str, Order]) -> None:
	for payload in FEEDBACK_FIXTURES:
		user = users[payload["user"]]
		vendor = vendors[payload["vendor"]]
		order = orders.get(payload["order_ref"])
		if not order:
			continue
		q = payload["quality_rating"]
		t = payload["time_rating"]
		b = payload["behavior_rating"]
		overall = round((q + t + b) / 3)
		feedback = Feedback(
			order_id=order.id,
			user_id=user.id,
			vendor_id=vendor.id,
			overall_rating=overall,
			quality_rating=q,
			time_rating=t,
			behavior_rating=b,
			comment=payload.get("comment"),
			created_at=NOW - timedelta(days=payload.get("days_offset", 0)),
		)
		session.add(feedback)


def seed_vendor_reviews(session: Session, users: Dict[str, User], vendors: Dict[str, User], orders: Dict[str, Order]) -> None:
	for payload in VENDOR_REVIEW_FIXTURES:
		user = users[payload["user"]]
		vendor = vendors[payload["vendor"]]
		order_id = None
		if payload.get("order_ref"):
			order = orders.get(payload["order_ref"])
			if order:
				order_id = order.id
		review = VendorReview(
			vendor_id=vendor.id,
			user_id=user.id,
			order_id=order_id,
			rating=payload["rating"],
			title=payload.get("title"),
			review_text=payload.get("review_text"),
			is_anonymous=payload.get("is_anonymous", False),
			created_at=NOW - timedelta(days=payload.get("days_offset", 0)),
		)
		session.add(review)


REWARD_TRANSACTION_FIXTURES: Sequence[Dict[str, Any]] = (
	# Naina: frequent user, lots of points
	{"user": "naina", "reward_type": RewardType.ORDER_COMPLETION, "points": 125.0, "description": "Earned 125 points for order completion", "order_ref": "ORD-NAINA-001", "days_offset": 0},
	{"user": "naina", "reward_type": RewardType.OFF_PEAK_BONUS, "points": 15.0, "description": "Off-peak bonus for order #1", "order_ref": "ORD-NAINA-001", "days_offset": 0},
	{"user": "naina", "reward_type": RewardType.ORDER_COMPLETION, "points": 189.0, "description": "Earned 189 points for order completion", "order_ref": "ORD-NAINA-002", "days_offset": 0},
	{"user": "naina", "reward_type": RewardType.ORDER_COMPLETION, "points": 229.0, "description": "Earned 229 points for order completion", "order_ref": "ORD-NAINA-003", "days_offset": 0},
	{"user": "naina", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-NAINA-001", "days_offset": 0},
	{"user": "naina", "reward_type": RewardType.LOYALTY_MILESTONE, "points": 100.0, "description": "Loyalty milestone: 5th order!", "days_offset": 1},
	{"user": "naina", "reward_type": RewardType.REFERRAL, "points": 25.0, "description": "Referral bonus — Sneha joined!", "days_offset": 2},
	{"user": "naina", "reward_type": RewardType.ORDER_COMPLETION, "points": 159.0, "description": "Earned 159 points for order completion", "order_ref": "ORD-NAINA-004", "days_offset": 0},
	# Rahul: regular user
	{"user": "rahul", "reward_type": RewardType.ORDER_COMPLETION, "points": 199.0, "description": "Earned 199 points for order completion", "order_ref": "ORD-RAHUL-001", "days_offset": 0},
	{"user": "rahul", "reward_type": RewardType.OFF_PEAK_BONUS, "points": 15.0, "description": "Off-peak bonus for order", "order_ref": "ORD-RAHUL-001", "days_offset": 0},
	{"user": "rahul", "reward_type": RewardType.ORDER_COMPLETION, "points": 129.0, "description": "Earned 129 points for order completion", "order_ref": "ORD-RAHUL-002", "days_offset": 0},
	{"user": "rahul", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-RAHUL-001", "days_offset": 0},
	{"user": "rahul", "reward_type": RewardType.ORDER_COMPLETION, "points": 99.0, "description": "Earned 99 points for order completion", "order_ref": "ORD-RAHUL-003", "days_offset": 0},
	# Ananya: health-focused
	{"user": "ananya", "reward_type": RewardType.ORDER_COMPLETION, "points": 219.0, "description": "Earned 219 points for order completion", "order_ref": "ORD-ANANYA-001", "days_offset": 0},
	{"user": "ananya", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-ANANYA-001", "days_offset": 0},
	{"user": "ananya", "reward_type": RewardType.ORDER_COMPLETION, "points": 229.0, "description": "Earned 229 points for order completion", "order_ref": "ORD-ANANYA-002", "days_offset": 0},
	# Kabir: pizza lover
	{"user": "kabir", "reward_type": RewardType.ORDER_COMPLETION, "points": 309.0, "description": "Earned 309 points for order completion", "order_ref": "ORD-KABIR-001", "days_offset": 0},
	{"user": "kabir", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-KABIR-001", "days_offset": 0},
	{"user": "kabir", "reward_type": RewardType.ORDER_COMPLETION, "points": 199.0, "description": "Earned 199 points for order completion", "order_ref": "ORD-KABIR-002", "days_offset": 0},
	# Meera: sweet tooth
	{"user": "meera", "reward_type": RewardType.ORDER_COMPLETION, "points": 109.0, "description": "Earned 109 points for order completion", "order_ref": "ORD-MEERA-001", "days_offset": 0},
	{"user": "meera", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-MEERA-001", "days_offset": 0},
	# Arjun: faculty
	{"user": "arjun", "reward_type": RewardType.ORDER_COMPLETION, "points": 129.0, "description": "Earned 129 points for order completion", "order_ref": "ORD-ARJUN-001", "days_offset": 0},
	{"user": "arjun", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-ARJUN-001", "days_offset": 0},
	{"user": "arjun", "reward_type": RewardType.OFF_PEAK_BONUS, "points": 15.0, "description": "Off-peak bonus — early breakfast slot!", "order_ref": "ORD-ARJUN-001", "days_offset": 0},
	# Dev: cancelled order, still has some points
	{"user": "dev", "reward_type": RewardType.ORDER_COMPLETION, "points": 139.0, "description": "Earned 139 points for order completion", "order_ref": "ORD-DEV-002", "days_offset": 0},
	{"user": "dev", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-DEV-002", "days_offset": 0},
	# Sneha: gluten-free explorer
	{"user": "sneha", "reward_type": RewardType.ORDER_COMPLETION, "points": 199.0, "description": "Earned 199 points for order completion", "order_ref": "ORD-SNEHA-001", "days_offset": 0},
	{"user": "sneha", "reward_type": RewardType.FIRST_ORDER, "points": 50.0, "description": "Welcome bonus — first order completed!", "order_ref": "ORD-SNEHA-001", "days_offset": 0},
	{"user": "sneha", "reward_type": RewardType.REFERRAL, "points": 25.0, "description": "Referral bonus — Kabir joined!", "days_offset": 1},
)

REWARD_REDEMPTION_FIXTURES: Sequence[Dict[str, Any]] = (
	# Naina redeemed some points
	{"user": "naina", "redemption_type": RedemptionType.DISCOUNT_PERCENTAGE, "points_used": 50.0, "value": 10.0, "description": "Redeemed 50 points for 10% discount", "days_offset": 0},
	{"user": "naina", "redemption_type": RedemptionType.DISCOUNT_FIXED, "points_used": 100.0, "value": 25.0, "description": "Redeemed 100 points for Rs 25 off", "days_offset": 1},
	# Rahul redeemed once
	{"user": "rahul", "redemption_type": RedemptionType.DISCOUNT_PERCENTAGE, "points_used": 50.0, "value": 5.0, "description": "Redeemed 50 points for 5% discount", "days_offset": 0},
	# Kabir redeemed for free item
	{"user": "kabir", "redemption_type": RedemptionType.FREE_ITEM, "points_used": 200.0, "value": 99.0, "description": "Redeemed 200 points for free garlic breadsticks", "days_offset": 2},
)

VOUCHER_FIXTURES: Sequence[Dict[str, Any]] = (
	{"code": "WELCOME10", "description": "Welcome discount — 10% off first order!", "discount_type": VoucherDiscountType.PERCENTAGE, "discount_value": 10.0, "min_order_amount_paise": 5000, "max_discount_amount_paise": 2000, "usage_limit": 100, "days_until_expiry": 30},
	{"code": "SAVE25", "description": "Flat Rs 25 off on orders above Rs 50", "discount_type": VoucherDiscountType.FIXED, "discount_value": 2500, "min_order_amount_paise": 5000, "usage_limit": 50, "days_until_expiry": 15},
	{"code": "CAMPUS20", "description": "20% off for campus foodies!", "discount_type": VoucherDiscountType.PERCENTAGE, "discount_value": 20.0, "min_order_amount_paise": 10000, "max_discount_amount_paise": 5000, "usage_limit": 30, "days_until_expiry": 20},
	{"code": "LUNCH15", "description": "Rs 15 off lunch orders", "discount_type": VoucherDiscountType.FIXED, "discount_value": 1500, "min_order_amount_paise": 3000, "usage_limit": 200, "days_until_expiry": 60},
	{"code": "FIRST50", "description": "50% off first stationery order (max Rs 100)", "discount_type": VoucherDiscountType.PERCENTAGE, "discount_value": 50.0, "min_order_amount_paise": 2000, "max_discount_amount_paise": 10000, "usage_limit": 25, "days_until_expiry": 45},
)


def seed_rewards(session: Session, users: Dict[str, User], orders: Dict[str, Order], admin_user: User) -> None:
	# Initialize default reward rules
	for rt, ppr, fp in [
		(RewardType.ORDER_COMPLETION, 5.0, None),
		(RewardType.FIRST_ORDER, 1.0, 50.0),
		(RewardType.REFERRAL, 1.0, 25.0),
		(RewardType.LOYALTY_MILESTONE, 1.0, 100.0),
		(RewardType.OFF_PEAK_BONUS, 1.0, 15.0),
		(RewardType.VOUCHER_REDEMPTION, 0.0, 0.0),
	]:
		existing = session.query(RewardRule).filter(RewardRule.reward_type == rt).first()
		if not existing:
			session.add(RewardRule(reward_type=rt, points_per_rupee=ppr, fixed_points=fp, is_active=1))

	for rt, mp, mdp, mda in [
		(RedemptionType.DISCOUNT_PERCENTAGE, 50.0, 20.0, None),
		(RedemptionType.DISCOUNT_FIXED, 100.0, None, 50.0),
		(RedemptionType.FREE_ITEM, 200.0, None, None),
	]:
		existing = session.query(RedemptionRule).filter(RedemptionRule.redemption_type == rt).first()
		if not existing:
			session.add(RedemptionRule(redemption_type=rt, min_points=mp, max_discount_percentage=mdp, max_discount_amount=mda, is_active=1))

	# Seed reward points balances
	for slug, user in users.items():
		rp = RewardPoints(user_id=user.id, points=0.0, total_earned=0.0, total_redeemed=0.0)
		session.add(rp)
	session.flush()

	# Seed transactions
	for payload in REWARD_TRANSACTION_FIXTURES:
		user = users[payload["user"]]
		order = orders.get(payload.get("order_ref", ""))
		rp = session.query(RewardPoints).filter(RewardPoints.user_id == user.id).first()
		if rp:
			rp.points += payload["points"]
			rp.total_earned += payload["points"]
		session.add(RewardTransaction(
			user_id=user.id,
			reward_type=payload["reward_type"],
			points=payload["points"],
			description=payload["description"],
			order_id=order.id if order else None,
			created_at=NOW - timedelta(days=payload.get("days_offset", 0)),
		))

	# Seed redemptions (deduct from balance)
	for payload in REWARD_REDEMPTION_FIXTURES:
		user = users[payload["user"]]
		rp = session.query(RewardPoints).filter(RewardPoints.user_id == user.id).first()
		if rp:
			rp.points = max(0, rp.points - payload["points_used"])
			rp.total_redeemed += payload["points_used"]
		session.add(RewardRedemption(
			user_id=user.id,
			redemption_type=payload["redemption_type"],
			points_used=payload["points_used"],
			value=payload["value"],
			description=payload["description"],
			created_at=NOW - timedelta(days=payload.get("days_offset", 0)),
		))

	# Seed vouchers
	for payload in VOUCHER_FIXTURES:
		session.add(Voucher(
			code=payload["code"],
			description=payload["description"],
			discount_type=payload["discount_type"],
			discount_value=payload["discount_value"],
			min_order_amount_paise=payload["min_order_amount_paise"],
			max_discount_amount_paise=payload.get("max_discount_amount_paise"),
			usage_limit=payload.get("usage_limit"),
			times_redeemed=0,
			expires_at=NOW + timedelta(days=payload["days_until_expiry"]),
			is_active=1,
			created_by_user_id=admin_user.id,
		))

	# Seed off-peak policy
	policy = OffPeakRewardPolicy(
		enabled=1,
		start_hour=15,
		end_hour=17,
		bonus_points_per_order=15.0,
		updated_by_user_id=admin_user.id,
	)
	session.add(policy)


def seed_database(session: Session) -> Dict[str, Any]:
	students = seed_students(session)
	vendors = seed_vendors(session, FOOD_VENDOR_FIXTURES + STATIONERY_VENDOR_FIXTURES)
	menu_items = seed_menu(session, vendors)
	stationery_services = seed_stationery(session, vendors)
	slots = seed_slots(session, vendors)
	orders = seed_orders(session, students, vendors, slots, menu_items)
	seed_notifications(session, students, orders)
	seed_feedback(session, students, vendors, orders)
	seed_vendor_reviews(session, students, vendors, orders)
	admin_user = User(phone="8800000099", name="System Admin", role=UserRole.ADMIN, is_active=True, is_approved=True)
	session.add(admin_user)
	session.flush()
	seed_rewards(session, students, orders, admin_user)
	seed_ai_rows(session, students, menu_items)
	seed_stationery_jobs(session, students, vendors, stationery_services)
	carts = build_cart_payloads(students, vendors, menu_items)
	return {
		"users": students,
		"vendors": vendors,
		"menu_items": menu_items,
		"orders": orders,
		"carts": carts,
	}


def run_seed(fresh: bool) -> None:
	maybe_reset_database(fresh)
	ensure_extra_tables(reset=fresh)
	with SessionLocal() as session:
		purge_existing_data(session)
		dataset = seed_database(session)
		session.commit()
	seed_carts(dataset["carts"])
	LOGGER.info(
		"Seeded %s users, %s vendors, %s menu items, %s orders",
		len(dataset["users"]),
		len(dataset["vendors"]),
		len(dataset["menu_items"]),
		len(dataset["orders"]),
	)


def main() -> None:
	parser = argparse.ArgumentParser(description="Seed the TNT development database")
	parser.add_argument("--fresh", action="store_true", help="Drop/recreate the database before seeding")
	args = parser.parse_args()

	logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

	run_seed(fresh=args.fresh)


if __name__ == "__main__":
	main()

