-- ------------------------------------------------------
--  REIMBIFY's SQLite Database Schema
--  init_db() must be called on startup so this file runs automatically.
-- ------------------------------------------------------------------------------


-- ------------------------------------------------------------
-- table 1: USERS
--    for logs in, we check email + password + role.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,  
    name          TEXT NOT NULL,                      
    email         TEXT NOT NULL UNIQUE,               --email must be unique
    password_hash TEXT NOT NULL,                      -- plain text for demo, bcrypt in scalability
    role          TEXT NOT NULL DEFAULT 'student'
                  CHECK(role IN ('student','admin')), 
    department    TEXT,                               
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP  
);


-- ------------------------------------------------------------
-- table 2: BUDGETS
-- each student has one row per spending category based on requests sent
--amount_used goes up every time an admin approves a request
-- remaining = total_allocated - amount_used (calculated live by python).
-- percent_used is also calculated live for guardrail alert feature
-- -------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budgets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,               --identify student
    category         TEXT    NOT NULL,               --Travel,hospitality, logistics
    total_allocated  REAL    NOT NULL DEFAULT 0.0,     --category wise budget limit set for students
    amount_used      REAL    NOT NULL DEFAULT 0.0,      --amount spent&reimbursed/approved by far
    academic_year    TEXT    DEFAULT '2026-27',          -- budget resets each year
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, category)                       --to prevent duplicate budget rows if init_db() runs twice
);


-- ------------------------------------------------------------
--table 3: REQUESTS
-- type='reimbursement'   student has already spent
--  type='advance'   student asks for money before spending
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,                    --identfy student who made this request foreign key refers table 1
    type          TEXT    NOT NULL
                  CHECK(type IN ('reimbursement','advance')),
    amount        REAL    NOT NULL,                   
    category      TEXT    NOT NULL,                   -- must match the pre def budget category
    description   TEXT,                              --student writes
    status        TEXT    NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending','approved','rejected','modification_requested')),
    admin_comment TEXT,                              --admin's note when reviewing
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- ------------------------------------------------------------------
--table4: BILLS
-- the uploaded invoice attached to the requests
-- a request can have multiple bills if needed so request_id not unique
-- extracted columns to be filled by Google Vision API after the bill is uploaded 
--is_manual_entry = 1 manual entry for fallback if vision fails and the student can enter the details themselves.
--0 = Vision API handleedd it, 1 = student filled it manually.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bills (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id        INTEGER NOT NULL,               --which request this bill belongs to
    file_path         TEXT    NOT NULL,                 --where we storing bill static/uploads/bill.jpg
    extracted_amount  REAL,                           --amount vision API read from the bill
    extracted_vendor  TEXT,                          --shop/vendor name from the bill
    extracted_date    TEXT,                           --date on bill
    is_manual_entry   INTEGER DEFAULT 0,         
    uploaded_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
--table5: ADVANCE_SETTLEMENTS
--When a student's advance gets approved.to track advance
--for eg- student gets 2000 advance but spends 1800.
--settled_amount = 1800, balance_returned = 200
-- (need to give back the 200 they didn't spend)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS advance_settlements (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_request_id  INTEGER NOT NULL,          --to refer the requests table where type='advance'
    settled_amount      REAL    NOT NULL,           -- how much actually spent
    balance_returned    REAL    DEFAULT 0.0,     -- leftover amount to be returned
    settled_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advance_request_id) REFERENCES requests(id) ON DELETE CASCADE
);


-- ------------------------------------------------------------
--table6: AUDIT LOG
--  Every single admin action (approve/reject/comment) is to be recorded here by database.py.
--The finance dashboard will read this table to show the complete history of all decisions ever made.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id   INTEGER NOT NULL,            --which request
    action_by    INTEGER NOT NULL,        -- which admin did the action
    action       TEXT    NOT NULL
                 CHECK(action IN ('approved','rejected','modification_requested')),
    comment      TEXT,                  --what the admin comments
    actioned_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE,
    FOREIGN KEY (action_by)  REFERENCES users(id)    ON DELETE CASCADE
);


