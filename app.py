from flask import Flask, render_template, request, redirect, session, jsonify
import mysql.connector
from google import genai
import random
import time
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "studentfeedback"


# ---------- DATABASE ----------

def get_db():
           
      print("HOST:", os.getenv("MYSQLHOST"))
      print("PORT:", os.getenv("MYSQLPORT"))
      print("USER:", os.getenv("MYSQLUSER"))
      print("DB:", os.getenv("MYSQLDATABASE"))
      return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),   # <-- changed
       port = int(os.getenv("MYSQLPORT", 3306))
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INT AUTO_INCREMENT PRIMARY KEY,
        fullname VARCHAR(100),
        email VARCHAR(100) UNIQUE,
        mobile VARCHAR(20),
        password VARCHAR(100)
    )
    """)

    cur.execute("""
   CREATE TABLE IF NOT EXISTS feedback(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    rollno VARCHAR(50),
    department VARCHAR(100),
    semester VARCHAR(20),
    teacher VARCHAR(100),
    subject VARCHAR(100),
    rating VARCHAR(20),
    comments TEXT
)
    """)

    conn.commit()
    conn.close()

init_db()


# ---------- LOGIN PAGE ----------

@app.route("/")
def index():
    return render_template("login.html")


# ---------- SIGNUP PAGE ----------

@app.route("/signup")
def signup():
    return render_template("signup.html")


# ---------- REGISTER ----------

@app.route("/register", methods=["POST"])
def register():

    fullname = request.form["fullname"]
    email = request.form["email"]
    mobile = request.form["mobile"]
    password = request.form["password"]

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "INSERT INTO users(fullname,email,mobile,password) VALUES(%s,%s,%s,%s)",
            (fullname, email, mobile, password)
        )
        conn.commit()

    except mysql.connector.IntegrityError:
        conn.close()
        return render_template(
            "signup.html",
            error="Email already exists"
        )

    conn.close()
    return redirect("/")
# ---------- LOGIN ----------

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
    "SELECT * FROM users WHERE email=%s AND password=%s",
    (email,password)
)

    user = cur.fetchone()

    conn.close()

    if user:
        session["user"] = user["fullname"]
        session["email"] = user["email"]   # NEW
        return redirect("/home")

    return render_template(
        "login.html",
        error="Invalid Email or Password"
    )


# ---------- HOME ----------

@app.route("/home")
def home():

    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT * FROM users WHERE email=%s",
        (session["email"],)
    )

    user = cur.fetchone()

    conn.close()

    return render_template("home.html", user=user)

# ---------- FEEDBACK ----------

@app.route("/feedback")
def feedback():

    if "user" not in session:
        return redirect("/")

    return render_template("feedback.html")

# ---------- SUBMIT FEEDBACK ----------

@app.route("/submit", methods=["POST"])
def submit():

    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO feedback
    (name,email,rollno,department,semester,teacher,subject,rating,comments)
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,
    (
        request.form["name"],
        session["email"],          # Logged-in user's email
        request.form["rollno"],
        request.form["department"],
        request.form["semester"],
        request.form["teacher"],
        request.form["subject"],
        request.form["rating"],
        request.form["comments"]
    ))

    conn.commit()
    conn.close()

    return render_template("successfulpage.html")

# ---------- AI CHATBOT ----------

client = genai.Client(api_key="AQ.Ab8RN6JF7WD0XcUe0eKk9JUzEGFFWRH3Gs7dYAwqCdIVhm7Gkg")

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/upload_photo", methods=["POST"])
def upload_photo():

    if "user" not in session:
        return redirect("/")

    file = request.files["photo"]

    if file.filename != "":

        filename = secure_filename(file.filename)

        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db()
        cur = conn.cursor()

        # 👇 Ye wahi code hai jiske baare me tum puch rahe the
        cur.execute(
            "UPDATE users SET profile_photo=%s WHERE email=%s",
            (filename, session["email"])
        )

        conn.commit()
        conn.close()

    return redirect("/studentprofile")

@app.route("/ai")
def ai():

    if "user" not in session:
        return redirect("/")

    return render_template("AIchatbot.html")


@app.route("/chat", methods=["POST"])
def chat():

    message = request.json["message"]

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=message
        )

        return jsonify({
            "reply": response.text
        })

    except Exception as e:
        return jsonify({
            "reply": str(e)
        })

    
# ---------- ADMIN LOGIN PAGE ----------

@app.route("/admin")
def admin():
    return render_template("adminlogin.html")


# ---------- ADMIN LOGIN ----------

@app.route("/adminlogin", methods=["POST"])
def adminlogin():

    username = request.form["username"]
    password = request.form["password"]

    if username == "admin" and password == "admin123":
        session["admin"] = username
        return redirect("/dashboard")

    return render_template(
        "adminlogin.html",
        error="Invalid Username or Password"
    )


# ---------- ADMIN DASHBOARD ----------

@app.route("/dashboard")
def dashboard():

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # -----------------------------
    # Get all feedback
    # -----------------------------

    cursor.execute("""
        SELECT *
        FROM feedback
        ORDER BY id DESC
    """)

    feedbacks = cursor.fetchall()


    # -----------------------------
    # Total Feedback
    # -----------------------------

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM feedback
    """)

    total_feedback = cursor.fetchone()["total"]


    # -----------------------------
    # Total Students
    # -----------------------------

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM users
    """)

    total_students = cursor.fetchone()["total"]


    # -----------------------------
    # Average Rating
    # -----------------------------

    cursor.execute("""
        SELECT rating
        FROM feedback
    """)

    rating_rows = cursor.fetchall()

    rating_values = {
        "Excellent": 5,
        "Very Good": 4,
        "Good": 4,
        "Average": 3,
        "Poor": 2,
        "Very Poor": 1
    }

    numeric_ratings = []

    for row in rating_rows:

        rating = row["rating"]

        if rating in rating_values:

            numeric_ratings.append(
                rating_values[rating]
            )

        else:

            try:
                numeric_ratings.append(
                    float(rating)
                )

            except:
                pass


    if numeric_ratings:

        average_rating = round(
            sum(numeric_ratings) /
            len(numeric_ratings),
            1
        )

    else:

        average_rating = 0


    cursor.close()
    conn.close()


    return render_template(
        "dashboard.html",

        feedbacks=feedbacks,

        total_feedback=total_feedback,

        total_students=total_students,

        average_rating=average_rating
    )

# ---------- REPORT ----------
@app.route("/report")
def report():

    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT * FROM feedback WHERE email=%s",
        (session["email"],)
    )

    feedback = cur.fetchall()

    conn.close()

    return render_template(
        "report.html",
        feedback=feedback
    )

@app.route("/edit/<int:id>")
def edit(id):

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM feedback WHERE id=%s", (id,))
    feedback = cur.fetchone()

    conn.close()

    return render_template("edit.html", feedback=feedback)


@app.route("/update/<int:id>", methods=["POST"])
def update(id):

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    UPDATE feedback
    SET
        name=%s,
        rollno=%s,
        department=%s,
        semester=%s,
        teacher=%s,
        subject=%s,
        rating=%s,
        comments=%s
    WHERE id=%s
    """,
    (
        request.form["name"],
        request.form["rollno"],
        request.form["department"],
        request.form["semester"],
        request.form["teacher"],
        request.form["subject"],
        request.form["rating"],
        request.form["comments"],
        id
    ))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/delete/<int:id>")
def delete(id):

    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
    "DELETE FROM feedback WHERE id=%s",
    (id,)
)

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------- PROFILE ----------

@app.route("/studentprofile")
def studentprofile():

    if "user" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT * FROM users WHERE email=%s",
        (session["email"],)
    )

    user = cur.fetchone()

    conn.close()

    password_changed = request.args.get("password_changed") == "1"

    return render_template(
        "studentprofile.html",
        user=user,
        password_changed=password_changed
    )

# ---------- CHANGE PASSWORD ----------

@app.route("/change_password", methods=["POST"])
def change_password():

    if "user" not in session:
        return redirect("/")

    old_password = request.form["old_password"]
    new_password = request.form["new_password"]

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Current user
    cur.execute(
        "SELECT * FROM users WHERE email=%s",
        (session["email"],)
    )

    user = cur.fetchone()

    # Check old password
    if user["password"] != old_password:
        conn.close()
        return """
        <script>
            alert("Old password is incorrect!");
            window.location.href="/studentprofile";
        </script>
        """

    # Update password
    cur.execute(
        "UPDATE users SET password=%s WHERE email=%s",
        (new_password, session["email"])
    )

    conn.commit()
    conn.close()

    # Show custom popup
    return redirect("/studentprofile?password_changed=1")

# ---------- FORGOT PASSWORD ----------

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return render_template(
                "forgot_password.html",
                error="Email address not found!"
            )

        # Generate 6 digit OTP
        otp = str(random.randint(100000, 999999))

        # Store OTP in session
        session["reset_email"] = email
        session["reset_otp"] = otp
        session["otp_time"] = time.time()

        # For testing: OTP will appear in VS Code terminal
        print("================================")
        print("PASSWORD RESET OTP:", otp)
        print("================================")

        return redirect("/verify_otp")

    return render_template("forgot_password.html")


# ---------- VERIFY OTP ----------

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if "reset_email" not in session:
        return redirect("/forgot_password")

    if request.method == "POST":

        entered_otp = request.form["otp"]

        saved_otp = session.get("reset_otp")
        otp_time = session.get("otp_time")

        # OTP valid for 5 minutes
        if otp_time and time.time() - otp_time > 300:

            session.pop("reset_otp", None)
            session.pop("otp_time", None)

            return render_template(
                "verify_otp.html",
                error="OTP expired. Please request a new OTP."
            )

        if entered_otp == saved_otp:

            session["otp_verified"] = True

            return redirect("/reset_password")

        return render_template(
            "verify_otp.html",
            error="Invalid OTP!"
        )

    return render_template("verify_otp.html")


# ---------- RESET PASSWORD ----------

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    if "reset_email" not in session:
        return redirect("/forgot_password")

    if not session.get("otp_verified"):
        return redirect("/verify_otp")

    if request.method == "POST":

        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:

            return render_template(
                "reset_password.html",
                error="Passwords do not match!"
            )

        if len(new_password) < 6:

            return render_template(
                "reset_password.html",
                error="Password must be at least 6 characters!"
            )

        email = session["reset_email"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (new_password, email)
        )

        conn.commit()

        cur.close()
        conn.close()

        # Clear reset session
        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        session.pop("otp_time", None)
        session.pop("otp_verified", None)

        return render_template("reset_success.html")

    return render_template("reset_password.html")

# ---------- ABOUT ----------

@app.route("/about")
def about():
    return render_template("about.html")


# ---------- LOGOUT ----------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True) 
