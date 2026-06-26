BEGIN;

-- Truncate users and restart identity cascade
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

-- Insert Student Users (IDs 1 to 50)
INSERT INTO users (id, phone, name, full_name, role, vendor_type, university_id, department, semester, device_token, push_enabled, is_active, is_approved, preferences, totp_secret, totp_enabled, created_at) VALUES
(1, '+919000000001', 'Amit Kumar', 'Amit Kumar', 'student', 'food', 'TNT-CSE-2023-001', 'CSE', 6, 'token_1', true, true, true, '{}', null, false, NOW() - INTERVAL '89 days 4 hours'),
(2, '+919000000002', 'Priya Sharma', 'Priya Sharma', 'student', 'food', 'TNT-IT-2023-002', 'IT', 6, 'token_2', true, true, true, '{}', null, false, NOW() - INTERVAL '89 days 3 hours'),
(3, '+919000000003', 'Rahul Verma', 'Rahul Verma', 'student', 'food', 'TNT-AIML-2023-003', 'AIML', 4, 'token_3', true, true, true, '{}', null, false, NOW() - INTERVAL '88 days 6 hours'),
(4, '+919000000004', 'Sneha Patel', 'Sneha Patel', 'student', 'food', 'TNT-CE-2023-004', 'CE', 4, 'token_4', true, true, true, '{}', null, false, NOW() - INTERVAL '88 days 2 hours'),
(5, '+919000000005', 'Vikram Singh', 'Vikram Singh', 'student', 'food', 'TNT-ME-2023-005', 'ME', 8, 'token_5', true, true, true, '{}', null, false, NOW() - INTERVAL '87 days 10 hours'),
(6, '+919000000006', 'Ananya Gupta', 'Ananya Gupta', 'student', 'food', 'TNT-Civil-2023-006', 'Civil', 8, 'token_6', true, true, true, '{}', null, false, NOW() - INTERVAL '87 days 8 hours'),
(7, '+919000000007', 'Rohan Mehta', 'Rohan Mehta', 'student', 'food', 'TNT-CSE-2023-007', 'CSE', 6, 'token_7', true, true, true, '{}', null, false, NOW() - INTERVAL '86 days 12 hours'),
(8, '+919000000008', 'Neha Sen', 'Neha Sen', 'student', 'food', 'TNT-IT-2023-008', 'IT', 6, 'token_8', true, true, true, '{}', null, false, NOW() - INTERVAL '86 days 9 hours'),
(9, '+919000000009', 'Abhishek Das', 'Abhishek Das', 'student', 'food', 'TNT-AIML-2023-009', 'AIML', 4, 'token_9', true, true, true, '{}', null, false, NOW() - INTERVAL '85 days 15 hours'),
(10, '+919000000010', 'Pooja Rao', 'Pooja Rao', 'student', 'food', 'TNT-CE-2023-010', 'CE', 4, 'token_10', true, true, true, '{}', null, false, NOW() - INTERVAL '85 days 7 hours'),
(11, '+919000000011', 'Siddharth Nair', 'Siddharth Nair', 'student', 'food', 'TNT-ME-2023-011', 'ME', 8, 'token_11', true, true, true, '{}', null, false, NOW() - INTERVAL '84 days 18 hours'),
(12, '+919000000012', 'Kriti Joshi', 'Kriti Joshi', 'student', 'food', 'TNT-Civil-2023-012', 'Civil', 8, 'token_12', true, true, true, '{}', null, false, NOW() - INTERVAL '84 days 11 hours'),
(13, '+919000000013', 'Arjun Mishra', 'Arjun Mishra', 'student', 'food', 'TNT-CSE-2023-013', 'CSE', 6, 'token_13', true, true, true, '{}', null, false, NOW() - INTERVAL '83 days 20 hours'),
(14, '+919000000014', 'Divya Bajaj', 'Divya Bajaj', 'student', 'food', 'TNT-IT-2023-014', 'IT', 6, 'token_14', true, true, true, '{}', null, false, NOW() - INTERVAL '83 days 14 hours'),
(15, '+919000000015', 'Varun Dhawan', 'Varun Dhawan', 'student', 'food', 'TNT-AIML-2023-015', 'AIML', 4, 'token_15', true, true, true, '{}', null, false, NOW() - INTERVAL '82 days 22 hours'),
(16, '+919000000016', 'Riya Kapoor', 'Riya Kapoor', 'student', 'food', 'TNT-CE-2023-016', 'CE', 4, 'token_16', true, true, true, '{}', null, false, NOW() - INTERVAL '82 days 13 hours'),
(17, '+919000000017', 'Aditya Roy', 'Aditya Roy', 'student', 'food', 'TNT-ME-2023-017', 'ME', 2, 'token_17', true, true, true, '{}', null, false, NOW() - INTERVAL '81 days 5 hours'),
(18, '+919000000018', 'Isha Talwar', 'Isha Talwar', 'student', 'food', 'TNT-Civil-2023-018', 'Civil', 2, 'token_18', true, true, true, '{}', null, false, NOW() - INTERVAL '81 days 1 hour'),
(19, '+919000000019', 'Manish Pandey', 'Manish Pandey', 'student', 'food', 'TNT-CSE-2023-019', 'CSE', 6, 'token_19', true, true, true, '{}', null, false, NOW() - INTERVAL '80 days 10 hours'),
(20, '+919000000020', 'Shreya Ghoshal', 'Shreya Ghoshal', 'student', 'food', 'TNT-IT-2023-020', 'IT', 6, 'token_20', true, true, true, '{}', null, false, NOW() - INTERVAL '80 days 4 hours'),
(21, '+919000000021', 'Karan Johar', 'Karan Johar', 'student', 'food', 'TNT-AIML-2023-021', 'AIML', 4, 'token_21', true, true, true, '{}', null, false, NOW() - INTERVAL '79 days 18 hours'),
(22, '+919000000022', 'Alia Bhatt', 'Alia Bhatt', 'student', 'food', 'TNT-CE-2023-022', 'CE', 4, 'token_22', true, true, true, '{}', null, false, NOW() - INTERVAL '79 days 9 hours'),
(23, '+919000000023', 'Ranbir Kapoor', 'Ranbir Kapoor', 'student', 'food', 'TNT-ME-2023-023', 'ME', 8, 'token_23', true, true, true, '{}', null, false, NOW() - INTERVAL '78 days 14 hours'),
(24, '+919000000024', 'Deepika Padukone', 'Deepika Padukone', 'student', 'food', 'TNT-Civil-2023-024', 'Civil', 8, 'token_24', true, true, true, '{}', null, false, NOW() - INTERVAL '78 days 8 hours'),
(25, '+919000000025', 'Ranveer Singh', 'Ranveer Singh', 'student', 'food', 'TNT-CSE-2023-025', 'CSE', 6, 'token_25', true, true, true, '{}', null, false, NOW() - INTERVAL '77 days 11 hours'),
(26, '+919000000026', 'Katrina Kaif', 'Katrina Kaif', 'student', 'food', 'TNT-IT-2023-026', 'IT', 6, 'token_26', true, true, true, '{}', null, false, NOW() - INTERVAL '77 days 7 hours'),
(27, '+919000000027', 'Vicky Kaushal', 'Vicky Kaushal', 'student', 'food', 'TNT-AIML-2023-027', 'AIML', 4, 'token_27', true, true, true, '{}', null, false, NOW() - INTERVAL '76 days 19 hours'),
(28, '+919000000028', 'Kiara Advani', 'Kiara Advani', 'student', 'food', 'TNT-CE-2023-028', 'CE', 4, 'token_28', true, true, true, '{}', null, false, NOW() - INTERVAL '76 days 13 hours'),
(29, '+919000000029', 'Sidharth Malhotra', 'Sidharth Malhotra', 'student', 'food', 'TNT-ME-2023-029', 'ME', 8, 'token_29', true, true, true, '{}', null, false, NOW() - INTERVAL '75 days 15 hours'),
(30, '+919000000030', 'Parineeti Chopra', 'Parineeti Chopra', 'student', 'food', 'TNT-Civil-2023-030', 'Civil', 8, 'token_30', true, true, true, '{}', null, false, NOW() - INTERVAL '75 days 10 hours'),
(31, '+919000000031', 'Ayushmann Khurrana', 'Ayushmann Khurrana', 'student', 'food', 'TNT-CSE-2023-031', 'CSE', 6, 'token_31', true, true, true, '{}', null, false, NOW() - INTERVAL '74 days 22 hours'),
(32, '+919000000032', 'Rajkummar Rao', 'Rajkummar Rao', 'student', 'food', 'TNT-IT-2023-032', 'IT', 6, 'token_32', true, true, true, '{}', null, false, NOW() - INTERVAL '74 days 14 hours'),
(33, '+919000000033', 'Bhumi Pednekar', 'Bhumi Pednekar', 'student', 'food', 'TNT-AIML-2023-033', 'AIML', 4, 'token_33', true, true, true, '{}', null, false, NOW() - INTERVAL '73 days 19 hours'),
(34, '+919000000034', 'Taapsee Pannu', 'Taapsee Pannu', 'student', 'food', 'TNT-CE-2023-034', 'CE', 4, 'token_34', true, true, true, '{}', null, false, NOW() - INTERVAL '73 days 11 hours'),
(35, '+919000000035', 'Kartik Aaryan', 'Kartik Aaryan', 'student', 'food', 'TNT-ME-2023-035', 'ME', 8, 'token_35', true, true, true, '{}', null, false, NOW() - INTERVAL '72 days 15 hours'),
(36, '+919000000036', 'Sara Ali Khan', 'Sara Ali Khan', 'student', 'food', 'TNT-Civil-2023-036', 'Civil', 8, 'token_36', true, true, true, '{}', null, false, NOW() - INTERVAL '72 days 9 hours'),
(37, '+919000000037', 'Janhvi Kapoor', 'Janhvi Kapoor', 'student', 'food', 'TNT-CSE-2023-037', 'CSE', 6, 'token_37', true, true, true, '{}', null, false, NOW() - INTERVAL '71 days 18 hours'),
(38, '+919000000038', 'Ishaan Khatter', 'Ishaan Khatter', 'student', 'food', 'TNT-IT-2023-038', 'IT', 6, 'token_38', true, true, true, '{}', null, false, NOW() - INTERVAL '71 days 12 hours'),
(39, '+919000000039', 'Ananya Panday', 'Ananya Panday', 'student', 'food', 'TNT-AIML-2023-039', 'AIML', 4, 'token_39', true, true, true, '{}', null, false, NOW() - INTERVAL '70 days 20 hours'),
(40, '+919000000040', 'Vijay Varma', 'Vijay Varma', 'student', 'food', 'TNT-CE-2023-040', 'CE', 4, 'token_40', true, true, true, '{}', null, false, NOW() - INTERVAL '70 days 14 hours'),
(41, '+919000000041', 'Sobhita Dhulipala', 'Sobhita Dhulipala', 'student', 'food', 'TNT-ME-2023-041', 'ME', 2, 'token_41', true, true, true, '{}', null, false, NOW() - INTERVAL '69 days 23 hours'),
(42, '+919000000042', 'Tripti Dimri', 'Tripti Dimri', 'student', 'food', 'TNT-Civil-2023-042', 'Civil', 2, 'token_42', true, true, true, '{}', null, false, NOW() - INTERVAL '69 days 17 hours'),
(43, '+919000000043', 'Babil Khan', 'Babil Khan', 'student', 'food', 'TNT-CSE-2023-043', 'CSE', 6, 'token_43', true, true, true, '{}', null, false, NOW() - INTERVAL '68 days 22 hours'),
(44, '+919000000044', 'Rashmika Mandanna', 'Rashmika Mandanna', 'student', 'food', 'TNT-IT-2023-044', 'IT', 6, 'token_44', true, true, true, '{}', null, false, NOW() - INTERVAL '68 days 15 hours'),
(45, '+919000000045', 'Dulquer Salmaan', 'Dulquer Salmaan', 'student', 'food', 'TNT-AIML-2023-045', 'AIML', 4, 'token_45', true, true, true, '{}', null, false, NOW() - INTERVAL '67 days 19 hours'),
(46, '+919000000046', 'Fahadh Faasil', 'Fahadh Faasil', 'student', 'food', 'TNT-CE-2023-046', 'CE', 4, 'token_46', true, true, true, '{}', null, false, NOW() - INTERVAL '67 days 11 hours'),
(47, '+919000000047', 'Nani Ganta', 'Nani Ganta', 'student', 'food', 'TNT-ME-2023-047', 'ME', 8, 'token_47', true, true, true, '{}', null, false, NOW() - INTERVAL '66 days 15 hours'),
(48, '+919000000048', 'Samantha Ruth', 'Samantha Ruth', 'student', 'food', 'TNT-Civil-2023-048', 'Civil', 8, 'token_48', true, true, true, '{}', null, false, NOW() - INTERVAL '66 days 9 hours'),
(49, '+919000000049', 'Vijay Deverakonda', 'Vijay Deverakonda', 'student', 'food', 'TNT-CSE-2023-049', 'CSE', 6, 'token_49', true, true, true, '{}', null, false, NOW() - INTERVAL '65 days 18 hours'),
(50, '+919000000050', 'Sai Pallavi', 'Sai Pallavi', 'student', 'food', 'TNT-IT-2023-050', 'IT', 6, 'token_50', true, true, true, '{}', null, false, NOW() - INTERVAL '65 days 10 hours');

-- Insert Faculty Users (IDs 51 to 65)
INSERT INTO users (id, phone, name, full_name, role, vendor_type, university_id, department, semester, device_token, push_enabled, is_active, is_approved, preferences, totp_secret, totp_enabled, created_at) VALUES
(51, '+919100000001', 'Dr. Ramesh Prasad', 'Dr. Ramesh Prasad', 'faculty', 'food', 'TNT-CSE-FAC-001', 'CSE', null, 'fac_token_1', true, true, true, '{}', null, false, NOW() - INTERVAL '89 days'),
(52, '+919100000002', 'Dr. Sunita Sharma', 'Dr. Sunita Sharma', 'faculty', 'food', 'TNT-IT-FAC-002', 'IT', null, 'fac_token_2', true, true, true, '{}', null, false, NOW() - INTERVAL '89 days'),
(53, '+919100000003', 'Prof. Alok Verma', 'Prof. Alok Verma', 'faculty', 'food', 'TNT-AIML-FAC-003', 'AIML', null, 'fac_token_3', true, true, true, '{}', null, false, NOW() - INTERVAL '88 days'),
(54, '+919100000004', 'Dr. Meena Patel', 'Dr. Meena Patel', 'faculty', 'food', 'TNT-CE-FAC-004', 'CE', null, 'fac_token_4', true, true, true, '{}', null, false, NOW() - INTERVAL '88 days'),
(55, '+919100000005', 'Prof. Harish Singh', 'Prof. Harish Singh', 'faculty', 'food', 'TNT-ME-FAC-005', 'ME', null, 'fac_token_5', true, true, true, '{}', null, false, NOW() - INTERVAL '87 days'),
(56, '+919100000006', 'Dr. Kavita Gupta', 'Dr. Kavita Gupta', 'faculty', 'food', 'TNT-Civil-FAC-006', 'Civil', null, 'fac_token_6', true, true, true, '{}', null, false, NOW() - INTERVAL '87 days'),
(57, '+919100000007', 'Dr. Rajesh Mehta', 'Dr. Rajesh Mehta', 'faculty', 'food', 'TNT-CSE-FAC-007', 'CSE', null, 'fac_token_7', true, true, true, '{}', null, false, NOW() - INTERVAL '86 days'),
(58, '+919100000008', 'Prof. Swati Sen', 'Prof. Swati Sen', 'faculty', 'food', 'TNT-IT-FAC-008', 'IT', null, 'fac_token_8', true, true, true, '{}', null, false, NOW() - INTERVAL '86 days'),
(59, '+919100000009', 'Dr. Jayant Das', 'Dr. Jayant Das', 'faculty', 'food', 'TNT-AIML-FAC-009', 'AIML', null, 'fac_token_9', true, true, true, '{}', null, false, NOW() - INTERVAL '85 days'),
(60, '+919100000010', 'Prof. Rekha Rao', 'Prof. Rekha Rao', 'faculty', 'food', 'TNT-CE-FAC-010', 'CE', null, 'fac_token_10', true, true, true, '{}', null, false, NOW() - INTERVAL '85 days'),
(61, '+919100000011', 'Dr. Anand Nair', 'Dr. Anand Nair', 'faculty', 'food', 'TNT-ME-FAC-011', 'ME', null, 'fac_token_11', true, true, true, '{}', null, false, NOW() - INTERVAL '84 days'),
(62, '+919100000012', 'Prof. Shalini Joshi', 'Prof. Shalini Joshi', 'faculty', 'food', 'TNT-Civil-FAC-012', 'Civil', null, 'fac_token_12', true, true, true, '{}', null, false, NOW() - INTERVAL '84 days'),
(63, '+919100000013', 'Dr. Devendra Mishra', 'Dr. Devendra Mishra', 'faculty', 'food', 'TNT-CSE-FAC-013', 'CSE', null, 'fac_token_13', true, true, true, '{}', null, false, NOW() - INTERVAL '83 days'),
(64, '+919100000014', 'Prof. Nidhi Bajaj', 'Prof. Nidhi Bajaj', 'faculty', 'food', 'TNT-IT-FAC-014', 'IT', null, 'fac_token_14', true, true, true, '{}', null, false, NOW() - INTERVAL '83 days'),
(65, '+919100000015', 'Dr. Vivek Dhawan', 'Dr. Vivek Dhawan', 'faculty', 'food', 'TNT-AIML-FAC-015', 'AIML', null, 'fac_token_15', true, true, true, '{}', null, false, NOW() - INTERVAL '82 days');

-- Insert Vendor Users (IDs 66 to 75)
-- Note: Roles are 'vendor'. vendor_type: 'food' (66-71), 'stationery' (72-75)
INSERT INTO users (id, phone, name, full_name, role, vendor_type, university_id, department, semester, device_token, push_enabled, is_active, is_approved, preferences, totp_secret, totp_enabled, created_at) VALUES
(66, '+919200000001', 'Campus Cafe Owner', 'Campus Cafe Owner', 'vendor', 'food', 'TNT-VND-001', 'IT', null, 'vnd_token_1', true, true, true, '{}', null, false, NOW() - INTERVAL '89 days'),
(67, '+919200000002', 'Food Junction Owner', 'Food Junction Owner', 'vendor', 'food', 'TNT-VND-002', 'CSE', null, 'vnd_token_2', true, true, true, '{}', null, false, NOW() - INTERVAL '89 days'),
(68, '+919200000003', 'Snack Corner Owner', 'Snack Corner Owner', 'vendor', 'food', 'TNT-VND-003', 'AIML', null, 'vnd_token_3', true, true, true, '{}', null, false, NOW() - INTERVAL '88 days'),
(69, '+919200000004', 'Coffee Hub Owner', 'Coffee Hub Owner', 'vendor', 'food', 'TNT-VND-004', 'ME', null, 'vnd_token_4', true, true, true, '{}', null, false, NOW() - INTERVAL '88 days'),
(70, '+919200000005', 'Student Kitchen Owner', 'Student Kitchen Owner', 'vendor', 'food', 'TNT-VND-005', 'Civil', null, 'vnd_token_5', true, true, true, '{}', null, false, NOW() - INTERVAL '87 days'),
(71, '+919200000006', 'Express Bites Owner', 'Express Bites Owner', 'vendor', 'food', 'TNT-VND-006', 'CE', null, 'vnd_token_6', true, true, true, '{}', null, false, NOW() - INTERVAL '87 days'),
(72, '+919200000007', 'Print Express Owner', 'Print Express Owner', 'vendor', 'stationery', 'TNT-VND-007', 'IT', null, 'vnd_token_7', true, true, true, '{}', null, false, NOW() - INTERVAL '86 days'),
(73, '+919200000008', 'Smart Print Owner', 'Smart Print Owner', 'vendor', 'stationery', 'TNT-VND-008', 'CSE', null, 'vnd_token_8', true, true, true, '{}', null, false, NOW() - INTERVAL '86 days'),
(74, '+919200000009', 'Campus Xerox Owner', 'Campus Xerox Owner', 'vendor', 'stationery', 'TNT-VND-009', 'AIML', null, 'vnd_token_9', true, true, true, '{}', null, false, NOW() - INTERVAL '85 days'),
(75, '+919200000010', 'Academic Prints Owner', 'Academic Prints Owner', 'vendor', 'stationery', 'TNT-VND-010', 'ME', null, 'vnd_token_10', true, true, true, '{}', null, false, NOW() - INTERVAL '85 days');

-- Insert Admin/Super Admin Users (IDs 76 to 78)
-- Roles: admin (76, 77), super_admin (78)
INSERT INTO users (id, phone, name, full_name, role, vendor_type, university_id, department, semester, device_token, push_enabled, is_active, is_approved, preferences, totp_secret, totp_enabled, created_at) VALUES
(76, '+919900000001', 'Admin User 1', 'Admin User 1', 'admin', 'food', 'TNT-ADM-001', 'IT', null, 'adm_token_1', true, true, true, '{}', 'TOTPSECRETACTUAL1', true, NOW() - INTERVAL '89 days'),
(77, '+919900000002', 'Admin User 2', 'Admin User 2', 'admin', 'food', 'TNT-ADM-002', 'CSE', null, 'adm_token_2', true, true, true, '{}', 'TOTPSECRETACTUAL2', true, NOW() - INTERVAL '88 days'),
(78, '+919900000003', 'Super Admin', 'Super Admin', 'super_admin', 'food', 'TNT-SAD-001', 'AIML', null, 'sad_token_1', true, true, true, '{}', 'TOTPSECRETSUPER', true, NOW() - INTERVAL '89 days');

COMMIT;
