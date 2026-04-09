"""
app.py — Reimbify
This is the brain of the whole application.
Every URL the user visits goes through a route defined here.
Flask reads the request, talks to the database via database.py,
and sends back either an HTML page or a JSON response.

HOW FLASK ROUTES WORK:
@app.route('/some-url') means "when someone visits /some-url, run this function"
session stores who is logged in — like a cookie that remembers the user
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename  # safely handles uploaded file names
from database import (
    init_db,
    # auth — single email lookup, role comes from DB
    get_user_by_email, verify_password,
    # student — budget
    get_student_budgets, get_budget_summary,
    # student — requests
    get_student_requests, get_request_by_id,
    create_request, get_pending_requests_count,
    get_request_stats, get_recent_requests,
    # bills
    save_bill, get_bills_for_request,
    # advance settlements
    settle_advance, get_advance_settlement,
    # admin — requests
    get_all_pending_requests, get_all_requests,
    update_request_status,
    # admin — analytics + finance dashboard (the bookkeeper stuff)
    get_audit_log, get_spending_analytics,
    get_department_summary, get_all_student_budgets
)


# ============================================================
#  APP SETUP
# ============================================================

app = Flask(__name__)

# Secret key is needed for sessions (login state) to work.
# In production we'll use a long random string and keep it secret.
app.secret_key = 'reimbify-secret-key-2026'

#where uploaded bill images get saved
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
#  DATABASE INIT
#  Runs schema.sql on first launch — creates all tables
#  and inserts sample data. Does nothing on subsequent runs.
# ============================================================

init_db()


# ============================================================
#  HELPER FUNCTIONS
# ============================================================

def allowed_file(filename):
    """Check if uploaded file is an allowed type (image or PDF)."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(role):
    """
    Checks if someone is logged in with the correct role.
    Use this at the start of any route that needs authentication.
    Returns True if good, False if they should be redirected.

    Example:
        if not login_required('student'):
            return redirect(url_for('login'))
    """
    return session.get('logged_in') and session.get('role') == role


def policy_check(amount, category):
    """
    Validates a claim against university spending policy.
    Returns (passed: bool, reason: str)
    Your teammate wrote the original version — kept her logic!
    Add more rules here as the university's policies expand.
    """
    if amount > 5000:
        return False, "Amount exceeds the Rs.5,000 per claim limit."
    if category == "Hospitality" and amount > 2000:
        return False, "Hospitality claims cannot exceed Rs.2,000."
    if category == "Logistics" and amount > 3000:
        return False, "Logistics claims cannot exceed Rs.3,000."
    return True, "Claim passed policy validation."


# ============================================================
#  HOME PAGE
# ============================================================

@app.route('/')
def home():
    """Home page — role selector. If already logged in, skip to dashboard."""
    if session.get('logged_in'):
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('home.html')


# ============================================================
#  UNIFIED AUTH ROUTES
#  One login page for everyone
#  Role is detected from the DB, not from a form field.
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Unified login — one page, works for both students and admins.
    Looks up user by email only.
    Role comes straight from the database — no guessing, no extra field.
    Redirects to the right dashboard automatically.
    """
    if session.get('logged_in'):
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))

    error = None

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        # Find user by email- role NOT checked, DB tells us automaically
        user = get_user_by_email(email)

        if user and verify_password(password, user['password_hash']):
            # Valid- save to session
            session['logged_in'] = True
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['role']      = user['role']  # direct from DB

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        else:
            error = "Invalid email or password."

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Universal logout — clears session, sends everyone back to home."""
    session.clear()
    return redirect(url_for('home'))


# ============================================================
#  STUDENT ROUTES
# ============================================================

@app.route('/student/dashboard')
def student_dashboard():
    """
    Main student dashboard — the overview page.
    Passes to the HTML:
      user_name       → for the welcome message "Hey [Name]!"
      summary         → total allocated / used / remaining across all categories
      budgets         → per category with percent_used (for progress bars)
      pending_count   → badge on nav bar
      stats           → { pending, approved, rejected } for quick stats section
      recent_requests → last 4 requests for the mini preview section
      over_80         → categories at or over 80% — triggers red looping banner
                        works for ANY student, not just Shreya!
    """
    if not login_required('student'):
        return redirect(url_for('login'))

    user_id = session['user_id']

    summary         = get_budget_summary(user_id)
    budgets         = get_student_budgets(user_id)
    pending_count   = get_pending_requests_count(user_id)
    stats           = get_request_stats(user_id)
    recent_requests = get_recent_requests(user_id, limit=4)

    # Any category hitting 80%+ triggers the alert
    over_80 = [b for b in budgets if b['percent_used'] >= 80]



    return render_template(
        'student/dashboard.html',
        user_name       = session['user_name'],
        summary         = summary,
        budgets         = budgets,
        pending_count   = pending_count,
        stats           = stats,
        recent_requests = recent_requests,
        over_80         = over_80
    )


@app.route('/student/my-requests')
def my_requests():
    """
    Full list of all requests this student has ever made.
    Shows type, amount, category, status, and admin comment.
    Student can see exactly why something was approved or rejected.

    Supports optional ?status= URL parameter for client-side filtering.
    e.g. /student/my-requests?status=pending
    Valid values: all, pending, approved, rejected
    Defaults to 'all' if no parameter is provided.
    """
    if not login_required('student'):
        return redirect(url_for('login'))

    user_id       = session['user_id']
    all_requests  = get_student_requests(user_id)  # fetch everything first
    pending_count = get_pending_requests_count(user_id)
    stats         = get_request_stats(user_id)

    # read the ?status= param from the URL, default to 'all'
    # filters in Python rather than making a separate DB query per status
    status_filter = request.args.get('status', 'all')
    if status_filter and status_filter != 'all':
        requests = [r for r in all_requests if r['status'] == status_filter]
    else:
        requests = all_requests  # no filter — show everything

    return render_template(
        'student/my_requests.html',
        user_name     = session['user_name'],
        requests      = requests,
        pending_count = pending_count,
        stats         = stats
    )


@app.route('/student/new-request', methods=['GET', 'POST'])
def new_request():
    """
    GET  → shows the new request form
    POST → validates, runs policy check, saves to DB, handles bill upload
    Covers BOTH reimbursement and advance request types.
    """
    if not login_required('student'):
        return redirect(url_for('login'))

    user_id       = session['user_id']
    pending_count = get_pending_requests_count(user_id)
    budgets       = get_student_budgets(user_id)  # for the category dropdown
    error         = None
    success       = None

    if request.method == 'POST':
        req_type    = request.form.get('type', '').strip()
        amount_str  = request.form.get('amount', '').strip()
        category    = request.form.get('category', '').strip().title()  
        description = request.form.get('description', '').strip()

        if not req_type or not amount_str or not category:
            error = "Please fill in all required fields."
        else:
            try:
                amount = float(amount_str)
            except ValueError:
                error = "Amount must be a valid number."
                return render_template('student/new_request.html',
                                       user_name=session['user_name'],
                                       budgets=budgets,
                                       pending_count=pending_count,
                                       error=error)

            # Policy check: auto-validates before reaching admin
            # "Policy Validation" our special feature from the proposal
            passed, reason = policy_check(amount, category)

            if not passed:
                # Instantly rejected with clear reason — no admin needed
                error = f"Policy check failed: {reason}"
            else:
                request_id = create_request(
                    user_id, req_type, amount, category, description
                )

                # Bill upload, reimbursements need it upfront
                # Advances submit bill later via /settle-advance
                if req_type == 'reimbursement' and 'bill' in request.files:
                    file = request.files['bill']
                    if file and file.filename != '' and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filename = f"req_{request_id}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        # Vision API extraction slots in here later
                        save_bill(request_id=request_id,
                                  file_path=filepath, is_manual=True)
                elif req_type == 'advance' and 'bill' in request.files \
                        and request.files['bill'].filename != '':
                    # Student uploaded a bill with an advance, we don't save it,
                    # but tell them where to actually submit it so it's not confusing
                    success = f"Request #{request_id} submitted! Status: Pending review. " \
                              f"(Your bill was not saved- for advances, submit your bill " \
                              f"after spending via 'Settle Advance'.)"

                success = f"Request #{request_id} submitted! Status: Pending review."

    return render_template(
        'student/new_request.html',
        user_name     = session['user_name'],
        budgets       = budgets,
        pending_count = pending_count,
        error         = error,
        success       = success
    )


@app.route('/student/profile')
def student_profile():
    """Student profile — name, department, full budget breakdown."""
    if not login_required('student'):
        return redirect(url_for('login'))

    user_id       = session['user_id']
    budgets       = get_student_budgets(user_id)
    summary       = get_budget_summary(user_id)
    pending_count = get_pending_requests_count(user_id)

    return render_template(
        'student/profile.html',
        user_name     = session['user_name'],
        user_id       = user_id,
        budgets       = budgets,
        summary       = summary,
        pending_count = pending_count
    )


@app.route('/student/settle-advance/<int:advance_request_id>', methods=['GET', 'POST'])
def settle_advance_route(advance_request_id):
    """
    Step 2 of an advance request.
    Student got money upfront → spent it → comes here to reconcile.

    GET  → form asking how much they actually spent
    POST → records settlement, calculates balance to return if any

    Example: got Rs.2000 advance, spent Rs.1800
             balance_returned = Rs.200 — student returns this to university
    """
    if not login_required('student'):
        return redirect(url_for('login'))

    user_id       = session['user_id']
    pending_count = get_pending_requests_count(user_id)

    # Security- making sure this advance belongs to this student
    advance = get_request_by_id(advance_request_id, user_id)
    if not advance or advance['type'] != 'advance':
        return redirect(url_for('my_requests'))

    balance_returned = None
    error = None

    if request.method == 'POST':
        try:
            settled_amount = float(request.form.get('settled_amount', 0))
        except ValueError:
            error = "Please enter a valid amount."
            return render_template('student/settle_advance.html',
                                   advance=advance,
                                   user_name=session['user_name'],
                                   pending_count=pending_count,
                                   error=error)

        if 'bill' in request.files:
            file = request.files['bill']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"settle_{advance_request_id}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                save_bill(request_id=advance_request_id,
                          file_path=filepath, is_manual=True)

        # settle_advance returns how much they need to give back
        balance_returned = settle_advance(advance_request_id, settled_amount)

    return render_template(
        'student/settle_advance.html',
        advance          = advance,
        user_name        = session['user_name'],
        pending_count    = pending_count,
        balance_returned = balance_returned,
        error            = error
    )


# ============================================================
#  ADMIN ROUTES
# sees everything, approves everything, has full visibility over all students and all money flows.
# ============================================================

@app.route('/admin/dashboard')
def admin_dashboard():
    """
    Admin command centre — now properly feeding the monitoring grid and charts.
    """
    if not login_required('admin'):
        return redirect(url_for('login'))

    # 1. Fetch all the data the template needs
    pending_reqs = get_all_pending_requests()
    audit_logs   = get_audit_log()
    budgets      = get_all_student_budgets() # You were missing this!
    
    # 2. Map the data to the names used in your HTML template
    return render_template(
        'admin/dashboard.html', 
        user_name   = session['user_name'],
        pending     = pending_reqs,    # Matches {{ pending | length }}
        audit       = audit_logs,      # Matches {% for log in audit %}
        all_budgets = budgets          # Matches {% for b in all_budgets %}
    )


@app.route('/admin/all-requests')
def all_requests():
    """
    Full history — approved, rejected, pending, everything.
    Admin as bookkeeper needs to see the complete picture.
    """
    if not login_required('admin'):
        return redirect(url_for('login'))

    return render_template(
        'admin/all_requests.html',
        user_name = session['user_name'],
        requests  = get_all_requests()
    )


@app.route('/admin/review/<int:request_id>', methods=['POST'])
def review_request(request_id):
    """
    Admin approves / rejects / requests modification.
    Audit log is written automatically — admin can't deny this happened.

    POST form needs:
        action  = 'approved' / 'rejected' / 'modification_requested'
        comment = explanation for the student
    """
    if not login_required('admin'):
        return redirect(url_for('login'))

    action   = request.form.get('action')
    comment  = request.form.get('comment', '')
    admin_id = session['user_id']

    # Also writes audit_log + updates budget if approved
    update_request_status(request_id, action, admin_id, comment)

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/analytics')
def admin_analytics():
    """
    Finance dashboard — the full money picture for the bookkeeper.
    Shows:
      - Total approved / pending / rejected
      - Which categories are spending most
      - Month by month spending trend
      - Department wise breakdown
      - Every student's budget health
      - Who is over 80% (admin guardrail visibility)
      - Full audit / compliance trail
    This is the Financial Governance Dashboard from the proposal.
    """
    if not login_required('admin'):
        return redirect(url_for('login'))

    analytics        = get_spending_analytics()
    departments      = get_department_summary()
    all_budgets      = get_all_student_budgets()
    audit            = get_audit_log()
    students_over_80 = [b for b in all_budgets if b['percent_used'] >= 80]

    return render_template(
        'admin/analytics.html',
        user_name        = session['user_name'],
        analytics        = analytics,
        departments      = departments,
        all_budgets      = all_budgets,
        audit            = audit,
        students_over_80 = students_over_80
    )

@app.route('/admin/audit')
def admin_audit():
    if not login_required('admin'):
        return redirect(url_for('login'))
    audit = get_audit_log()
    return render_template(
        'admin/audit.html',
        user_name = session['user_name'],
        audit     = audit
    )


# ============================================================
#  API ROUTES (JSON)
#  Used by JavaScript for live updates without page reloads.
# ============================================================

@app.route('/api/request-status/<int:request_id>')
def get_request_status(request_id):
    """Status of one request as JSON — for live status updates on my-requests page."""
    if not login_required('student'):
        return jsonify({"error": "Not logged in"}), 401

    req = get_request_by_id(request_id, session['user_id'])
    if not req:
        return jsonify({"error": "Request not found"}), 404

    return jsonify({
        "id":            req['id'],
        "status":        req['status'],
        "admin_comment": req['admin_comment'],
        "amount":        req['amount'],
        "category":      req['category']
    })


@app.route('/api/budget-summary')
def budget_summary_api():
    """Live budget numbers as JSON — dashboard can refresh without page reload."""
    if not login_required('student'):
        return jsonify({"error": "Not logged in"}), 401

    return jsonify({
        "summary": get_budget_summary(session['user_id']),
        "budgets": get_student_budgets(session['user_id'])
    })


@app.route('/api/analytics')
def analytics_api():
    """All analytics as JSON — admin charts can render dynamically from this."""
    if not login_required('admin'):
        return jsonify({"error": "Not logged in"}), 401

    return jsonify({
        "analytics":   get_spending_analytics(),
        "departments": get_department_summary(),
        "budgets":     get_all_student_budgets()
    })


# ============================================================
#  RUN THE SERVER
#  host='0.0.0.0' required for Render deployment
#  TURN debug=False before presenting
# ============================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

