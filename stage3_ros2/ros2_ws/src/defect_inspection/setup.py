import os
from glob import glob

from setuptools import find_packages, setup

package_name = "defect_inspection"

setup(
    name=package_name,
    version="0.2.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
            ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        # Launch files, Gazebo world, and RViz config.
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "worlds"), glob("worlds/*.world")),
        (os.path.join("share", package_name, "rviz"), glob("rviz/*.rviz")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Ashkan Aghamoali",
    maintainer_email="ashkaan.aghamoali@gmail.com",
    description="Stage 3 ROS 2 nodes for the Defect Inspection Digital Twin.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            # node_name = package.module:main
            "camera_node = defect_inspection.camera_node:main",
            "inspection_node = defect_inspection.inspection_node:main",
            "decision_node = defect_inspection.decision_node:main",
            "digital_twin_node = defect_inspection.digital_twin_node:main",
        ],
    },
)
