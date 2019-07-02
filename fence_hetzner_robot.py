#!/usr/bin/python -tt
import atexit
import logging
import requests
import sys
import time

sys.path.append("/usr/share/fence")
from fencing import atexit_handler, check_input, process_input, show_docs, \
    run_delay, fence_action, all_opt, fail_usage, EC_GENERIC_ERROR, fail, EC_TIMED_OUT

try:
    from httplib import HTTPSConnection
except ImportError:
    from http.client import HTTPSConnection


PATIENCE = 120 # seconds to wait for server deactivation
ROBOT_HOST = "robot-ws.your-server.de"


class RobotConnection(object):
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        self._api_endpoint = "https://%s" % ROBOT_HOST

    def endpoint(self):
        return self._api_endpoint


class Robot(object):
    def __init__(self, user, passwd):
        self.conn = RobotConnection(user, passwd)

    def endpoint(self):
        return self.conn.endpoint()

    def activate_rescue(self, server_id):
        url = "%s/boot/%s/rescue" % (self.endpoint(), server_id)
        r = requests.post(
            url, data={'os': 'linux', 'arch': '64'}, auth=self.auth())
        logging.debug("Activate rescue response: %r", r)
        if not r.ok:
            logging.error("Error in activate rescue: %r", r)
            fail(EC_GENERIC_ERROR)

    def deactivate_rescue(self, server_id):
        url = "%s/boot/%s/rescue" % (self.endpoint(), server_id)
        r = requests.delete(url,  auth=self.auth())
        logging.debug("Deactivate rescue response: %r", r)
        if not r.ok:
            logging.error("Error in deactivate rescue %s: %r", url, r)
            fail(EC_GENERIC_ERROR)

    def is_rescue_enabled(self, server_id):
        url = "%s/boot/%s/rescue" % (self.endpoint(), server_id)
        r = requests.get(url,  auth=self.auth())
        logging.debug("Rescue status response: %r", r)
        if r.ok:
            data = r.json()
            logging.debug("Rescue response data: %r", data)
            return data.get("rescue", {}).get("active", False)
        else:
            logging.error("Error in get rescue status %s: %r", url, r)
            fail(EC_GENERIC_ERROR)

    def reset_server(self, server_id, rst_type="hw"):
        url = "%s/reset/%s" % (self.endpoint(), server_id)
        r = requests.post(url, data={'type': rst_type}, auth=self.auth())
        logging.debug("Reset response: %r", r)
        if not r.ok:
            logging.error("Error in reset request: %r", r)
            fail(EC_GENERIC_ERROR)

    def auth(self):
        return (self.conn.user, self.conn.passwd)


def define_new_opts():
    all_opt["server_id"] = {
        "getopt": "I:",
        "longopt": "server_id",
        "help": "-I, --server_id=[server_id]    Hetzner server id, normally the assigned ip address",
        "required": "1",
        "shortdesc": "Robot server ID",
        "order": 1}


def get_nodes_list(_conn, _options):
    fail_usage("Action 'list' is not supported in this fence agent")

def perform_power_off(conn, options):
    logging.debug("Activate rescue system...")
    conn.activate_rescue(server_id(options))

    logging.debug("Rebooting server...")
    conn.reset_server(server_id(options))

    # if server gets rebooted, rescue system is deactivated automatically
    start_time = time.time()
    while True:
        logging.debug("Checking server status...")
        time.sleep(5)

        current_time = time.time()
        if current_time > start_time + PATIENCE:
            logging.info("Machine didn't come down after %d seconds.", PATIENCE)
            fail(EC_TIMED_OUT)
            break

        if conn.is_rescue_enabled(server_id(options)):
            logging.debug("Still not down...")
        else:
            logging.debug("Server is now down")
            return

def perform_power_on(conn, options):
    perform_power_off(conn, options)

    logging.debug("Deactivate rescue system... (just in case)")
 
    logging.debug("Rebooting server...")
    conn.reset_server(server_id(options))

def server_id(options):
    return options["--server_id"]

def main():
    device_opt = ["ipaddr", "login", "passwd", "server_id",
                  "web", "no_status", "no_port"]

    atexit.register(atexit_handler)

    define_new_opts()

    options = check_input(device_opt, process_input(device_opt))

    docs = {}
    docs["shortdesc"] = "Fence agent for Hetzner Roboto"
    docs["longdesc"] = "fence_hetzner_robot is an Power Fencing agent \
which can be used within an Hetzner datacenter. \
Poweroff is simulated with a reset and reboot into rescue mode."

    docs["vendorurl"] = "https://robot.your-server.de/doc/"
    show_docs(options, docs)

    if "--server_id" not in options:
        fail_usage("You have to enter server ID (server main ip address)")

    if options["--action"] == "validate-all":
        sys.exit(0)

    run_delay(options)

    conn = Robot(options["--username"], options["--password"])

    # Operate the fencing device
    if options["--action"] == 'off':
        perform_power_off(conn, options)
    elif options["--action"] in  ['on', 'reboot']:
        perform_power_on(conn, options)
        logging.debug("Waiting for OS to be up...")
        time.sleep(PATIENCE) # give OS sometime to boot...

    sys.exit(0)


if __name__ == "__main__":
    main()
