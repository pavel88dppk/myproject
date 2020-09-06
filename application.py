import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import requests
import urllib.parse


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # only the get method

    # prevent for error - new user hasn't got any subjects; hence the sumavg[0]["SUM(average)"] is classified as a NoneType variable
    try:
        # selecting the distinct subjects
        realsubjects = db.execute("SELECT DISTINCT(name) FROM subjectss WHERE id = :id", id=session["user_id"])

        # selecting de facto all marks
        subjects = db.execute("SELECT * FROM subjectss WHERE id = :id", id=session["user_id"])
        avg = db.execute("SELECT * FROM avg WHERE id = :id", id=session["user_id"])
        counter = 0
        for i in range(len(realsubjects)):
            averagee = db.execute("SELECT average FROM avg WHERE subject = :subject AND id = :id", subject=realsubjects[i]["name"], id=session["user_id"])
            if averagee[0]["average"] != 0:
                counter += 1
            else:
                counter += 0
        # counting the overall average
        sumavg = db.execute("SELECT SUM(average) as sum FROM avg WHERE id = :id", id=session["user_id"])
        overallavg = round(sumavg[0]["sum"]/counter, 2)
    except:
        # if new user
        overallavg = 0

    # returning the 'homepage' template with all marks
    body = "body"
    return render_template("index.html", subjects=subjects, realsubjects=realsubjects, avg=avg, overallavg=overallavg, bodyclass=body)


@app.route("/add-subject", methods=["GET", "POST"])
@login_required
def addsubject():
    """Adds subject"""
    # post method
    if request.method == "POST":

        # for easiness
        subject = request.form.get("name")

        if not subject:
            subject = "You must provide the name of the subject"
            return render_template("add.html", error=subject)

        # errorhandling so that no two subjects have the same name - quite a stupid way; however, probably the only working :D
        try:
            subjects = db.execute("SELECT name FROM subjectss WHERE id = :id AND name = :name", id=session["user_id"], name=subject)
            if not subjects:
                db.execute("INSERT INTO subjectss (id, name) VALUES (:id, :subject)", id=session["user_id"], subject=subject,)
                db.execute("INSERT INTO avg (id, subject) VALUES(:id, :subject)", id=session["user_id"], subject=subject)
                return redirect("/")
        except:
            db.execute("INSERT INTO subjectss (id, name) VALUES (:id, :subject)", id=session["user_id"], subject=subject,)
            db.execute("INSERT INTO avg (id, subject) VALUES(:id, :subject)", id=session["user_id"], subject=subject)
            return redirect("/")

        exist = "subject already exists"
        return render_template("add.html", error=exist)
    else:
        # get method
        return render_template("add.html")


@app.route("/add-marks", methods=["GET", "POST"])
@login_required
def addmarks():
    """Adds marks"""

    # if the method is get, it moves the user to that page
    if request.method == "GET":
        # finds all subjects used in the select block
        subjects = db.execute("SELECT DISTINCT(name) FROM subjectss WHERE id = :id", id=session["user_id"])
        return render_template("addmark.html", subjects=subjects)
    else:
        # for clarity :)
        subject = request.form.get("subject")
        grade = request.form.get("grade")
        weight = request.form.get("weight")
        points = request.form.get("points")
        maxpoints = request.form.get("maxpoints")
        event = request.form.get("event")

        subjects = db.execute("SELECT DISTINCT(name) FROM subjectss WHERE id = :id", id=session["user_id"])

        # the input fields grade, weight, points and maxpoints have to be filled with integer
        try:
            if int(grade) > 0:
                grade = grade
        except:
            integer = "Grade must be an integer"
            return render_template("addmark.html", error=integer, subjects=subjects)

        try:
            if float(weight) > 0:
                weight = weight
        except:
            integer = "Weight must be an integer"
            return render_template("addmark.html", error=integer, subjects=subjects)

        if points:
            try:
                if int(points) > 0:
                    points = points
            except:
                integer = "Points must be an integer"
                return render_template("addmark.html", error=integer, subjects=subjects)

            try:
                if int(maxpoints) > 0:
                    maxpoints = maxpoints
            except:
                integer = "Maximum Points must be an integer"
                return render_template("addmark.html", error=integer, subjects=subjects)

        # no need of checking, it is set as "required"

        # errorhandling, you cannot divide zero by zero!
        if not points:
            db.execute("INSERT INTO subjectss (id, name, grade, weight, marks, outofmarks, percentage, event) VALUES (:id, :name, :grade, :weight, :marks, :outofmarks, :percentage, :event)",
                       id=session["user_id"], name=subject, grade=grade, weight=weight, marks=None, outofmarks=None, percentage=None, event=event)
        else:
            # if the points are included, the percentage can't be set to null
            db.execute("INSERT INTO subjectss (id, name, grade, weight, marks, outofmarks, percentage, event) VALUES (:id, :name, :grade, :weight, :marks, :outofmarks, :percentage, :event)",
                       id=session["user_id"], name=subject, grade=grade, weight=weight, marks=points, outofmarks=maxpoints, percentage=round((int(points)/int(maxpoints))*100, 1), event=event)

        # seting the average after adding the mark
        average = db.execute(
            "SELECT ROUND(SUM(grade * weight) / SUM(weight), 0) as average FROM subjectss WHERE name = :name AND id = :id", name=subject, id=session["user_id"])
        db.execute("UPDATE avg SET average = :average WHERE subject = :subject AND id = :id",
                   average=average[0]["average"], subject=subject, id=session["user_id"])

        # redirecting user back to homepage
        return redirect("/")


@app.route("/delete-subject", methods=["GET", "POST"])
@login_required
def delete():
    """Deletes subject"""

    # code for post method
    if request.method == "POST":

        # user inputs only the name of subject
        subject = request.form.get("name")

        # checking for user input
        subjects = db.execute("SELECT DISTINCT(name) FROM subjectss WHERE id = :id", id=session["user_id"])
        if not subject:
            subject = "You must provide the name of subject"
            return render_template("deletemark.html", error=subject, subjects=subjects)

        # deleting all data somewhat realted to the subject whose name matches user's desire
        db.execute("DELETE FROM subjectss WHERE name = :name AND id = :id", name=subject, id=session["user_id"])
        db.execute("DELETE FROM avg WHERE subject = :subject AND id = :id", subject=subject, id=session["user_id"])

        # redirects user to the homepage
        return redirect("/")
    else:
        # if the method is get, it finds all subjects which then appear in the select block of html
        subjects = db.execute("SELECT DISTINCT(name) FROM subjectss WHERE id = :id", id=session["user_id"])
        return render_template("delete.html", subjects=subjects)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in user"""
    # the code is based on CS50 staff's solution from finance
    # Forget any user id
    session.clear()

    # code for post method
    if request.method == "POST":
        # calrity
        username = request.form.get("username")
        password = request.form.get("password")

        # checking user input
        if not username:
            username = "You must provide a username"
            return render_template("login.html", error=username)
        if not password:
            password = "You must provide a password"
            return render_template("login.html", error=password)

        # Query database for username
        rows = db.execute("SELECT * FROM userss WHERE username = :username",
                          username=username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            apology = "invalid username and/or password"
            return render_template("login.html", error=apology)

        # starting the session of the user
        session["user_id"] = rows[0]["id"]

        # Redirect user to the index.html template
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user id
    session.clear()
    # redirect to homepage; therefore, to login page because the index page requires the user to be logged in
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # code for the post method
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")

        # checking for user input
        if not username:
            username = "You must provide a username"
            return render_template("register.html", error=username)
        if not password:
            password = "You must provide a password"
            return render_template("register.html", error=password)
        if not email:
            email = "You must provide an email"
            return render_template("register.html", error=email)
        # checking whether the passwords match
        if password != request.form.get("confirmation"):
            confirm = "Passwords don't match"
            return render_template("register.html", error=confirm)

        # generating the password hash for security
        hash = generate_password_hash(password)

        # checking for the uniqueness of username
        try:
            new_user = db.execute("INSERT INTO userss (username, hash, email) VALUES(:username, :hash, :email)",
                                  username=username, hash=hash, email=email)
        except:
            exist = "Username already exists"
            return render_template("register.html", error=exist)

        # starting the session
        session["user_id"] = new_user

        flash("Registered!")

        # redirecting the user to the index page
        return redirect("/")

    else:
        # if the method is get, then return the corresponding page
        return render_template("register.html")


@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
    """Change the password of a user"""
    # code for regarding the post method
    if request.method == "POST":
        newpass = request.form.get("newpass")
        conf = request.form.get("confirmation")

        # checking for user input
        if not newpass:
            password = "You must provide a new password"
            return render_template("changepass.html", error=password)
        # checking if the passwords match
        if newpass != conf:
            confirm = "Passwords don't match"
            return render_template("changepass.html", error=confirm)

        # safety precautions
        hash = generate_password_hash(newpass)
        # updating the password
        db.execute("UPDATE userss SET hash = :hash WHERE id = :id", hash=hash, id=session["user_id"])
        # redirecting the user back to the index page
        return redirect("/")

    else:
        # if the method is get, then return the changepass file
        return render_template("changepass.html")


@app.route("/delete-mark", methods=["GET", "POST"])
@login_required
def deletemark():
    """Delete Mark"""
    # what happens if the method is post
    if request.method == "POST":

        # for clarity
        subject = request.form.get("subject")
        grade = request.form.get("grade")
        weight = request.form.get("weight")
        name = request.form.get("name")

        # checking for input
        subjects = db.execute("SELECT DISTINCT(name) FROM subjectss WHERE id = :id", id=session["user_id"])
        if not subject:
            subject = "You must provide the name of subject"
            return render_template("deletemark.html", error=subject, subjects=subjects)
        if not grade:
            grade = "You must provide the grade"
            return render_template("deletemark.html", error=grade, subjects=subjects)
        if not weight:
            weight = "You must provide the weight of the mark"
            return render_template("deletemark.html", error=weight, subjects=subjects)

        if not name:
            is_in_db = db.execute("SELECT * FROM subjectss WHERE name = :subject AND id = :id AND grade = :grade AND weight = :weight",
                                  id=session["user_id"], subject=subject, grade=grade, weight=weight)
            if not is_in_db:
                not_in_db = "The mark you want to delete does not exist"
                return render_template("deletemark.html", error=not_in_db, subjects=subjects)
            else:
                if len(is_in_db) > 1:
                    # deleting the mark from the sqlite database - only one mark!!!
                    db.execute("DELETE FROM subjectss WHERE name = :subject AND id = :id AND grade = :grade AND weight = :weight",
                               id=session["user_id"], subject=subject, grade=grade, weight=weight)

                    for i in range(len(is_in_db)-1):
                        db.execute("INSERT INTO subjectss (id, name, grade, weight) VALUES (:id, :name, :grade, :weight)",
                                   id=session["user_id"], name=subject, grade=grade, weight=weight)

                else:
                    db.execute("DELETE FROM subjectss WHERE name = :subject AND id = :id AND grade = :grade AND weight = :weight",
                               id=session["user_id"], subject=subject, grade=grade, weight=weight)

                # updating the average of the student
                average = db.execute(
                    "SELECT ROUND(SUM(grade * weight) / SUM(weight), 0) as average FROM subjectss WHERE name = :name AND id = :id", name=subject, id=session["user_id"])
                average = average[0]["average"]
                # if no marks are left, set average to zero
                if average is None:
                    average = 0
                # update the average
                db.execute("UPDATE avg SET average = :average WHERE subject = :subject AND id = :id",
                           average=average, subject=subject, id=session["user_id"])
                # redirect the user to homepage
                return redirect("/")
        else:

            # checking whether the deleted mark exists
            is_in_db = db.execute("SELECT * FROM subjectss WHERE name = :subject AND id = :id AND event = :name AND grade = :grade AND weight = :weight",
                                  name=name, id=session["user_id"], subject=subject, grade=grade, weight=weight)
            if not is_in_db:
                not_in_db = "The mark you want to delete does not exist"
                return render_template("deletemark.html", error=not_in_db, subjects=subjects)
            else:
                if len(is_in_db) > 1:
                    # deleting the mark from the sqlite database
                    db.execute("DELETE FROM subjectss WHERE name = :subject AND id = :id AND event = :name AND grade = :grade AND weight = :weight",
                               name=name, id=session["user_id"], subject=subject, grade=grade, weight=weight)

                    for i in range(len(is_in_db) - 1):
                        db.execute("INSERT INTO subjectss (id, name, grade, weight, event) VALUES (:id, :name, :grade, :weight, :event)",
                                   id=session["user_id"], name=subject, grade=grade, weight=weight, event=name)
                else:
                    db.execute("DELETE FROM subjectss WHERE name = :subject AND id = :id AND event = :name AND grade = :grade AND weight = :weight",
                               name=name, id=session["user_id"], subject=subject, grade=grade, weight=weight)

                # updating the average of the student
                average = db.execute(
                    "SELECT SUM(grade * weight) / SUM(weight) as average FROM subjectss WHERE name = :name AND id = :id", name=subject, id=session["user_id"])
                average = average[0]["average"]

                # if no marks are left, set average to zero
                if average is None:
                    average = 0
                # update the average
                db.execute("UPDATE avg SET average = :average WHERE subject = :subject AND id = :id",
                           average=average, subject=subject, id=session["user_id"])
                # redirect the user to homepage
                return redirect("/")
    else:
        # searching for all subjects to be included in the select form in the html file
        subjects = db.execute("SELECT DISTINCT(name) FROM subjectss WHERE id = :id", id=session["user_id"])
        # returning the requested template
        return render_template("deletemark.html", subjects=subjects)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return render_template("index.html", bigerror=e)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)