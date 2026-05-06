from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required

auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/login")
def login():
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    return redirect(url_for("index"))
