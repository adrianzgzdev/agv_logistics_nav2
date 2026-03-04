#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

# NUEVO: Importamos el tipo de mensaje Twist. 
# Twist es el estándar en robótica para enviar comandos de velocidad (lineal y angular).
from geometry_msgs.msg import Twist 

class AgvMonitor(Node):
    
    def __init__(self):
        super().__init__('agv_monitor_node')
        
        # 1. Nuestro Suscriptor (los "ojos" del nodo)
        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        
        # 2. NUEVO: Nuestro Publicador (la "voz" del nodo para frenar)
        # Argumentos: 1. Tipo de mensaje, 2. Topic al que hablar, 3. Tamaño de la cola (QoS)
        self.publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )
        
        # Definimos nuestro límite de seguridad en metros por segundo (ej. 0.8 m/s)
        self.speed_limit = 0.8 
        
        self.get_logger().info('Monitor y Freno de Emergencia iniciados...')

    def odom_callback(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        linear_speed = msg.twist.twist.linear.x
        
        # BUENA PRÁCTICA: Imprimimos la posición SOLO cada 0.5 segundos. 
        # El cerebro del nodo sigue leyendo la odometría a 50Hz, pero solo te lo cuenta 2 veces por segundo.
        self.get_logger().info(
            f'X: {x:.2f}m, Y: {y:.2f}m | Vel: {linear_speed:.2f} m/s',
            throttle_duration_sec=0.5
        )

        # 3. La lógica del Freno de Emergencia
        if abs(linear_speed) > self.speed_limit:
            
            # También estrangulamos la alarma para que salga amarilla, pero sin parpadear como loca. 1 aviso por segundo.
            self.get_logger().warn(
                '¡PELIGRO! Exceso de velocidad. Activando freno de emergencia...',
                throttle_duration_sec=1.0
            )
            
            stop_msg = Twist()
            stop_msg.linear.x = 0.0
            stop_msg.angular.z = 0.0
            self.publisher.publish(stop_msg)    


def main(args=None):
    rclpy.init(args=args)
    monitor_node = AgvMonitor()
    try:
        rclpy.spin(monitor_node)
    except KeyboardInterrupt:
        pass
    finally:
        monitor_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()