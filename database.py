"""
database.py — Reimbify
SQLite version — zero installation needed, just works.
PRODUCTION NOTE: swap sqlite3 for mysql-connector-python, 
change get_db() to MySQL connection — everything else stays identical.
"""

import sqlite3
import os
"""
database.py — Reimbify
SQLite version — zero installation needed, just works.
PRODUCTION NOTE: swap sqlite3 for mysql-connector-python, 
change get_db() to MySQL connection — everything else stays identical.
"""

import sqlite3
import os

# Database file lives in your project root — just one file, no server needed
DB_PATH = os.path.join(os.path.dirname(__file__), 'reimbify.db')


def get_db():
    """Returns a fresh database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # makes rows behave like dictionaries
    conn.execute("PRAGMA foreign_keys = ON")  # enforce foreign keys
    return conn


# ============================================================
#  AUTH FUNCTIONS
# ============================================================

def get_user_by_email(email): # Removed 'role' parameter single login fro cleaner approach
    """
    Fetch a user by email only. 
    This allows a single login page to identify if the user is a student or admin.
    """
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def verify_password(plain_password, stored_password):
    """
    Plain text comparison for demo.
    PRODUCTION TODO: replace with bcrypt.checkpw()
    """
    return plain_password == stored_password


def hash_password(plain_password):
    """
    Returns as-is for demo.
    PRODUCTION TODO: replace with bcrypt.hashpw()
    """
    return plain_password


# ============================================================
#  BUDGET FUNCTIONS  (powers the dashboard summary cards)
# ============================================================

def get_student_budgets(user_id):
    """
    Returns all budget rows for a student.
    Each row has: category, total_allocated, amount_used, remaining.
    """
    conn = get_db()
    budgets = conn.execute(
        """
        SELECT
            category,
            total_allocated,
            amount_used,
            (total_allocated - amount_used)                    AS remaining,
            ROUND((amount_used * 100.0 / total_allocated), 1)  AS percent_used
        FROM budgets
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(b) for b in budgets]


def get_budget_summary(user_id):
    """
    Returns totals across ALL categories combined.
    Used for the top summary cards on the student dashboard.
    """
    conn = get_db()
    summary = conn.execute(
        """
        SELECT
            SUM(total_allocated)                                        AS total_allocated,
            SUM(amount_used)                                           AS total_used,
            SUM(total_allocated - amount_used)                         AS total_remaining,
            ROUND(SUM(amount_used) * 100.0 / SUM(total_allocated), 1)  AS overall_percent
        FROM budgets
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(summary) if summary else None


# ============================================================
#  REQUEST FUNCTIONS  (my requests page + new request form)
# ============================================================

def get_student_requests(user_id):
    """
    All requests by a student, newest first.
    LEFT JOIN with bills so each request carries its bill file path.
    LEFT JOIN means requests with no bill still show up (bill_path will be None).
    GROUP BY r.id prevents duplicate rows if a request has multiple bills.
    """
    conn = get_db()
    requests = conn.execute(
        """
        SELECT r.*, b.file_path AS bill_path
        FROM requests r
        LEFT JOIN bills b ON b.request_id = r.id
        WHERE r.user_id = ?
        GROUP BY r.id
        ORDER BY r.created_at DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in requests]


def get_request_by_id(request_id, user_id):
    """Single request — also checks it belongs to this user (security)."""
    conn = get_db()
    request = conn.execute(
        "SELECT * FROM requests WHERE id = ? AND user_id = ?",
        (request_id, user_id)
    ).fetchone()
    conn.close()
    return dict(request) if request else None


def create_request(user_id, req_type, amount, category, description, event='N/A'):
    """
    Insert a new request row.
    Returns the new request's ID so we can attach a bill right after.
    """
    conn = get_db()
    # FIXED: Added correct syntax for execute and closed parentheses
    cursor = conn.execute(
        """
        INSERT INTO requests (user_id, type, amount, category, event, description, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
        (user_id, req_type, amount, category, event or 'N/A', description)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_pending_requests_count(user_id):
    """Quick count of pending requests — for dashboard badge."""
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM requests WHERE user_id = ? AND status = 'pending'",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def get_request_stats(user_id):
    """
    Returns all three counts at once for the dashboard quick stats section.
    pending, approved, rejected — one DB call instead of three.
    Works for ANY student in the database, not hardcoded to anyone.
    """
    conn = get_db()
    row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'pending'  THEN 1 ELSE 0 END) AS pending,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected
        FROM requests
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()
    conn.close()
    # Return 0s if student has no requests yet to avoid None errors in HTML
    return {
        "pending":  row["pending"]  or 0,
        "approved": row["approved"] or 0,
        "rejected": row["rejected"] or 0
    }


def get_recent_requests(user_id, limit=4):
    """
    Returns the most recent N requests — for the mini preview on dashboard.
    Default 4. Full list is on the My Requests page.
    """
    conn = get_db()
    requests = conn.execute(
        """
        SELECT * FROM requests
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in requests]

def get_pending_advances(user_id):
    """
    Returns all approved advances for a student that
    have NOT been settled yet — these are the ones where
    student still needs to upload their bill.
    Used for the advance tracker on new-request page.
    
    How it works: joins requests with advance_settlements.
    If no settlement row exists for an advance → it's unsettled.
    LEFT JOIN means we get the advance row even if settlement is NULL.
    """
    conn = get_db()
    advances = conn.execute(
        """
        SELECT 
            r.*,
            s.settled_amount,
            s.balance_returned,
            s.settled_at,
            CASE WHEN s.id IS NULL THEN 0 ELSE 1 END AS is_settled
        FROM requests r
        LEFT JOIN advance_settlements s ON s.advance_request_id = r.id
        WHERE r.user_id = ?
        AND r.type = 'advance'
        AND r.status = 'approved'
        ORDER BY r.created_at DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(a) for a in advances]

# ============================================================
#  BILL FUNCTIONS  (upload bill + Vision API results)
# ============================================================

def save_bill(request_id, file_path, extracted_amount=None,
              extracted_vendor=None, extracted_date=None, is_manual=False):
    """
    Save a bill record after upload.
    extracted_* fields come from Google Vision API.
    If Vision fails, is_manual=True and student typed the values.
    """
    conn = get_db()
    conn.execute(
        """
        INSERT INTO bills
            (request_id, file_path, extracted_amount, extracted_vendor,
             extracted_date, is_manual_entry)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (request_id, file_path, extracted_amount,
         extracted_vendor, extracted_date, int(is_manual))
    )
    conn.commit()
    conn.close()


def get_bills_for_request(request_id):
    """All bills attached to a specific request."""
    conn = get_db()
    bills = conn.execute(
        "SELECT * FROM bills WHERE request_id = ?",
        (request_id,)
    ).fetchall()
    conn.close()
    return [dict(b) for b in bills]


def save_bill_with_details(request_id, file_path, amount, vendor, date, is_manual):
    """
    Cleaner wrapper for saving final bill after confirmation
    """
    save_bill(
        request_id=request_id,
        file_path=file_path,
        extracted_amount=amount,
        extracted_vendor=vendor,
        extracted_date=date,
        is_manual=is_manual
    )


# ============================================================
#  ADMIN FUNCTIONS  (approve / reject / comment)
# ============================================================

def get_all_pending_requests():
    """All pending requests across ALL students — for admin dashboard."""
    conn = get_db()
    requests = conn.execute(
        """
        SELECT r.*, u.name AS student_name, u.department, u.role AS user_role
        FROM requests r
        JOIN users u ON r.user_id = u.id
        WHERE r.status = 'pending'
        ORDER BY r.created_at ASC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in requests]


def update_request_status(request_id, status, admin_id, comment=""):
    """
    Admin approves / rejects a request.
    Also writes to audit_log automatically — compliance trail.
    """
    conn = get_db()

    # Update the request status
    conn.execute(
        "UPDATE requests SET status = ?, admin_comment = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, comment, request_id)
    )

    # Write to audit log
    conn.execute(
        """
        INSERT INTO audit_log (request_id, action_by, action, comment)
        VALUES (?, ?, ?, ?)
        """,
        (request_id, admin_id, status, comment)
    )

    if status == 'approved':
        req_row = conn.execute(
            "SELECT type FROM requests WHERE id = ?", (request_id,)
        ).fetchone()

        if req_row and req_row['type'] == 'reimbursement':
            conn.execute(
                """
                UPDATE budgets
                SET amount_used = amount_used + (
                    SELECT amount FROM requests WHERE id = ?
                )
                WHERE user_id = (
                    SELECT user_id FROM requests WHERE id = ?
                )
                AND category = (
                    SELECT category FROM requests WHERE id = ?
                )
                """,
                (request_id, request_id, request_id)
            )

    conn.commit()
    conn.close()


def get_audit_log():
    """Full audit trail for finance dashboard."""
    conn = get_db()
    log = conn.execute(
        """
        SELECT
            al.*,
            u.name  AS admin_name,
            r.amount, r.category, r.type,
            s.name  AS student_name
        FROM audit_log al
        JOIN users    u ON al.action_by  = u.id
        JOIN requests r ON al.request_id = r.id
        JOIN users    s ON r.user_id     = s.id
        ORDER BY al.actioned_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(l) for l in log]


# ============================================================
#  ADVANCE SETTLEMENT FUNCTIONS
# ============================================================

def settle_advance(advance_request_id, settled_amount):
    """
    Called when a student submits their actual bill after
    receiving an advance.
    """
    conn = get_db()

    original = conn.execute(
        "SELECT amount FROM requests WHERE id = ?",
        (advance_request_id,)
    ).fetchone()

    if not original:
        conn.close()
        return None

    advance_amount   = original['amount']
    balance_returned = max(0, advance_amount - settled_amount)

    conn.execute(
        """
        INSERT INTO advance_settlements
            (advance_request_id, settled_amount, balance_returned)
        VALUES (?, ?, ?)
        """,
        (advance_request_id, settled_amount, balance_returned)
    )

    conn.execute(
        "UPDATE requests SET status = 'approved' WHERE id = ?",
        (advance_request_id,)
    )

    conn.execute(
        """
        UPDATE budgets
        SET amount_used = amount_used + ?
        WHERE user_id = (
            SELECT user_id FROM requests WHERE id = ?
        )
        AND category = (
            SELECT category FROM requests WHERE id = ?
        )
        """,
        (settled_amount, advance_request_id, advance_request_id)
    )

    conn.commit()
    conn.close()
    return balance_returned


def get_advance_settlement(advance_request_id):
    conn = get_db()
    settlement = conn.execute(
        "SELECT * FROM advance_settlements WHERE advance_request_id = ?",
        (advance_request_id,)
    ).fetchone()
    conn.close()
    return dict(settlement) if settlement else None

def is_advance_settled(request_id):
    settlement = get_advance_settlement(request_id)
    return settlement is not None


# ============================================================
#  EXTRA ADMIN FUNCTIONS
# ============================================================

def get_all_requests():
    conn = get_db()
    requests = conn.execute(
        """
        SELECT r.*, u.name AS student_name, u.department
        FROM requests r
        JOIN users u ON r.user_id = u.id
        ORDER BY r.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in requests]

#for audit log 
from collections import defaultdict

def get_grouped_student_budgets():
    conn = get_db()
    rows = conn.execute("""
        SELECT 
            u.id as user_id,
            u.name,
            u.department,
            b.category,
            b.amount_used,
            b.total_allocated,
            ROUND((b.amount_used * 100.0 / b.total_allocated), 1) as percent_used
        FROM budgets b
        JOIN users u ON u.id = b.user_id
    """).fetchall()
    conn.close()

    grouped = defaultdict(lambda: {
        "name": "",
        "department": "",
        "budgets": []
    })

    for row in rows:
        uid = row["user_id"]

        grouped[uid]["name"] = row["name"]
        grouped[uid]["department"] = row["department"]

        grouped[uid]["budgets"].append({
            "category": row["category"],
            "amount_used": row["amount_used"],
            "total_allocated": row["total_allocated"],
            "percent_used": row["percent_used"]
        })

    return list(grouped.values())


def get_spending_analytics():
    conn = get_db()

    totals = conn.execute(
        """
        SELECT
            status,
            COUNT(*)      AS count,
            SUM(amount)   AS total_amount
        FROM requests
        GROUP BY status
        """
    ).fetchall()

    by_category = conn.execute(
        """
        SELECT
            category,
            COUNT(*)                                                    AS count,
            SUM(amount)                                                 AS total_amount,
            SUM(CASE WHEN status='approved' THEN amount ELSE 0 END) AS approved_amount,
            SUM(CASE WHEN status='pending'  THEN amount ELSE 0 END) AS pending_amount
        FROM requests
        GROUP BY category
        ORDER BY total_amount DESC
        """
    ).fetchall()

    by_month = conn.execute(
        """
        SELECT
            strftime('%Y-%m', created_at) AS month,
            SUM(amount)                   AS total_amount,
            COUNT(*)                      AS count
        FROM requests
        WHERE status = 'approved'
        GROUP BY month
        ORDER BY month ASC
        """
    ).fetchall()

    conn.close()
    return {
        "totals":      [dict(t) for t in totals],
        "by_category": [dict(c) for c in by_category],
        "by_month":    [dict(m) for m in by_month]
    }


def get_department_summary():
    conn = get_db()
    summary = conn.execute(
        """
        SELECT
            u.department,
            COUNT(DISTINCT r.user_id)                                   AS student_count,
            COUNT(r.id)                                                 AS request_count,
            SUM(CASE WHEN r.status='approved' THEN r.amount ELSE 0 END) AS approved_total,
            SUM(CASE WHEN r.status='pending'  THEN r.amount ELSE 0 END) AS pending_total
        FROM requests r
        JOIN users u ON r.user_id = u.id
        GROUP BY u.department
        ORDER BY approved_total DESC
        """
    ).fetchall()
    conn.close()
    return [dict(s) for s in summary]


def get_all_student_budgets():
    conn = get_db()
    budgets = conn.execute(
        """
        SELECT
            u.name,
            u.department,
            b.category,
            b.total_allocated,
            b.amount_used,
            (b.total_allocated - b.amount_used)                        AS remaining,
            ROUND(b.amount_used * 100.0 / b.total_allocated, 1)        AS percent_used
        FROM budgets b
        JOIN users u ON b.user_id = u.id
        ORDER BY percent_used DESC
        """
    ).fetchall()
    conn.close()
    return [dict(b) for b in budgets]


# ============================================================
#  DATABASE INITIALISER
# ============================================================

def init_db():
    conn = get_db()

    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if os.path.exists(schema_path):
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())

    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    if count == 0:
        sample_path = os.path.join(os.path.dirname(__file__), 'sample.sql')
        if os.path.exists(sample_path):
            with open(sample_path, 'r') as f:
                conn.executescript(f.read())

    conn.commit()
    conn.close()



