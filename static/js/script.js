let rents = [];
let selectedRent = null;

// LOAD PAYMENTS FROM SQL
async function loadPayments() {

    try {

        const response = await fetch("/payments");

        const data = await response.json();

        if (data.error) {

            console.error("SQL Error:", data.error);

            return;
        }


        rents = data.map(function(payment) {

            return {

                id: payment.id,

                name: payment.name,

                type: payment.payment_type,

                monthlyRent: payment.amount,

                dueDate: payment.due_date,

                paid: payment.paid_amount,

                payments: payment.payments || []

            };

        });


        displayRents();

        updateDashboard();

        displayReminders();

    }

    catch (error) {

        console.error(
            "Could not load payments:",
            error
        );

    }
}

function formatDate(date) {
    if (!date) return "Not Set";

    const parts = date.split("-");

    return `${parts[2]}/${parts[1]}/${parts[0]}`;
}


// TODAY'S DATE
function getToday() {
    const today = new Date();

    return today.toISOString().split("T")[0];
}


// SHOW TODAY
document.getElementById("today").innerText =
    new Date().toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });


// PAGE NAVIGATION
function showPage(page) {

    document.querySelectorAll(".page").forEach(function(section) {
        section.classList.add("hidden");
    });

    document.getElementById(page).classList.remove("hidden");

    if (page === "payments") {
        displayPayments();
    }

    if (page === "reminders") {
        displayReminders();
    }
}


// OPEN ADD RENT
function openRentForm() {
    document.getElementById("rentModal").style.display = "flex";
}


// CLOSE ADD RENT
function closeRentForm() {
    document.getElementById("rentModal").style.display = "none";
}


// ADD RENT
// ADD RENT
async function addRent() {

    const name =
        document.getElementById("personName").value.trim();

    const type =
        document.getElementById("rentType").value;

    const rent =
        Number(document.getElementById("monthlyRent").value);

    const dueDate =
        document.getElementById("dueDate").value;


    if (!name || !rent || !dueDate) {

        alert("Please fill all details.");

        return;
    }


    try {

        const response = await fetch("/add-payment", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                name: name,

                payment_type: type,

                amount: rent,

                due_date: dueDate

            })

        });


        const result = await response.json();


        if (!result.success) {

            alert(
                "❌ Payment could not be added.\n\n" +
                result.error
            );

            return;
        }


        closeRentForm();


        document.getElementById("personName").value = "";

        document.getElementById("monthlyRent").value = "";

        document.getElementById("dueDate").value = "";


        alert(
            "Payment added successfully! ✅"
        );


        // Reload records from SQL
        await loadPayments();

    }

    catch (error) {

        alert(
            "❌ Server connection error.\n\n" +
            error
        );

    }
}


// DISPLAY RENT
  // DISPLAY RENT
function displayRents() {

    const list =
        document.getElementById("rentList");

    const list2 =
        document.getElementById("rentList2");

    let html = "";

    if (rents.length === 0) {

        html = `
            <p>No rent records yet.</p>
        `;

    } else {

        rents.forEach(function(rent) {

            const pending =
                Math.max(
                    rent.monthlyRent - rent.paid,
                    0
                );

            let status = "Not Paid";
            let statusClass = "pending";

            if (rent.paid >= rent.monthlyRent) {

                status = "Paid";
                statusClass = "paid";

            } else if (rent.paid > 0) {

                status = "Partially Paid";
                statusClass = "partial";
            }

            html += `

                <div class="rent-card">

                    <div class="rent-top">

                        <div>

                            <h3>
                                ${rent.name}
                            </h3>

                            <p>
                                ${rent.type}
                            </p>

                        </div>

                        <span class="status ${statusClass}">
                            ${status}
                        </span>

                    </div>


                    <div class="rent-details">

                        <div>

                            <span>
                                Monthly Rent
                            </span>

                            <strong>
                                ₹${rent.monthlyRent}
                            </strong>

                        </div>


                        <div>

                            <span>
                                Paid
                            </span>

                            <strong>
                                ₹${rent.paid}
                            </strong>

                        </div>


                        <div>

                            <span>
                                Pending
                            </span>

                            <strong>
                                ₹${pending}
                            </strong>

                        </div>


                        <div>

                            <span>
                                Due Day
                            </span>

                            <strong>
                                ${formatDate(rent.dueDate)}
                            </strong>

                        </div>

                    </div>


                    <div class="rent-buttons">

                        ${
                            pending > 0
                            ?

                            `
                            <button
                                class="paid-button"
                                onclick="markFullPaid(${rent.id})">

                                ✅ Paid

                            </button>


                            <button
                                class="partial-button"
                                onclick="openPartialPayment(${rent.id})">

                                🟡 Partially Paid

                            </button>
                            `

                            :

                            `
                            <button
                                class="paid-button"
                                disabled>

                                ✅ Paid

                            </button>
                            `
                        }


                        <button
                            class="edit-button"
                            onclick="editRent(${rent.id})">

                            ✏️ Edit

                        </button>

                    </div>


                    ${
                        rent.payments.length > 0

                        ?

                        `

                        <div class="payment-history">

                            <h4>
                                Payment History
                            </h4>

                            ${getPaymentHistory(rent)}

                        </div>

                        `

                        :

                        ""
                    }

                </div>

            `;

        });

    }


    list.innerHTML = html;

    list2.innerHTML = html;
}

// FULL PAYMENT
async function markFullPaid(id) {

    const rent =
        rents.find(function(item) {
            return item.id === id;
        });

    if (!rent) {
        return;
    }

    const pending =
        rent.monthlyRent - rent.paid;

    if (pending <= 0) {
        return;
    }

    const method =
        prompt(
            "How did they pay?\n\n" +
            "Type: Cash, UPI or Bank Transfer"
        );

    if (!method) {
        return;
    }

    const response =
    await fetch("/mark-paid/" + id, {

        method: "PUT",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({

            method: method,

            date: getToday()

        })

    });

    const result =
        await response.json();

    if (!result.success) {

        alert(
            "❌ Could not update SQL.\n\n" +
            result.error
        );

        return;
    }


    // UPDATE WEBSITE
    rent.paid =
        rent.monthlyRent;


    rent.payments.push({

        amount: pending,

        method: method,

        date: getToday()

    });


    displayRents();

    updateDashboard();

    displayPayments();

    displayReminders();


    alert(
        "Payment marked as PAID! ✅\n\n" +
        "Amount: ₹" + pending
    );
}


// OPEN PARTIAL PAYMENT
function openPartialPayment(id) {

    selectedRent =
        rents.find(function(item) {
            return item.id === id;
        });


    if (!selectedRent) {
        return;
    }


    document.getElementById("paymentPerson")
        .innerText =
        selectedRent.name;


    document.getElementById("paymentRent")
        .innerText =
        "₹" + selectedRent.monthlyRent;


    document.getElementById("paymentAlreadyPaid")
        .innerText =
        "₹" + selectedRent.paid;


    document.getElementById("paymentRemaining")
        .innerText =
        "₹" +
        (
            selectedRent.monthlyRent -
            selectedRent.paid
        );


    document.getElementById("paymentAmount")
        .value = "";


    // AUTOMATICALLY USE TODAY'S DATE
    document.getElementById("paymentDate")
        .value =
        getToday();


    document.getElementById("paymentModal")
        .style.display =
        "flex";
}


// CLOSE PAYMENT
function closePaymentForm() {

    document.getElementById("paymentModal")
        .style.display =
        "none";
}


// RECORD PARTIAL PAYMENT
// RECORD PARTIAL PAYMENT
async function recordPayment() {

    const amount =
        Number(
            document.getElementById("paymentAmount").value
        );

    const method =
        document.getElementById("paymentMethod").value;

    const date = getToday();

    if (!amount || amount <= 0) {

        alert("Please enter the amount received.");

        return;
    }

    const pending =
        selectedRent.monthlyRent -
        selectedRent.paid;

    if (amount > pending) {

        alert(
            "Amount cannot be greater than the pending rent."
        );

        return;
    }

    try {

        const response = await fetch(
            "/partial-payment/" + selectedRent.id,
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json"
                },

               body: JSON.stringify({

    amount: amount,

    method: method,

    date: date

})
            }
        );

        const result = await response.json();

        if (!result.success) {

            alert(
                "❌ Payment could not be saved.\n\n" +
                result.error
            );

            return;
        }

        // Update website
        selectedRent.paid =
            result.paid_amount;

        selectedRent.payments.push({

            amount: amount,

            method: method,

            date: date

        });

        closePaymentForm();

        displayRents();

        updateDashboard();

        displayPayments();

        displayReminders();

        if (result.status === "Paid") {

            alert(
                "Full rent received! ✅"
            );

        } else {

            alert(
                "Partial payment recorded! 🟡"
            );
        }

    } catch (error) {

        alert(
            "❌ Server connection error.\n\n" +
            error
        );
    }
}

// PAYMENT HISTORY
function getPaymentHistory(rent) {

    let history = "";

    rent.payments.forEach(function(payment) {

        history += `

            <div class="history-row">

                <span>
                    ₹${payment.amount}
                </span>

                <span>
                    ${payment.method}
                </span>

                <span>
                    ${payment.date}
                </span>

                <button
                    class="edit-button"
                    onclick="editPayment(${payment.id})">

                    ✏️ Edit

                </button>

            </div>

        `;

    });

    return history;
}
// EDIT INDIVIDUAL PAYMENT
async function editPayment(historyId) {

    let payment = null;
    let selectedRent = null;

    // Find the payment inside rents
    for (const rent of rents) {

        const found = rent.payments.find(function(item) {
            return item.id === historyId;
        });

        if (found) {
            payment = found;
            selectedRent = rent;
            break;
        }
    }

    if (!payment) {

        alert("Payment history not found.");

        return;
    }


    const newAmount = prompt(
        "Enter payment amount:",
        payment.amount
    );

    if (newAmount === null) {
        return;
    }


    const amount = Number(newAmount.trim());

    if (isNaN(amount) || amount <= 0) {

        alert("Please enter a valid amount.");

        return;
    }


    const newMethod = prompt(
        "Enter payment method:",
        payment.method
    );

    if (newMethod === null) {
        return;
    }


    const newDate = prompt(
        "Enter payment date (YYYY-MM-DD):",
        payment.date
    );

    if (newDate === null) {
        return;
    }


    try {

        const response = await fetch(
            "/edit-payment-history/" + historyId,
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    amount: amount,

                    method: newMethod.trim(),

                    date: newDate

                })
            }
        );


        const result = await response.json();


        if (!result.success) {

            alert(
                "❌ Payment could not be edited.\n\n" +
                result.error
            );

            return;
        }


        // Update website data
        payment.amount = amount;

        payment.method = newMethod.trim();

        payment.date = newDate;


        selectedRent.paid =
            result.paid_amount;


        // Update status displays
        displayRents();

        updateDashboard();

        displayPayments();

        displayReminders();


        alert(
            "Payment updated successfully! ✅"
        );

    } catch (error) {

        alert(
            "❌ Server connection error.\n\n" +
            error
        );
    }
}

// DASHBOARD
function updateDashboard() {

    let totalRent = 0;

    let totalPaid = 0;

    let totalPending = 0;


    rents.forEach(function(rent) {

        totalRent += rent.monthlyRent;

        totalPaid += rent.paid;

        totalPending +=
            Math.max(
                rent.monthlyRent -
                rent.paid,
                0
            );

    });


    document.getElementById("totalRent")
        .innerText =
        "₹" + totalRent;


    document.getElementById("totalPaid")
        .innerText =
        "₹" + totalPaid;


    document.getElementById("totalPending")
        .innerText =
        "₹" + totalPending;


    document.getElementById("totalRecords")
        .innerText =
        rents.length;
}


// PAYMENT HISTORY PAGE
function displayPayments() {

    const box =
        document.getElementById("paymentHistory");


    let html = "";


    rents.forEach(function(rent) {

        rent.payments.forEach(function(payment) {

            html += `

                <div class="rent-card">

                    <h3>
                        ${rent.name}
                    </h3>

                    <p>
                        ${rent.type}
                    </p>

                    <br>

                    <strong>
                        ₹${payment.amount}
                    </strong>

                    <p>
                        ${payment.method}
                        •
                        ${payment.date}
                    </p>

                </div>

            `;

        });

    });


    if (!html) {

        html =
            "<p>No payments recorded yet.</p>";

    }


    box.innerHTML = html;
}


// REMINDERS
// 🔔 REMINDERS
function displayReminders() {

    const box = document.getElementById("reminderList");

    let html = "";

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    rents.forEach(function(rent) {

        const pending =
            rent.monthlyRent - rent.paid;

        // Skip fully paid payments
        if (pending <= 0) {
            return;
        }

        const dueDate = new Date(rent.dueDate);
        dueDate.setHours(0, 0, 0, 0);

        const difference =
            Math.ceil(
                (dueDate - today) /
                (1000 * 60 * 60 * 24)
            );

        let status = "";
        let statusClass = "";

        if (difference < 0) {

            // 🔴 OVERDUE
            status = "🔴 OVERDUE";
            statusClass = "overdue";

        } else if (difference === 0) {

            // 🟠 DUE TODAY
            status = "🟠 DUE TODAY";
            statusClass = "due-today";

        } else if (difference === 1) {

            // 🟡 DUE TOMORROW
            status = "🟡 DUE TOMORROW";
            statusClass = "due-tomorrow";

        } else if (difference <= 7) {

            // 🔵 DUE SOON
            status = "🔵 DUE SOON";
            statusClass = "due-soon";

        } else {

            // More than 7 days away
            status = "📅 UPCOMING";
            statusClass = "upcoming";
        }

        html += `

            <div class="rent-card ${statusClass}">

                <h3>
                    ${status} — ${rent.name}
                </h3>

                <p>
                    ${rent.type}
                </p>

                <p>
                    💰 Monthly Rent:
                    ₹${rent.monthlyRent}
                </p>

                <p>
                    ✅ Paid:
                    ₹${rent.paid}
                </p>

                <p>
                    <strong>
                        💸 Pending:
                        ₹${pending}
                    </strong>
                </p>

                <p>
                    📅 Due Date:
                    ${formatDate(rent.dueDate)}
                </p>

            </div>

        `;
    });

    if (!html) {

        html =
            "<p>🎉 No pending payments!</p>";
    }

    box.innerHTML = html;
}


// INITIAL LOAD
loadPayments();
// EDIT RENT
// EDIT RENT
async function editRent(id) {

    const rent = rents.find(function(item) {
        return item.id === id;
    });

    if (!rent) {
        return;
    }

    const newName = prompt(
        "Enter name:",
        rent.name
    );

    if (newName === null) {
        return;
    }

    const newType = prompt(
        "Enter type:",
        rent.type
    );

    if (newType === null) {
        return;
    }

    const newRent = prompt(
        "Enter monthly rent:",
        rent.monthlyRent
    );

    if (newRent === null) {
        return;
    }

    const rentAmount = Number(newRent.trim());

    if (isNaN(rentAmount) || rentAmount <= 0) {

        alert("Please enter a valid rent amount.");

        return;
    }

    const newDueDate = prompt(
        "Enter due date (YYYY-MM-DD):",
        rent.dueDate
    );

    if (newDueDate === null) {
        return;
    }


    try {

        const response = await fetch(
            "/edit-payment/" + id,
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    name: newName.trim(),

                    payment_type: newType.trim(),

                    amount: rentAmount,

                    due_date: newDueDate

                })
            }
        );


        const result = await response.json();


        if (!result.success) {

            alert(
                "❌ Edit could not be saved.\n\n" +
                result.error
            );

            return;
        }


        // Update website
        rent.name = newName.trim();

        rent.type = newType.trim();

        rent.monthlyRent = rentAmount;

        rent.dueDate = newDueDate;


        displayRents();

        updateDashboard();

        displayReminders();


        alert(
            "Rent details updated successfully! ✅"
        );

    } catch (error) {

        alert(
            "❌ Server connection error.\n\n" +
            error
        );
    }
}
// 🔔 BROWSER NOTIFICATION
     // 📊 DASHBOARD
function updateDashboard() {

    let totalRent = 0;
    let totalPaid = 0;
    let totalPending = 0;

    let totalOverdue = 0;
    let totalUpcoming = 0;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    rents.forEach(function(rent) {

        totalRent += rent.monthlyRent;

        totalPaid += rent.paid;

        const pending =
            Math.max(
                rent.monthlyRent - rent.paid,
                0
            );

        totalPending += pending;

        // Only check unpaid payments
        if (pending > 0) {

            const dueDate =
                new Date(rent.dueDate);

            dueDate.setHours(0, 0, 0, 0);

            const difference =
                Math.ceil(
                    (dueDate - today) /
                    (1000 * 60 * 60 * 24)
                );

            // 🔴 OVERDUE
            if (difference < 0) {
                totalOverdue++;
            }

            // 🔵 UPCOMING
            else if (difference >= 0) {
                totalUpcoming++;
            }
        }
    });


    document.getElementById("totalRent")
        .innerText =
        "₹" + totalRent;


    document.getElementById("totalPaid")
        .innerText =
        "₹" + totalPaid;


    document.getElementById("totalPending")
        .innerText =
        "₹" + totalPending;


    document.getElementById("totalRecords")
        .innerText =
        rents.length;


    document.getElementById("totalOverdue")
        .innerText =
        totalOverdue;


    document.getElementById("totalUpcoming")
        .innerText =
        totalUpcoming;
}
