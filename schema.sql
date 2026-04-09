-- ============================================================
--  REIMBIFY - SQLite Database Schema
--
--  app.py calls init_db() on startup which runs this
--  automatically.
--  SQLite vs MySQL difference: instead of a server running
--  in the background, the entire database is just one file.
--  Way simpler for development and demo purposes.
-- ============================================================


-- ------------------------------------------------------------
-- 1. USERS
--    Stores everyone who can log in, students AND admins.
--    We don't need two separate tables because the 'role'
--    column tells us who is who.
--    When someone logs in, Flask checks email + password + role.
--    If role doesn't match the portal they're using then rejected.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,  -- auto-assigned unique ID
    name          TEXT NOT NULL,                      -- full name
    email         TEXT NOT NULL UNIQUE,               -- login email, must be unique
    password_hash TEXT NOT NULL,                      -- plain text for demo, bcrypt in production
    role          TEXT NOT NULL DEFAULT 'student'
                  CHECK(role IN ('student','admin')), -- only these two values allowed
    department    TEXT,                               -- e.g. Computer Science
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP  -- auto-set when row is created
);


-- ------------------------------------------------------------
-- 2. BUDGETS
--    Each student has one row per spending category.
--    e.g. Shreya has Travel, Hospitality, Logistics rows.
--
--    amount_used goes up every time an admin approves a request.
--    remaining = total_allocated - amount_used (calculated live in Python).
--    percent_used is also calculated in Python and used for
--    80% guardrail alert on the student dashboard.
--
--    FOREIGN KEY means user_id must exist in the users table.
--    ON DELETE CASCADE means if a user is deleted, their
--    budget rows are automatically deleted too.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budgets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,               -- which student this budget belongs to
    category         TEXT    NOT NULL,               -- e.g. Travel, Hospitality, Logistics
    total_allocated  REAL    NOT NULL DEFAULT 0.0,   -- how much they're allowed to spend
    amount_used      REAL    NOT NULL DEFAULT 0.0,   -- how much has been approved so far
    academic_year    TEXT    DEFAULT '2026-27',       -- budget resets each year
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, category)                       -- prevents duplicate budget rows if init_db() runs twice
);


-- ------------------------------------------------------------
-- 3. REQUESTS
--    The heart of the entire system.
--    Every reimbursement claim AND every advance request
--    lives in this one table. The 'type' column separates them.
--
--    type = 'reimbursement' → student already spent, wants money back
--    type = 'advance'       → student needs money before spending
--
--    status moves through this lifecycle:
--    pending → approved   (admin approved it)
--    pending → rejected   (admin rejected it)
--    pending → modification_requested (admin wants changes)
--
--    admin_comment is what the admin writes when they
--    approve/reject, student can see this on their dashboard.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,                   -- which student made this request
    type          TEXT    NOT NULL
                  CHECK(type IN ('reimbursement','advance')),
    amount        REAL    NOT NULL,                   -- amount in rupees
    category      TEXT    NOT NULL,                   -- must match a budget category
    description   TEXT,                              -- what was the expense for
    status        TEXT    NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending','approved','rejected','modification_requested')),
    admin_comment TEXT,                              -- admin's note when reviewing
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
-- 4. BILLS
--    The uploaded receipt/invoice attached to a request.
--    One request can have multiple bills if needed.
--
--    file_path stores where the image was saved on the server
--    (inside static/uploads/).
--
--    extracted_* columns are filled by Google Vision API
--    after the image is uploaded — it reads the bill and
--    pulls out the important details automatically.
--
--    is_manual_entry = 1 means Vision API failed (e.g. handwritten
--    bill) and the student typed the details themselves.
--    0 = Vision API filled it, 1 = student filled it manually.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bills (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id        INTEGER NOT NULL,               -- which request this bill belongs to
    file_path         TEXT    NOT NULL,               -- e.g. static/uploads/bill_123.jpg
    extracted_amount  REAL,                           -- amount Vision API read from the bill
    extracted_vendor  TEXT,                           -- shop/vendor name from the bill
    extracted_date    TEXT,                           -- date on the bill
    is_manual_entry   INTEGER DEFAULT 0,              -- 0 = Vision API, 1 = typed manually
    uploaded_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
-- 5. ADVANCE SETTLEMENTS
--    When a student received an advance
--    and then submits the actual bill afterwards, this table
--    records how it was reconciled.
--
--    Example: student got 2000 advance, spent 1800.
--    settled_amount = 1800, balance_returned = 200
--    (they give back the 200 they didn't spend)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS advance_settlements (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_request_id  INTEGER NOT NULL,   -- links to requests table where type='advance'
    settled_amount      REAL    NOT NULL,   -- how much they actually spent
    balance_returned    REAL    DEFAULT 0.0,-- leftover amount returned to university
    settled_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advance_request_id) REFERENCES requests(id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
-- 6. AUDIT LOG
--    Every single admin action (approve/reject/comment) is
--    automatically recorded here by database.py.
--
--    The finance dashboard will also read this table to show the
--    complete history of all decisions ever made.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id   INTEGER NOT NULL,          -- which request was acted on
    action_by    INTEGER NOT NULL,          -- which admin did it (their user id)
    action       TEXT    NOT NULL
                 CHECK(action IN ('approved','rejected','modification_requested')),
    comment      TEXT,                      -- what the admin wrote
    actioned_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE,
    FOREIGN KEY (action_by)  REFERENCES users(id)    ON DELETE CASCADE
);
