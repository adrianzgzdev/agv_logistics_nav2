#!/usr/bin/env python3
"""
safety_event_monitor.py

Colored terminal monitor for /safety_event topic.
Replaces plain 'ros2 topic echo' for demo recording.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


# ANSI color codes
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    PURPLE  = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"


ZONE_COLORS = {
    "SAFE":       Color.GREEN,
    "SLOW":       Color.YELLOW,
    "STOP":       Color.RED,
    "RESTRICTED": Color.PURPLE,
}

ZONE_ICONS = {
    "SAFE":       "🟢",
    "SLOW":       "🟡",
    "STOP":       "🔴",
    "RESTRICTED": "🟣",
}


class SafetyEventMonitor(Node):

    def __init__(self):
        super().__init__('safety_event_monitor')
        self.subscription = self.create_subscription(
            String,
            '/safety_event',
            self._callback,
            10
        )
        print(f"\n{Color.CYAN}{Color.BOLD}{'─' * 52}{Color.RESET}")
        print(f"{Color.CYAN}{Color.BOLD}  AGV Safety Event Monitor — /safety_event{Color.RESET}")
        print(f"{Color.CYAN}{Color.BOLD}{'─' * 52}{Color.RESET}\n")

    def _callback(self, msg: String) -> None:
        parts = msg.data.split("|")
        if len(parts) != 3:
            return

        zone_type, zone_name, speed = parts
        color = ZONE_COLORS.get(zone_type, Color.WHITE)
        icon  = ZONE_ICONS.get(zone_type, "⚪")

        print(
            f"{color}{Color.BOLD}{icon}  {zone_type:<12}{Color.RESET}"
            f"  {Color.WHITE}zone={Color.BOLD}{zone_name:<28}{Color.RESET}"
            f"  {color}speed={speed} m/s{Color.RESET}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = SafetyEventMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()