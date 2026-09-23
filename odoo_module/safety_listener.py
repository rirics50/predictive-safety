import time
import threading
import roslibpy

client = roslibpy.Ros(host='localhost', port=9090)
client.run()
print("Connected to ROS 2 WebSocket bridge from Odoo!")

manual_force_stop = False
last_message_time = None

def check_pressure(message):
    global manual_force_stop, last_message_time
    last_message_time = time.time()

    pressure = message['data']
    print(f"Pressure received: {pressure:.2f} PSI")

    # Publisher for valve shutdown signal
    # NOTE: ROS 2 type strings need the '/msg/' segment - 'std_msgs/Float32'
    # is the ROS 1 convention and will silently fail to match in ROS 2/rosbridge
    talker = roslibpy.Topic(client, '/valve_shutdown', 'std_msgs/msg/Float32')

    if manual_force_stop or pressure > 53.0:
        print(">>> CRITICAL: Emergency valve shutdown activated!")
        talker.publish(roslibpy.Message({'data': 1.0}))
    else:
        talker.publish(roslibpy.Message({'data': 0.0}))

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

# Run the command listener in the background
threading.Thread(target=terminal_listener, daemon=True).start()

def watchdog():
    # Same "not working" pattern as ros_bridge.py - if nothing has come
    # through for a while, say so loudly instead of staying silent
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
