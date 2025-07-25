from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
from helpers import login_required, apology, extension
import email_validator 
from pathlib import Path
from uuid import uuid4

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
AVATARS_FOLDER = UPLOAD_FOLDER / "avatars"
POSTS_FOLDER = UPLOAD_FOLDER / "posts"
for folder in [UPLOAD_FOLDER, AVATARS_FOLDER, POSTS_FOLDER]:
    folder.mkdir(exist_ok=True, parents=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
DEFAULT_AVATAR_PIC = AVATARS_FOLDER / "default_avatar.jpg"
ALLOWED_EXTS = {".png", ".jpeg", ".jpg"}

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DB_NAME = "faran.db"
MAX_USERNAME_LEN = 30

# @app.after_request
# def after_request(response):
#     """Ensure responses aren't cached"""
#     response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     response.headers["Expires"] = 0
#     response.headers["Pragma"] = "no-cache"
#     return response

@app.route("/")
@login_required
def index():
    return redirect("/home")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()
        email = request.form.get("email")
        password = request.form.get("password")
        repassword = request.form.get("re-password")
        profile_picture = request.files.get("profile-picture")

        # form validation
        if not username:
            return apology("Must provide username", 403)
        
        if not email:
            return apology("Must provide email address", 403)

        if not password:
            return apology("Must provide password", 403)
        
        if not repassword:
            return apology("Must provide password twice", 403)
        
        if password != repassword:
            return apology("Make sure you provided the same password twice", 400)
        
        if len(username) > MAX_USERNAME_LEN:
            return apology(f"Your username may not be longer than {MAX_USERNAME_LEN} chars", 403)

        with sqlite3.connect(DB_NAME) as connection:
            cursor = connection.cursor()
            rows = cursor.execute("SELECT username, email FROM users WHERE username = ? OR email = ?", (username, email)).fetchall()

        # check if the username or the email is in the DB
        for username_db, email_db in rows:
            if username == username_db:
                return apology(f"The username {username} is already registered, try logging in", 409)
                # returning 409 to indicate conflict
            if email == email_db:
                return apology(f"The email {email} is already registered, try logging in", 409)

        # check if the email provided is a valid email
        try:
            emailinfo = email_validator.validate_email(email, check_deliverability=True)
            email = emailinfo.normalized
        except email_validator.EmailNotValidError as e:
            apology("Please enter a valid email", 403)

        # TODO: if it is not too hard send them an email with a verification code

        password = generate_password_hash(password)

        # insert the data into the DB
        if profile_picture:
            # check the avatars extension
            if not extension(profile_picture, ALLOWED_EXTS):
                return apology("Your profile picture must contain the following extensions only:\npng, jpg", 415)
            
            # first we must enter what we have from the user into the database in order to have a uid which we can later use as the image name
            with sqlite3.connect(DB_NAME) as connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (username, password, email, creation_date) VALUES (?, ?, ?, ?)", (username, password, email, datetime.now()))
                connection.commit()

                user_id = cursor.execute("SELECT user_id FROM users WHERE username = ?", (username, )).fetchone()[0]

            # secure the filename using secure_file name from werkzeug
            ext = Path(profile_picture.filename).suffix.lower()
            filename = secure_filename(f"{str(user_id)}{ext}")

            # save the file into the upload/avatars
            filepath = AVATARS_FOLDER  / filename
            profile_picture.save(filepath)

            with sqlite3.connect(DB_NAME) as connection:
                cursor = connection.cursor()

                cursor.execute("UPDATE users SET avatar = ? WHERE user_id = ?", (str(filename), user_id))
        else:
            with sqlite3.connect(DB_NAME) as connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (username, password, email, creation_date) VALUES (?, ?, ?, ?)", (username, password, email, datetime.now()))
                connection.commit()

        return redirect("/")
    else:
        return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip().lower()
        password = request.form.get("password")

        if not username:
            return apology("Must provide username", 403)

        if not password:
            return apology("Must provide password", 403)
        
        # make sure that username exists in the db and the hashed password is the same as the one stored in the DB
        with sqlite3.connect(DB_NAME) as connection: 
            cursor = connection.cursor()
            row = cursor.execute("SELECT user_id, password FROM users WHERE username = ?", (username, )).fetchone()

        if not row:
            return apology(f"The username {username} does not exist try signing up", 403)

        if not check_password_hash(row[1], password):
            return apology("Incorrect password", 403)
    
        session["user_id"] = row[0]

        return redirect("/")
    else:
        return render_template("login.html")
    
@app.route("/logout")
def logout():
    session.clear()

    return redirect("/")

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":   
        caption = request.form.get("caption")
        picture = request.files.get("picture")

        if not caption:
            return apology("Must provide caption", 400)
        
        if not picture:
            return apology("Must provide picture", 400)
        
        if not extension(picture, ALLOWED_EXTS):
            return apology("Your profile picture must contain the following extensions only:\npng, jpg", 415)
        
        ext = Path(picture.filename).suffix.lower()
        filename = secure_filename(uuid4().hex + ext)
        filepath = POSTS_FOLDER / filename

        picture.save(filepath)

        with sqlite3.connect(DB_NAME) as connection:
            cursor = connection.cursor()

            cursor.execute("INSERT INTO uploads (caption, picture, uploader_id, creation_date) VALUES (?, ?, ?, ?)", (caption, filename, session["user_id"], datetime.now()))

        return redirect("/")
    else:
        return render_template("upload.html")

@app.route("/my_profile")
def my_profile():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        username = cursor.execute("SELECT username FROM users WHERE user_id = ?", (session["user_id"], )).fetchone()[0]

    return redirect(f"/user/{username}")

@app.route("/home")
def home():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # select the people the user is following
        followings_ids = cursor.execute("SELECT following_id FROM follows WHERE follower_id = ?", (session["user_id"], )).fetchall()
        followings_ids = [row[0] for row in followings_ids]

        # if they dont have anyone followed
        if not followings_ids:
            return apology("follow someone to get view their recent posts in your home page", 200)

        # select 5 latest posts from each person along with captions and 
        placeholder = ",".join("?" * len(followings_ids))
        q = f"SELECT users.avatar, users.username, uploads.caption, uploads.picture, uploads.creation_date FROM uploads JOIN users ON uploads.uploader_id = users.user_id WHERE uploader_id IN ({placeholder}) ORDER BY uploads.creation_date DESC LIMIT 5 "
        rows = cursor.execute(q, followings_ids).fetchall()

        if not rows:
            return apology("None of your followings have posted anything", 200)

        posts = []
        for row in rows:
            post = {}
            post["avatar"] = row[0]
            post["username"] = row[1]
            post["caption"] = row[2]
            post["picture"] = row[3]
            post["date"] = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S.%f").strftime("%B %d, %Y")
            posts.append(post)

        # load the posts into the home page based on date (newer posts must be upper)
        return render_template("home.html", posts=posts)

@app.route("/explore")
def explore():
    return apology("TODO", 500)

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("username").strip()

        if not query:
            return apology("You did not search for anything", 400)
    
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            results = cursor.execute("SELECT username, avatar FROM users WHERE username LIKE ? ORDER BY username DESC", (f"{query}%", )).fetchall()

        if not results:
            empty = ""
            return render_template("search.html", empty=empty)
        
        rows = []
        for row in results:
            tmp = {}
            tmp["username"] = row[0]
            tmp["picture"] = row[1]
            rows.append(tmp)

        return render_template("search.html", rows=rows)
    else:
        return render_template("search.html")
    
@app.route("/user/<string:username>")
def user_profile(username):
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.cursor()

        user_id = cursor.execute("SELECT user_id FROM users WHERE username = ?", (username, )).fetchone()[0]
        avatar = cursor.execute("SELECT avatar FROM users WHERE username = ?", (username, )).fetchone()[0]
        posts_count = cursor.execute("SELECT COUNT(*) FROM uploads WHERE uploader_id = ?", (user_id, )).fetchone()[0]

        # count the number of followings and followers
        followers = cursor.execute("SELECT COUNT(*) FROM follows WHERE following_id = ?", (user_id, )).fetchone()[0]
        followings = cursor.execute("SELECT COUNT(*) FROM follows WHERE follower_id = ?", (user_id, )).fetchone()[0]

        datas = cursor.execute("SELECT picture, caption FROM uploads WHERE uploader_id = ? ORDER BY creation_date DESC", (user_id, )).fetchall()
        posts = []
        for data in datas:
            tmp = {}
            tmp["picture"] = data[0]
            tmp["caption"] = data[1]
            posts.append(tmp)

        if session["user_id"] == user_id:
            # this means that the user is visiting their own profile, so no follow_button
            return render_template("profile.html", username=username, avatar=avatar, posts_count=posts_count, posts=posts, followings=followings, followers=followers)

        # check the follows table, based on that change the value of follow_button
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            row = cursor.execute("SELECT 1 FROM follows WHERE following_id = ? AND follower_id = ?", (user_id, session["user_id"])).fetchone()
            if row:
                visitor_has_page_followed = row[0]
            else:
                visitor_has_page_followed = False

            row = cursor.execute("SELECT 1 FROM follows WHERE following_id = ? AND follower_id = ?", (session["user_id"], user_id)).fetchone()
            if row:    
                page_has_visitor_followed = row[0]
            else:
                page_has_visitor_followed = False

        if visitor_has_page_followed:
            follow_button = "unfollow"
        elif page_has_visitor_followed:
            follow_button = "follow back"
        elif not visitor_has_page_followed and not page_has_visitor_followed:
            follow_button = "follow"

    return render_template("profile.html", username=username, avatar=avatar, posts_count=posts_count, posts=posts, follow_button=follow_button, followings=followings, followers=followers)

@app.route("/follow/<string:username>", methods=["POST"])
@login_required
def follow(username):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT user_id FROM users WHERE username = ?", (username, )).fetchone()

        if not row:
            return apology("Such user does not exist", 404)
        
        user_id = row[0]

        # check if the user is trying to self follow
        if session["user_id"] == user_id:
            return apology("You cannot follow yourself", 403)

        # check if the user already has the person they are trying to follow, followd
        already_followed = cursor.execute("SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?", (session["user_id"], user_id)).fetchone()

        if already_followed:
            return apology("You are already following this person", 400)
        
        cursor.execute("INSERT INTO follows (follower_id, following_id) VALUES (?, ?)", (session["user_id"], user_id))

    return redirect(request.referrer or "/")

@app.route("/unfollow/<string:username>", methods=["POST"])
@login_required
def unfollow(username):
    with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT user_id FROM users WHERE username = ?", (username, )).fetchone()

            if not row:
                return apology("Such user does not exist", 404)
            
            user_id = row[0]

            # check if the user is trying to self unfollow
            if session["user_id"] == user_id:
                return apology("You cannot unfollow yourself", 403)
            
            # check if the user already has the person they are trying to unfollow, followed
            already_followed = cursor.execute("SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?", (session["user_id"], user_id)).fetchone()

            if not already_followed:
                return apology("You are not following this person, and you cannot unfollow them when not having them followed", 400)
            
            cursor.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", (session["user_id"], user_id))

    return redirect(request.referrer or "/")

@app.route("/<string:username>/followings")
@login_required
def followings(username):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        user_id = cursor.execute("SELECT user_id FROM users WHERE username = ?", (username, )).fetchone()

        if not user_id:
            return apology("Such user does not exist", 400)
        else:
            user_id = user_id[0]

        data = cursor.execute("SELECT following_id FROM follows WHERE follower_id = ?", (user_id, )).fetchall()

        following_ids = []
        for row in data:
            following_ids.append(row[0])

        if following_ids == []:
            return apology("No followings", 200)

        placeholder = ",".join("?" * len(following_ids))
        q = f"SELECT username FROM users WHERE user_id IN ({placeholder})"
        data = cursor.execute(q, following_ids).fetchall()

        usernames = []
        for row in data:
            usernames.append(row[0])

        return render_template("list.html", list_type="Followings", usernames=usernames)

@app.route("/<string:username>/followers")
@login_required
def followers(username):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        user_id = cursor.execute("SELECT user_id FROM users WHERE username = ?", (username, )).fetchone()

        if not user_id:
            return apology("Such user does not exist", 400)
        else:
            user_id = user_id[0]

        data = cursor.execute("SELECT follower_id FROM follows WHERE following_id = ?", (user_id, )).fetchall()

        followers_ids = []
        for row in data:
            followers_ids.append(row[0])

        if followers_ids == []:
            return apology("No followings", 200)

        placeholder = ",".join("?" * len(followers_ids))
        q = f"SELECT username FROM users WHERE user_id IN ({placeholder})"
        data = cursor.execute(q, followers_ids).fetchall()

        usernames = []
        for row in data:
            usernames.append(row[0])

        return render_template("list.html", list_type="Followers", usernames=usernames)