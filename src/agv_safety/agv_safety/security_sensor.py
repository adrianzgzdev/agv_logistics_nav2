import rclpy
from rclpy.node import Node 
from std_msgs.msg import String 

class SecuritySensor(Node): 
    def __init__(self):

        super().__init__('security_sensor_node')
        
        self.publisher_ = self.create_publisher(String, '/safety_status', 10)
        
        
        self.timer = self.create_timer(1.0, self.publish_status)
        
        self.get_logger().info('Nodo Sensor de Seguridad Iniciado...')

    def publish_status(self):
        msg = String()
        msg.data = 'TODO DESPEJADO: AGV en movimiento' 
        
       
        self.publisher_.publish(msg)
        
       
        self.get_logger().info(f'Publicando: "{msg.data}"')

def main(args=None):
    rclpy.init(args=args) 
    node = SecuritySensor() 
    try:
        rclpy.spin(node) 
    except KeyboardInterrupt:
        pass
    node.destroy_node() 
    rclpy.shutdown()

if __name__ == '__main__':
    main()