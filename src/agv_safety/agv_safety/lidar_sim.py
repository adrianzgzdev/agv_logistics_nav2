import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import math
import time # Importamos time aquí arriba, como debe ser

class LidarSim(Node):
    def __init__(self):
        super().__init__('lidar_sim_node')
        self.publisher_ = self.create_publisher(LaserScan, '/scan', 10)
        self.timer = self.create_timer(0.1, self.publish_scan)

    def publish_scan(self):
        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = 'lidar_link'
        
        scan.angle_min = -1.57
        scan.angle_max = 1.57
        scan.angle_increment = 3.14 / 100
        scan.range_min = 0.1
        scan.range_max = 10.0

        # Lógica de la pared dinámica bien indentada (alineada)
        distancia_dinamica = 3.0 + math.sin(time.time())
        scan.ranges = [distancia_dinamica] * 100
        
        self.publisher_.publish(scan)

def main():
    rclpy.init()
    node = LidarSim()
    rclpy.spin(node)
    rclpy.shutdown()