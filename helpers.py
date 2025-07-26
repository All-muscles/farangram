from flask import render_template, redirect, session
from functools import wraps
import requests
from pathlib import Path
from werkzeug.datastructures import FileStorage
from typing import Iterable
from datetime import datetime

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def apology(error_text: str, error_code: int = 500):
    url = "https://api.memegen.link/images/doge/" + error_text + "/" + str(error_code)
    return render_template("apology.html", url=url, error=error_text + "Error code: " + str(error_code))

def extension(file: FileStorage, allowed_exts: Iterable[str]) -> bool:
    """To check if a filename ends within a list of particular extensions
    returns true if the extension is in the iterable 
    
    Args:
        file (str): any str
        allowed_exts : any iterable

    Returns:
        bool: returns true if the extension is in the allowed_exts var 
    """
    ext = Path(file.filename).suffix.lower()

    if ext in allowed_exts:
        return True
    
    return False

def format_date(date: str):
    return datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f").strftime("%B %d, %Y")