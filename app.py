import os
import sqlite3
import webbrowser
from flask import Flask, render_template, request, redirect, session
from PyPDF2 import PdfReader

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "resumes"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------- DATABASE --------
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        score REAL,
        skills TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------- PDF TEXT --------
def extract_text(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text

# -------- MATCH --------
def match_score(resume_text, job_desc):
    resume_words = set(resume_text.lower().split())
    job_words = set(job_desc.lower().split())

    if len(job_words) == 0:
        return 0, []

    matched = resume_words.intersection(job_words)
    score = (len(matched) / len(job_words)) * 100

    return round(score, 2), list(matched)

# -------- ROUTES --------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        data = cur.fetchone()
        conn.close()

        if data:
            session["user"] = user
            return redirect("/dashboard")
        else:
            return "Invalid Login ❌"

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pwd))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("signup.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    score = None
    skills = None

    if request.method == "POST":
        file = request.files["resume"]
        job_desc = request.form["job_desc"]

        if file:
            path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(path)

            text = extract_text(path)
            score, skills = match_score(text, job_desc)

            conn = sqlite3.connect("users.db")
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO results (username, score, skills) VALUES (?, ?, ?)",
                (session["user"], score, ", ".join(skills))
            )
            conn.commit()
            conn.close()

    # FETCH HISTORY
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT score FROM results WHERE username=?",
        (session["user"],)
    )
    scores = [row[0] for row in cur.fetchall()]

    conn.close()

    return render_template("dashboard.html", score=score, skills=skills, scores=scores)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True)