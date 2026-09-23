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

# Latching shutdown: the valve closes above CLOSE_THRESHOLD (or on Force
# Shutdown from Odoo) and stays closed until Manual Reset in Odoo reopens it.
CLOSE_THRESHOLD = 53.0

manual_force_stop = False
valve_is_closed = False
last_message_time = None

# Publisher for valve shutdown signal
talker = roslibpy.Topic(client, '/valve_shutdown', 'std_msgs/msg/Float32')


def check_pressure(message):
    global manual_force_stop, valve_is_closed, last_message_time
    last_message_time = time.time()

    pressure = message['data']
    print(f"Pressure received: {pressure:.2f} PSI")

    # Once closed, the valve stays closed regardless of pressure - only
    # override_callback (Manual Reset from Odoo) can reopen it
    if not valve_is_closed and (manual_force_stop or pressure > CLOSE_THRESHOLD):
        print(">>> CRITICAL: Emergency valve shutdown activated! Manual Reset in Odoo required to reopen.")
        talker.publish(roslibpy.Message({'data': 1.0}))
        valve_is_closed = True

    status = 'critical' if valve_is_closed else 'safe'

    # Push this reading into Odoo. On 'critical', receive_safety_reading()
    # automatically creates the Maintenance ticket - nothing else to do here.
    try:
        odoo_models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'predictive.safety.pipeline', 'receive_safety_reading',
            [[pipeline_id], status, pressure]
        )
    except Exception as e:
        print(f">>> NOT WORKING: failed to update Odoo: {e}")


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

# Subscribe to live pressure stream from ROS bridge
listener = roslibpy.Topic(client, '/live_pressure', 'std_msgs/msg/Float32')
listener.subscribe(check_pressure)


def terminal_listener():
    global manual_force_stop
    while True:
        cmd = input().strip().lower()
        if cmd == 'stop':
            manual_force_stop = True
            print(">>> MANUAL OVERRIDE: Force Stop activated.")
        elif cmd == 'resume':
            manual_force_stop = False
            print(">>> MANUAL OVERRIDE: System released back to automated control.")


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