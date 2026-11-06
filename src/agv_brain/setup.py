import os
from glob import glob
from setuptools import setup

package_name = 'agv_brain'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        (os.path.join('share', package_name, 'web'), glob('agv_brain/web/*')),
    ],
    package_data={'agv_brain': ['web/*']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Joao Pedro',
    maintainer_email='jpcampos147@gmail.com',
    description='Inteligencia do AGV: visao computacional e controle seguidor de linha.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'line_detector = agv_brain.line_detector_node:main',
            'line_follower = agv_brain.line_follower_node:main',
            'agv_cmd = agv_brain.agv_commander_node:main',
            'web_dashboard = agv_brain.web_dashboard_node:main',
        ],
    },
)
