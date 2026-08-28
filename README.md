# 边缘设备的AI大模型语音交互

> 边缘设备的AI大模型语音交互是将离线ASR和离线TTS与离线的大语言模型（LLM）核心连接起来，形成一个完整的、能听、会说、会思考的对话系统。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Gaop-C/AI-LLM-Based-Voice-Interaction-on-Edge-Devices.svg)](https://github.com/Gaop-C/AI-LLM-Based-Voice-Interaction-on-Edge-Devices/stargazers)

## 📦 平台要求
Linux系统、ARM64架构（测试平台Raspberry Pi5 8G）

## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/Gaop-C/AI-LLM-Based-Voice-Interaction-on-Edge-Devices.git
```
并将cgp_ws文件夹复制到用户目录下方

### 2. 安装所需要的dockers环境
下载docker服务端，并将带有所需环境的docker镜像容器化，镜像链接：https://pan.baidu.com/s/1idSVjjMrFFO79_glgFDoqw?pwd=1234 提取码: 1234

### 3. 安装所需要的ollama服务
通过ollama途径下载所需的LLM，并在 cgp_ws\src\largemodel\config\large_model_interface.yaml 中配置 ollama_model 字段为相应模型

### 4. 下载ASR与TTS模型
分别放入 cgp_ws\src\largemodel\MODELS\asr 与 cgp_ws\src\largemodel\MODELS\tts （large_model_interface.yaml 默认配置）
下载链接：https://pan.baidu.com/s/1w7FlMGxKtAvCwCwdmtH_JQ?pwd=1234 提取码: 1234

### 5. 运行docker启动脚本文件
ros2_docker.sh

### 6. ROS2构建项目
进入运行的容器后，在挂载的工作空间目录cgp_ws下运行指令
```bash
colcon build
source install/setup.bash
echo "source ~/yahboomcar_ws/install/setup.bash" >> ~/.bashrc
```

### 7. 运行ROS2语音交互程序
```bash
ros2 launch largemodel largemodel_control.launch.py
```
唤醒: 对着麦克风说：“你好，小亚。”
对话: 扬声器回应之后，就可以说出你想提问的话。

### 8. 对话日志
可在 cgp_ws\src\largemodel\resources_file\conversation_message.json 中查看对话历史
