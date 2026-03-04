import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster # Herramienta para emitir TFs
from geometry_msgs.msg import TransformStamped # El tipo de mensaje que entiende RViz
from turtlesim.msg import Pose # El mensaje que emite la tortuga

class TurtleTFFrame(Node):
    def __init__(self):
        super().__init__('turtle_tf_broadcaster')
        # Inicializamos el emisor de TFs
        self.tf_broadcaster = TransformBroadcaster(self)
        # Nos suscribimos a la posición de la tortuga
        self.subscription = self.create_subscription(Pose, '/turtle1/pose', self.handle_turtle_pose, 10)

    def handle_turtle_pose(self, msg):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'world' # El origen del universo
        t.child_frame_id = 'base_link' # El nombre que RViz buscaba antes

        # Pasamos la posición de la tortuga al eje de coordenadas
        t.transform.translation.x = msg.x - 5.5 # Ajustamos para centrar en el mundo
        t.transform.translation.y = msg.y - 5.5 # Ajustamos para centrar en el mundo
        t.transform.translation.z = 0.0

        # Para la rotación (Theta), ROS usa cuaterniones. 
        # De momento, usamos esta fórmula simple para convertir el ángulo:
        from math import sin, cos
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = sin(msg.theta / 2.0)
        t.transform.rotation.w = cos(msg.theta / 2.0)

        # Emitimos la transformación
        self.tf_broadcaster.sendTransform(t)

def main():
    rclpy.init()
    node = TurtleTFFrame()
    rclpy.spin(node)
    rclpy.shutdown()