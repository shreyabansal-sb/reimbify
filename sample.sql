-- ============================================================
--  SAMPLE DATA — DELETE FOR PRODUCTION
--
--  Login credentials:
--  shreya@sau.ac.in  / test123   (student)
--  srija@sau.ac.in   / test123   (student)
--  cstc@sau.ac.in    / test123   (club)
--  admin@sau.ac.in   / admin123  (admin)
-- ============================================================

INSERT OR IGNORE INTO users (name, email, password_hash, role, department) VALUES
('Shreya Bansal', 'shreya@sau.ac.in', 'test123',  'student', 'Computer Science'),
('Srija Das',     'srija@sau.ac.in',  'test123',  'student', 'Computer Science'),
('CSTC',          'cstc@sau.ac.in',   'test123',  'club',    'Computer Science'),
('Admin User',    'admin@sau.ac.in',  'admin123', 'admin',   'Finance');

-- Shreya's budgets (Hospitality at 87% triggers the guardrail alert)
INSERT OR IGNORE INTO budgets (user_id, category, total_allocated, amount_used) VALUES
(1, 'Travel',      5000.0, 2000.0),
(1, 'Hospitality', 3000.0, 2600.0),
(1, 'Logistics',   2000.0,  400.0);

-- Srija's budgets
INSERT OR IGNORE INTO budgets (user_id, category, total_allocated, amount_used) VALUES
(2, 'Travel',    4000.0, 500.0),
(2, 'Logistics', 1500.0,   0.0);

-- CSTC club budgets (higher allocations — clubs run large events)
INSERT OR IGNORE INTO budgets (user_id, category, total_allocated, amount_used) VALUES
(3, 'Travel',      15000.0,  3000.0),
(3, 'Hospitality', 20000.0,  8500.0),
(3, 'Logistics',   10000.0,  2200.0),
(3, 'Marketing',   12000.0,  4000.0);

-- Student requests — event = 'N/A' (individuals have no event context)
INSERT OR IGNORE INTO requests (user_id, type, amount, category, event, description, status) VALUES
(1, 'reimbursement', 1200.0, 'Travel',      'N/A', 'Cab to IGI Airport for research conference', 'pending'),
(1, 'reimbursement',  800.0, 'Hospitality', 'N/A', 'Team dinner for Under25 Summit volunteers',  'approved'),
(1, 'advance',       1500.0, 'Travel',      'N/A', 'Train tickets for college fest outstation',  'pending'),
(2, 'reimbursement',  500.0, 'Logistics',   'N/A', 'Printed banners for event',                  'rejected'),
(1, 'advance',       2000.0, 'Logistics',   'N/A', 'Advance for stationery and printing supplies','approved'),
(2, 'reimbursement', 500.0,  'Travel'   ,   'N/A',  'Transporting research prototype from XYZ university', 'approved');

-- CSTC club requests — all tied to real events
INSERT OR IGNORE INTO requests (user_id, type, amount, category, event, description, status) VALUES
(3, 'reimbursement', 4500.0, 'Hospitality', 'Tech Fest 2026',          'Catering for opening ceremony',            'approved'),
(3, 'advance',       8000.0, 'Logistics',   'Code Sprint April 2026',  'Advance for printing and setup',           'pending'),
(3, 'reimbursement', 2800.0, 'Marketing',   'Tech Fest 2026',          'Poster printing and social media boosts',  'approved'),
(3, 'reimbursement', 1200.0, 'Travel',      'Inter-College Debate 2026','Bus hire for outstation team travel',      'pending');

-- Audit log (admin is now user id 4)
INSERT OR IGNORE INTO audit_log (request_id, action_by, action, comment) VALUES
(2, 4, 'approved', 'Valid expense, within policy limits.'),
(4, 4, 'rejected', 'Receipt not attached. Please resubmit with bill.'),
(5, 4, 'approved', 'Advance approved. Submit actual bill after spending.'),
(6, 4, 'approved', 'Catering invoice verified. Within hospitality limits.'),
(8, 4, 'approved', 'Marketing receipts in order.');

-- Settlement for request #5 (Shreya's advance: got ₹2000, spent ₹1800, returns ₹200)
INSERT OR IGNORE INTO advance_settlements (advance_request_id, settled_amount, balance_returned) VALUES
(5, 1800.0, 200.0);
