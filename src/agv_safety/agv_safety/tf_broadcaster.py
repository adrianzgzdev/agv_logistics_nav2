import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster 
from geometry_msgs.msg import TransformStamped 
from turtlesim.msg import Pose 

class TurtleTFFrame(Node):
    def __init__(self):
        super().__init__('turtle_tf_broadcaster')
        
        self.tf_broadcaster = TransformBroadcaster(self)
        
        self.subscription = self.create_subscription(Pose, '/turtle1/pose', self.handle_turtle_pose, 10)

    def handle_turtle_pose(self, msg):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world'
        t.child_frame_id = 'base_link' 

        t.transform.translation.x = msg.x - 5.5 
        t.transform.translation.y = msg.y - 5.5 
        t.transform.translation.z = 0.0

        from math import sin, cos
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = sin(msg.theta / 2.0)
        t.transform.rotation.w = cos(msg.theta / 2.0)

        self.tf_broadcaster.sendTransform(t)

def main():
    rclpy.init()
    node = TurtleTFFrame()
    rclpy.spin(node)
    rclpy.shutdown()