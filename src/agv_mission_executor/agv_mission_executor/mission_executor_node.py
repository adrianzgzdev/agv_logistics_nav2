#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from enum import Enum
from std_msgs.msg import String
from action_msgs.msg import GoalStatus


class MissionState(Enum):
    IDLE = "IDLE"
    APPROACHING_PICKUP = "APPROACHING_PICKUP"
    MOVING_TO_PICKUP = "MOVING_TO_PICKUP"
    LOADING = "LOADING"
    MOVING_TO_DROPOFF = "MOVING_TO_DROPOFF"
    UNLOADING = "UNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AGVMissionExecutor(Node):
    def __init__(self):
        super().__init__('agv_mission_executor_node')

        self.current_state = MissionState.IDLE
        self.get_logger().info(
            f"[INIT] AGV Mission Executor started. Current state: {self.current_state.value}"
        )

        self.nav_to_pose_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.state_publisher = self.create_publisher(String, '/agv_mission_state', 10)

        # -----------------------------
        # ROS 2 Parameters
        # -----------------------------
        self.declare_parameter('navigation_timeout_sec', 60.0)
        self.declare_parameter('max_retries', 1)

        self.navigation_timeout_sec = float(
            self.get_parameter('navigation_timeout_sec').value
        )
        self.max_retries = int(
            self.get_parameter('max_retries').value
        )

        self.get_logger().info(
            f"[CONFIG] navigation_timeout_sec={self.navigation_timeout_sec:.1f}, "
            f"max_retries={self.max_retries}"
        )

        # -----------------------------
        # Mission Definition
        # Tuned manually in simulation
        # to improve final pallet pickup
        # approach and loading behavior
        # -----------------------------
        
        self.mission_tasks = [
            {
                "task_type": "approach",
                "target_name": "Pallet A (Approach Point)",
                "x": -0.58,
                "y": 5.625,
                "yaw_deg": -9.7,
                "wait_time": 1.0
            },
            {
                "task_type": "pickup",
                "target_name": "Pallet A (Pickup Zone)",
                "x": 0.34,
                "y": 5.725,
                "yaw_deg": -1.7,
                "wait_time": 5.0
            },
            {
                "task_type": "dropoff",
                "target_name": "Dispatch Zone (Dropoff)",
                "x": 0.434,
                "y": 0.022,
                "yaw_deg": 12.7,
                "wait_time": 3.0
            }
        ]

        self.validate_mission_tasks()

        self.current_task_index = 0
        self.wait_timer = None
        self.retry_timer = None

        self.current_retry_count = 0

        self.last_feedback_second_logged = -1
        self.last_recovery_count_logged = 0

        self.current_goal_handle = None
        self.nav_timeout_timer = None
        self.navigation_in_progress = False
        self.failure_handled_for_current_goal = False

        # -----------------------------
        # Metrics
        # -----------------------------
        self.mission_start_time_ns = None
        self.task_start_time_ns = None
        self.process_start_time_ns = None
        self.total_recovery_events = 0

        for task in self.mission_tasks:
            task["navigation_duration_sec"] = None
            task["process_duration_sec"] = None
            task["result"] = "PENDING"
            task["recoveries"] = 0
            task["retry_attempts"] = 0

        self.get_logger().info("[SYSTEM] Waiting for Nav2 action server...")

        if not self.nav_to_pose_client.wait_for_server(timeout_sec=10.0):
            self.update_state(MissionState.FAILED)
            self.get_logger().error(
                "[SYSTEM] Nav2 action server not available after 10 seconds. Mission aborted."
            )
            return

        self.get_logger().info("[SYSTEM] Nav2 action server is available. Starting mission...")
        self.mission_start_time_ns = self.get_current_time_ns()
        self.execute_next_task()

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_current_time_ns(self):
        """Return current ROS time in nanoseconds."""
        return self.get_clock().now().nanoseconds

    def ns_to_sec(self, duration_ns):
        """Convert nanoseconds to seconds."""
        return duration_ns / 1e9

    def update_state(self, new_state):
        """Update internal AGV state, log the transition, and publish it."""
        self.current_state = new_state
        self.get_logger().info(f"[STATE CHANGE] ---> {self.current_state.value}")

        state_msg = String()
        state_msg.data = self.current_state.value
        self.state_publisher.publish(state_msg)

    def validate_mission_tasks(self):
        """Validate mission task structure before execution."""
        required_keys = ["task_type", "target_name", "x", "y", "yaw_deg", "wait_time"]
        valid_task_types = {"approach", "pickup", "dropoff"}

        for i, task in enumerate(self.mission_tasks):
            for key in required_keys:
                if key not in task:
                    raise ValueError(f"Mission task {i} is missing required key: '{key}'")

            if task["task_type"] not in valid_task_types:
                raise ValueError(
                    f"Mission task {i} has invalid task_type: '{task['task_type']}'"
                )

    def start_navigation_timeout(self):
        """Start a watchdog timer for the active navigation goal."""
        self.cancel_navigation_timeout()
        self.nav_timeout_timer = self.create_timer(
            self.navigation_timeout_sec,
            self.navigation_timeout_callback
        )

    def cancel_navigation_timeout(self):
        """Cancel the navigation watchdog timer if it exists."""
        if self.nav_timeout_timer is not None:
            self.nav_timeout_timer.cancel()
            self.nav_timeout_timer = None

    def abort_active_navigation(self):
        """
        Abort the currently active Nav2 goal, if any.

        This is a software-level goal cancellation, not a hardware safety stop.
        """
        if self.current_goal_handle is not None:
            self.get_logger().warn("[ABORT] Cancelling active Nav2 goal...")
            self.current_goal_handle.cancel_goal_async()
        else:
            self.get_logger().warn("[ABORT] No active Nav2 goal to cancel.")

    def get_quaternion_from_yaw(self, yaw_degrees):
        """
        Convert a human-readable yaw angle in degrees
        into a ROS 2 quaternion for 2D navigation.
        """
        yaw_rad = math.radians(yaw_degrees)

        qx = 0.0
        qy = 0.0
        qz = math.sin(yaw_rad / 2.0)
        qw = math.cos(yaw_rad / 2.0)

        return qx, qy, qz, qw

    def get_current_task(self):
        """Return the current mission task."""
        return self.mission_tasks[self.current_task_index]

    # -------------------------------------------------------------------------
    # Failure / Timeout Handling
    # -------------------------------------------------------------------------

    def navigation_timeout_callback(self):
        """Trigger failure handling if navigation exceeds the allowed time limit."""
        if not self.navigation_in_progress:
            return

        task = self.get_current_task()
        self.get_logger().error(
            f"[TIMEOUT] Navigation to '{task['target_name']}' exceeded "
            f"{self.navigation_timeout_sec:.1f} seconds."
        )

        self.cancel_navigation_timeout()
        self.abort_active_navigation()

        if not self.failure_handled_for_current_goal:
            self.failure_handled_for_current_goal = True
            self.navigation_in_progress = False
            task["result"] = "TIMEOUT"
            self.handle_task_failure()

    def handle_task_failure(self):
        """Handle navigation failure by retrying or aborting the mission."""
        self.cancel_navigation_timeout()
        self.navigation_in_progress = False

        task = self.get_current_task()
        task["retry_attempts"] = self.current_retry_count + 1

        if self.current_retry_count < self.max_retries:
            self.current_retry_count += 1

            self.get_logger().warn(
                f"[RETRY] Attempt {self.current_retry_count} of {self.max_retries} "
                f"for target '{task['target_name']}'. Retrying in 3 seconds..."
            )

            if self.retry_timer is not None:
                self.retry_timer.cancel()
                self.retry_timer = None

            self.retry_timer = self.create_timer(3.0, self.trigger_retry_callback)

        else:
            task["result"] = "FAILED"
            self.update_state(MissionState.FAILED)
            self.get_logger().error(
                "[ABORT] Maximum retries reached. Mission FAILED. Human intervention required."
            )
            self.log_mission_summary()

    def trigger_retry_callback(self):
        """Execute the retry attempt after the waiting period."""
        if self.retry_timer is not None:
            self.retry_timer.cancel()
            self.retry_timer = None

        self.get_logger().info("[RETRY] Retrying current navigation task now...")
        self.execute_next_task()

    # -------------------------------------------------------------------------
    # Mission Execution
    # -------------------------------------------------------------------------

    def execute_next_task(self):
        """Process the current task from the mission queue."""
        if self.current_task_index >= len(self.mission_tasks):
            self.update_state(MissionState.COMPLETED)
            self.get_logger().info(
                "[SUCCESS] All mission tasks completed successfully. AGV is now idle."
            )
            self.log_mission_summary()
            return

        task = self.get_current_task()

        if task["task_type"] == "approach":
            self.update_state(MissionState.APPROACHING_PICKUP)
        elif task["task_type"] == "pickup":
            self.update_state(MissionState.MOVING_TO_PICKUP)
        elif task["task_type"] == "dropoff":
            self.update_state(MissionState.MOVING_TO_DROPOFF)

        self.get_logger().info(
            f"[TASK {self.current_task_index + 1}/{len(self.mission_tasks)}] "
            f"Sending AGV to: {task['target_name']}"
        )

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = task["x"]
        goal_msg.pose.pose.position.y = task["y"]

        qx, qy, qz, qw = self.get_quaternion_from_yaw(task["yaw_deg"])
        self.get_logger().info(
            f"[MATH] Requested yaw: {task['yaw_deg']} deg -> "
            f"Quaternion: x={qx:.2f}, y={qy:.2f}, z={qz:.2f}, w={qw:.2f}"
        )

        goal_msg.pose.pose.orientation.x = qx
        goal_msg.pose.pose.orientation.y = qy
        goal_msg.pose.pose.orientation.z = qz
        goal_msg.pose.pose.orientation.w = qw

        self.last_feedback_second_logged = -1
        self.last_recovery_count_logged = task["recoveries"]
        self.failure_handled_for_current_goal = False
        self.navigation_in_progress = True
        self.current_goal_handle = None
        self.task_start_time_ns = self.get_current_time_ns()

        self.start_navigation_timeout()

        send_goal_future = self.nav_to_pose_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """Handle Nav2 goal acceptance or rejection."""
        try:
            goal_handle = future.result()
        except Exception as e:
            self.get_logger().error(f"[ERROR] Failed to receive goal response: {e}")
            if not self.failure_handled_for_current_goal:
                self.failure_handled_for_current_goal = True
                self.get_current_task()["result"] = "ERROR"
                self.handle_task_failure()
            return

        if not goal_handle.accepted:
            self.cancel_navigation_timeout()
            self.navigation_in_progress = False
            self.current_goal_handle = None
            self.get_logger().error("[REJECTED] Goal was rejected by Nav2.")

            if not self.failure_handled_for_current_goal:
                self.failure_handled_for_current_goal = True
                self.get_current_task()["result"] = "REJECTED"
                self.handle_task_failure()
            return

        self.current_goal_handle = goal_handle
        self.get_logger().info("[ACCEPTED] Nav2 accepted the goal. AGV is moving.")

        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        """Receive progress feedback while the AGV is navigating."""
        feedback = feedback_msg.feedback
        nav_time_sec = feedback.navigation_time.sec
        recovery_count = feedback.number_of_recoveries
        task = self.get_current_task()

        if recovery_count > self.last_recovery_count_logged:
            new_recoveries = recovery_count - self.last_recovery_count_logged
            self.last_recovery_count_logged = recovery_count
            task["recoveries"] = recovery_count
            self.total_recovery_events += new_recoveries

            self.get_logger().warn(
                f"[RECOVERY] Nav2 recovery triggered. "
                f"Task recoveries: {recovery_count} | "
                f"Distance remaining: {feedback.distance_remaining:.2f} m | "
                f"Navigation time: {nav_time_sec} s"
            )

        if nav_time_sec != self.last_feedback_second_logged:
            self.last_feedback_second_logged = nav_time_sec
            self.get_logger().info(
                f"[FEEDBACK] Distance remaining: {feedback.distance_remaining:.2f} m | "
                f"Navigation time: {nav_time_sec} s | "
                f"Recoveries: {recovery_count}"
            )

    def get_result_callback(self, future):
        """Handle the final result of the active navigation goal."""
        self.cancel_navigation_timeout()
        self.navigation_in_progress = False

        try:
            result = future.result()
            status = result.status
        except Exception as e:
            self.current_goal_handle = None
            self.get_logger().error(f"[ERROR] Failed to receive navigation result: {e}")

            if not self.failure_handled_for_current_goal:
                self.failure_handled_for_current_goal = True
                self.get_current_task()["result"] = "ERROR"
                self.handle_task_failure()
            return

        self.current_goal_handle = None
        task = self.get_current_task()

        if self.task_start_time_ns is not None:
            task["navigation_duration_sec"] = self.ns_to_sec(
                self.get_current_time_ns() - self.task_start_time_ns
            )

        if status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error(
                f"[FAILED] Navigation to '{task['target_name']}' failed with status code: {status}"
            )

            if not self.failure_handled_for_current_goal:
                self.failure_handled_for_current_goal = True
                task["result"] = f"FAILED_STATUS_{status}"
                self.handle_task_failure()
            return

        self.current_retry_count = 0
        task["result"] = "SUCCEEDED"

        if task["task_type"] == "approach":
            self.get_logger().info(
                "[PROCESS] Approach point reached. Performing final alignment before pickup."
            )
        elif task["task_type"] == "pickup":
            self.update_state(MissionState.LOADING)
            self.get_logger().info(
                f"[PROCESS] Simulating loading process for {task['wait_time']} seconds..."
            )
        elif task["task_type"] == "dropoff":
            self.update_state(MissionState.UNLOADING)
            self.get_logger().info(
                f"[PROCESS] Simulating unloading process for {task['wait_time']} seconds..."
            )

        self.process_start_time_ns = self.get_current_time_ns()
        self.wait_timer = self.create_timer(
            task["wait_time"],
            self.process_completed_callback
        )

    def process_completed_callback(self):
        """Advance to the next mission task after the simulated process time."""
        if self.wait_timer is not None:
            self.wait_timer.cancel()
            self.wait_timer = None

        task = self.get_current_task()

        if self.process_start_time_ns is not None:
            task["process_duration_sec"] = self.ns_to_sec(
                self.get_current_time_ns() - self.process_start_time_ns
            )

        self.get_logger().info(
            f"[PROCESS] Task completed for '{task['target_name']}'."
        )

        self.log_task_summary(task, self.current_task_index)

        self.current_task_index += 1
        self.execute_next_task()

    # -------------------------------------------------------------------------
    # Metrics / Summary Logging
    # -------------------------------------------------------------------------

    def log_task_summary(self, task, task_index):
        """Log a structured summary for a completed or failed task."""
        nav_time = (
            f"{task['navigation_duration_sec']:.2f}s"
            if task["navigation_duration_sec"] is not None
            else "N/A"
        )
        process_time = (
            f"{task['process_duration_sec']:.2f}s"
            if task["process_duration_sec"] is not None
            else "N/A"
        )

        self.get_logger().info(
            f"[TASK SUMMARY] Task {task_index + 1}/{len(self.mission_tasks)} | "
            f"Target='{task['target_name']}' | "
            f"Type={task['task_type']} | "
            f"Result={task['result']} | "
            f"NavTime={nav_time} | "
            f"ProcessTime={process_time} | "
            f"Recoveries={task['recoveries']} | "
            f"RetryAttempts={task['retry_attempts']}"
        )

    def log_mission_summary(self):
        """Log a final mission execution summary."""
        if self.mission_start_time_ns is None:
            total_mission_time = "N/A"
        else:
            total_mission_time = (
                f"{self.ns_to_sec(self.get_current_time_ns() - self.mission_start_time_ns):.2f}s"
            )

        succeeded_tasks = sum(1 for task in self.mission_tasks if task["result"] == "SUCCEEDED")
        failed_tasks = sum(
            1 for task in self.mission_tasks
            if task["result"] not in ("SUCCEEDED", "PENDING")
        )

        self.get_logger().info("--------------------------------------------------")
        self.get_logger().info("[MISSION SUMMARY] Mission execution finished.")
        self.get_logger().info(f"[MISSION SUMMARY] Final state: {self.current_state.value}")
        self.get_logger().info(f"[MISSION SUMMARY] Total mission time: {total_mission_time}")
        self.get_logger().info(
            f"[MISSION SUMMARY] Tasks succeeded: {succeeded_tasks}/{len(self.mission_tasks)}"
        )
        self.get_logger().info(f"[MISSION SUMMARY] Tasks failed: {failed_tasks}")
        self.get_logger().info(
            f"[MISSION SUMMARY] Total recovery events detected: {self.total_recovery_events}"
        )

        for i, task in enumerate(self.mission_tasks):
            nav_time = (
                f"{task['navigation_duration_sec']:.2f}s"
                if task["navigation_duration_sec"] is not None
                else "N/A"
            )
            process_time = (
                f"{task['process_duration_sec']:.2f}s"
                if task["process_duration_sec"] is not None
                else "N/A"
            )

            self.get_logger().info(
                f"[MISSION SUMMARY] Task {i + 1}: "
                f"Target='{task['target_name']}', "
                f"Type={task['task_type']}, "
                f"Result={task['result']}, "
                f"NavTime={nav_time}, "
                f"ProcessTime={process_time}, "
                f"Recoveries={task['recoveries']}, "
                f"RetryAttempts={task['retry_attempts']}"
            )

        self.get_logger().info("--------------------------------------------------")

    # -------------------------------------------------------------------------
    # Shutdown / Cleanup
    # -------------------------------------------------------------------------

    def cleanup_resources(self):
        """Safely clean up timers and active goals before shutdown."""
        self.cancel_navigation_timeout()

        if self.wait_timer is not None:
            self.wait_timer.cancel()
            self.wait_timer = None

        if self.retry_timer is not None:
            self.retry_timer.cancel()
            self.retry_timer = None

        self.abort_active_navigation()


def main(args=None):
    rclpy.init(args=args)
    agv_mission_executor = AGVMissionExecutor()

    try:
        rclpy.spin(agv_mission_executor)
    except KeyboardInterrupt:
        agv_mission_executor.get_logger().info("[SYSTEM] Mission Executor stopped by user.")
    finally:
        agv_mission_executor.cleanup_resources()
        agv_mission_executor.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

