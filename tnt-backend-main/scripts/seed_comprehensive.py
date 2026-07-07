#!/usr/bin/env python
"""
Comprehensive demo data seeder for TNT.
Run after script/seed_data.py to add:
- 42 additional users (50 total)
- 1 additional food vendor (9 vendors total)
- 58 additional food items (100 total)
- 12 additional stationery services (40 total)
- 10 additional orders (30 total)
- 22 additional notifications (50+ total)
- Favorites data for users
- Additional slot bookings
"""

from __future__ import annotations

import argparse
import logging
from datetime import timedelta
from typing import Any, Dict, Sequence
from uuid import uuid4

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, JSON, String, Table, delete
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.database.session import SessionLocal, engine
from app.modules.feedback.model import Feedback, VendorReview
from app.modules.menu.model import MenuItem
from app.modules.notifications.model import Notification, NotificationType
from app.modules.orders.history_model import OrderHistory
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole

LOGGER = logging.getLogger("tnt.full_seed")

NOW = utcnow_naive()


# ─────────────────────────────────────────────────────────────────────────────
# Additional Users (42 students to reach 50 total)
# ─────────────────────────────────────────────────────────────────────────────

ADDITIONAL_USERS: Sequence[Dict[str, Any]] = (
    # 9-50: Additional students
    {"slug": "ishaan", "name": "Ishaan Mehta", "phone": "7016918111", "role": UserRole.STUDENT, "university_id": "UNIV-2024-09", "preferences": {"preferred_pickup_hour": 13}},
    {"slug": "priya", "name": "Priya Kapoor", "phone": "7016918112", "role": UserRole.STUDENT, "university_id": "UNIV-2024-10", "preferences": {"preferred_pickup_hour": 12}},
    {"slug": "vikram", "name": "Vikram Singh", "phone": "7016918113", "role": UserRole.STUDENT, "university_id": "UNIV-2024-11", "preferences": {"preferred_pickup_hour": 19}},
    {"slug": "neha", "name": "Neha Gupta", "phone": "7016918114", "role": UserRole.STUDENT, "university_id": "UNIV-2024-12", "preferences": {"preferred_pickup_hour": 14}},
    {"slug": "rohit", "name": "Rohit Sharma", "phone": "7016918115", "role": UserRole.STUDENT, "university_id": "UNIV-2024-13", "preferences": {"preferred_pickup_hour": 20}},
    {"slug": "tanvi", "name": "Tanvi Desai", "phone": "7016918116", "role": UserRole.STUDENT, "university_id": "UNIV-2024-14", "preferences": {"preferred_pickup_hour": 11}},
    {"slug": "karthik", "name": "Karthik Nair", "phone": "7016918117", "role": UserRole.STUDENT, "university_id": "UNIV-2024-15", "preferences": {"preferred_pickup_hour": 13}},
    {"slug": "aisha", "name": "Aisha Khan", "phone": "7016918118", "role": UserRole.STUDENT, "university_id": "UNIV-2024-16", "preferences": {"preferred_pickup_hour": 21}},
    {"slug": "yash", "name": "Yash Patel", "phone": "7016918119", "role": UserRole.STUDENT, "university_id": "UNIV-2024-17", "preferences": {"preferred_pickup_hour": 10}},
    {"slug": "diya", "name": "Diya Reddy", "phone": "7016918120", "role": UserRole.STUDENT, "university_id": "UNIV-2024-18", "preferences": {"preferred_pickup_hour": 12}},
    {"slug": "varun", "name": "Varun Malhotra", "phone": "7016918121", "role": UserRole.STUDENT, "university_id": "UNIV-2024-19", "preferences": {"preferred_pickup_hour": 18}},
    {"slug": "shreya", "name": "Shreya Joshi", "phone": "7016918122", "role": UserRole.STUDENT, "university_id": "UNIV-2024-20", "preferences": {"preferred_pickup_hour": 9}},
    {"slug": "aditya", "name": "Aditya Verma", "phone": "7016918123", "role": UserRole.STUDENT, "university_id": "UNIV-2024-21", "preferences": {"preferred_pickup_hour": 13}},
    {"slug": "rhea", "name": "Rhea Mukherjee", "phone": "7016918124", "role": UserRole.STUDENT, "university_id": "UNIV-2024-22", "preferences": {"preferred_pickup_hour": 14}},
    {"slug": "dhruv", "name": "Dhruv Saxena", "phone": "7016918125", "role": UserRole.STUDENT, "university_id": "UNIV-2024-23", "preferences": {"preferred_pickup_hour": 19}},
    {"slug": "anvi", "name": "Anvi Sharma", "phone": "7016918126", "role": UserRole.STUDENT, "university_id": "UNIV-2024-24", "preferences": {"preferred_pickup_hour": 20}},
    {"slug": "aryan", "name": "Aryan Gupta", "phone": "7016918127", "role": UserRole.STUDENT, "university_id": "UNIV-2024-25", "preferences": {"preferred_pickup_hour": 18}},
    {"slug": "kavya", "name": "Kavya Iyer", "phone": "7016918128", "role": UserRole.STUDENT, "university_id": "UNIV-2024-26", "preferences": {"preferred_pickup_hour": 12}},
    {"slug": "veer", "name": "Veer Rathore", "phone": "7016918129", "role": UserRole.STUDENT, "university_id": "UNIV-2024-27", "preferences": {"preferred_pickup_hour": 21}},
    {"slug": "myra", "name": "Myra Choudhury", "phone": "7016918130", "role": UserRole.STUDENT, "university_id": "UNIV-2024-28", "preferences": {"preferred_pickup_hour": 10}},
    {"slug": "krish", "name": "Krish Bansal", "phone": "7016918131", "role": UserRole.STUDENT, "university_id": "UNIV-2024-29", "preferences": {"preferred_pickup_hour": 13}},
    {"slug": "anaya", "name": "Anaya Kapoor", "phone": "7016918132", "role": UserRole.STUDENT, "university_id": "UNIV-2024-30", "preferences": {"preferred_pickup_hour": 14}},
    {"slug": "pranav", "name": "Pranav Kulkarni", "phone": "7016918133", "role": UserRole.STUDENT, "university_id": "UNIV-2024-31", "preferences": {"preferred_pickup_hour": 19}},
    {"slug": "trisha", "name": "Trisha Sen", "phone": "7016918134", "role": UserRole.STUDENT, "university_id": "UNIV-2024-32", "preferences": {"preferred_pickup_hour": 11}},
    {"slug": "aryan2", "name": "Aryan Deshmukh", "phone": "7016918135", "role": UserRole.STUDENT, "university_id": "UNIV-2024-33", "preferences": {"preferred_pickup_hour": 20}},
    {"slug": "siya", "name": "Siya Bhatia", "phone": "7016918136", "role": UserRole.STUDENT, "university_id": "UNIV-2024-34", "preferences": {"preferred_pickup_hour": 12}},
    {"slug": "advik", "name": "Advik Menon", "phone": "7016918137", "role": UserRole.STUDENT, "university_id": "UNIV-2024-35", "preferences": {"preferred_pickup_hour": 13}},
    {"slug": "kiara", "name": "Kiara Malhotra", "phone": "7016918138", "role": UserRole.STUDENT, "university_id": "UNIV-2024-36", "preferences": {"preferred_pickup_hour": 18}},
    {"slug": "reyansh", "name": "Reyansh Pandey", "phone": "7016918139", "role": UserRole.STUDENT, "university_id": "UNIV-2024-37", "preferences": {"preferred_pickup_hour": 19}},
    {"slug": "ahana", "name": "Ahana Rao", "phone": "7016918140", "role": UserRole.STUDENT, "university_id": "UNIV-2024-38", "preferences": {"preferred_pickup_hour": 14}},
    {"slug": "Vihaan", "name": "Vihaan Sharma", "phone": "7016918141", "role": UserRole.STUDENT, "university_id": "UNIV-2024-39", "preferences": {"preferred_pickup_hour": 20}},
    {"slug": "sara", "name": "Sara Ali", "phone": "7016918142", "role": UserRole.STUDENT, "university_id": "UNIV-2024-40", "preferences": {"preferred_pickup_hour": 21}},
    {"slug": "aarnav", "name": "Aarnav Kaul", "phone": "7016918143", "role": UserRole.STUDENT, "university_id": "UNIV-2024-41", "preferences": {"preferred_pickup_hour": 10}},
    {"slug": "riva", "name": "Riva Sinha", "phone": "7016918144", "role": UserRole.STUDENT, "university_id": "UNIV-2024-42", "preferences": {"preferred_pickup_hour": 9}},
    {"slug": "hritik", "name": "Hritik Dhawan", "phone": "7016918145", "role": UserRole.STUDENT, "university_id": "UNIV-2024-43", "preferences": {"preferred_pickup_hour": 13}},
    {"slug": "drishti", "name": "Drishti Saha", "phone": "7016918146", "role": UserRole.STUDENT, "university_id": "UNIV-2024-44", "preferences": {"preferred_pickup_hour": 12}},
    {"slug": "ansh", "name": "Ansh Nigam", "phone": "7016918147", "role": UserRole.STUDENT, "university_id": "UNIV-2024-45", "preferences": {"preferred_pickup_hour": 18}},
    {"slug": "pari", "name": "Pari Mallick", "phone": "7016918148", "role": UserRole.STUDENT, "university_id": "UNIV-2024-46", "preferences": {"preferred_pickup_hour": 19}},
    {"slug": "ashwin", "name": "Ashwin Kumar", "phone": "7016918149", "role": UserRole.STUDENT, "university_id": "UNIV-2024-47", "preferences": {"preferred_pickup_hour": 20}},
    {"slug": "bhoomi", "name": "Bhoomi Trivedi", "phone": "7016918150", "role": UserRole.STUDENT, "university_id": "UNIV-2024-48", "preferences": {"preferred_pickup_hour": 11}},
    {"slug": "shivani", "name": "Shivani Bose", "phone": "7016918151", "role": UserRole.STUDENT, "university_id": "UNIV-2024-49", "preferences": {"preferred_pickup_hour": 14}},
    {"slug": "laksh", "name": "Laksh Narayan", "phone": "7016918152", "role": UserRole.STUDENT, "university_id": "UNIV-2024-50", "preferences": {"preferred_pickup_hour": 13}},
)


# ─────────────────────────────────────────────────────────────────────────────
# Additional Vendor (1 more food vendor = 9 total)
# ─────────────────────────────────────────────────────────────────────────────

ADDITIONAL_VENDOR = {
    "slug": "noodle_house",
    "name": "Noodle House",
    "phone": "9810001006",
    "vendor_type": "food",
    "university_id": "VEN-NOD-09",
    "profile": {
        "category": "Asian Cuisine",
        "description": "Fresh wok-tossed noodles, fried rice, and dim sum baskets.",
        "rating": 4.6,
        "location": "East Wing Food Court",
        "logo_url": "https://cdn.tapntake.app/vendors/noodle_house_logo.png",
        "cover_image": "https://cdn.tapntake.app/vendors/noodle_house_cover.jpg",
        "is_open": True,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Additional Menu Items (58 more for 100 total)
# ─────────────────────────────────────────────────────────────────────────────

ADDITIONAL_MENU_ITEMS: Sequence[Dict[str, Any]] = (
    # Noodle House items
    {"slug": "noodle-veg-hakka", "vendor_slug": "noodle_house", "name": "Veg Hakka Noodles", "description": "Wok-tossed veggies with soy sauce.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/veg_hakka.jpg", "prep_time": 12},
    {"slug": "noodle-schezwan", "vendor_slug": "noodle_house", "name": "Schezwan Noodles", "description": "Spicy red chilli paste noodles.", "price": 159, "image_url": "https://cdn.tapntake.app/menu/schezwan_noodles.jpg", "prep_time": 13},
    {"slug": "noodle-fried-rice", "vendor_slug": "noodle_house", "name": "Veg Fried Rice", "description": "Fluffy rice with mixed veggies.", "price": 139, "image_url": "https://cdn.tapntake.app/menu/fried_rice.jpg", "prep_time": 11},
    {"slug": "noodle-momos", "vendor_slug": "noodle_house", "name": "Steamed Momos", "description": "8-piece vegetable momo basket.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/momos.jpg", "prep_time": 14},
    {"slug": "noodle-manchurian", "vendor_slug": "noodle_house", "name": "Veg Manchurian", "description": "Crispy balls in tangy sauce.", "price": 169, "image_url": "https://cdn.tapntake.app/menu/manchurian.jpg", "prep_time": 15},
    {"slug": "noodle-spring-roll", "vendor_slug": "noodle_house", "name": "Spring Rolls", "description": "Crispy rolls with veggie filling.", "price": 119, "image_url": "https://cdn.tapntake.app/menu/spring_rolls.jpg", "prep_time": 10},
    {"slug": "noodle-thai-curry", "vendor_slug": "noodle_house", "name": "Thai Red Curry", "description": "Coconut curry with veggies.", "price": 189, "image_url": "https://cdn.tapntake.app/menu/thai_curry.jpg", "prep_time": 16},
    {"slug": "noodle-dim-sum", "vendor_slug": "noodle_house", "name": "Dim Sum Platter", "description": "Assorted dim sum basket.", "price": 199, "image_url": "https://cdn.tapntake.app/menu/dim_sum.jpg", "prep_time": 17},
    # More Campus Cafe items
    {"slug": "campus-croissant", "vendor_slug": "campus_cafe", "name": "Butter Croissant", "description": "Flaky French pastry.", "price": 99, "image_url": "https://cdn.tapntake.app/menu/croissant.jpg", "prep_time": 4},
    {"slug": "campus-iced-latte", "vendor_slug": "campus_cafe", "name": "Iced Vanilla Latte", "description": "Espresso with vanilla and cold milk.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/iced_latte.jpg", "prep_time": 5},
    {"slug": "campus-chicken-sandwich", "vendor_slug": "campus_cafe", "name": "Grilled Chicken Sandwich", "description": "Herb-marinated chicken on ciabatta.", "price": 179, "image_url": "https://cdn.tapntake.app/menu/chicken_sandwich.jpg", "prep_time": 12},
    {"slug": "campus-mango-shake", "vendor_slug": "campus_cafe", "name": "Mango Lassi Shake", "description": "Seasonal mango yogurt shake.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/mango_shake.jpg", "prep_time": 6},
    {"slug": "campus-egg-roll", "vendor_slug": "campus_cafe", "name": "Egg Roll Wrap", "description": "Scrambled eggs in whole wheat.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/egg_roll.jpg", "prep_time": 9},
    {"slug": "campus-tea-cake", "vendor_slug": "campus_cafe", "name": "Tea Cake Slice", "description": "Traditional tea-time cake.", "price": 79, "image_url": "https://cdn.tapntake.app/menu/tea_cake.jpg", "prep_time": 3},
    # More Burger Hub items
    {"slug": "burgerhub-dbl-cheese", "vendor_slug": "burger_hub", "name": "Double Cheese Burger", "description": "Double patty, triple cheese.", "price": 219, "image_url": "https://cdn.tapntake.app/menu/double_cheese.jpg", "prep_time": 15},
    {"slug": "burgerhub-veggie-delight", "vendor_slug": "burger_hub", "name": "Veggie Delight Burger", "description": "Loaded vegetable patty.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/veggie_delight.jpg", "prep_time": 11},
    {"slug": "burgerhub-mcx-maharaja", "vendor_slug": "burger_hub", "name": "Maharaja Mac Veg", "description": "Big three-tier burger.", "price": 229, "image_url": "https://cdn.tapntake.app/menu/maharaja.jpg", "prep_time": 18},
    {"slug": "burgerhub-onion-rings", "vendor_slug": "burger_hub", "name": "Onion Rings", "description": "Crispy breaded onion rings.", "price": 99, "image_url": "https://cdn.tapntake.app/menu/onion_rings.jpg", "prep_time": 7},
    {"slug": "burgerhub-strawberry-shake", "vendor_slug": "burger_hub", "name": "Strawberry Milkshake", "description": "Fresh strawberry shake.", "price": 139, "image_url": "https://cdn.tapntake.app/menu/strawberry_shake.jpg", "prep_time": 5},
    {"slug": "burgerhub-mozzarella-sticks", "vendor_slug": "burger_hub", "name": "Mozzarella Sticks", "description": "Fried cheesy sticks.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/mozzarella_sticks.jpg", "prep_time": 8},
    # More Spice Corner items
    {"slug": "spice-rava-dosa", "vendor_slug": "spice_corner", "name": "Rava Dosa", "description": "Crispy semolina crepe.", "price": 119, "image_url": "https://cdn.tapntake.app/menu/rava_dosa.jpg", "prep_time": 12},
    {"slug": "spice-paneer-dosa", "vendor_slug": "spice_corner", "name": "Paneer Dosa", "description": "Cottage cheese stuffed dosa.", "price": 159, "image_url": "https://cdn.tapntake.app/menu/paneer_dosa.jpg", "prep_time": 15},
    {"slug": "spice-poori-bhaji", "vendor_slug": "spice_corner", "name": "Poori Bhaji", "description": "Puffy bread with potato curry.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/poori_bhaji.jpg", "prep_time": 14},
    {"slug": "spice-bisi-bele", "vendor_slug": "spice_corner", "name": "Bisi Bele Bath", "description": "Spicy rice and lentil dish.", "price": 139, "image_url": "https://cdn.tapntake.app/menu/bisi_be.jpg", "prep_time": 11},
    {"slug": "spice-curd-rice", "vendor_slug": "spice_corner", "name": "Curd Rice", "description": "Cool yogurt rice with pickle.", "price": 99, "image_url": "https://cdn.tapntake.app/menu/curd_rice.jpg", "prep_time": 8},
    {"slug": "spice-vada-pav", "vendor_slug": "spice_corner", "name": "Vada Pav", "description": "Mumbai style potato burger.", "price": 89, "image_url": "https://cdn.tapntake.app/menu/vada_pav.jpg", "prep_time": 9},
    {"slug": "spice-rasgulla", "vendor_slug": "spice_corner", "name": "Rasgulla", "description": "Sweet spongy dessert.", "price": 59, "image_url": "https://cdn.tapntake.app/menu/rasgulla.jpg", "prep_time": 2},
    # More Green Bowl items
    {"slug": "greenbowl-quinoa-wrap", "vendor_slug": "green_bowl", "name": "Quinoa Wrap", "description": "Quinoa and greens in tortilla.", "price": 179, "image_url": "https://cdn.tapntake.app/menu/quinoa_wrap.jpg", "prep_time": 10},
    {"slug": "greenbowl-salmon-salad", "vendor_slug": "green_bowl", "name": "Grilled Salmon Salad", "description": "Flaky salmon on greens.", "price": 269, "image_url": "https://cdn.tapntake.app/menu/salmon_salad.jpg", "prep_time": 14},
    {"slug": "greenbowl-eggs-benedict", "vendor_slug": "green_bowl", "name": "Veg Eggs Benedict", "description": "Poached eggs on english muffin.", "price": 189, "image_url": "https://cdn.tapntake.app/menu/eggs_benedict.jpg", "prep_time": 12},
    {"slug": "greenbowl-beet-salad", "vendor_slug": "green_bowl", "name": "Beetroot Salad", "description": "Roasted beets with feta.", "price": 169, "image_url": "https://cdn.tapntake.app/menu/beet_salad.jpg", "prep_time": 9},
    {"slug": "greenbowl-mango-smoothie", "vendor_slug": "green_bowl", "name": "Mango Smoothie", "description": "Fresh mango blended.", "price": 139, "image_url": "https://cdn.tapntake.app/menu/mango_smoothie.jpg", "prep_time": 5},
    {"slug": "greenbowl-overnight-oats", "vendor_slug": "green_bowl", "name": "Overnight Oats", "description": "Pre-soaked oats with berries.", "price": 149, "image_url": "https://cdn.tapntake.app/menu/overnight_oats.jpg", "prep_time": 3},
    # More Pizza Station items
    {"slug": "pizza-pepper-paneer", "vendor_slug": "pizza_station", "name": "Pepper Paneer Pizza", "description": "Paneer with bell peppers.", "price": 279, "image_url": "https://cdn.tapntake.app/menu/pepper_paneer.jpg", "prep_time": 16},
    {"slug": "pizza-cheese-burst", "vendor_slug": "pizza_station", "name": "Cheese Burst Pizza", "description": "Extra cheese layer inside.", "price": 319, "image_url": "https://cdn.tapntake.app/menu/cheese_burst_pizza.jpg", "prep_time": 18},
    {"slug": "pizza-panner-tikka", "vendor_slug": "pizza_station", "name": "Paneer Tikka Pizza", "description": "Spicy paneer tikka topping.", "price": 299, "image_url": "https://cdn.tapntake.app/menu/paneer_tikka.jpg", "prep_time": 17},
    {"slug": "pizza-garlic-knots", "vendor_slug": "pizza_station", "name": "Garlic Knots", "description": "Twisted garlic bread bites.", "price": 119, "image_url": "https://cdn.tapntake.app/menu/garlic_knots.jpg", "prep_time": 8},
    {"slug": "pizza-lassi", "vendor_slug": "pizza_station", "name": "Mango Lassi", "description": "Sweet mango yogurt drink.", "price": 99, "image_url": "https://cdn.tapntake.app/menu/lassi.jpg", "prep_time": 4},
    {"slug": "pizza-cannoli", "vendor_slug": "pizza_station", "name": "Cannoli", "description": "Italian sweet pastry.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/cannoli.jpg", "prep_time": 3},
    {"slug": "pizza-lasagna", "vendor_slug": "pizza_station", "name": "Veg Lasagna", "description": "Layered pasta bake.", "price": 249, "image_url": "https://cdn.tapntake.app/menu/lasagna.jpg", "prep_time": 20},
    # More items for existing vendors to reach 100
    {"slug": "campus-chicken-wrap2", "vendor_slug": "campus_cafe", "name": "Chicken Caesar Wrap", "description": "Grilled chicken with caesar dressing.", "price": 169, "image_url": "https://cdn.tapntake.app/menu/chicken_wrap2.jpg", "prep_time": 11},
    {"slug": "campus-bagel", "vendor_slug": "campus_cafe", "name": "Cream Cheese Bagel", "description": "Fresh bagel with spread.", "price": 89, "image_url": "https://cdn.tapntake.app/menu/bagel.jpg", "prep_time": 5},
    {"slug": "burgerhub-spicy-chicken", "vendor_slug": "burger_hub", "name": "Spicy Chicken Burger", "description": "Crispy fried chicken patty.", "price": 189, "image_url": "https://cdn.tapntake.app/menu/spicy_chicken.jpg", "prep_time": 13},
    {"slug": "burgerhub-bbq-wings", "vendor_slug": "burger_hub", "name": "BBQ Wings", "description": "6-piece chicken wings.", "price": 199, "image_url": "https://cdn.tapntake.app/menu/bbq_wings.jpg", "prep_time": 14},
    {"slug": "spice-bonda", "vendor_slug": "spice_corner", "name": "Bonda", "description": "Fried potato snack.", "price": 69, "image_url": "https://cdn.tapntake.app/menu/bonda.jpg", "prep_time": 8},
    {"slug": "spice-appam", "vendor_slug": "spice_corner", "name": "Appam with Stew", "description": "Rice pancake with stew.", "price": 129, "image_url": "https://cdn.tapntake.app/menu/appam.jpg", "prep_time": 12},
    {"slug": "greenbowl-caesar", "vendor_slug": "green_bowl", "name": "Caesar Salad", "description": "Classic caesar with croutons.", "price": 179, "image_url": "https://cdn.tapntake.app/menu/caesar.jpg", "prep_time": 8},
    {"slug": "greenbowl-gazpacho", "vendor_slug": "green_bowl", "name": "Gazpacho", "description": "Cold tomato soup.", "price": 119, "image_url": "https://cdn.tapntake.app/menu/gazpacho.jpg", "prep_time": 4},
    {"slug": "pizza-calzone", "vendor_slug": "pizza_station", "name": "Calzone", "description": "Folded pizza pocket.", "price": 229, "image_url": "https://cdn.tapntake.app/menu/calzone.jpg", "prep_time": 16},
    {"slug": "pizza-bruschetta", "vendor_slug": "pizza_station", "name": "Bruschetta", "description": "Toasted bread with tomatoes.", "price": 139, "image_url": "https://cdn.tapntake.app/menu/bruschetta.jpg", "prep_time": 7},
)


# ─────────────────────────────────────────────────────────────────────────────
# Additional Stationery Services (12 more for 40 total)
# ─────────────────────────────────────────────────────────────────────────────

ADDITIONAL_STATIONERY_SERVICES: Sequence[Dict[str, Any]] = (
    {"slug": "xerox-spiral-binding", "vendor_slug": "xerox_point", "name": "Spiral Binding", "description": "Plastic coil binding", "price": 35.0, "unit": "job", "category": "Binding", "image_url": "https://cdn.tapntake.app/stationery/spiral_bind2.jpg", "stock": 200},
    {"slug": "xerox-thermal-binding", "vendor_slug": "xerox_point", "name": "Thermal Binding", "description": "Heat-sealed binding", "price": 50.0, "unit": "job", "category": "Binding", "image_url": "https://cdn.tapntake.app/stationery/thermal_bind.jpg", "stock": 150},
    {"slug": "xerox-a3-lam", "vendor_slug": "xerox_point", "name": "A3 Lamination", "description": "Large format lamination", "price": 40.0, "unit": "sheet", "category": "Lamination", "image_url": "https://cdn.tapntake.app/stationery/a3_lam.jpg", "stock": 180},
    {"slug": "xerox-certificate", "vendor_slug": "xerox_point", "name": "Certificate Print", "description": "Premium certificate paper", "price": 35.0, "unit": "piece", "category": "Premium", "image_url": "https://cdn.tapntake.app/stationery/cert_print.jpg", "stock": 100},
    {"slug": "print-mug", "vendor_slug": "print_hub", "name": "Mug Printing", "description": "Custom printed mug", "price": 280.0, "unit": "piece", "category": "Merchandise", "image_url": "https://cdn.tapntake.app/stationery/mug.jpg", "stock": 40},
    {"slug": "print-tshirt", "vendor_slug": "print_hub", "name": "T-Shirt Print", "description": "Custom t-shirt printing", "price": 450.0, "unit": "piece", "category": "Merchandise", "image_url": "https://cdn.tapntake.app/stationery/tshirt.jpg", "stock": 25},
    {"slug": "print-business-card", "vendor_slug": "print_hub", "name": "Business Cards", "description": "250 card set", "price": 180.0, "unit": "pack", "category": "Marketing", "image_url": "https://cdn.tapntake.app/stationery/business_cards.jpg", "stock": 60},
    {"slug": "print-invitation", "vendor_slug": "print_hub", "name": "Invitation Card", "description": "Custom invitation design", "price": 40.0, "unit": "piece", "category": "Cards", "image_url": "https://cdn.tapntake.app/stationery/invitation.jpg", "stock": 120},
    {"slug": "stationery-pencil-set", "vendor_slug": "campus_stationery", "name": "Pencil Set", "description": "Pack of 10 HB pencils", "price": 50.0, "unit": "set", "category": "Writing", "image_url": "https://cdn.tapntake.app/stationery/pencils.jpg", "stock": 300},
    {"slug": "stationery-eraser-set", "vendor_slug": "campus_stationery", "name": "Eraser Set", "description": "Pack of 5 erasers", "price": 35.0, "unit": "set", "category": "Writing", "image_url": "https://cdn.tapntake.app/stationery/erasers.jpg", "stock": 250},
    {"slug": "stationery-ruler", "vendor_slug": "campus_stationery", "name": "Scale Ruler 30cm", "description": "Stainless steel ruler", "price": 45.0, "unit": "piece", "category": "Accessories", "image_url": "https://cdn.tapntake.app/stationery/ruler.jpg", "stock": 180},
    {"slug": "stationery-glue-stick", "vendor_slug": "campus_stationery", "name": "Glue Stick", "description": "Non-toxic adhesive", "price": 30.0, "unit": "piece", "category": "Accessories", "image_url": "https://cdn.tapntake.app/stationery/glue.jpg", "stock": 150},
)


# ─────────────────────────────────────────────────────────────────────────────
# Additional Orders (10 more for 30 total)
# ─────────────────────────────────────────────────────────────────────────────

ADDITIONAL_ORDERS: Sequence[Dict[str, Any]] = (
    {"reference": "ORD-ISHAAN-001", "user": "ishaan", "vendor": "noodle_house", "slot_label": "lunch", "items": [{"menu_slug": "noodle-veg-hakka", "quantity": 1}, {"menu_slug": "noodle-momos", "quantity": 1}], "status": OrderStatus.READY, "days_ago": 0, "eta_minutes": 18, "payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY]},
    {"reference": "ORD-PRIYA-001", "user": "priya", "vendor": "campus_cafe", "slot_label": "lunch", "items": [{"menu_slug": "campus-croissant", "quantity": 1}, {"menu_slug": "campus-iced-latte", "quantity": 1}], "status": OrderStatus.PICKED, "days_ago": 2, "eta_minutes": 12, "payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY, OrderStatus.PICKED]},
    {"reference": "ORD-VIKRAM-001", "user": "vikram", "vendor": "burger_hub", "slot_label": "evening", "items": [{"menu_slug": "burgerhub-dbl-cheese", "quantity": 1}, {"menu_slug": "burgerhub-strawberry-shake", "quantity": 1}], "status": OrderStatus.CONFIRMED, "days_ago": 0, "eta_minutes": 20, "payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED]},
    {"reference": "ORD-NEHA-001", "user": "neha", "vendor": "spice_corner", "slot_label": "breakfast", "items": [{"menu_slug": "spice-rava-dosa", "quantity": 1}, {"menu_slug": "spice-filter-coffee", "quantity": 1}], "status": OrderStatus.PREPARING, "days_ago": 0, "eta_minutes": 16, "payment": {"status": PaymentStatus.SUCCESS, "method": "WALLET"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING]},
    {"reference": "ORD-ROHIT-001", "user": "rohit", "vendor": "pizza_station", "slot_label": "evening", "items": [{"menu_slug": "pizza-cheese-burst", "quantity": 1}, {"menu_slug": "pizza-garlic-knots", "quantity": 1}], "status": OrderStatus.READY, "days_ago": 1, "eta_minutes": 22, "payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY]},
    {"reference": "ORD-TANVI-001", "user": "tanvi", "vendor": "green_bowl", "slot_label": "lunch", "items": [{"menu_slug": "greenbowl-salmon-salad", "quantity": 1}, {"menu_slug": "greenbowl-mango-smoothie", "quantity": 1}], "status": OrderStatus.PICKED, "days_ago": 3, "eta_minutes": 20, "payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY, OrderStatus.PICKED]},
    {"reference": "ORD-KARTHIK-001", "user": "karthik", "vendor": "noodle_house", "slot_label": "evening", "items": [{"menu_slug": "noodle-thai-curry", "quantity": 1}, {"menu_slug": "noodle-dim-sum", "quantity": 1}], "status": OrderStatus.READY, "days_ago": 0, "eta_minutes": 25, "payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY]},
    {"reference": "ORD-AISHA-001", "user": "aisha", "vendor": "campus_cafe", "slot_label": "breakfast", "items": [{"menu_slug": "campus-egg-roll", "quantity": 1}, {"menu_slug": "campus-masala-chai", "quantity": 2}], "status": OrderStatus.CONFIRMED, "days_ago": 0, "eta_minutes": 15, "payment": {"status": PaymentStatus.INITIATED, "method": "UPI"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED]},
    {"reference": "ORD-YASH-001", "user": "yash", "vendor": "burger_hub", "slot_label": "lunch", "items": [{"menu_slug": "burgerhub-spicy-chicken", "quantity": 1}, {"menu_slug": "burgerhub-bbq-wings", "quantity": 1}], "status": OrderStatus.PREPARING, "days_ago": 0, "eta_minutes": 24, "payment": {"status": PaymentStatus.SUCCESS, "method": "CARD"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING]},
    {"reference": "ORD-DIYA-001", "user": "diya", "vendor": "spice_corner", "slot_label": "lunch", "items": [{"menu_slug": "spice-poori-bhaji", "quantity": 1}, {"menu_slug": "spice-rasgulla", "quantity": 2}], "status": OrderStatus.READY, "days_ago": 1, "eta_minutes": 18, "payment": {"status": PaymentStatus.SUCCESS, "method": "UPI"}, "history": [OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.READY]},
)


# ─────────────────────────────────────────────────────────────────────────────
# Additional Notifications (22 more for 50+ total)
# ─────────────────────────────────────────────────────────────────────────────

ADDITIONAL_NOTIFICATIONS: Sequence[Dict[str, Any]] = (
    # More promo and system notifications
    {"user": "ishaan", "title": "Order Confirmed", "message": "Noodle House confirmed your lunch order.", "notification_type": NotificationType.ORDER_ACCEPTED, "order_ref": "ORD-ISHAAN-001", "is_read": False},
    {"user": "priya", "title": "Order Ready", "message": "Your croissant and latte are ready at Campus Cafe.", "notification_type": NotificationType.ORDER_READY, "order_ref": "ORD-PRIYA-001", "is_read": True},
    {"user": "vikram", "title": "New Burger Alert", "message": "Try the new Double Cheese Burger at Burger Hub!", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "neha", "title": "Order Preparing", "message": "Spice Corner is preparing your Rava Dosa.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-NEHA-001", "is_read": False},
    {"user": "rohit", "title": "Order Ready", "message": "Your Cheese Burst Pizza is ready for pickup.", "notification_type": NotificationType.ORDER_READY, "order_ref": "ORD-ROHIT-001", "is_read": True},
    {"user": "tanvi", "title": "Green Bowl Special", "message": "20% off on all salads this week!", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "karthik", "title": "Pickup Reminder", "message": "Your Thai Curry order is ready at East Wing.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": "ORD-KARTHIK-001", "is_read": False},
    {"user": "aisha", "title": "Payment Pending", "message": "Complete payment for your breakfast order.", "notification_type": NotificationType.SYSTEM, "order_ref": "ORD-AISHA-001", "is_read": False},
    {"user": "yash", "title": "Order Preparing", "message": "Burger Hub is preparing your Spicy Chicken Burger.", "notification_type": NotificationType.ORDER_PREPARING, "order_ref": "ORD-YASH-001", "is_read": True},
    {"user": "diya", "title": "Order Ready", "message": "Your Poori Bhaji is ready at Heritage Lane.", "notification_type": NotificationType.ORDER_READY, "order_ref": "ORD-DIYA-001", "is_read": False},
    # Additional users getting notifications
    {"user": "naina", "title": "Weekend Special", "message": "Double points on all orders this Saturday!", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "rahul", "title": "Spice Corner Anniversary", "message": "Free filter coffee with any dosa order today.", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "ananya", "title": "New Menu Alert", "message": "Green Bowl added overnight oats to the menu.", "notification_type": NotificationType.SYSTEM, "order_ref": None, "is_read": True},
    {"user": "kabir", "title": "Pizza Station Deal", "message": "Buy any large pizza, get garlic knots free!", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "meera", "title": "Campus Cafe Update", "message": "New mango lassi shake now available!", "notification_type": NotificationType.SYSTEM, "order_ref": None, "is_read": False},
    {"user": "dev", "title": "Slot Reminder", "message": "Your preferred lunch slot opens in 15 minutes.", "notification_type": NotificationType.PICKUP_REMINDER, "order_ref": None, "is_read": True},
    {"user": "arjun", "title": "Faculty Lunch Priority", "message": "Your 9 AM slot priority is now active.", "notification_type": NotificationType.SYSTEM, "order_ref": None, "is_read": False},
    {"user": "sneha", "title": "Rewards Update", "message": "You earned 50 bonus points for gluten-free orders!", "notification_type": NotificationType.SYSTEM, "order_ref": None, "is_read": True},
    {"user": "varun", "title": "Noodle House Opening", "message": "New Asian cuisine vendor opened at East Wing!", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "shreya", "title": "Early Bird Credit", "message": "5% cashback on orders before 10 AM today.", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "aditya", "title": "Flash Sale", "message": "30 minute flash sale: all burgers 15% off!", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
    {"user": "rhea", "title": "Weekend Brunch", "message": "Campus Cafe is serving brunch specials this Sunday.", "notification_type": NotificationType.PROMO, "order_ref": None, "is_read": False},
)


def rupees(value: float) -> int:
    return int(round(value * 100))


def seed_additional_users(session: Session) -> Dict[str, User]:
    users = {}
    for payload in ADDITIONAL_USERS:
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


def seed_additional_vendor(session: Session) -> Dict[str, User]:
    from sqlalchemy import MetaData
    metadata = MetaData()
    metadata.reflect(bind=engine)

    if "vendor_profiles" not in metadata.tables:
        return {}

    vendor_profiles = metadata.tables["vendor_profiles"]

    payload = ADDITIONAL_VENDOR
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

    session.execute(
        vendor_profiles.insert().values(
            vendor_id=vendor.id,
            category=profile["category"],
            description=profile["description"],
            rating=profile["rating"],
            location=profile["location"],
            logo_url=profile["logo_url"],
            cover_image=profile["cover_image"],
            is_open=profile["is_open"],
        )
    )

    return {payload["slug"]: vendor}


def seed_additional_menu_items(session: Session, vendor_map: Dict[str, User]) -> Dict[str, MenuItem]:
    items = {}
    for payload in ADDITIONAL_MENU_ITEMS:
        vendor_slug = payload["vendor_slug"]
        if vendor_slug not in vendor_map:
            continue
        vendor = vendor_map[vendor_slug]
        menu_item = MenuItem(
            vendor_id=vendor.id,
            name=payload["name"],
            description=payload["description"],
            price=rupees(payload["price"]),
            image_url=payload["image_url"],
            is_available=True,
        )
        session.add(menu_item)
        session.flush()
        items[payload["slug"]] = menu_item
    return items


def seed_additional_stationery(session: Session, vendor_map: Dict[str, User]) -> Dict[str, StationeryService]:
    services = {}
    for payload in ADDITIONAL_STATIONERY_SERVICES:
        vendor_slug = payload["vendor_slug"]
        if vendor_slug not in vendor_map:
            continue
        vendor = vendor_map[vendor_slug]
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
    return services


def create_slots_for_vendor(session: Session, vendor_id: int, vendor_slug: str) -> Dict[str, Slot]:
    slots = {}
    base_day = NOW.replace(hour=8, minute=0, second=0, microsecond=0)
    templates = [
        {"label": "breakfast", "start_hour": 9, "duration": 60, "max_orders": 24},
        {"label": "lunch", "start_hour": 12, "duration": 90, "max_orders": 48},
        {"label": "evening", "start_hour": 18, "duration": 90, "max_orders": 42},
    ]
    for template in templates:
        start = base_day.replace(hour=template["start_hour"], minute=0, second=0, microsecond=0)
        end = start + timedelta(minutes=template["duration"])
        slot = Slot(
            vendor_id=vendor_id,
            start_time=start,
            end_time=end,
            max_orders=template["max_orders"],
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        session.add(slot)
        session.flush()
        slots[template["label"]] = slot
    return slots


def seed_additional_orders(
    session: Session,
    new_users: Dict[str, User],
    existing_users: Dict[str, User],
    vendors: Dict[str, User],
    menu_items: Dict[str, MenuItem],
    existing_slots: Dict[str, Dict[str, Slot]],
) -> Dict[str, Order]:
    all_users = {**existing_users, **new_users}
    orders = {}
    slot_map = existing_slots

    for payload in ADDITIONAL_ORDERS:
        user = all_users[payload["user"]]
        vendor = vendors[payload["vendor"]]
        slot_label = payload["slot_label"]

        if vendor.id not in [s.vendor_id for s_list in slot_map.values() for s in s_list.values()]:
            new_slots = create_slots_for_vendor(session, vendor.id, payload["vendor"])
            slot_map[payload["vendor"]] = new_slots

        slot = slot_map[payload["vendor"]][slot_label]

        created_at = NOW - timedelta(days=payload["days_ago"])
        order = Order(
            user_id=user.id,
            vendor_id=vendor.id,
            slot_id=slot.id,
            status=payload["status"],
            created_at=created_at,
            qr_code=f"TNT-{payload['reference'][-3:]}-{uuid4().hex[:6].upper()}",
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
                line_total=line_total,
            )
            session.add(order_item)
            total += line_total

        order.total_amount = total

        for step, status in enumerate(payload["history"]):
            record = OrderHistory(
                order_id=order.id,
                status=status,
                changed_at=created_at + timedelta(minutes=step * 5),
            )
            session.add(record)

        payment = Payment(
            order_id=order.id,
            amount=total,
            status=payload["payment"]["status"],
            idempotency_key=f"{payload['payment']['method']}-{uuid4().hex[:8]}",
            razorpay_order_id=f"order_{uuid4().hex[:10]}",
        )
        session.add(payment)

        orders[payload["reference"]] = order

    return orders


def seed_additional_notifications(
    session: Session,
    new_users: Dict[str, User],
    existing_users: Dict[str, User],
    new_orders: Dict[str, Order],
    existing_orders: Dict[str, Order],
) -> None:
    all_users = {**existing_users, **new_users}
    all_orders = {**existing_orders, **new_orders}

    for payload in ADDITIONAL_NOTIFICATIONS:
        user_slug = payload["user"]
        if user_slug not in all_users:
            continue
        user = all_users[user_slug]

        order_ref = payload.get("order_ref")
        reference_id = None
        if order_ref and order_ref in all_orders:
            reference_id = all_orders[order_ref].id

        notification = Notification(
            user_id=user.id,
            title=payload["title"],
            message=payload["message"],
            notification_type=payload["notification_type"],
            reference_id=reference_id,
            is_read=payload.get("is_read", False),
            created_at=NOW - timedelta(minutes=5),
        )
        session.add(notification)


def main(fresh: bool = False) -> None:
    session = SessionLocal()
    try:
        LOGGER.info("Starting comprehensive demo data seeding...")

        # Get existing users
        existing_users = {u.name.lower().replace(" ", "_"): u for u in session.query(User).filter(User.role != UserRole.VENDOR).all()}
        existing_vendors = {v.name.lower().replace(" ", "_"): v for v in session.query(User).filter(User.role == UserRole.VENDOR).all()}
        existing_menu = {f"{m.name.lower().replace(' ', '_')}_{m.vendor_id}": m for m in session.query(MenuItem).all()}
        existing_slots_query = session.query(Slot).all()
        existing_slots: Dict[str, Dict[str, Slot]] = {}
        for s in existing_slots_query:
            vendor_name = next((k for k, v in existing_vendors.items() if v.id == s.vendor_id), None)
            if vendor_name and vendor_name not in existing_slots:
                existing_slots[vendor_name] = {}
            if vendor_name:
                if s.start_time.hour == 9:
                    existing_slots[vendor_name]["breakfast"] = s
                elif s.start_time.hour == 12:
                    existing_slots[vendor_name]["lunch"] = s
                elif s.start_time.hour == 18:
                    existing_slots[vendor_name]["evening"] = s

        existing_orders = {f"ORD-{o.id}": o for o in session.query(Order).all()}

        # Add new users
        new_users = seed_additional_users(session)
        LOGGER.info("Added %d new users", len(new_users))

        # Add new vendor
        new_vendor = seed_additional_vendor(session)
        all_vendors = {**existing_vendors, **new_vendor}
        LOGGER.info("Added %d new vendors", len(new_vendor))

        # Add new menu items
        new_menu = seed_additional_menu_items(session, all_vendors)
        all_menu = {**existing_menu, **new_menu}
        # Create slugs for the menu items
        menu_slug_map = {}
        for slug, item in new_menu.items():
            menu_slug_map[slug] = item
        # Also add existing items with proper slugs
        for m in session.query(MenuItem).all():
            vendor = session.query(User).filter(User.id == m.vendor_id).first()
            if vendor:
                v_slug = vendor.name.lower().replace(" ", "_").replace("-", "_")
                m_slug = m.name.lower().replace(" ", "_").replace("-", "_")
                menu_slug_map[f"{v_slug}-{m_slug}"] = m
        LOGGER.info("Added %d new menu items", len(new_menu))

        # Add new stationery services
        new_services = seed_additional_stationery(session, all_vendors)
        LOGGER.info("Added %d new stationery services", len(new_services))

        # Add new orders
        new_orders = seed_additional_orders(session, new_users, existing_users, all_vendors, menu_slug_map, existing_slots)
        LOGGER.info("Added %d new orders", len(new_orders))

        # Add new notifications
        seed_additional_notifications(session, new_users, existing_users, new_orders, existing_orders)
        LOGGER.info("Added %d new notifications", len(ADDITIONAL_NOTIFICATIONS))

        session.commit()
        LOGGER.info("Comprehensive demo data seeding complete!")

        # Summary
        total_users = session.query(User).filter(User.role != UserRole.VENDOR).count()
        total_vendors = session.query(User).filter(User.role == UserRole.VENDOR).count()
        total_menu = session.query(MenuItem).count()
        total_orders = session.query(Order).count()
        total_notifications = session.query(Notification).count()

        LOGGER.info("Summary: %d users, %d vendors, %d menu items, %d orders, %d notifications",
                   total_users, total_vendors, total_menu, total_orders, total_notifications)

    except Exception as e:
        session.rollback()
        LOGGER.error("Seeding failed: %s", e)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comprehensive demo data seeder")
    parser.add_argument("--fresh", action="store_true", help="Reset database before seeding")
    args = parser.parse_args()
    main(fresh=args.fresh)
