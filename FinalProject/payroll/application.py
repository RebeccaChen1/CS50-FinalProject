from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir



from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///payroll.db")

@app.route("/")
@login_required
def index():
    
    # if user is manager, shows each user, hours worked for each, total amount owed to each, 
    # and amount owed in total to all employees
    if session["user_id"] == 1:
        users = db.execute("SELECT * FROM users")
        total = db.execute("SELECT sum(cash) FROM users")[0]["sum(cash)"]
        return render_template("manager.html", users = users, Total = total)
        
        
    # only prints stock from current user
    usernum = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["id"]
    # stores info from all of users hours
    hours = db.execute("SELECT * FROM hours WHERE User=:id", id = usernum)
    # stores amount of cash user is owed
    cash = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["cash"]
    

    return render_template("index.html", hours = hours, Total = cash)

@app.route("/hours", methods=["GET", "POST"])
@login_required
def hours():
    """Buy shares of stock."""
    if request.method == "POST":
    
        if not request.form.get("hours"):
            apology = "Must provide hours."
            return render_template("apology.html", apology = apology)
        if not request.form.get("wage"):
            apology = "Must provide wage."
            return render_template("apology.html", apology = apology)
        if not request.form.get("date"):
            apology = "Must provide date."
            return render_template("apology.html", apology = apology)
        if float(request.form.get("wage")) < 0 or float(request.form.get("hours")) < 0:
            apology = "Must provide positive integer."
            return render_template("apology.html", apology = apology)

        cost = float(request.form.get("hours")) * float(request.form.get("wage"))
        
        
        # inserts info into history table
        db.execute("INSERT INTO history (date, hours, wage, user, total) VALUES(:date, :hours, :wage, :user, :total)",
        date = request.form.get("date"), 
        hours = request.form.get("hours"), 
        wage = request.form.get("wage"), 
        user = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["id"],
        total = cost)
        
        # inserts info into hours table
        db.execute("INSERT INTO hours (date, hours, wage, user, total) VALUES(:date, :hours, :wage, :user, :total)",
        date = request.form.get("date"), 
        hours = request.form.get("hours"), 
        wage = request.form.get("wage"), 
        user = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["id"],
        total = cost)

        
        # updates amount of cash user has
        db.execute("UPDATE users SET cash = ':cash' WHERE id=:id", 
        cash = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["cash"] + cost,
        id = session["user_id"])
        
        # updates amount of hours user has worked
        db.execute("UPDATE users SET hours = ':hours' WHERE id=:id", 
        hours = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["hours"] + int(request.form.get("hours")),
        id = session["user_id"])
        
        return redirect(url_for("index"))
        
    else:
        return render_template("hours.html")
        
    


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            apology = "Must provide username."
            return render_template("apology.html", apology = apology)

        # ensure password was submitted
        elif not request.form.get("password"):
            apology = "Must provide password."
            return render_template("apology.html", apology = apology)

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["password"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST":
        
        if not request.form.get("username"):
            apology = "Must provide username."
            return render_template("apology.html", apology = apology)
            
        elif not request.form.get("password"):
            apology = "Must provide password."
            return render_template("apology.html", apology = apology)
            
        if db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username")) != []:
            apology = "Username taken."
            return render_template("apology.html", apology = apology)
            
        if request.form.get("password") != request.form.get("confirm password"):
            apology = "Passwords must match."
            return render_template("apology.html", apology = apology)
        
        # hashes password    
        hash = pwd_context.encrypt(request.form.get("password"))
        
        # inserts username and hashed password into users table
        db.execute("INSERT INTO users (username, password) VALUES(:username, :password)",
        username=request.form.get("username"), 
        password = hash) 
        
        return redirect(url_for("index"))
        
    else:
        return render_template("register.html")
        

@app.route("/clear", methods=["GET", "POST"])
@login_required
def clear():
    """Sell shares of stock."""
    if request.method == "POST":
        
        # if the user is the manager, they can reset numbers for all users
        if session["user_id"] == 1:
            db.execute("DELETE FROM hours")
            db.execute("UPDATE users SET cash = ':cash'", 
            cash = 0)
            db.execute("UPDATE users SET hours = ':hours'", 
            hours = 0)
        
        
        # if user only wants to delete shifts from a certain date
        if request.form.get("shift"):
            # subtracts hours from total hours for use for all shifts that day
            db.execute("UPDATE users SET hours =':hours' WHERE id=:id", 
            hours = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["hours"] - db.execute("SELECT sum(hours) FROM hours WHERE User=:id AND date=:date", id = session["user_id"], date = request.form.get("shift"))[0]["sum(hours)"],
            id = session["user_id"])
            # subtracts cash from total cash for user for all shifts that day
            db.execute("UPDATE users SET cash = ':cash' WHERE id=:id", 
            cash = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["cash"] - db.execute("SELECT sum(total) FROM hours WHERE User=:id AND date=:date", id = session["user_id"], date = request.form.get("shift"))[0]["sum(total)"],
            id = session["user_id"])
            # deletes shifts from select date from history table
            db.execute("DELETE FROM history WHERE user=:id AND date=:date", id = session["user_id"], date = request.form.get("shift"))
            # deletes shifts from select date from history table
            db.execute("DELETE FROM hours WHERE user=:id AND date=:date", id = session["user_id"], date = request.form.get("shift"))
            
            return redirect(url_for("index"))
        
        # sets cash value to zero
        db.execute("UPDATE users SET cash = ':cash' WHERE id=:id", 
        cash = 0,
        id = session["user_id"])
        
        # sets hours to zero
        db.execute("UPDATE users SET hours = ':hours' WHERE id=:id", 
        hours = 0,
        id = session["user_id"])
        
        # delete shift from table
        db.execute("DELETE FROM hours WHERE user=:id", id = session["user_id"])
        
        
        return redirect(url_for("index"))
        
    else:
        return render_template("clear.html")

@app.route("/history")
@login_required
def history():
    """Show history of work."""
    
     # only prints shifts from current user
    usernum = db.execute("SELECT * FROM users WHERE id=:id", id = session["user_id"])[0]["id"]
    
    # stores shift data into hours
    hours = db.execute("SELECT * FROM history WHERE User=:id", id = usernum)
    
    # calculates total amount of cash ever paid to user
    cash = db.execute("SELECT sum(total) FROM history WHERE User=:id", id = session["user_id"])[0]["sum(total)"]
    
    return render_template("history.html", hours = hours, Total = cash)
    