import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_name = 'agv_description'
    pkg_share = get_package_share_directory(pkg_name)

    use_sim_time = LaunchConfiguration('use_sim_time')
    robot_name   = LaunchConfiguration('robot_name')
    x            = LaunchConfiguration('x')
    y            = LaunchConfiguration('y')
    z            = LaunchConfiguration('z')
    yaw          = LaunchConfiguration('yaw')

    declare_args = [
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('robot_name',   default_value='mi_linde'),
        # ✅ Ajusta estos defaults a un sitio “limpio” de tu almacén
        DeclareLaunchArgument('x',            default_value='0.0'),
        DeclareLaunchArgument('y',            default_value='0.0'),
        DeclareLaunchArgument('z',            default_value='0.5'),
        DeclareLaunchArgument('yaw',          default_value='0.0'),
    ]

    urdf_file = os.path.join(pkg_share, 'urdf', 'linde_agv.urdf')
    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': use_sim_time}],
    )

    # World desde agv_worlds
    world_file = os.path.join(
        get_package_share_directory('agv_worlds'),
        'worlds',
        'almacen.sdf'
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_file}'}.items(),
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-name', robot_name,
            '-x', '-5.0',
            '-y', '-3.0',
            '-z', '0.5',
            '-Y', '0.0',
            '-allow_renaming', 'true'
        ],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}], # <-- ¡AÑADE ESTA LÍNEA AQUÍ!
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
        ],
    )

    return LaunchDescription(declare_args + [
        rsp,
        gazebo,
        spawn_entity,
        bridge,
    ])