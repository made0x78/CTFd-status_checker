#!/usr/bin/env python3
import threading
import time
import queue
import os
import stat
import sys
import subprocess
import json
import copy
import re
import datetime
import traceback

config = None
checker_dict = None
runner = None

def read_JSON(filename):
    try:
        with open(filename, "rb") as f:
            data = json.load(f)
            return data
    except Exception as e:
        return None

def check_flag(msg):
    global config
    flag = re.findall(config["flag_regex"], str(msg))
    if len(flag) == 1:
        return True
    return False

def get_timestamp():
    return datetime.datetime.now()

def get_checker_dict():
    checker_path = "./exploits/"
    global checker_dict
    checker_dict = {}

    for path, dirs, files in os.walk(checker_path):
        path_splitted = path.split(os.sep)
        category = path_splitted[2]
        for f in files:
            if f.startswith("exploit"):
                checker_location = path + "/" + f
                challenge_name = path_splitted[3]

                if category in checker_dict.keys():
                    checker_dict[category][challenge_name] = {"location": checker_location, "status": "error", "msg": "", "timestamp": get_timestamp(), "action": "refresh"}
                else:
                    checker_dict[category] = {}
                    checker_dict[category][challenge_name] = {"location": checker_location, "status": "error", "msg": "", "timestamp": get_timestamp(), "action": "refresh"}
    return checker_dict


def execute_checker(checker_location, temp_config):
    checker_file = "./" + os.path.basename(checker_location)
    path = os.path.dirname(checker_location)
    
    try:
        st = os.stat(checker_location)
        os.chmod(checker_location, st.st_mode | stat.S_IEXEC)
        try:
            result = subprocess.check_output(checker_file, cwd=path, stderr=subprocess.STDOUT, timeout=temp_config["timeout"])
            return (True, result)
        except subprocess.TimeoutExpired:
            return (False, "Timeout")
        except subprocess.CalledProcessError as exception:
            msg = "Exit-Code: %d Output: %s" % (exception.returncode, exception.output)
            return (False, msg)
        except:
            return (False, traceback.format_exc())
    except:
        return (False, traceback.format_exc())

class TaskQueue(queue.Queue):
    def __init__(self, num_workers=10):
        queue.Queue.__init__(self)
        self.num_workers = num_workers
        self.start_workers()

    def add_task(self, task):
        challenge_name = task[0]
        checker_category = task[1]
        if checker_dict[checker_category][challenge_name]["action"] != "queued":
            checker_dict[checker_category][challenge_name]["action"] = "queued"
            self.put(task)
            return True
        else:
            return False

    def start_workers(self):
        for i in range(self.num_workers):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()

    def worker(self):
        global checker_dict
        global config
        while True:
            task = self.get()
            challenge_name = task[0]
            checker_category = task[1]
            checker_location = checker_dict[checker_category][challenge_name]["location"]

            # Config overwrite
            path = os.path.dirname(checker_location)
            checker_config_path = path + "/config.json"
            temp_config = copy.deepcopy(config)

            if os.path.isfile(checker_config_path):
                # load config, overwrite some config e.g. timeout
                checker_config = read_JSON(checker_config_path)

                for key in checker_config:
                    if key in temp_config:
                        temp_config[key] = checker_config[key] # "whitelist" approach

            count = 1
            while count <= temp_config["retries"]:
                # Execute Script with timeout
                result = execute_checker(checker_location, temp_config)
                # Check if flag is in stdout
                if result[0] and check_flag(result[1]):
                    checker_dict[checker_category][challenge_name]["status"] = "success"
                    checker_dict[checker_category][challenge_name]["msg"] = ""
                    break
                elif result[0]:
                    checker_dict[checker_category][challenge_name]["status"] = "error"
                    checker_dict[checker_category][challenge_name]["msg"] = "Flag not found or too many returned"
                else:
                    checker_dict[checker_category][challenge_name]["status"] = "error"
                    checker_dict[checker_category][challenge_name]["msg"] = result[1] # error message
                count += 1
            checker_dict[checker_category][challenge_name]["timestamp"] = get_timestamp() # update timestamp
            checker_dict[checker_category][challenge_name]["action"] = "refresh"
            self.task_done()

class Runner(threading.Thread):
    def __init__(self, workers, delay):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = TaskQueue(workers)
        self.delay = delay

    def run(self):
        global checker_dict
        while True:
            # scheduled update
            # add all to queue
            for category in checker_dict:
                for checker in checker_dict[category]:
                    self.queue.add_task((checker, category))
            time.sleep(self.delay)

def init():  
    global config
    config = read_JSON("./checker_config.json")

    global checker_dict
    checker_dict = get_checker_dict()

    global runner
    runner = Runner(workers=config["workers"], delay=config["delay_in_seconds"])
    runner.start()