from flask import Flask, render_template, request, redirect
import sqlite3, hashlib

app = Flask(__name__)

# ✅ Create DB if not exists
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    phone TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()

init_db()

# ✅ Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 🟢 Login Page
@app.route("/")
def home():
    return render_template("login.html")

# 🟢 Signup Page
@app.route("/signup")
def signup_page():
    return render_template("signup.html")

# 🟢 Handle Signup
@app.route("/do_signup", methods=["POST"])
def do_signup():
    phone = request.form.get("phone")
    password = request.form.get("password")

    if not phone or not password:
        return render_template("error.html", message="⚠ Phone & Password required")

    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (phone, password) VALUES (?, ?)", 
                  (phone, hash_password(password)))
        conn.commit()
        conn.close()
        return redirect("/")  # after signup → login
    except sqlite3.IntegrityError:
        conn.close()
        return render_template("error.html", message="⚠ Phone already registered. Please login.")

# 🟢 Handle Login
@app.route("/login", methods=["POST"])
def login():
    phone = request.form.get("phone")
    password = request.form.get("password")

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE phone = ?", (phone,))
    row = c.fetchone()
    conn.close()

    if row and row[0] == hash_password(password):
        # ✅ Redirect to Quote Generator App
        return redirect("https://quote-generator-blond-seven.vercel.app/")
    else:
        return render_template("error.html", message="❌ Invalid phone or password!")

if __name__ == "__main__":
    app.run(debug=True)
