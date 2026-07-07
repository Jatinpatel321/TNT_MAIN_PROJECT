BEGIN;
TRUNCATE TABLE calendar_events RESTART IDENTITY CASCADE;

-- Calendar Events (15 total)
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (1, '2026-06-10', 'End Semester Exams Begin', 'exam', true, 'Exams start. High traffic at stationery vendors.', '2026-06-10') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (2, '2026-06-25', 'End Semester Exams End', 'exam', false, 'Exams end. Hostel check-outs start.', '2026-06-25') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (3, '2026-07-15', 'Monsoon Semester Starts', 'academic', false, 'Classes resume. High traffic expected.', '2026-07-15') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (4, '2026-08-15', 'Independence Day Holiday', 'holiday', true, 'National holiday. Campus food vendors closed.', '2026-08-15') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (5, '2026-09-05', 'Teachers Day Celebration', 'festival', false, 'Teachers Day events. Cafe Hub special buffet.', '2026-09-05') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (6, '2026-10-02', 'Gandhi Jayanti Holiday', 'holiday', true, 'National holiday. All stalls closed.', '2026-10-02') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (7, '2026-10-22', 'Dussera Festival Break', 'holiday', true, 'Dussehra break begins. Low campus activity.', '2026-10-22') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (8, '2026-11-12', 'Diwali Festival Break', 'holiday', true, 'Diwali holidays. Vendors closed.', '2026-11-12') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (9, '2026-12-25', 'Christmas Holiday', 'holiday', true, 'Winter break. All stalls closed.', '2026-12-25') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (10, '2026-01-26', 'Republic Day Holiday', 'holiday', true, 'National holiday. All stalls closed.', '2026-01-26') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (11, '2026-03-08', 'Holi Festival Break', 'holiday', true, 'Holi holidays. Stalls closed.', '2026-03-08') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (12, '2026-04-14', 'Ambedkar Jayanti Holiday', 'holiday', true, 'National holiday. All stalls closed.', '2026-04-14') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (13, '2026-05-01', 'Summer Vacation Starts', 'academic', true, 'Summer break. Limited food court hours.', '2026-05-01') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (14, '2026-05-20', 'Summer Midterm Exams', 'exam', true, 'Midterm exams for summer courses.', '2026-05-20') ON CONFLICT DO NOTHING;
INSERT INTO calendar_events (id, event_date, label, event_type, affects_ordering, description, created_at) VALUES (15, '2026-06-05', 'World Environment Day Seminar', 'academic', false, 'Campus seminar. Food Junction catering order.', '2026-06-05') ON CONFLICT DO NOTHING;

COMMIT;