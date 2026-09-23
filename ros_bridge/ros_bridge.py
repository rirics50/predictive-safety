import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

STALE_THRESHOLD_SEC = 3.0  # if no good reading for this long, something's wrong

class CoppeliaBridge(Node):
    def __init__(self):
        super().__init__('coppelia_bridge')

        # Publishers and Subscribers
        self.pressure_publisher = self.create_publisher(Float32, '/live_pressure', 10)
        self.subscription = self.create_subscription(
            Float32,
            '/valve_shutdown',
            self.shutdown_callback,
            10
        )

        # Connect to CoppeliaSim ZMQ remote API on the Mac host
        self.get_logger().info('Connecting to CoppeliaSim on macOS host...')
        self.client = RemoteAPIClient('host.docker.internal', 23000)
        self.sim = self.client.require('sim')
        self.get_logger().info('Connected! Broadcasting pressure & listening for commands...')

        # Watchdog state: tracks the last time we got a real reading
        self.last_good_reading_time = time.time()
        self.warned_stale = False

        # Timer for polling simulation signals
        self.timer = self.create_timer(0.1, self.timer_callback)
        # Separate, slower timer just to check the watchdog
        self.watchdog_timer = self.create_timer(1.0, self.watchdog_callback)

    def timer_callback(self):
        try:
            # Read live pressure from CoppeliaSim
            pressure = self.sim.getFloatSignal('live_pressure')
            if pressure is not None:
                msg = Float32()
                msg.data = float(pressure)
                self.pressure_publisher.publish(msg)

                # Got a good reading - reset the watchdog
                self.last_good_reading_time = time.time()
                if self.warned_stale:
                    self.get_logger().info('>>> RECOVERED: live_pressure is flowing again.')
                    self.warned_stale = False
        except Exception as e:
            self.get_logger().error(f'Failed to read/publish live_pressure: {e}')

    def watchdog_callback(self):
        elapsed = time.time() - self.last_good_reading_time
        if elapsed > STALE_THRESHOLD_SEC and not self.warned_stale:
            self.get_logger().error(
                f'>>> NOT WORKING: no live_pressure reading in {elapsed:.1f}s. '
                'Check that CoppeliaSim is running, the scene is playing, '
                'and the ZMQ remote API is reachable on host.docker.internal:23000.'
            )
            self.warned_stale = True

    def shutdown_callback(self, msg):
        try:
            # Forward the shutdown command signal back into CoppeliaSim, but
            # only when it changes the valve state so repeats don't spam the log
            shutdown_val = 1.0 if msg.data >= 0.5 else 0.0
            if shutdown_val == self.sim.getFloatSignal('valve_shutdown'):
                return
            self.sim.setFloatSignal('valve_shutdown', shutdown_val)
            if shutdown_val:
                self.get_logger().warn('VALVE SHUTDOWN RECEIVED: Closing valve!')
            else:
                self.get_logger().info('VALVE SHUTDOWN CLEARED: Opening valve.')
        except Exception as e:
            self.get_logger().error(f'Failed to set shutdown signal in simulation: {e}')

def main(args=None):
    rclpy.init(args=args)
    bridge = CoppeliaBridge()
    try:
        rclpy.spin(bridge)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
