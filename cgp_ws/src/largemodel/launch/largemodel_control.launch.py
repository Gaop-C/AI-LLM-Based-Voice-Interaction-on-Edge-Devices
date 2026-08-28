import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import UnlessCondition

def generate_launch_description():
    # Get the package's shared directory. / 获取包的共享目录。
    params_file=os.path.join(get_package_share_directory('largemodel'), "config", "cgp.yaml") 

    # Launch arguments. / 启动参数。
    text_chat_mode = LaunchConfiguration('text_chat_mode', default=False)
    text_chat_mode_arg= DeclareLaunchArgument('text_chat_mode', default_value=text_chat_mode)
    
    # Define nodes. / 定义节点。
    model_server = Node(
        package='largemodel',
        executable='model_service',
        name='model_service',
        parameters=[
            params_file,
            {
                'text_chat_mode': text_chat_mode,
            }  # Dynamic parameter, command line arguments override the homonymous parameters in yahboom.yaml and are passed to the node. / 动态参数，命令行参数覆盖yahboom.yaml同名参数再传给节点。
        ],
        output='screen'
    )

    asr_server = Node(
        package='largemodel',
        executable='asr',
        name='asr',
        parameters=[params_file],
        output='screen',
        condition=UnlessCondition(text_chat_mode)
    )

    return LaunchDescription([
        text_chat_mode_arg,    # Declare launch arguments. / 声明启动参数。
        model_server,          # Start the model service node. / 启动模型服务节点。
        asr_server,            # Start the ASR user interaction node. / 启动asr用户交互节点。
    ])





