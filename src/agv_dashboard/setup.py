import os
from glob import glob
from setuptools import setup, find_packages

package_name = 'agv_dashboard'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'static'), glob('agv_dashboard/static/*.*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='João Pedro',
    maintainer_email='joaopedro@agv.local',
    description='Dashboard Web de Telemetria e Operação do AGV',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dashboard_server = agv_dashboard.dashboard_node:main',
        ],
    },
)
