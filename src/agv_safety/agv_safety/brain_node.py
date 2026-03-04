import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Empty
from rclpy.action import ActionServer # Nueva importación
import time

class AGVBrain(Node):
    def __init__(self):
        super().__init__('agv_brain_node')

    self._action_server = ActionServer(
    self,
    NavigateToPose, # Esto es un tipo de acción estándar de Nav2
    'navigate_to',
    self.execute_callback)

    def execute_callback(self, goal_handle):
        self.get_logger().info('Ejecutando trayectoria...')
        
        # Simulamos el movimiento con un bucle
        for i in range(1, 6):
            self.get_logger().info(f'Avanzando... {i*20}% completado')
            time.sleep(1) # Esperamos 1 segundo por paso
        
        goal_handle.succeed() # Marcamos que la acción terminó con éxito
        
        result = NavigateToPose.Result()
        return result    
        self.is_blocked = True  # Variable para simular el estado del AGV (bloqueado o no)
        self.srv = self.create_service(Empty, 'reset_agv', self.reset_agv_callback)  # Servicio para resetear el AGV
        self.declare_parameter('max_speed', 1.5)  # Parámetro para la velocidad máxima del AGV
        
        # Suscriptor: (Tipo de msg, Topic, Función que procesa el dato, Cola)
        self.subscription = self.create_subscription(
            String,
            '/safety_status',
            self.listener_callback,
            10)
        
        self.get_logger().info('Cerebro del AGV online y escuchando...')

    def reset_agv_callback(self, request, response):
        # Esta función se ejecuta cada vez que se llama al servicio 'reset_agv'
        self.is_blocked = False  # Simulamos que el AGV se desbloquea
        self.get_logger().info('AGV reseteado. Camino despejado.')
        return response  # Retornamos la respuesta vacía del servicio

    def listener_callback(self, msg):

        current_speed = self.get_parameter('max_speed').get_parameter_value().double_value
        # Esta función se ejecuta CADA VEZ que llega un mensaje al topic
        if 'OBSTÁCULO' in msg.data:
            # Si el mensaje contiene la palabra OBSTÁCULO, lanzamos un Warning
            self.get_logger().warn(f'¡FRENO! Obstáculo detectado.')
        else:
            # Si no, simplemente confirmamos que todo va bien
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