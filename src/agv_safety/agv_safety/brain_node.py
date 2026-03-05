import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Empty
from rclpy.action import ActionServer 

class AGVBrain(Node):
    def __init__(self):
        super().__init__('agv_brain_node')

    self._action_server = ActionServer(
    self,
    NavigateToPose, 
    'navigate_to',
    self.execute_callback)

    def execute_callback(self, goal_handle):
        self.get_logger().info('Ejecutando trayectoria...')
        
        for i in range(1, 6):
            self.get_logger().info(f'Avanzando... {i*20}% completado')
            time.sleep(1) 
        
        goal_handle.succeed() 
        
        result = NavigateToPose.Result()
        return result    
        self.is_blocked = True  
        self.srv = self.create_service(Empty, 'reset_agv', self.reset_agv_callback)  
        self.declare_parameter('max_speed', 1.5)  
        self.subscription = self.create_subscription(
            String,
            '/safety_status',
            self.listener_callback,
            10)
        
        self.get_logger().info('Cerebro del AGV online y escuchando...')

    def reset_agv_callback(self, request, response):
        
        self.is_blocked = False  
        self.get_logger().info('AGV reseteado. Camino despejado.')
        return response  

    def listener_callback(self, msg):

        current_speed = self.get_parameter('max_speed').get_parameter_value().double_value
        
        if 'OBSTÁCULO' in msg.data:
           
            self.get_logger().warn(f'¡FRENO! Obstáculo detectado.')
        else:
          
            self.get_logger().info(f'Camino libre. Velocidad configurada: {current_speed} m/s')

def main(args=None):
    rclpy.init(args=args)
    node = AGVBrain()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()