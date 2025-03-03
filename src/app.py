from flask import Flask, render_template, request, jsonify, Response
import pandas as pd
import json
from datetime import datetime

app = Flask(__name__)

DB_FILE = "db.json"

# Load database
def load_db():
    with open(DB_FILE, "r") as file:
        return json.load(file)

# Save database
def save_db(data):
    with open(DB_FILE, "w") as file:
        json.dump(data, file, indent=4)

def update_warranty(mfg_old, warranty_till_old):
    current_date = datetime.now()
    current_month = current_date.strftime("%b").lower()  # Example: "mar"
    current_year = current_date.year  # Example: 2025

    # Extract warranty years from old data
    try:
        mfg_old_year = int(mfg_old.split("-")[1])  # Extracting year from "Jan-2023"
        warranty_old_year = int(warranty_till_old.split("-")[1])  # Extracting year from "Jul-2028"
        warranty_duration = warranty_old_year - mfg_old_year  # Calculate warranty duration
    except (IndexError, ValueError):
        return None, None  # Return None if parsing fails

    # Update manufacturing date and warranty till date
    new_mfg = f"{current_month}-{current_year}"
    new_warranty_till = f"{current_month}-{current_year + warranty_duration}"

    return new_mfg, new_warranty_till

@app.route("/seller")
def index():
    data = load_db()
    customer_count = sum(1 for item in data if "Customer_Name" in item and "Phone_Number" in item)
    # Extract customers who have bought products
    customers = [
        {"Customer_Name": item["Customer_Name"], "Phone_Number": item["Phone_Number"], "serial_number": item["serial_number"]}
        for item in data if "Customer_Name" in item and "Phone_Number" in item
    ]

    return render_template("index.html", customer_count=customer_count, customers=customers)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/seller/add_customer", methods=["GET", "POST"])
def add_customer():
    message = ""
    error = False  # Default: No error

    if request.method == "POST":
        phone = request.form.get("phone")
        name = request.form.get("name")
        serial_number = request.form.get("serial")

        if not phone or not name or not serial_number:
            message = "All fields are required!"
            error = True  # This is an error
            return render_template("add_customer.html", message=message, error=error)

        try:
            serial_number = int(serial_number)  # Convert to int
        except ValueError:
            message = "Invalid serial number format!"
            error = True  # This is an error
            return render_template("add_customer.html", message=message, error=error)

        data = load_db()

        for item in data:
            if item["serial_number"] == serial_number:
                if item["Status"] == "Sold":
                    message = "This serial number is already sold!"
                    error = True  # This is an error
                else:
                    # Update manufacturing date and warranty based on previous data
                    new_mfg, new_warranty_till = update_warranty(item["mfg"], item["warranty_till"])

                    if new_mfg and new_warranty_till:
                        item["Customer_Name"] = name
                        item["Phone_Number"] = phone
                        item["Status"] = "Sold"
                        item["mfg"] = new_mfg
                        item["warranty_till"] = new_warranty_till
                        save_db(data)
                        message = "✅ Product successfully sold with updated warranty!"
                        error = False  # This is a success message
                    else:
                        message = "Error processing warranty details."
                        error = True  # This is an error

                return render_template("add_customer.html", message=message, error=error)

        message = "Error: No serial number found."
        error = True  # This is an error

    return render_template("add_customer.html", message=message, error=error)

@app.route("/download_excel")
def download_excel():
    data = load_db()

    # Extract customers who have bought products
    customers = [
        {"Customer Name": item["Customer_Name"], "Phone Number": item["Phone_Number"], "Serial Number": item["serial_number"]}
        for item in data if "Customer_Name" in item and "Phone_Number" in item
    ]

    if not customers:
        return "No customer data available.", 404

    # Convert to DataFrame
    df = pd.DataFrame(customers)

    # Convert DataFrame to Excel format
    excel_data = df.to_csv(index=False)  # Using CSV format as an alternative to Excel

    # Send response with Excel file
    response = Response(
        excel_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=customers.csv"}
    )
    return response

@app.route("/get_qr_detail_view", methods=["GET"])
def product_lookup():
    serial_number = request.args.get("serial_number")
    product_info = None
    error = None

    if serial_number:
        data = load_db()
        product_info = next((p for p in data if str(p["serial_number"]) == serial_number), None)
        if not product_info:
            error = "❌ Product not found!"

    return render_template("product_lookup.html", product=product_info, error=error)

# ✅ API Endpoint to get product details in JSON format
@app.route("/api/product/<serial_number>")
def get_product(serial_number):
    data = load_db()
    product_info = next((p for p in data if str(p["serial_number"]) == serial_number), None)
    if product_info:
        return jsonify(product_info)
    return jsonify({"error": "Product not found"}), 404

@app.route("/authenticate", methods=["GET", "POST"])
def authenticate():
    message = None

    if request.method == "POST":
        serial_number = request.form.get("serial_number")
        phone_number = request.form.get("phone_number")

        if serial_number and phone_number:
            data = load_db()
            product_info = next(
                (p for p in data if str(p["serial_number"]) == serial_number and str(p["Phone_Number"]) == phone_number),
                None
            )
            if product_info:
                message = "✅ Product is original"
                is_original = True
            else:
                message = "❌ Can't find record in our database"
                is_original = False

    return render_template("authenticate.html", message=message)

@app.route("/logout")
def logout():
    return render_template("logout.html")

if __name__ == "__main__":
    app.run(debug=False)
