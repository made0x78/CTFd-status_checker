from flask import render_template, request, Blueprint, Flask, jsonify
from CTFd import utils
from CTFd.utils.user import is_admin
from CTFd.plugins import register_user_page_menu_bar
from CTFd.utils.decorators import (
    during_ctf_time_only,
    require_verified_emails,
    authed_only
)
import requests
import json
import sys

def load(app):
    app.db.create_all()
    status_checker_blueprint = Blueprint("status_checker_blueprint", __name__, template_folder="templates")
    register_user_page_menu_bar("Status", "status")

    def get_status():
        url = "http://192.168.0.4"
        try:
            response = requests.get(url)
        except requests.ConnectionError:
           return render_template("error.html", error="Connection error. Please report.")
        if response.text == "Error":
            return render_template("error.html", error="JSON data error. Please report.") 
        try:
            data = json.loads(response.text)
        except ValueError:
            return render_template("error.html", error="JSON decode error. Please report.")
        return data

    @status_checker_blueprint.route("/status", methods=["GET", "POST"])
    @during_ctf_time_only
    @require_verified_emails
    @authed_only
    def view_status():

        if request.method == "POST":
            category = request.form.get("category")
            challenge = request.form.get("challenge")
            
            if category is None or challenge is None:
                return render_template("status.html", data=res, msg="", admin=is_admin())

            try:
                url = "http://192.168.0.4/refresh"
                response = requests.get(url, params={"category": category, "challenge": challenge})

                res = get_status()
                if response.text == "Error":
                    return render_template("status.html", data=res, msg="Something went wrong. Please try again.", admin=is_admin())
                elif response.text == "Queued":
                    return render_template("status.html", data=res, msg="Your request is already queued. Please wait.", admin=is_admin())
                elif response.text.startswith("Wait"):
                    msg = "Please wait for %d seconds." % int(response.text[4:])
                    return render_template("status.html", data=res, msg=msg, admin=is_admin())
            except requests.ConnectionError:
                return render_template("status.html", data=res, msg="Connection error. Please try again later.", admin=is_admin())
            return render_template("status.html", data=res, msg="Your request is queued. Please wait.", admin=is_admin())
        
        res = get_status()
        return render_template("status.html", data=res, msg="", admin=is_admin())

    app.register_blueprint(status_checker_blueprint)
