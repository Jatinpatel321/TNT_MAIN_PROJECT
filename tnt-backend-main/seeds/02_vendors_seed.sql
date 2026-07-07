-- Passwords: vendor_password='vendor123', staff_password='staff123'
BEGIN;

-- Truncate vendor related tables
TRUNCATE TABLE vendor_staff_permissions RESTART IDENTITY CASCADE;
TRUNCATE TABLE vendor_staff RESTART IDENTITY CASCADE;
TRUNCATE TABLE vendor_profiles RESTART IDENTITY CASCADE;
TRUNCATE TABLE vendor_wallets RESTART IDENTITY CASCADE;
TRUNCATE TABLE vendors RESTART IDENTITY CASCADE;

-- Insert Vendors (IDs 1 to 10)
-- owner_id points to users.id (66 to 75)
INSERT INTO vendors (vendor_id, vendor_name, vendor_type, owner_id, password_hash, status, created_at) VALUES
(1, 'Campus Cafe', 'food', 66, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '88 days'),
(2, 'Food Junction', 'food', 67, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '88 days'),
(3, 'Snack Corner', 'food', 68, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '87 days'),
(4, 'Coffee Hub', 'food', 69, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '87 days'),
(5, 'Student Kitchen', 'food', 70, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '86 days'),
(6, 'Express Bites', 'food', 71, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '86 days'),
(7, 'Print Express', 'stationery', 72, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '85 days'),
(8, 'Smart Print', 'stationery', 73, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '85 days'),
(9, 'Campus Xerox', 'stationery', 74, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '84 days'),
(10, 'Academic Prints', 'stationery', 75, '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', 'active', NOW() - INTERVAL '84 days');

-- Insert Vendor Profiles
INSERT INTO vendor_profiles (id, vendor_id, business_name, category, description, phone, email, location, latitude, longitude, logo_url, cover_image, business_hours, pickup_instructions, holidays, is_open, max_pickup_distance_km, prep_time_minutes, created_at, updated_at) VALUES
(1, 1, 'Campus Cafe', 'food', 'Your favorite spot for quick snacks, delicious meals, and hot beverages on campus.', '+919200000001', 'contact@campuscafe.com', 'Academic Block A, Ground Floor', 12.9716, 77.5946, '/assets/logos/campus_cafe.png', '/assets/covers/campus_cafe.jpg', '{"monday": {"open": "08:00", "close": "20:00"}, "tuesday": {"open": "08:00", "close": "20:00"}, "wednesday": {"open": "08:00", "close": "20:00"}, "thursday": {"open": "08:00", "close": "20:00"}, "friday": {"open": "08:00", "close": "20:00"}, "saturday": {"open": "09:00", "close": "18:00"}, "sunday": {"open": "09:00", "close": "18:00"}}', 'Please collect your orders from Counter 1.', '[]', true, 2.5, 10, NOW() - INTERVAL '88 days', NOW() - INTERVAL '88 days'),
(2, 2, 'Food Junction', 'food', 'Multi-cuisine food court serving North Indian, South Indian, and Chinese delicacies.', '+919200000002', 'contact@foodjunction.com', 'Central Food Court, Shop 1', 12.9720, 77.5950, '/assets/logos/food_junction.png', '/assets/covers/food_junction.jpg', '{"monday": {"open": "09:00", "close": "22:00"}, "tuesday": {"open": "09:00", "close": "22:00"}, "wednesday": {"open": "09:00", "close": "22:00"}, "thursday": {"open": "09:00", "close": "22:00"}, "friday": {"open": "09:00", "close": "22:00"}, "saturday": {"open": "10:00", "close": "21:00"}, "sunday": {"open": "10:00", "close": "21:00"}}', 'Collect from Food Junction counter.', '[]', true, 2.5, 15, NOW() - INTERVAL '88 days', NOW() - INTERVAL '88 days'),
(3, 3, 'Snack Corner', 'food', 'Quick bites, sandwiches, samosas, patties, and refreshing cold drinks.', '+919200000003', 'contact@snackcorner.com', 'Student Center, Ground Floor', 12.9712, 77.5938, '/assets/logos/snack_corner.png', '/assets/covers/snack_corner.jpg', '{"monday": {"open": "08:30", "close": "19:30"}, "tuesday": {"open": "08:30", "close": "19:30"}, "wednesday": {"open": "08:30", "close": "19:30"}, "thursday": {"open": "08:30", "close": "19:30"}, "friday": {"open": "08:30", "close": "19:30"}, "saturday": {"open": "09:00", "close": "17:00"}, "sunday": {"open": "09:00", "close": "17:00"}}', 'Counter pickup at Student Center.', '[]', true, 2.5, 8, NOW() - INTERVAL '87 days', NOW() - INTERVAL '87 days'),
(4, 4, 'Coffee Hub', 'food', 'Freshly brewed coffees, mocktails, cookies, and pastries.', '+919200000004', 'contact@coffeehub.com', 'Library Building Lobby', 12.9730, 77.5960, '/assets/logos/coffee_hub.png', '/assets/covers/coffee_hub.jpg', '{"monday": {"open": "08:00", "close": "21:00"}, "tuesday": {"open": "08:00", "close": "21:00"}, "wednesday": {"open": "08:00", "close": "21:00"}, "thursday": {"open": "08:00", "close": "21:00"}, "friday": {"open": "08:00", "close": "21:00"}, "saturday": {"open": "08:00", "close": "21:00"}, "sunday": {"open": "08:00", "close": "21:00"}}', 'Collect your coffee from the main pickup bar.', '[]', true, 2.5, 5, NOW() - INTERVAL '87 days', NOW() - INTERVAL '87 days'),
(5, 5, 'Student Kitchen', 'food', 'Healthy, home-style meals at highly subsidized student prices.', '+919200000005', 'contact@studentkitchen.com', 'Hostel Mess Block 2', 12.9705, 77.5925, '/assets/logos/student_kitchen.png', '/assets/covers/student_kitchen.jpg', '{"monday": {"open": "07:30", "close": "21:30"}, "tuesday": {"open": "07:30", "close": "21:30"}, "wednesday": {"open": "07:30", "close": "21:30"}, "thursday": {"open": "07:30", "close": "21:30"}, "friday": {"open": "07:30", "close": "21:30"}, "saturday": {"open": "08:00", "close": "21:00"}, "sunday": {"open": "08:00", "close": "21:00"}}', 'Mess card/QR display required at Mess Counter 3.', '[]', true, 2.5, 12, NOW() - INTERVAL '86 days', NOW() - INTERVAL '86 days'),
(6, 6, 'Express Bites', 'food', 'Fast food stall specializing in burgers, fries, momos, and wraps.', '+919200000006', 'contact@expressbites.com', 'Sports Complex Plaza', 12.9740, 77.5970, '/assets/logos/express_bites.png', '/assets/covers/express_bites.jpg', '{"monday": {"open": "10:00", "close": "22:00"}, "tuesday": {"open": "10:00", "close": "22:00"}, "wednesday": {"open": "10:00", "close": "22:00"}, "thursday": {"open": "10:00", "close": "22:00"}, "friday": {"open": "10:00", "close": "22:00"}, "saturday": {"open": "10:00", "close": "23:00"}, "sunday": {"open": "10:00", "close": "23:00"}}', 'Pickup at the plaza window.', '[]', true, 2.5, 7, NOW() - INTERVAL '86 days', NOW() - INTERVAL '86 days'),
(7, 7, 'Print Express', 'stationery', 'High-speed printing, thesis binding, and basic office/classroom stationery.', '+919200000007', 'contact@printexpress.com', 'Academic Block B, Room 102', 12.9718, 77.5948, '/assets/logos/print_express.png', '/assets/covers/print_express.jpg', '{"monday": {"open": "08:30", "close": "18:30"}, "tuesday": {"open": "08:30", "close": "18:30"}, "wednesday": {"open": "08:30", "close": "18:30"}, "thursday": {"open": "08:30", "close": "18:30"}, "friday": {"open": "08:30", "close": "18:30"}, "saturday": {"open": "09:00", "close": "14:00"}}', 'Pick up documents at the front printing counter.', '[]', true, 2.5, 15, NOW() - INTERVAL '85 days', NOW() - INTERVAL '85 days'),
(8, 8, 'Smart Print', 'stationery', 'Color printing, poster plotting, scanning, laminating, and spiral binding services.', '+919200000008', 'contact@smartprint.com', 'Admin Block, Basement Shop 2', 12.9725, 77.5955, '/assets/logos/smart_print.png', '/assets/covers/smart_print.jpg', '{"monday": {"open": "09:00", "close": "18:00"}, "tuesday": {"open": "09:00", "close": "18:00"}, "wednesday": {"open": "09:00", "close": "18:00"}, "thursday": {"open": "09:00", "close": "18:00"}, "friday": {"open": "09:00", "close": "18:00"}, "saturday": {"open": "09:00", "close": "13:00"}}', 'Pick up documents at Counter A.', '[]', true, 2.5, 20, NOW() - INTERVAL '85 days', NOW() - INTERVAL '85 days'),
(9, 9, 'Campus Xerox', 'stationery', 'Subsidized copying, reference material prints, and exam supplies.', '+919200000009', 'contact@campusxerox.com', 'Central Library, Ground Floor Corner', 12.9728, 77.5958, '/assets/logos/campus_xerox.png', '/assets/covers/campus_xerox.jpg', '{"monday": {"open": "08:00", "close": "20:00"}, "tuesday": {"open": "08:00", "close": "20:00"}, "wednesday": {"open": "08:00", "close": "20:00"}, "thursday": {"open": "08:00", "close": "20:00"}, "friday": {"open": "08:00", "close": "20:00"}, "saturday": {"open": "09:00", "close": "17:00"}}', 'Pickup at the library photocopying room counter.', '[]', true, 2.5, 10, NOW() - INTERVAL '84 days', NOW() - INTERVAL '84 days'),
(10, 10, 'Academic Prints', 'stationery', 'High quality thesis binding, project report printouts, and stationery products.', '+919200000010', 'contact@academicprints.com', 'Science Block Plaza, Shop 5', 12.9735, 77.5965, '/assets/logos/academic_prints.png', '/assets/covers/academic_prints.jpg', '{"monday": {"open": "08:30", "close": "19:00"}, "tuesday": {"open": "08:30", "close": "19:00"}, "wednesday": {"open": "08:30", "close": "19:00"}, "thursday": {"open": "08:30", "close": "19:00"}, "friday": {"open": "08:30", "close": "19:00"}, "saturday": {"open": "09:00", "close": "15:00"}}', 'Pickup at counter. Bring order number.', '[]', true, 2.5, 20, NOW() - INTERVAL '84 days', NOW() - INTERVAL '84 days');

-- Insert Vendor Staff (1 manager, 1 helper for each of 10 vendors = 20 total)
INSERT INTO vendor_staff (id, vendor_id, name, role, phone, permissions, password_hash, is_active, created_at) VALUES
(1, 1, 'Rajesh Kumar', 'manager', '+919800000001', '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(2, 1, 'Karan Dev', 'staff', '+919800000002', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(3, 2, 'Sohan Lal', 'manager', '+919800000003', '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(4, 2, 'Ramesh Ram', 'staff', '+919800000004', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(5, 3, 'Vijay Singh', 'manager', '+919800000005', '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(6, 3, 'Ankit Kumar', 'staff', '+919800000006', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(7, 4, 'Tarun Roy', 'manager', '+919800000007', '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(8, 4, 'Manpreet Singh', 'staff', '+919800000008', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(9, 5, 'Ravi Verma', 'manager', '+919800000009', '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(10, 5, 'Ajay Das', 'staff', '+919800000010', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(11, 6, 'Gopal Sen', 'manager', '+919800000011', '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(12, 6, 'Kartik Sen', 'staff', '+919800000012', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(13, 7, 'Sanjay Gupta', 'manager', '+919800000013', '{"orders": ["view", "edit", "status_update"], "services": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(14, 7, 'Naveen Gupta', 'staff', '+919800000014', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(15, 8, 'Mahesh Nair', 'manager', '+919800000015', '{"orders": ["view", "edit", "status_update"], "services": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(16, 8, 'Pramod Nair', 'staff', '+919800000016', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(17, 9, 'Devendra Jha', 'manager', '+919800000017', '{"orders": ["view", "edit", "status_update"], "services": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(18, 9, 'Bipin Jha', 'staff', '+919800000018', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(19, 10, 'Subhas Bose', 'manager', '+919800000019', '{"orders": ["view", "edit", "status_update"], "services": ["edit"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days'),
(20, 10, 'Nehru Sen', 'staff', '+919800000020', '{"orders": ["view", "status_update"]}', '$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS', true, NOW() - INTERVAL '70 days');

-- Insert Vendor Staff Permissions (2 permissions per manager/staff = 40 total)
INSERT INTO vendor_staff_permissions (id, staff_id, permission, is_granted, created_at) VALUES
(1, 1, 'orders_view', true, NOW() - INTERVAL '70 days'),
(2, 1, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(3, 2, 'orders_view', true, NOW() - INTERVAL '70 days'),
(4, 2, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(5, 3, 'orders_view', true, NOW() - INTERVAL '70 days'),
(6, 3, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(7, 4, 'orders_view', true, NOW() - INTERVAL '70 days'),
(8, 4, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(9, 5, 'orders_view', true, NOW() - INTERVAL '70 days'),
(10, 5, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(11, 6, 'orders_view', true, NOW() - INTERVAL '70 days'),
(12, 6, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(13, 7, 'orders_view', true, NOW() - INTERVAL '70 days'),
(14, 7, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(15, 8, 'orders_view', true, NOW() - INTERVAL '70 days'),
(16, 8, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(17, 9, 'orders_view', true, NOW() - INTERVAL '70 days'),
(18, 9, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(19, 10, 'orders_view', true, NOW() - INTERVAL '70 days'),
(20, 10, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(21, 11, 'orders_view', true, NOW() - INTERVAL '70 days'),
(22, 11, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(23, 12, 'orders_view', true, NOW() - INTERVAL '70 days'),
(24, 12, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(25, 13, 'orders_view', true, NOW() - INTERVAL '70 days'),
(26, 13, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(27, 14, 'orders_view', true, NOW() - INTERVAL '70 days'),
(28, 14, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(29, 15, 'orders_view', true, NOW() - INTERVAL '70 days'),
(30, 15, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(31, 16, 'orders_view', true, NOW() - INTERVAL '70 days'),
(32, 16, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(33, 17, 'orders_view', true, NOW() - INTERVAL '70 days'),
(34, 17, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(35, 18, 'orders_view', true, NOW() - INTERVAL '70 days'),
(36, 18, 'orders_edit', false, NOW() - INTERVAL '70 days'),
(37, 19, 'orders_view', true, NOW() - INTERVAL '70 days'),
(38, 19, 'orders_edit', true, NOW() - INTERVAL '70 days'),
(39, 20, 'orders_view', true, NOW() - INTERVAL '70 days'),
(40, 20, 'orders_edit', false, NOW() - INTERVAL '70 days');

-- Insert Vendor Wallets (1 per vendor user 66-75 = 10 total)
-- vendor_id references users.id! (66 to 75)
-- Use paise values (e.g. total_earned = 1000000 is ₹10000. total_pending = 50000 is ₹500, balance = 50000 is ₹500, etc.)
INSERT INTO vendor_wallets (id, vendor_id, total_earned, total_pending, total_settled, total_refunded, balance, created_at, updated_at) VALUES
(1, 66, 1000000.0, 50000.0, 900000.0, 50000.0, 50000.0, NOW() - INTERVAL '88 days', NOW() - INTERVAL '1 days'),
(2, 67, 1200000.0, 40000.0, 1100000.0, 60000.0, 40000.0, NOW() - INTERVAL '88 days', NOW() - INTERVAL '1 days'),
(3, 68, 800000.0, 30000.0, 720000.0, 50000.0, 30000.0, NOW() - INTERVAL '87 days', NOW() - INTERVAL '1 days'),
(4, 69, 1500000.0, 60000.0, 1380000.0, 60000.0, 60000.0, NOW() - INTERVAL '87 days', NOW() - INTERVAL '1 days'),
(5, 70, 950000.0, 25000.0, 875000.0, 50000.0, 25000.0, NOW() - INTERVAL '86 days', NOW() - INTERVAL '1 days'),
(6, 71, 1100000.0, 35000.0, 1015000.0, 50000.0, 35000.0, NOW() - INTERVAL '86 days', NOW() - INTERVAL '1 days'),
(7, 72, 750000.0, 20000.0, 680000.0, 50000.0, 20000.0, NOW() - INTERVAL '85 days', NOW() - INTERVAL '1 days'),
(8, 73, 620000.0, 15000.0, 570000.0, 35000.0, 15000.0, NOW() - INTERVAL '85 days', NOW() - INTERVAL '1 days'),
(9, 74, 580000.0, 10000.0, 540000.0, 30000.0, 10000.0, NOW() - INTERVAL '84 days', NOW() - INTERVAL '1 days'),
(10, 75, 690000.0, 18000.0, 642000.0, 30000.0, 18000.0, NOW() - INTERVAL '84 days', NOW() - INTERVAL '1 days');

COMMIT;
