from flask import Flask, jsonify, request
import json
import checker
import time
import datetime
app = Flask(__name__)

def update_actions():
    # update actions based on timestamp
    now = datetime.datetime.now()
    for category in checker.checker_dict:
        for challenge in checker.checker_dict[category]:
            if checker.checker_dict[category][challenge]["action"] == "queued":
                continue
            delta = now-checker.checker_dict[category][challenge]["timestamp"]
            if delta.seconds < checker.config["up_to_date_interval_in_seconds"]:
                checker.checker_dict[category][challenge]["action"] = str(checker.config["up_to_date_interval_in_seconds"]-delta.seconds) # up to date for x seconds
            else:
                checker.checker_dict[category][challenge]["action"] = "refresh"

@app.route("/", methods=["GET"])
def get_status():
    try:
        update_actions()
        return jsonify(checker.checker_dict)
    except TypeError:
        return "Error"

@app.route("/refresh", methods=["GET"])
def refresh():
    category = request.args.get("category")
    challenge = request.args.get("challenge")

    if category is None or challenge is None:
        return "Error"
    
    if category in checker.checker_dict and challenge in checker.checker_dict[category]:
        if checker.checker_dict[category][challenge]["action"] == "queued":
            return "Queued"
        delta = checker.get_timestamp()-checker.checker_dict[category][challenge]["timestamp"]
        if delta.seconds > checker.config["up_to_date_interval_in_seconds"]:
            if checker.runner.queue.add_task((challenge, category)):
                return "Ok"
            else:
                return "Queued"
        else:
            return "Wait" + str(checker.config["up_to_date_interval_in_seconds"]-delta.seconds)
    else:
        return "Error"

if __name__ == "__main__":
    # start checker module
    checker.init()

    # start server to serve current status in json
    app.run(host="192.168.0.4", port=80, debug=False)
