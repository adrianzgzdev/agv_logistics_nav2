#!/usr/bin/env python3
"""
demo_mission.py

Demo mission for Project 4 recording.
Adapted from mission_executor_node.py (Project 2) — same waypoints,
same action client, same logic.

Key change: publishes to /mission_state (dashboard topic)
in addition to /agv_mission_state (original topic).

Mission flow:
  IDLE → APPROACHING_PICKUP → MOVING_TO_PICKUP → LOADING
       → MOVING_TO_DROPOFF → UNLOADING → COMPLETED → IDLE

Usage:
    source ~/agv_ws/install/setup.zsh
    python3 ~/agv_ws/agv_dashboard/demo_mission.py
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus
from std_msgs.msg import String
from enum import Enum


class MissionState(Enum):
    IDLE               = "IDLE"
    APPROACHING_PICKUP = "APPROACHING_PICKUP"
    MOVING_TO_PICKUP   = "MOVING_TO_PICKUP"
    LOADING            = "LOADING"
    MOVING_TO_DROPOFF  = "MOVING_TO_DROPOFF"
    UNLOADING          = "UNLOADING"
    COMPLETED          = "COMPLETED"
    FAILED             = "FAILED"


# Waypoints validated in simulation (Project 2)
# Start pose: x=1.69, y=3.95

MISSION_TASKS = [
    {
        "state":       MissionState.APPROACHING_PICKUP,
        "task_type":   "approach",
        "target_name": "Pallet A (Approach Point)",
        "x": -0.58, "y": 5.625, "yaw_deg": -9.7,
        "wait_time": 1.5,
    },
    {
        "state":       MissionState.MOVING_TO_PICKUP,
        "task_type":   "pickup",
        "target_name": "Pallet A (Pickup Zone)",
        "x": 0.34, "y": 5.725, "yaw_deg": -1.7,
        "wait_time": 5.0,
    },
    {
        "state":       MissionState.MOVING_TO_DROPOFF,
        "task_type":   "dropoff",
        "target_name": "Dispatch Zone (Dropoff)",
        "x": 0.434, "y": 0.022, "yaw_deg": 12.7,
        "wait_time": 3.0,
    },
    {
        "state":       MissionState.COMPLETED,
        "task_type":   "home",
        "target_name": "Home Position",
        "x": 1.69, "y": 3.95, "yaw_deg": 0.0,
        "wait_time": 2.0,
    },
]


class DemoMissionNode(Node):

    def __init__(self):
        super().__init__("demo_mission_node")

        self.current_state           = MissionState.IDLE
        self.current_task_idx        = 0
        self.wait_timer              = None
        self.nav_timeout_timer       = None
        self.current_goal_handle     = None
        self.navigation_in_progress  = False
        self.failure_handled         = False

        self._state_pub = self.create_publisher(String, "/mission_state",     10)
        self._orig_pub  = self.create_publisher(String, "/agv_mission_state", 10)

        self._nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")

        self.get_logger().info("[DemoMission] Waiting for Nav2 action server...")

        if not self._nav_client.wait_for_server(timeout_sec=15.0):
            self.get_logger().error("[DemoMission] Nav2 not available. Aborting.")
            self._publish_state(MissionState.FAILED)
            return

        self.get_logger().info("[DemoMission] Nav2 ready. Starting in 3 s...")
        self._init_timer = self.create_timer(3.0, self._start_once)

    def _publish_state(self, state: MissionState):
        self.current_state = state
        msg = String()
        msg.data = state.value
        self._state_pub.publish(msg)
        self._orig_pub.publish(msg)
        self.get_logger().info(f"[STATE] ──► {state.value}")

    def _start_once(self):
        self._init_timer.cancel()
        self._execute_task()

    def _execute_task(self):
        if self.current_task_idx >= len(MISSION_TASKS):
            self._publish_state(MissionState.IDLE)
            self.get_logger().info("[DemoMission] Mission complete.")
            return

        task = MISSION_TASKS[self.current_task_idx]
        self._publish_state(task["state"])

        self.get_logger().info(
            f"[NAV] → '{task['target_name']}' "
            f"({task['x']:.3f}, {task['y']:.3f}, {task['yaw_deg']:.1f}°)"
        )

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp    = self.get_clock().now().to_msg()

        yaw_rad = math.radians(task["yaw_deg"])
        goal.pose.pose.position.x    = task["x"]
        goal.pose.pose.position.y    = task["y"]
        goal.pose.pose.orientation.z = math.sin(yaw_rad / 2.0)
        goal.pose.pose.orientation.w = math.cos(yaw_rad / 2.0)

        self.navigation_in_progress = True
        self.failure_handled        = False

        future = self._nav_client.send_goal_async(
            goal, feedback_callback=self._feedback_cb
        )
        future.add_done_callback(self._goal_accepted_cb)
        self.nav_timeout_timer = self.create_timer(90.0, self._timeout_cb)

    def _goal_accepted_cb(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("[NAV] Goal rejected.")
            self._handle_failure()
            return
        self.current_goal_handle = handle
        handle.get_result_async().add_done_callback(self._result_cb)

    def _feedback_cb(self, feedback_msg):
        fb = feedback_msg.feedback
        self.get_logger().info(
            f"[FB] dist={fb.distance_remaining:.2f}m",
            throttle_duration_sec=3.0,
        )

    def _result_cb(self, future):
        self._cancel_timeout()
        self.navigation_in_progress = False
        self.current_goal_handle    = None

        try:
            status = future.result().status
        except Exception as exc:
            self.get_logger().error(f"[NAV] Error: {exc}")
            self._handle_failure()
            return

        if status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error(f"[NAV] Failed — status {status}")
            self._handle_failure()
            return

        task = MISSION_TASKS[self.current_task_idx]
        self.get_logger().info(f"[NAV] Reached '{task['target_name']}'")

        if task["task_type"] == "pickup":
            self._publish_state(MissionState.LOADING)
        elif task["task_type"] == "dropoff":
            self._publish_state(MissionState.UNLOADING)

        self.wait_timer = self.create_timer(task["wait_time"], self._advance)

    def _advance(self):
        if self.wait_timer:
            self.wait_timer.cancel()
            self.wait_timer = None
        self.current_task_idx += 1
        self._execute_task()

    def _timeout_cb(self):
        if not self.navigation_in_progress:
            return
        self.get_logger().error("[TIMEOUT] Navigation exceeded 90 s.")
        self._handle_failure()

    def _handle_failure(self):
        if self.failure_handled:
            return
        self.failure_handled = True
        self._cancel_timeout()
        self.navigation_in_progress = False
        if self.current_goal_handle:
            self.current_goal_handle.cancel_goal_async()
            self.current_goal_handle = None
        self._publish_state(MissionState.FAILED)

    def _cancel_timeout(self):
        if self.nav_timeout_timer:
            self.nav_timeout_timer.cancel()
            self.nav_timeout_timer = None

    def cleanup(self):
        self._cancel_timeout()
        if self.wait_timer:
            self.wait_timer.cancel()
        if self.current_goal_handle:
            self.current_goal_handle.cancel_goal_async()


def main(args=None):
    rclpy.init(args=args)
    node = DemoMissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("[DemoMission] Stopped by user.")
    finally:
        node.cleanup()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
