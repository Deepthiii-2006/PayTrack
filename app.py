from flask import Flask, render_template, request, jsonify
from database import get_connection

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


# TEST DATABASE
@app.route("/test-db")
def test_db():

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM Payments")
        count = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return f"✅ SQL Connected! Payments records: {count}"

    except Exception as e:
        return f"❌ Database Error: {e}"


# ADD PAYMENT TO SQL
@app.route("/add-payment", methods=["POST"])
def add_payment():

    try:

        data = request.json

        name = data["name"]
        payment_type = data["payment_type"]
        amount = data["amount"]
        due_date = data["due_date"]

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO Payments
            (name, payment_type, amount, due_date, status, paid_amount)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            payment_type,
            amount,
            due_date,
            "Not Paid",
            0
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

    # GET PAYMENTS FROM SQL
@app.route("/payments")
def get_payments():
    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Get all payments
        cursor.execute("""
            SELECT
                id,
                name,
                payment_type,
                amount,
                due_date,
                status,
                paid_amount
            FROM Payments
            ORDER BY id
        """)

        rows = cursor.fetchall()

        payments = []

        for row in rows:

            payment_id = row[0]

            # Get payment history for this payment
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
                "payments": history
            })

        cursor.close()
        connection.close()

        return jsonify(payments)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

   # MARK PAYMENT AS FULLY PAID
# MARK PAYMENT AS FULLY PAID
@app.route("/mark-paid/<int:payment_id>", methods=["PUT"])
def mark_paid(payment_id):

    try:
        data = request.json

        method = data["method"]
        payment_date = data["date"]

        connection = get_connection()
        cursor = connection.cursor()

        # Get existing payment details
        cursor.execute("""
            SELECT amount, paid_amount
            FROM Payments
            WHERE id = %s
        """, (payment_id,))

        row = cursor.fetchone()

        if not row:
            return jsonify({
                "success": False,
                "error": "Payment not found"
            }), 404

        amount = float(row[0])
        paid_amount = float(row[1] or 0)

        pending = amount - paid_amount

        if pending <= 0:
            return jsonify({
                "success": False,
                "error": "Payment is already fully paid."
            }), 400

        # Mark remaining amount as paid
        cursor.execute("""
            UPDATE Payments
            SET
                status = 'Paid',
                paid_amount = amount,
                payment_method = %s,
                paid_date = %s
            WHERE id = %s
        """, (
            method,
            payment_date,
            payment_id
        ))

        # Add this payment to PaymentHistory
        cursor.execute("""
            INSERT INTO PaymentHistory
            (payment_id, amount, payment_method, payment_date)
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
     # RECORD PARTIAL PAYMENT
# RECORD PARTIAL PAYMENT
@app.route("/partial-payment/<int:payment_id>", methods=["PUT"])
def partial_payment(payment_id):

    try:
        data = request.json

        amount = float(data["amount"])
        method = data["method"]
        payment_date = data["date"]

        connection = get_connection()
        cursor = connection.cursor()

        # Get current payment details
        cursor.execute("""
            SELECT amount, paid_amount
            FROM Payments
            WHERE id = %s
        """, (payment_id,))

        row = cursor.fetchone()

        if not row:
            return jsonify({
                "success": False,
                "error": "Payment not found"
            }), 404

        total_amount = float(row[0])
        current_paid = float(row[1] or 0)

        pending = total_amount - current_paid

        if amount <= 0:
            return jsonify({
                "success": False,
                "error": "Invalid payment amount."
            }), 400

        if amount > pending:
            return jsonify({
                "success": False,
                "error": "Amount cannot be greater than pending amount."
            }), 400

        new_paid = current_paid + amount

        if new_paid >= total_amount:
            status = "Paid"
        else:
            status = "Partially Paid"

        # Update main payment
        cursor.execute("""
            UPDATE Payments
            SET
                paid_amount = %s,
                status = %s
            WHERE id = %s
        """, (
            new_paid,
            status,
            payment_id
        ))

        # Save individual payment
        cursor.execute("""
            INSERT INTO PaymentHistory
            (payment_id, amount, payment_method, payment_date)
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
            "paid_amount": new_paid,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

        # Get current paid amount and total amount
        cursor.execute("""
            SELECT amount, paid_amount
            FROM Payments
            WHERE id = ?
        """, (payment_id,))

        row = cursor.fetchone()

        if not row:
            return jsonify({
                "success": False,
                "error": "Payment not found"
            }), 404

        total_amount = float(row[0])
        current_paid = float(row[1] or 0)

        new_paid = current_paid + amount

        if new_paid > total_amount:
            return jsonify({
                "success": False,
                "error": "Payment amount cannot exceed the rent amount."
            }), 400

        if new_paid >= total_amount:
            status = "Paid"
        else:
            status = "Partially Paid"

        cursor.execute("""
            UPDATE Payments
            SET
                paid_amount = ?,
                status = ?
            WHERE id = ?
        """, (
            new_paid,
            status,
            payment_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "paid_amount": new_paid,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    # EDIT PAYMENT
@app.route("/edit-payment/<int:payment_id>", methods=["PUT"])
def edit_payment(payment_id):

    try:
        data = request.json

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
        """, (
            name,
            payment_type,
            amount,
            due_date,
            payment_id
        ))

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

    # EDIT PAYMENT HISTORY
@app.route("/edit-payment-history/<int:history_id>", methods=["PUT"])
def edit_payment_history(history_id):

    try:
        data = request.json

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

        # Get the existing payment history record
        cursor.execute("""
            SELECT payment_id
            FROM PaymentHistory
            WHERE id = %s
        """, (history_id,))

        row = cursor.fetchone()

        if not row:
            return jsonify({
                "success": False,
                "error": "Payment history not found."
            }), 404

        payment_id = row[0]

        # Update the individual payment
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

        # Calculate total paid again
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM PaymentHistory
            WHERE payment_id = %s
        """, (payment_id,))

        total_paid = float(cursor.fetchone()[0])

        # Get total payment amount
        cursor.execute("""
            SELECT amount
            FROM Payments
            WHERE id = %s
        """, (payment_id,))

        payment_row = cursor.fetchone()

        if not payment_row:
            return jsonify({
                "success": False,
                "error": "Main payment not found."
            }), 404

        total_amount = float(payment_row[0])

        # Don't allow history payments to exceed total amount
        if total_paid > total_amount:

            connection.rollback()

            return jsonify({
                "success": False,
                "error": "Total payments cannot exceed the rent amount."
            }), 400

        # Determine status
        if total_paid >= total_amount:
            status = "Paid"
        elif total_paid > 0:
            status = "Partially Paid"
        else:
            status = "Not Paid"

        # Update main Payments table
        cursor.execute("""
            UPDATE Payments
            SET
                paid_amount = %s,
                status = %s
            WHERE id = %s
        """, (
            total_paid,
            status,
            payment_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "paid_amount": total_paid,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
if __name__ == "__main__":
    app.run(debug=True)