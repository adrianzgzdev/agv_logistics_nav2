import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Definir primero las configuraciones (Buenas prácticas)
    # Esto soluciona el error 'not defined'
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    autostart = LaunchConfiguration('autostart', default='true')

    # 2. Rutas a los paquetes
    agv_nav2_dir = get_package_share_directory('agv_nav2')
    agv_bringup_dir = get_package_share_directory('agv_bringup')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    rviz_config_file = os.path.join(agv_nav2_dir, 'rviz', 'mi_vista.rviz')
    # Ruta a tu nuevo mapa profesional 
    map_file = os.path.join(agv_nav2_dir, 'maps', 'almacen_pro.yaml')

    # 3. Lanzar Simulador y Puente
    sim_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(agv_bringup_dir, 'launch', 'sim_launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # 4. Lanzar Nav2 con Autostart (para no tener que dar al botón Startup)
    nav2_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_file,
            'use_sim_time': use_sim_time,
            'autostart': autostart
        }.items()
    )

    # 5. Lanzar RViz
    rviz_cmd = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('autostart', default_value='true'),
        sim_cmd,
        nav2_cmd,
        rviz_cmd
    ])