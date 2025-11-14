# Copyright 2022 Trossen Robotics
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the copyright holder nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from launch import LaunchDescription
from launch import conditions
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from interbotix_common_modules.launch import AndCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

def launch_setup(context, *args, **kwargs):

    enable_camera_launch_arg = LaunchConfiguration('enable_camera')
    pointcloud_enable_launch_arg = LaunchConfiguration('rs_camera_pointcloud_enable')
    rbg_camera_profile_launch_arg = LaunchConfiguration('rs_camera_rbg_camera_profile')
    depth_module_profile_launch_arg = LaunchConfiguration('rs_camera_depth_module_profile')
    logging_level_launch_arg = LaunchConfiguration('rs_camera_logging_level')
    output_location_launch_arg = LaunchConfiguration('rs_camera_output_location')
    initial_reset_launch_arg = LaunchConfiguration('rs_camera_initial_reset')

    filter_ns_launch_arg = LaunchConfiguration('filter_ns')
    filter_params_launch_arg = LaunchConfiguration('filter_params')
    use_pointcloud_tuner_gui_launch_arg = LaunchConfiguration('use_pointcloud_tuner_gui')
    enable_pipeline_launch_arg = LaunchConfiguration('enable_pipeline')
    cloud_topic_launch_arg = LaunchConfiguration('cloud_topic')

    # GStreamer streaming parameters
    enable_gstreamer_launch_arg = LaunchConfiguration('enable_gstreamer')
    gstreamer_image_topic_launch_arg = LaunchConfiguration('gstreamer_image_topic')
    gstreamer_host_launch_arg = LaunchConfiguration('gstreamer_host')
    gstreamer_port_launch_arg = LaunchConfiguration('gstreamer_port')

    rs_camera_launch_include = IncludeLaunchDescription(
        condition=conditions.IfCondition(enable_camera_launch_arg),
        launch_description_source=PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('realsense2_camera'),
                'launch',
                'rs_launch.py',
            ])
        ]),
        launch_arguments={
            'camera_name': 'camera',
            'camera_namespace': '',
            'rgb_camera.color_profile': rbg_camera_profile_launch_arg,
            'depth_module.depth_profile': depth_module_profile_launch_arg,
            'depth_module.color_profile': rbg_camera_profile_launch_arg,  # D405 uses depth_module for color stream
            # infra is disabled in the launch file by default
            'pointcloud.enable': pointcloud_enable_launch_arg,
            'initial_reset': initial_reset_launch_arg,
            'log_level': logging_level_launch_arg,
            'output': output_location_launch_arg,
        }.items()
    )

    pc_filter_launch_include = IncludeLaunchDescription(
        condition=conditions.IfCondition(enable_camera_launch_arg),
        launch_description_source=PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('interbotix_perception_modules'),
                'launch',
                'pc_filter.launch.py',
            ])
        ]),
        launch_arguments={
            'filter_ns': filter_ns_launch_arg,
            'filter_params': filter_params_launch_arg,
            'enable_pipeline': enable_pipeline_launch_arg,
            'cloud_topic': cloud_topic_launch_arg,
            'use_pointcloud_tuner_gui': use_pointcloud_tuner_gui_launch_arg,
        }.items(),
    )

    camera_tf_launch_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution([
                    FindPackageShare('viper_track'),
                    'launch',
                    'camera_tf.launch.py',
                ])
            ]
        ),
        launch_arguments={
            'parent_link': 'vx300s/gripper_link',
            'roll': '0',
            'pitch': '0',
            'yaw': '0',
            'x': '0.0205',
            'y': '0',
            'z': '0.065',
        }.items(),
    )

    # GStreamer streaming node - bridges ROS image topic to GStreamer pipeline
    # This subscribes to ROS image topic and streams it via GStreamer TCP server
    gstreamer_bridge_node = Node(
        package='viper_track',
        executable='ros_to_gstreamer_bridge',
        name='gstreamer_bridge',
        condition=AndCondition([
            conditions.IfCondition(enable_camera_launch_arg),
            conditions.IfCondition(enable_gstreamer_launch_arg)
        ]),
        parameters=[{
            'image_topic': gstreamer_image_topic_launch_arg,
            'host': gstreamer_host_launch_arg,
            'port': gstreamer_port_launch_arg,
        }],
    )

    return [
        rs_camera_launch_include,
        pc_filter_launch_include,
        camera_tf_launch_include,
        gstreamer_bridge_node,
    ]


def generate_launch_description():
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            'enable_camera',
            default_value='true',
            choices=('true', 'false'),
            description='enable the RealSense camera.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_pointcloud_enable',
            default_value='true',
            choices=('true', 'false'),
            description="enables the RealSense camera's pointcloud.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_rbg_camera_profile',
            default_value='1280,720,15',
            description='profile for the rbg camera image stream, in `<width>,<height>,<fps>`.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_depth_module_profile',
            default_value='1280,720,15',
            description='profile for the depth module stream, in `<width>,<height>,<fps>`.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_logging_level',
            default_value='info',
            choices=('debug', 'info', 'warn', 'error', 'fatal'),
            description='set the logging level for the realsense2_camera launch include.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_output_location',
            default_value='screen',
            choices=('screen', 'log'),
            description='set the logging location for the realsense2_camera launch include.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'rs_camera_initial_reset',
            default_value='false',
            choices=('true', 'false'),
            description=(
                'On occasions the RealSense camera is not closed properly and due to firmware '
                'issues needs to reset. If set to `true`, the device will reset prior to usage.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'filter_ns',
            default_value='pc_filter',
            description='namespace where the pointcloud related nodes and parameters are located.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'filter_params',
            default_value=PathJoinSubstitution([
                FindPackageShare('interbotix_xsarm_perception'),
                'config',
                'filter_params.yaml'
            ]),
            description=(
                'file location of the parameters used to tune the perception pipeline filters.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'use_pointcloud_tuner_gui',
            default_value='false',
            choices=('true', 'false'),
            description='whether to show a GUI that a user can use to tune filter parameters.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'enable_pipeline',
            default_value=LaunchConfiguration('use_pointcloud_tuner_gui'),
            choices=('true', 'false'),
            description=(
                'whether to enable the perception pipeline filters to run continuously; to save '
                'computer processing power, this should be set to `false` unless you are actively '
                'trying to tune the filter parameters; if `false`, the pipeline will only run if '
                'the `get_cluster_positions` ROS service is called.'
            ),
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'cloud_topic',
            default_value='/camera/depth/color/points',
            description='the absolute ROS topic name to subscribe to raw pointcloud data.',
        )
    )
    # GStreamer streaming parameters
    declared_arguments.append(
        DeclareLaunchArgument(
            'enable_gstreamer',
            default_value='false',
            choices=('true', 'false'),
            description='Enable GStreamer streaming from ROS image topic.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'gstreamer_image_topic',
            default_value='/camera/color/image_rect_raw',
            description='ROS image topic to stream via GStreamer.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'gstreamer_host',
            default_value='127.0.0.1',
            description='Host address for GStreamer TCP server sink.',
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            'gstreamer_port',
            default_value='5000',
            description='Port for GStreamer TCP server sink.',
        )
    )
    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
