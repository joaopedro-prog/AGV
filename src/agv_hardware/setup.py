import os
from glob import glob
from setuptools import setup

package_name = 'agv_hardware'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Joao Pedro',
    maintainer_email='jpcampos147@gmail.com',
    description='Camada de hardware do AGV: comunicacao serial USB com microcontrolador, camera e bringup.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'serial_bridge = agv_hardware.serial_bridge_node:main',
            'rpi_sensors = agv_hardware.rpi_sensors_node:main',
        ],
    },
)
