import rclpy # Librería principal de ROS 2 para Python
from rclpy.node import Node # Importamos la clase Node
from std_msgs.msg import String # Importamos un tipo de mensaje estándar (texto)

class SecuritySensor(Node): # Heredamos de Node para tener todas sus funciones
    def __init__(self):
        # Inicializamos el nodo con el nombre 'security_sensor_node'
        super().__init__('security_sensor_node')
        
        # Creamos un 'Publisher'. 
        # Tipo de mensaje: String, Nombre del topic: '/safety_status', Cola: 10
        self.publisher_ = self.create_publisher(String, '/safety_status', 10)
        
        # Creamos un temporizador que ejecute la función cada 1 segundo
        self.timer = self.create_timer(1.0, self.publish_status)
        
        self.get_logger().info('Nodo Sensor de Seguridad Iniciado...')

    def publish_status(self):
        msg = String() # Creamos el objeto del mensaje
        msg.data = 'TODO DESPEJADO: AGV en movimiento' # Definimos el contenido
        
        # Publicamos el mensaje en el topic
        self.publisher_.publish(msg)
        
        # Imprimimos en la terminal del nodo para saber que funciona
        self.get_logger().info(f'Publicando: "{msg.data}"')

def main(args=None):
    rclpy.init(args=args) # Inicializa la comunicación ROS 2
    node = SecuritySensor() # Instancia nuestra clase
    try:
        rclpy.spin(node) # Mantiene el nodo vivo escuchando/publicando
    except KeyboardInterrupt:
        pass
    node.destroy_node() # Limpieza al cerrar
    rclpy.shutdown() # Cierre de comunicaciones

if __name__ == '__main__':
    main()