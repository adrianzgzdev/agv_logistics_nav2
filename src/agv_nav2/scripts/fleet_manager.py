#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus
import time  

class FleetManager(Node):
    def __init__(self):
        super().__init__('fleet_manager_node')
        self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        self.rutas = [
            {"nombre": "Pallet A (Zona de Recogida)", "x": -0.039, "y": 5.55, "espera": 5},
            {"nombre": "Zona de Expedición (Entrega)", "x": 0.64, "y": 0.087, "espera": 0}
        ]
        self.paso_actual = 0 

    def iniciar_jornada(self):
        self.get_logger().info('SGA: Esperando a que el AGV esté en línea y rearmado...')
        self.action_client.wait_for_server()
        self.enviar_siguiente_mision()

    def enviar_siguiente_mision(self):
        if self.paso_actual >= len(self.rutas):
            self.get_logger().info('SGA: [FIN DE TURNO] Todas las misiones completadas. AGV en reposo.')
            rclpy.shutdown()
            return

        destino = self.rutas[self.paso_actual]
        
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = destino['x']
        goal_msg.pose.pose.position.y = destino['y']
        goal_msg.pose.pose.orientation.w = 1.0

        self.get_logger().info(f"\nSGA: ---> [MISIÓN {self.paso_actual + 1}/{len(self.rutas)}] Yendo a {destino['nombre']}...")
        
        self.send_goal_future = self.action_client.send_goal_async(goal_msg)
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('SGA: ¡Misión RECHAZADA por el AGV! (Posible obstáculo o fuera de mapa)')
            rclpy.shutdown()
            return

        self.get_logger().info('SGA: AGV en tránsito...')
        self.result_future = goal_handle.get_result_async()
        self.result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        status = future.result().status
        destino = self.rutas[self.paso_actual]
        
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"SGA: [ÉXITO] AGV ha aparcado en {destino['nombre']}.")
            
            if destino['espera'] > 0:
                self.get_logger().info(f"SGA: Iniciando maniobra de carga. Esperando {destino['espera']} segundos...")
                time.sleep(destino['espera'])
                self.get_logger().info("SGA: ¡Carga completada y asegurada!")

            self.paso_actual += 1
            self.enviar_siguiente_mision()
            
        else:
            self.get_logger().error(f'SGA: [FALLO] El AGV abortó la maniobra. Código de estado: {status}')
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    sga_node = FleetManager()
    
    sga_node.iniciar_jornada()
    
    rclpy.spin(sga_node)

if __name__ == '__main__':
    main()