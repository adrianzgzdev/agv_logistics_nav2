from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'agv_safety'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'scripts'), glob('scripts/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='adrian_zgz_dev',
    maintainer_email='adrian_zgz_dev@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'security_sensor = agv_safety.security_sensor:main',
            'brain_node = agv_safety.brain_node:main',
            'tf_broadcaster = agv_safety.tf_broadcaster:main',
            'lidar_sim = agv_safety.lidar_sim:main',
            'safety_monitor_node = agv_safety.safety_monitor_node:main',

        ],
    },
)

# Este es el setup.py He actualizado entry_points pero en data_files hay muchas cosas. Me ayudas porfi