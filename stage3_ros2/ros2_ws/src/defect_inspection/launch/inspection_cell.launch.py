"""Launch the full inspection cell: camera → inspection → decision → digital-twin,
with optional Gazebo scene and RViz visualization.

Example (from the repo root, after building the workspace):

    ros2 launch defect_inspection inspection_cell.launch.py \
        repo_root:=$PWD \
        weights:=$PWD/outputs/best_model.pt \
        image_dir:=$PWD/data/synthetic/test \
        use_rviz:=true use_gazebo:=false

Set use_gazebo:=true to also bring up the Gazebo inspection-cell world (requires
ros-humble-gazebo-ros-pkgs).
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare("defect_inspection")

    # --- arguments ---
    repo_root = LaunchConfiguration("repo_root")
    weights = LaunchConfiguration("weights")
    image_dir = LaunchConfiguration("image_dir")
    store = LaunchConfiguration("store")
    device = LaunchConfiguration("device")
    publish_rate = LaunchConfiguration("publish_rate")
    reuse_min = LaunchConfiguration("reuse_min")
    repair_min = LaunchConfiguration("repair_min")
    use_rviz = LaunchConfiguration("use_rviz")
    use_gazebo = LaunchConfiguration("use_gazebo")

    args = [
        DeclareLaunchArgument("repo_root", default_value="",
                              description="Repo root (if stage1/stage2 not pip-installed)."),
        DeclareLaunchArgument("weights", default_value="",
                              description="Path to Stage 1 checkpoint (best_model.pt)."),
        DeclareLaunchArgument("image_dir", default_value="",
                              description="Folder of part images for the camera node."),
        DeclareLaunchArgument("store", default_value="",
                              description="Digital-twin JSONL path (default outputs/...)."),
        DeclareLaunchArgument("device", default_value="cpu",
                              description="cpu | cuda | auto."),
        DeclareLaunchArgument("publish_rate", default_value="0.5",
                              description="Camera publish rate (Hz)."),
        DeclareLaunchArgument("reuse_min", default_value="80.0"),
        DeclareLaunchArgument("repair_min", default_value="50.0"),
        DeclareLaunchArgument("use_rviz", default_value="true"),
        DeclareLaunchArgument("use_gazebo", default_value="false"),
    ]

    # --- the four pipeline nodes ---
    camera = Node(
        package="defect_inspection", executable="camera_node", name="camera_node",
        output="screen",
        parameters=[{"image_dir": image_dir, "publish_rate": publish_rate}],
    )
    inspection = Node(
        package="defect_inspection", executable="inspection_node", name="inspection_node",
        output="screen",
        parameters=[{"weights": weights, "device": device, "repo_root": repo_root}],
    )
    decision = Node(
        package="defect_inspection", executable="decision_node", name="decision_node",
        output="screen",
        parameters=[{"reuse_min": reuse_min, "repair_min": repair_min,
                     "repo_root": repo_root}],
    )
    twin = Node(
        package="defect_inspection", executable="digital_twin_node", name="digital_twin_node",
        output="screen",
        parameters=[{"store": store, "repo_root": repo_root, "marker_frame": "world"}],
    )

    # --- optional RViz ---
    rviz = Node(
        package="rviz2", executable="rviz2", name="rviz2", output="screen",
        condition=IfCondition(use_rviz),
        arguments=["-d", PathJoinSubstitution([pkg_share, "rviz", "inspection.rviz"])],
    )

    # --- optional Gazebo inspection-cell world ---
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("gazebo_ros"), "launch", "gazebo.launch.py"])
        ),
        condition=IfCondition(use_gazebo),
        launch_arguments={
            "world": PathJoinSubstitution(
                [pkg_share, "worlds", "inspection_cell.world"]),
        }.items(),
    )

    return LaunchDescription(args + [camera, inspection, decision, twin, rviz, gazebo])
