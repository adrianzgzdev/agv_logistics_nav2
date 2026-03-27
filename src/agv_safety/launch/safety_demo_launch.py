import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    agv_nav2_dir    = get_package_share_directory('agv_nav2')
    agv_safety_dir  = get_package_share_directory('agv_safety')

    zones_config = os.path.join(agv_safety_dir, 'config', 'zones.yaml')

    # ------------------------------------------------------------------
    # 1. Full navigation stack (sim + Nav2 + RViz) — reuse existing
    # ------------------------------------------------------------------
    nav_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(agv_nav2_dir, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # ------------------------------------------------------------------
    # 2. Safety monitor node — Project 3 core
    # ------------------------------------------------------------------
    safety_monitor_cmd = Node(
        package='agv_safety',
        executable='safety_monitor_node',
        name='safety_monitor_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'zones_config_path': zones_config,
        }]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        nav_cmd,
        safety_monitor_cmd,
    ])