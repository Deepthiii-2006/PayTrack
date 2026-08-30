from flask import Flask, render_template, request, jsonify, redirect
from database import get_connection
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = "change-this-to-a-random-secret-key"


# ---------------------------------------------------------
# FLASK LOGIN
# ---------------------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------------------------------------------------
# USER CLASS
# ---------------------------------------------------------

class User(UserMixin):

    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash


# ---------------------------------------------------------
# LOAD USER
# ---------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT id, username, email, password_hash
            FROM users
            WHERE id = %s
        """, (user_id,))

        row = cursor.fetchone()

        if row:
            return User(
                row[0],
                row[1],
                row[2],
                row[3]
            )

        return None

    finally:

        cursor.close()
        connection.close()


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    # Already logged in?
    # Don't show register page again.
    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST":

        data = request.json or {}

        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        if not username or not email or not password:

            return jsonify({
                "success": False,
                "error": "Username, email and password are required."
            }), 400

        password_hash = generate_password_hash(password)

        connection = get_connection()
        cursor = connection.cursor()

        try:

            # Check whether email already exists
            cursor.execute("""
                SELECT id
                FROM users
                WHERE email = %s
            """, (email,))

            existing_user = cursor.fetchone()

            if existing_user:

                return jsonify({
                    "success": False,
                    "error": "An account with this email already exists. Please login."
                }), 400

            cursor.execute("""
                INSERT INTO users
                (username, email, password_hash)
                VALUES (%s, %s, %s)
            """, (
                username,
                email,
                password_hash
            ))

            connection.commit()

            return jsonify({
                "success": True,
                "message": "Account created successfully!"
            })

        except Exception as e:

            connection.rollback()

            return jsonify({
                "success": False,
                "error": str(e)
            }), 400

        finally:

            cursor.close()
            connection.close()

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Already logged in?
    # Go directly to dashboard.
    if current_user.is_authenticated and request.method == "GET":
        return redirect("/")

    if request.method == "POST":

        data = request.json or {}

        email = data.get("email")
        password = data.get("password")

        if not email or not password:

            return jsonify({
                "success": False,
                "error": "Email and password are required."
            }), 400

        connection = get_connection()
        cursor = connection.cursor()

        try:

            cursor.execute("""
                SELECT id, username, email, password_hash
                FROM users
                WHERE email = %s
            """, (email,))

            row = cursor.fetchone()

        finally:

            cursor.close()
            connection.close()

        if row and check_password_hash(row[3], password):

            user = User(
                row[0],
                row[1],
                row[2],
                row[3]
            )

            login_user(user)

            return jsonify({
                "success": True,
                "message": "Login successful!"
            })

        return jsonify({
            "success": False,
            "error": "Invalid email or password."
        }), 401

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return jsonify({
        "success": True,
        "message": "Logged out successfully!"
    })


# =========================================================
# HOME / DASHBOARD
# =========================================================

@app.route("/")
def home():

    # Not logged in → LOGIN
    if not current_user.is_authenticated:
        return redirect("/login")

    # Logged in → DASHBOARD
    return render_template("index.html")


# =========================================================
# TEST DATABASE
# =========================================================

@app.route("/test-db")
@login_required
def test_db():

    try:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM Payments
            WHERE user_id = %s
        """, (current_user.id,))

        count = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return f"✅ Database connected! Payments records: {count}"

    except Exception as e:

        return f"❌ Database Error: {e}"


# =========================================================
# ADD PAYMENT
# =========================================================

@app.route("/add-payment", methods=["POST"])
@login_required
def add_payment():

    try:

        data = request.json or {}

        name = data["name"]
        payment_type = data["payment_type"]
        amount = float(data["amount"])
        due_date = data["due_date"]

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Payments
            (
                name,
                payment_type,
                amount,
                due_date,
                status,
                paid_amount,
                user_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            name,
            payment_type,
            amount,
            due_date,
            "Not Paid",
            0,
            current_user.id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "message": "Payment added successfully!"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# GET PAYMENTS
# =========================================================

@app.route("/payments")
@login_required
def get_payments():

    try:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                payment_type,
                amount,
                due_date,
                status,
                paid_amount,
                payment_method,
                paid_date
            FROM Payments
            WHERE user_id = %s
            ORDER BY id
        """, (current_user.id,))

        rows = cursor.fetchall()

        payments = []

        for row in rows:

            payment_id = row[0]

            # Get payment history
            cursor.execute("""
                SELECT
                    id,
                    amount,
                    payment_method,
                    payment_date
                FROM PaymentHistory
                WHERE payment_id = %s
                ORDER BY id
            """, (payment_id,))

            history_rows = cursor.fetchall()

            history = []

            for payment in history_rows:

                history.append({
                    "id": payment[0],
                    "amount": float(payment[1]),
                    "method": payment[2],
                    "date": str(payment[3])
                })

            payments.append({

                "id": row[0],

                "name": row[1],

                "payment_type": row[2],

                "amount": float(row[3]),

                "due_date": str(row[4]),

                "status": row[5],

                "paid_amount": float(row[6] or 0),

                "payment_method": row[7],

                "paid_date": str(row[8]) if row[8] else None,

                "payments": history

            })

        cursor.close()
        connection.close()

        return jsonify(payments)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# =========================================================
# MARK PAYMENT FULLY PAID
# =========================================================

@app.route("/mark-paid/<int:payment_id>", methods=["PUT"])
@login_required
def mark_paid(payment_id):

    try:

        data = request.json or {}

        method = data["method"]
        payment_date = data["date"]

        connection = get_connection()
        cursor = connection.cursor()

        # Get payment
        cursor.execute("""
            SELECT
                amount,
                paid_amount
            FROM Payments
            WHERE id = %s
            AND user_id = %s
        """, (
            payment_id,
            current_user.id
        ))

        row = cursor.fetchone()

        if not row:

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Payment not found."
            }), 404

        amount = float(row[0])

        paid_amount = float(row[1] or 0)

        pending = amount - paid_amount

        if pending <= 0:

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Payment is already fully paid."
            }), 400

        # Update main Payments table
        cursor.execute("""
            UPDATE Payments
            SET
                status = 'Paid',
                paid_amount = amount,
                payment_method = %s,
                paid_date = %s
            WHERE id = %s
            AND user_id = %s
        """, (
            method,
            payment_date,
            payment_id,
            current_user.id
        ))

        # Save transaction history
        cursor.execute("""
            INSERT INTO PaymentHistory
            (
                payment_id,
                amount,
                payment_method,
                payment_date
            )
            VALUES (%s, %s, %s, %s)
        """, (
            payment_id,
            pending,
            method,
            payment_date
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "message": "Payment marked as paid!",
            "paid_amount": amount,
            "status": "Paid"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# PARTIAL PAYMENT
# =========================================================

@app.route("/partial-payment/<int:payment_id>", methods=["PUT"])
@login_required
def partial_payment(payment_id):

    try:

        data = request.json or {}

        amount = float(data["amount"])
        method = data["method"]
        payment_date = data["date"]

        if amount <= 0:

            return jsonify({
                "success": False,
                "error": "Payment amount must be greater than 0."
            }), 400

        connection = get_connection()
        cursor = connection.cursor()

        # Get current payment
        cursor.execute("""
            SELECT
                amount,
                paid_amount
            FROM Payments
            WHERE id = %s
            AND user_id = %s
        """, (
            payment_id,
            current_user.id
        ))

        row = cursor.fetchone()

        if not row:

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Payment not found."
            }), 404

        total_amount = float(row[0])

        current_paid = float(row[1] or 0)

        pending = total_amount - current_paid

        if amount > pending:

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Amount cannot be greater than the pending amount."
            }), 400

        # Calculate new paid amount
        new_paid = current_paid + amount

        # Calculate status
        if new_paid >= total_amount:

            status = "Paid"

        else:

            status = "Partially Paid"

        # -------------------------------------------------
        # UPDATE MAIN PAYMENTS TABLE
        # -------------------------------------------------

        cursor.execute("""
            UPDATE Payments
            SET
                paid_amount = %s,
                status = %s,
                payment_method = %s,
                paid_date = %s
            WHERE id = %s
            AND user_id = %s
        """, (
            new_paid,
            status,
            method,
            payment_date,
            payment_id,
            current_user.id
        ))

        # -------------------------------------------------
        # SAVE PARTIAL PAYMENT HISTORY
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO PaymentHistory
            (
                payment_id,
                amount,
                payment_method,
                payment_date
            )
            VALUES (%s, %s, %s, %s)
        """, (
            payment_id,
            amount,
            method,
            payment_date
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "message": "Partial payment recorded successfully!",
            "paid_amount": new_paid,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# EDIT MAIN PAYMENT
# =========================================================

@app.route("/edit-payment/<int:payment_id>", methods=["PUT"])
@login_required
def edit_payment(payment_id):

    try:

        data = request.json or {}

        name = data["name"]
        payment_type = data["payment_type"]
        amount = float(data["amount"])
        due_date = data["due_date"]

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE Payments
            SET
                name = %s,
                payment_type = %s,
                amount = %s,
                due_date = %s
            WHERE id = %s
            AND user_id = %s
        """, (
            name,
            payment_type,
            amount,
            due_date,
            payment_id,
            current_user.id
        ))

        if cursor.rowcount == 0:

            connection.rollback()

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Payment not found."
            }), 404

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "message": "Payment updated successfully!"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# EDIT PAYMENT HISTORY
# =========================================================

@app.route("/edit-payment-history/<int:history_id>", methods=["PUT"])
@login_required
def edit_payment_history(history_id):

    try:

        data = request.json or {}

        new_amount = float(data["amount"])
        new_method = data["method"]
        new_date = data["date"]

        if new_amount <= 0:

            return jsonify({
                "success": False,
                "error": "Amount must be greater than 0."
            }), 400

        connection = get_connection()
        cursor = connection.cursor()

        # Find history record and connected payment
        cursor.execute("""
            SELECT ph.payment_id
            FROM PaymentHistory ph
            INNER JOIN Payments p
                ON p.id = ph.payment_id
            WHERE ph.id = %s
            AND p.user_id = %s
        """, (
            history_id,
            current_user.id
        ))

        row = cursor.fetchone()

        if not row:

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Payment history not found."
            }), 404

        payment_id = row[0]

        # -------------------------------------------------
        # UPDATE PAYMENT HISTORY
        # -------------------------------------------------

        cursor.execute("""
            UPDATE PaymentHistory
            SET
                amount = %s,
                payment_method = %s,
                payment_date = %s
            WHERE id = %s
        """, (
            new_amount,
            new_method,
            new_date,
            history_id
        ))

        # -------------------------------------------------
        # RECALCULATE TOTAL PAID
        # -------------------------------------------------

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM PaymentHistory
            WHERE payment_id = %s
        """, (
            payment_id,
        ))

        total_paid = float(cursor.fetchone()[0])

        # -------------------------------------------------
        # GET TOTAL PAYMENT AMOUNT
        # -------------------------------------------------

        cursor.execute("""
            SELECT amount
            FROM Payments
            WHERE id = %s
            AND user_id = %s
        """, (
            payment_id,
            current_user.id
        ))

        payment_row = cursor.fetchone()

        if not payment_row:

            connection.rollback()

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Main payment not found."
            }), 404

        total_amount = float(payment_row[0])

        # -------------------------------------------------
        # VALIDATE TOTAL
        # -------------------------------------------------

        if total_paid > total_amount:

            connection.rollback()

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "error": "Total payments cannot exceed the rent amount."
            }), 400

        # -------------------------------------------------
        # DETERMINE STATUS
        # -------------------------------------------------

        if total_paid >= total_amount:

            status = "Paid"

        elif total_paid > 0:

            status = "Partially Paid"

        else:

            status = "Not Paid"

        # -------------------------------------------------
        # UPDATE MAIN PAYMENT
        # -------------------------------------------------

        cursor.execute("""
            UPDATE Payments
            SET
                paid_amount = %s,
                status = %s,
                payment_method = %s,
                paid_date = %s
            WHERE id = %s
            AND user_id = %s
        """, (
            total_paid,
            status,
            new_method,
            new_date,
            payment_id,
            current_user.id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "message": "Payment history updated successfully!",
            "paid_amount": total_paid,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )