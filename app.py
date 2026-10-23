from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
import smtplib
import base64
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

app = Flask(__name__)
app.secret_key = "secret123"
crime_df = pd.read_csv("crime_data.csv")

# EMAIL CONFIG
SENDER_EMAIL = "bagwanibrahim802@gmail.com"
APP_PASSWORD = "puvbwjtzibueldmh"


# ---------------- DATABASE ----------------
def create_table():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            username TEXT,
            password TEXT,
            phone1 TEXT,
            phone2 TEXT,
            phone3 TEXT
        )
    """)

    conn.commit()
    conn.close()

create_table()


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("login.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username=? AND password=?",
                (username, password))

    user = cur.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        return redirect("/dashboard")
    else:
        flash("Invalid Username or Password")
        return redirect("/")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name")
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (name,email,username,password)
        VALUES (?,?,?,?)
    """, (name, email, username, password))

    conn.commit()
    conn.close()

    return redirect("/")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT phone1, phone2, phone3
        FROM users WHERE id=?
    """, (session["user_id"],))

    data = cur.fetchone()
    conn.close()

    contacts = [c for c in data if c and str(c).strip()] if data else []

    return render_template("dashboard.html", contacts=contacts)


# ---------------- SOS EMAIL FUNCTION ----------------
def send_email(receiver, lat, lon, image_bytes):

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver
    msg["Subject"] = "🚨 EMERGENCY SOS ALERT"

    location_link = f"https://www.google.com/maps?q={lat},{lon}"

    body = f"""
🚨 EMERGENCY ALERT 🚨

Live Location:
{location_link}

Camera snapshot attached.
"""

    msg.attach(MIMEText(body, "plain"))

    if image_bytes:
        img = MIMEImage(image_bytes)
        img.add_header("Content-Disposition", "attachment", filename="sos.png")
        msg.attach(img)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()


# ---------------- SOS ----------------
@app.route("/send_sos", methods=["POST"])
def send_sos():

    if "user_id" not in session:
        return redirect("/")

    data = request.get_json()

    lat = data.get("lat")
    lon = data.get("lon")
    image = data.get("image")

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT phone1, phone2, phone3
        FROM users WHERE id=?
    """, (session["user_id"],))

    rows = cur.fetchone()
    conn.close()

    contacts = [c for c in rows if c and str(c).strip()] if rows else []

    if not contacts:
        return "❌ No emergency contacts found"

    image_bytes = None

    if image:
        try:
            header, encoded = image.split(",", 1)
            image_bytes = base64.b64decode(encoded)
        except:
            image_bytes = None

        # send emails safely
    for email in contacts:

        if "@" not in str(email):
            print("Skipping invalid contact:", email)
            continue

        try:
            send_email(email, lat, lon, image_bytes)
        except Exception as e:
            print("Email error:", e)

    return "🚨 SOS SENT SUCCESSFULLY"
@app.route("/crime_info")
def crime_info():

    area = request.args.get("area", "").strip().lower()

    for _, row in crime_df.iterrows():

        if str(row["area"]).strip().lower() == area:

            return {
                "status": "Found",
                "crime": row["crime_type"],
                "risk": row["risk_level"]
            }

    return {
        "status": "Unknown",
        "crime": "No data available",
        "risk": "Low"
    }

    
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)