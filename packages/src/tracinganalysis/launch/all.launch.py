import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, LogInfo
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Get the map name from the environment or use a default
    map_name = os.getenv('MAP_NAME', 'racetrack_decorated')
    # Define all launch processes
    gazebo_world = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_gazebo', 'gazebo_world.launch.py',
            'use_sim_time:=true'
        ],
        output='screen'
    )

    spawn_robot = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_gazebo', 'spawn_robot.launch.py',
            'robot_index:=1', 'use_sim_time:=true'
        ],
        output='screen'
    )

    zenohd = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'rmw_zenoh_cpp', 'rmw_zenohd'
        ],
        output='screen'
    )

    map_server = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_nav2', 'map_server.launch.py',
            f'map_name:={map_name}'
        ],
        output='screen'
    )

    global_tf = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_tf', 'global_tf.launch.py',
            'use_sim_time:=true'
        ],
        output='screen'
    )

    localization_pose_publisher = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_tf', 'localization_pose_publisher.launch.py',
            'robot_index:=1', 'use_sim_time:=true'
        ],
        output='screen'
    )

    static_transform = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_ground_truth', 'static_transform.launch.py',
            'use_sim_time:=true'
        ],
        output='screen'
    )

    ground_truth = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_ground_truth', 'ground_truth.launch.py',
            'robot_index:=1', 'use_sim_time:=true'
        ],
        output='screen'
    )

    cmd_vel_multiplexer = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_control', 'cmd_vel_multiplexer.launch.py',
            'namespace:=robot1', 'use_sim_time:=true', 'initial_source:=cacc'
        ],
        output='screen'
    )

    control_panel = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_control', 'control_panel.launch.py',
            'robot_index:=1'
        ],
        output='screen'
    )

    ekf_sim = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_ekf', 'ekf_sim.launch.py',
            'robot_index:=1', 'use_sim_time:=true'
        ],
        output='screen'
    )

    navigation_single_robot = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_nav2', 'navigation_single_robot.launch.py',
            'robot_index:=1', 'use_sim_time:=true'
        ],
        output='screen'
    )

    cacc_controller = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_cacc', 'single_cacc_controller.launch.py',
            'robot_index:=1'
        ],
        output='screen'
    )

    wallfollowing = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_wallfollowing', 'wallfollowing.launch.py',
            'robot_index:=1', 'namespace:=robot1'
        ],
        output='screen'
    )

    waypoint_publisher = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_waypoints', 'waypoint_publisher.launch.py',
            'robot_index:=1', 'namespace:=robot1'
        ],
        output='screen'
    )

    cam_communication = ExecuteProcess(
        cmd=[
            'ros2', 'launch', 'auna_comm', 'single_cam_communication.launch.py',
            'robot_index:=1', 'namespace:=robot1'
        ],
        output='screen'
    )

    # Add a delay before spawning the robot
    delay_spawn_robot = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=gazebo_world,
            on_exit=[
                LogInfo(msg="Gazebo world started, spawning robot..."),
                spawn_robot
            ],
        )
    )

    # Create the launch description
    ld = LaunchDescription()

    # Add all processes to the launch description
    ld.add_action(gazebo_world)
    ld.add_action(spawn_robot)
    ld.add_action(zenohd)
    ld.add_action(map_server)
    ld.add_action(global_tf)
    ld.add_action(localization_pose_publisher)
    ld.add_action(static_transform)
    ld.add_action(ground_truth)
    ld.add_action(cmd_vel_multiplexer)
    ld.add_action(control_panel)
    ld.add_action(ekf_sim)
    ld.add_action(navigation_single_robot)
    ld.add_action(cacc_controller)
    ld.add_action(wallfollowing)
    ld.add_action(waypoint_publisher)
    ld.add_action(cam_communication)

    return ld
