import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    bringup_dir = get_package_share_directory('agv_bringup')

    base_simulation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_dir, 'launch', 'sim_slam_teleop.launch.py')
        )
    )

    safety_monitor_node = Node(
        package='agv_bringup',
        executable='agv_monitor.py',
        name='agv_monitor_node',
        output='screen',
        emulate_tty=True  
    )

    return LaunchDescription([
        base_simulation_launch,
        safety_monitor_node
    ])