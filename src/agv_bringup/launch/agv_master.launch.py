import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Buscamos dónde está instalado nuestro paquete en las tripas de ROS 2
    bringup_dir = get_package_share_directory('agv_bringup')

    # 2. LA MUÑECA RUSA: Incluimos el launch que ya tenías.
    # Así no tenemos que copiar y pegar todo el código de Gazebo, RViz y Teleop.
    # Reutilizamos el trabajo previo. ¡Buenas prácticas!
    base_simulation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_dir, 'launch', 'sim_slam_teleop.launch.py')
        )
    )

    # 3. Añadimos tu nuevo nodo de seguridad (Freno de Emergencia)
    # Le decimos explícitamente que escupa sus logs ('output="screen"') en esta terminal.
    safety_monitor_node = Node(
        package='agv_bringup',
        executable='agv_monitor.py',
        name='agv_monitor_node',
        output='screen',
        emulate_tty=True  # <- ¡LA MAGIA DE SENIOR! Esto fuerza a ROS 2 a usar colores (como el amarillo de los Warnings) en el Launch.
    )

    # 4. Devolvemos la lista de "tareas" para que ROS 2 las ejecute todas a la vez
    return LaunchDescription([
        base_simulation_launch,
        safety_monitor_node
    ])