import json
import os
import time
import threading
import roslibpy
import xmlrpc.client

# --- Odoo connection settings ---
# Set ODOO_URL / ODOO_DB / ODOO_USERNAME / ODOO_PASSWORD in the environment to
# override these local-demo defaults, e.g.:
#   ODOO_PASSWORD=secret python safety_listener.py
ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'admin')
ODOO_USERNAME = os.environ.get('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'admin')

# The Equipment ID (the 'name' field) of the pipeline record you created in Odoo
PIPELINE_NAME = 'P-101'

# --- Connect to Odoo over XML-RPC ---
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
odoo_models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

if not uid:
    raise RuntimeError(
        'Failed to authenticate with Odoo - check ODOO_DB/USERNAME/PASSWORD above.'
    )
print(f">>> Authenticated with Odoo (uid={uid})")

# Look up the pipeline record's database id once at startup
pipeline_ids = odoo_models.execute_kw(
    ODOO_DB, uid, ODOO_PASSWORD,
    'predictive.safety.pipeline', 'search',
    [[['name', '=', PIPELINE_NAME]]]
)
if not pipeline_ids:
    raise RuntimeError(
        f'No pipeline record named "{PIPELINE_NAME}" found in Odoo - '
        f'create it first, or update PIPELINE_NAME above.'
    )
pipeline_id = pipeline_ids[0]
print(f">>> Found pipeline record '{PIPELINE_NAME}' (id={pipeline_id})")

# --- ROS connection ---
client = roslibpy.Ros(host='localhost', port=9090)
client.run()
print(">>> Connected to ROS 2 WebSocket bridge from Odoo!")

# Latching shutdown: MATLAB's CRITICAL on /safety_status (or Force Shutdown
# from Odoo, or 'stop' in this terminal) closes the valve, and it stays closed
# until Manual Reset in Odoo reopens it. While it's closed, MATLAB is ignored.
valve_is_closed = False
last_pressure = None
last_message_time = None

# Publisher for valve shutdown signal
talker = roslibpy.Topic(client, '/valve_shutdown', 'std_msgs/msg/Float32')


def check_pressure(message):
    """Log live pressure for the Odoo dashboard chart. Never decides the
    valve or the safety status - that's MATLAB's job (safety_status_callback)."""
    global last_pressure, last_message_time
    last_message_time = time.time()

    pressure = message['data']
    # The bridge re-publishes the same held value ~10x/second - only send changes
    if pressure == last_pressure:
        return
    last_pressure = pressure
    print(f"Pressure received: {pressure:.2f} PSI")

    try:
        odoo_models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'predictive.safety.pipeline', 'log_pressure_reading',
            [[pipeline_id], pressure]
        )
    except Exception as e:
        print(f">>> NOT WORKING: failed to log pressure in Odoo: {e}")


def report_status(status, reason):
    """Sync Odoo's current_status; on the switch to critical it also opens the
    Maintenance ticket and posts the Discuss alert with this reason."""
    try:
        odoo_models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'predictive.safety.pipeline', 'receive_safety_reading',
            [[pipeline_id], status],
            {'pressure': last_pressure, 'reason': reason}
        )
    except Exception as e:
        print(f">>> NOT WORKING: failed to update Odoo status: {e}")


def close_valve(reason):
    global valve_is_closed
    print(f">>> CRITICAL: {reason} - emergency valve shutdown activated! Manual Reset in Odoo required to reopen.")
    talker.publish(roslibpy.Message({'data': 1.0}))
    valve_is_closed = True


def safety_status_callback(message):
    """MATLAB's decision on /safety_status: {"status": "SAFE"|"WARNING"|"CRITICAL", "reason": "..."}"""
    try:
        payload = json.loads(message['data'])
        status = payload['status'].lower()
        reason = payload.get('reason')
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        print(f">>> NOT WORKING: bad /safety_status message {message.get('data')!r}: {e}")
        return
    if status not in ('safe', 'warning', 'critical'):
        print(f">>> NOT WORKING: unknown status {status!r} on /safety_status - ignored")
        return

    # A closed valve is latched (auto, Force Shutdown or terminal stop) - MATLAB
    # can't reopen it or change Odoo's status until Manual Reset in Odoo
    if valve_is_closed:
        return

    print(f"MATLAB: {status.upper()} - {reason}")
    if status == 'critical':
        close_valve(reason or 'MATLAB flagged CRITICAL')
    report_status(status, reason)


def override_callback(message):
    global valve_is_closed
    value = message['data']

    if value >= 0.5:
        print(">>> MANUAL OVERRIDE (Odoo): Force Shutdown - valve locked closed.")
        if not valve_is_closed:
            talker.publish(roslibpy.Message({'data': 1.0}))
            valve_is_closed = True
    elif value <= -0.5:
        print(">>> MANUAL OVERRIDE (Odoo): Manual Reset - valve reopened, automatic monitoring resumed.")
        talker.publish(roslibpy.Message({'data': 0.0}))
        valve_is_closed = False


# Manual Force Shutdown / Reset commands from the Odoo form buttons
roslibpy.Topic(client, '/manual_override', 'std_msgs/msg/Float32').subscribe(override_callback)

# Subscribe to live pressure stream from ROS bridge (dashboard chart only)
listener = roslibpy.Topic(client, '/live_pressure', 'std_msgs/msg/Float32')
listener.subscribe(check_pressure)

# MATLAB's safety decisions - the only automatic trigger for the valve
roslibpy.Topic(client, '/safety_status', 'std_msgs/msg/String').subscribe(safety_status_callback)


def terminal_listener():
    while True:
        cmd = input().strip().lower()
        if cmd == 'stop':
            print(">>> MANUAL OVERRIDE: Force Stop activated.")
            if not valve_is_closed:
                close_valve('Force Stop from listener terminal')
                report_status('critical', 'Force Stop from listener terminal')
        elif cmd == 'resume':
            print(">>> Valve is latched - use Manual Reset in Odoo to reopen it.")


threading.Thread(target=terminal_listener, daemon=True).start()


def watchdog():
    while True:
        time.sleep(1)
        if last_message_time is not None and time.time() - last_message_time > 3.0:
            print(">>> NOT WORKING: no /live_pressure messages received in 3+ seconds. "
                  "Check ros_bridge.py and rosbridge_websocket are both running.")


threading.Thread(target=watchdog, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    client.terminate()