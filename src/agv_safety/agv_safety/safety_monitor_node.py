#!/usr/bin/env python3

"""
safety_monitor_node.py

Subscribes to /amcl_pose, checks AGV position against configured
safety zones, and publishes safety events to /safety_event.

Also publishes a MarkerArray to /safety_zones_markers for RViz
visualization of all defined zones.
"""

import os
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from ament_index_python.packages import get_package_share_directory

from agv_safety.zone_checker import ZoneChecker, ZoneType


# ---------------------------------------------------------------------------
# Color map for RViz zone visualization
# ---------------------------------------------------------------------------

ZONE_COLORS = {
    ZoneType.SAFE:       (0.1, 0.8, 0.1, 0.25),   # green,  semi-transparent
    ZoneType.SLOW:       (1.0, 0.7, 0.0, 0.30),   # amber
    ZoneType.STOP:       (0.9, 0.1, 0.1, 0.35),   # red
    ZoneType.RESTRICTED: (0.5, 0.1, 0.8, 0.35),   # purple
}


class SafetyMonitorNode(Node):

    def __init__(self):
        super().__init__('safety_monitor_node')

        # ------------------------------------------------------------------
        # Parameters
        # ------------------------------------------------------------------
        self.declare_parameter('zones_config_path', '')
        self.declare_parameter('publish_rate_hz', 10.0)

        zones_path = self.get_parameter('zones_config_path').value

        if not zones_path:
            pkg_share = get_package_share_directory('agv_safety')
            zones_path = os.path.join(pkg_share, 'config', 'zones.yaml')

        self.get_logger().info(f'[INIT] Loading zones from: {zones_path}')

        # ------------------------------------------------------------------
        # Zone checker
        # ------------------------------------------------------------------
        self.checker = ZoneChecker(zones_path)
        self.get_logger().info(
            f'[INIT] Loaded {len(self.checker.zones)} safety zones.'
        )

        # ------------------------------------------------------------------
        # Publishers
        # ------------------------------------------------------------------
        self.event_publisher = self.create_publisher(
            String, '/safety_event', 10
        )
        self.marker_publisher = self.create_publisher(
            MarkerArray, '/safety_zones_markers', 10
        )

        # ------------------------------------------------------------------
        # Subscriber
        # ------------------------------------------------------------------
        self.pose_subscriber = self.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self._pose_callback,
            10
        )

        # ------------------------------------------------------------------
        # Timer — publish zone markers periodically for RViz
        # ------------------------------------------------------------------
        rate = self.get_parameter('publish_rate_hz').value
        self.create_timer(1.0 / rate, self._publish_zone_markers)

        # ------------------------------------------------------------------
        # State tracking
        # ------------------------------------------------------------------
        self.last_zone_type = None

        self.get_logger().info('[INIT] Safety Monitor Node is active.')

    # -----------------------------------------------------------------------
    # Pose callback — core logic
    # -----------------------------------------------------------------------

    def _pose_callback(self, msg: PoseWithCovarianceStamped) -> None:
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        result = self.checker.check(x, y)

        # Only log and publish when zone type changes
        if result.zone_type != self.last_zone_type:
            self.last_zone_type = result.zone_type
            self._handle_zone_transition(x, y, result)

    def _handle_zone_transition(self, x, y, result) -> None:
        """Log and publish a safety event on every zone type change."""

        zone_name = result.active_zone.name if result.active_zone else "open_area"

        self.get_logger().info(
            f'[ZONE CHANGE] → {result.zone_type} | '
            f'zone="{zone_name}" | '
            f'speed_limit={result.speed_limit} m/s | '
            f'pos=({x:.2f}, {y:.2f})'
        )

        if result.zone_type == ZoneType.STOP:
            self.get_logger().warn(
                f'[SAFETY] STOP event triggered at ({x:.2f}, {y:.2f}). '
                f'Zone: "{zone_name}"'
            )
        elif result.zone_type == ZoneType.RESTRICTED:
            self.get_logger().error(
                f'[SAFETY] RESTRICTED zone violation at ({x:.2f}, {y:.2f}). '
                f'Zone: "{zone_name}"'
            )

        event_msg = String()
        event_msg.data = (
            f'{result.zone_type}|{zone_name}|{result.speed_limit}'
        )
        self.event_publisher.publish(event_msg)

    # -----------------------------------------------------------------------
    # RViz marker publisher
    # -----------------------------------------------------------------------

    def _publish_zone_markers(self) -> None:
        marker_array = MarkerArray()

        for idx, zone in enumerate(self.checker.zones):
            marker = Marker()
            marker.header.frame_id = 'map'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'safety_zones'
            marker.id = idx
            marker.type = Marker.LINE_STRIP
            marker.action = Marker.ADD
            marker.scale.x = 0.05   # line width in metres

            r, g, b, a = ZONE_COLORS.get(zone.zone_type, (1.0, 1.0, 1.0, 0.3))
            marker.color.r = r
            marker.color.g = g
            marker.color.b = b
            marker.color.a = a

            # Close the polygon by repeating the first vertex at the end
            polygon = zone.polygon + [zone.polygon[0]]
            for vx, vy in polygon:
                from geometry_msgs.msg import Point
                p = Point()
                p.x = float(vx)
                p.y = float(vy)
                p.z = 0.05
                marker.points.append(p)

            marker_array.markers.append(marker)

            # Zone label marker
            label = Marker()
            label.header.frame_id = 'map'
            label.header.stamp = marker.header.stamp
            label.ns = 'safety_zone_labels'
            label.id = idx + 1000
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.scale.z = 0.2    # text height in metres
            label.color.r = r
            label.color.g = g
            label.color.b = b
            label.color.a = 1.0
            label.text = f'{zone.zone_type}\n{zone.name}'

            # Place label at polygon centroid
            cx = sum(v[0] for v in zone.polygon) / len(zone.polygon)
            cy = sum(v[1] for v in zone.polygon) / len(zone.polygon)
            label.pose.position.x = cx
            label.pose.position.y = cy
            label.pose.position.z = 0.3
            label.pose.orientation.w = 1.0

            marker_array.markers.append(label)

        self.marker_publisher.publish(marker_array)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = SafetyMonitorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('[SYSTEM] Safety Monitor stopped by user.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()