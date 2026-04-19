#!/usr/bin/env python3
"""
ros_bridge.py

Runs rclpy in a background thread and subscribes to:
  - /amcl_pose       → AGV position (x, y, yaw)
  - /safety_event    → Zone type, zone name, speed limit
  - /cmd_vel         → Current linear velocity

Maintains a shared AGVState dataclass that FastAPI reads
and pushes to WebSocket clients.

Usage:
    from ros_bridge import ROSBridge
    bridge = ROSBridge()
    bridge.start()          # non-blocking
    state = bridge.get_state()
    bridge.stop()
"""

import math
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor

from geometry_msgs.msg import Twist
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import String


# ---------------------------------------------------------------------------
# AGV state — single shared object, written by ROS callbacks, read by FastAPI
# ---------------------------------------------------------------------------

class AGVState:
    def __init__(self):
        self._lock = threading.Lock()

        self.pose_x:       float = 0.0
        self.pose_y:       float = 0.0
        self.pose_yaw:     float = 0.0

        self.zone:         str   = "SAFE"
        self.zone_name:    str   = "open_area"
        self.speed_limit:  float = 1.0

        self.current_speed: float = 0.0

        self.mission_state: str  = "IDLE"

        self.uptime:        int  = 0
        self._start_time:   float = time.time()

    def update_pose(self, x: float, y: float, yaw: float) -> None:
        with self._lock:
            self.pose_x   = round(x,   3)
            self.pose_y   = round(y,   3)
            self.pose_yaw = round(yaw, 3)

    def update_safety(self, zone: str, zone_name: str, speed_limit: float) -> None:
        with self._lock:
            self.zone        = zone
            self.zone_name   = zone_name
            self.speed_limit = speed_limit

    def update_velocity(self, linear_x: float) -> None:
        with self._lock:
            self.current_speed = round(abs(linear_x), 3)

    def update_mission(self, state: str) -> None:
        with self._lock:
            self.mission_state = state

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "pose_x":        self.pose_x,
                "pose_y":        self.pose_y,
                "pose_yaw":      self.pose_yaw,
                "zone":          self.zone,
                "zone_name":     self.zone_name,
                "speed_limit":   self.speed_limit,
                "current_speed": self.current_speed,
                "mission_state": self.mission_state,
                "uptime":        int(time.time() - self._start_time),
            }


# ---------------------------------------------------------------------------
# ROS 2 node — subscribes to all relevant topics
# ---------------------------------------------------------------------------

class AGVBridgeNode(Node):

    def __init__(self, state: AGVState):
        super().__init__("agv_bridge_node")
        self._state = state

        # /amcl_pose — published by Nav2 AMCL localisation
        self.create_subscription(
            PoseWithCovarianceStamped,
            "/amcl_pose",
            self._amcl_callback,
            10,
        )

        # /safety_event — published by safety_monitor_node (Project 3)
        # Message format: "ZONE_TYPE|zone_name|speed_limit"
        self.create_subscription(
            String,
            "/safety_event",
            self._safety_callback,
            10,
        )

        # /cmd_vel — velocity commands sent by Nav2 controller
        self.create_subscription(
            Twist,
            "/cmd_vel",
            self._cmd_vel_callback,
            10,
        )

        # /mission_state — optional: published by mission_executor (Project 2)
        self.create_subscription(
            String,
            "/mission_state",
            self._mission_callback,
            10,
        )

        self.get_logger().info("[AGVBridgeNode] Subscribed to all topics.")

    # ── Callbacks ──────────────────────────────────────────────────────────

    def _amcl_callback(self, msg: PoseWithCovarianceStamped) -> None:
        x   = msg.pose.pose.position.x
        y   = msg.pose.pose.position.y
        yaw = self._quat_to_yaw(msg.pose.pose.orientation)
        self._state.update_pose(x, y, yaw)

    def _safety_callback(self, msg: String) -> None:
        parts = msg.data.split("|")
        if len(parts) != 3:
            return
        zone, zone_name, speed_str = parts
        try:
            speed_limit = float(speed_str)
        except ValueError:
            speed_limit = 1.0
        self._state.update_safety(zone, zone_name, speed_limit)

    def _cmd_vel_callback(self, msg: Twist) -> None:
        self._state.update_velocity(msg.linear.x)

    def _mission_callback(self, msg: String) -> None:
        self._state.update_mission(msg.data.strip())

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _quat_to_yaw(q) -> float:
        """Convert geometry_msgs/Quaternion to yaw angle (radians)."""
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)


# ---------------------------------------------------------------------------
# ROSBridge — manages the rclpy thread lifecycle
# ---------------------------------------------------------------------------

class ROSBridge:
    """
    Wraps rclpy in a daemon thread so FastAPI can import and use it
    without blocking the async event loop.

    Usage:
        bridge = ROSBridge()
        bridge.start()
        ...
        state_dict = bridge.get_state()   # call from FastAPI handlers
        ...
        bridge.stop()
    """

    def __init__(self):
        self.state     = AGVState()
        self._executor = None
        self._node     = None
        self._thread   = None
        self._running  = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._executor:
            self._executor.shutdown()
        if self._node:
            self._node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass

    def get_state(self) -> dict:
        return self.state.to_dict()

    # ── Internal spin loop (runs in daemon thread) ──────────────────────────

    def _spin(self) -> None:
        try:
            rclpy.init()
            self._node     = AGVBridgeNode(self.state)
            self._executor = SingleThreadedExecutor()
            self._executor.add_node(self._node)

            while self._running and rclpy.ok():
                self._executor.spin_once(timeout_sec=0.05)

        except Exception as exc:
            print(f"[ROSBridge] Thread error: {exc}")
        finally:
            if self._node:
                self._node.destroy_node()
            try:
                rclpy.shutdown()
            except Exception:
                pass
