import os
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String,Bool
from utils import large_model_interface
from utils.tools_chain_manager import ToolChainManager
from ament_index_python.packages import get_package_share_directory
import threading
import pygame
import numpy as np
import atexit

class LargeModelService(Node):
    def __init__(self):
        super().__init__('LargeModelService')

        self.init_param_config()

        # Dependencies first: initialize all tools and services. / 依赖前置：先初始化所有工具和服务。
        self.tools_chain_manager = ToolChainManager(self)
        from utils.mcp_server import MCPServer
        self.mcp_server = MCPServer(self, self.tools_chain_manager)

        # Then initialize the large models that depend on them. / 再初始化依赖它们的大模型。
        self.init_largemodel()

        # Finally, initialize other modules. / 最后初始化其他模块。
        self.init_ros_comunication()

        # Initialize the audio player. / 初始化音频播放器。
        pygame.mixer.init()
        self.current_thread = None
        self.stop_event = threading.Event()

        # Used to save and trace Ollama's messages in multi-turn conversations. / 用于在多轮对话中保存和追溯Ollama的message。
        self.message_file_path = os.path.join(self.pkg_path, "resources_file", "conversation_message.json")
        self.init_message_file()
        atexit.register(self.cleanup_message_file)

        # Log information. / 打印日志。
        self.get_logger().info('LargeModelService node Initialization completed...')

    def init_param_config(self):
        """Initializes ROS parameters and file paths. / 初始化ROS参数和文件路径。"""
        src_path = os.path.expanduser("~/cgp_ws/src/largemodel")
        if os.path.exists(src_path):
            self.pkg_path = src_path
            self.get_logger().info(f"Using development path: {self.pkg_path}")
        else:
            self.pkg_path = get_package_share_directory('largemodel')
            self.get_logger().info(f"Using install path: {self.pkg_path}")
        # Declare parameters. / 参数声明。
        self.declare_parameter('language', 'zh')
        self.declare_parameter('text_chat_mode', False)
        self.declare_parameter('llm_platform', 'ollama')
        self.declare_parameter('useolinetts', False)
        self.declare_parameter("regional_setting", "China")

        # Get parameters from the parameter server. / 获取参数服务器参数。
        self.language = self.get_parameter('language').get_parameter_value().string_value 
        self.text_chat_mode = self.get_parameter('text_chat_mode').get_parameter_value().bool_value 
        self.useolinetts = self.get_parameter('useolinetts').get_parameter_value().bool_value
        self.llm_platform = self.get_parameter('llm_platform').get_parameter_value().string_value
        self.regional_setting = (self.get_parameter("regional_setting").get_parameter_value().string_value)

        # Set TTS output path. / 设置TTS输出路径。

    def init_largemodel(self):
        """Initializes the large language model client based on configuration. / 根据配置初始化大语言模型客户端。"""
        # Create a model interface client and pass the platform name and logger. / 创建模型接口客户端,并传入平台名称和logger。
        self.model_client = large_model_interface.model_interface(
            llm_platform=self.llm_platform,
            logger=self.get_logger(),
            mcp_server=self.mcp_server
        )
        # Call LLM initialization. / 调用LLM初始化。
        self.model_client.init_llm()
        # Initialize the language for the large model interface. / 初始化大模型接口的语言。
        self.model_client.init_language(self.language)
        self.model_client.init_messages()
        self.get_logger().info(f'Using LLM platform: {self.llm_platform}')

    def init_ros_comunication(self):
        """Initializes all ROS2 publishers and subscribers. / 初始化所有ROS2的发布者和订阅者。"""
        # ASR topic subscriber. / asr话题订阅者。
        self.asrsub = self.create_subscription(String,'asr', self.asr_callback,1)
        # Create a text interaction publisher. / 创建文字交互发布者。
        self.text_pub = self.create_publisher(String, "text_response", 1)
        # Create a TTS publisher. / 创建TTS发布者。
        self.TTS_publisher = self.create_publisher(String, "tts_topic", 5)
        # Initialize the TTS system. / 初始化TTS系统。
        self.system_sound_init()
        # Create a wake-up subscriber. / 创建唤醒订阅者。
        self.wakeup_sub = self.create_subscription(Bool, 'wakeup', self.wakeup_callback, 5)

    def init_message_file(self):
        """Initialize the message file. / 初始化message文件。"""
        try:
            # Ensure the directory exists. / 确保目录存在。
            os.makedirs(os.path.dirname(self.message_file_path), exist_ok=True)
            
            # If the file does not exist or is empty, create an empty message array. / 如果文件不存在或为空，创建空的message数组。
            if not os.path.exists(self.message_file_path):
                with open(self.message_file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)  # Ensure it's an empty array. / 确保是空数组。
            else:
                # Check the format of the existing file. / 检查现有文件格式。
                try:
                    with open(self.message_file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            json.loads(content)  # Verify JSON format. / 验证JSON格式。
                        else:
                            # If the file is empty, write an empty array. / 文件为空，写入空数组。
                            with open(self.message_file_path, 'w', encoding='utf-8') as f:
                                json.dump([], f, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    # If the file format is incorrect, reinitialize. / 文件格式错误，重新初始化。
                    self.get_logger().warning("Message file format error, reinitializing...")
                    with open(self.message_file_path, 'w', encoding='utf-8') as f:
                        json.dump([], f, ensure_ascii=False, indent=2)
                    
            self.get_logger().info(f"Message file initialized at: {self.message_file_path}")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize message file: {e}")

    def save_message_to_file(self, messages):
        """Save messages to a file. / 保存message到文件。"""
        try:
            with open(self.message_file_path, 'w', encoding='utf-8') as f:
                messages_to_save = messages if messages is not None else []
                
                # Ensure the uniqueness and existence of the system prompt. / 确保 system prompt 的唯一性和存在性。
                # 1. Get the correct initial message list containing the system prompt from memory. / 1. 从内存中获取包含 system prompt 的、正确的初始消息列表。
                initial_template = self.model_client.messages.copy()
                
                # 2. From the messages to be saved, filter out only the user and assistant conversation history. / 2. 从待保存的消息中，只筛选出 user 和 assistant 的对话历史。
                history_only = [m for m in messages_to_save if m.get('role') in ['user', 'assistant']]
                
                # 3. Merge the correct initial template with the clean conversation history. / 3. 将正确的初始模板和纯净的对话历史合并。
                final_messages = initial_template + history_only

                # Limit the size of messages to prevent the file from becoming too large. / 限制messages大小，防止文件过大。
                if len(final_messages) > 50:
                    # Truncate only the user and assistant messages. / 只截断 user 和 assistant 的消息。
                    recent_history = [m for m in final_messages if m.get('role') in ['user', 'assistant']][-40:]
                    # Re-merge with the initial template and the truncated history. / 重新用初始模板和截断后的历史合并。
                    final_messages = initial_template + recent_history
                
                json.dump(final_messages, f, ensure_ascii=False, indent=2)
                    
            self.get_logger().debug(f"Messages saved to file, size: {len(final_messages)}")
        except Exception as e:
            self.get_logger().error(f"Failed to save messages to file: {e}")

    def load_message_from_file(self):
        """Load messages from a file. / 从文件加载messages。"""
        try:
            if os.path.exists(self.message_file_path):
                with open(self.message_file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return []  # Return empty list for empty file
                    messages = json.loads(content)
                    
                # Check and limit the number of messages. / 检查并限制消息数量。
                if isinstance(messages, list) and len(messages) > 100:
                    system_msgs = [msg for msg in messages if msg.get('role') == 'system']
                    recent_msgs = [msg for msg in messages if msg.get('role') != 'system'][-80:]
                    messages = system_msgs + recent_msgs
                    self.save_message_to_file(messages)  # Save the truncated messages. / 保存截断后的messages。
                    self.get_logger().info("Messages truncated after loading from file")
                    
                self.get_logger().debug(f"Messages loaded from file, count: {len(messages) if messages else 0}")
                return messages
            else:
                return []  # File doesn't exist, return empty list
        except Exception as e:
            self.get_logger().error(f"Failed to load messages from file: {e}")
            self.clear_message_file()  # Clear corrupted file
            return []  # Return empty list

    def cleanup_message_file(self):
        """Clean up the message file. / 清理message文件。"""
        try:
            if os.path.exists(self.message_file_path):
                os.remove(self.message_file_path)
                print(f"Message file cleaned up: {self.message_file_path}")
        except Exception as e:
            print(f"Failed to cleanup message file: {e}")

    def clear_message_file(self):
        """Clear the message content. / 清空message内容。"""
        self.save_message_to_file(None)
        self.get_logger().info("Message file cleared")

    # TTS initialization. / TTS初始化。
    def system_sound_init(self):
        """Initialize TTS system"""
        if self.regional_setting == "China":  # 如果是中国地区
            if self.useolinetts:
                model_type = "oline"
                self.tts_out_path = os.path.join(self.pkg_path, "resources_file", "tts_output.mp3")
            else:
                model_type = "local"
                self.tts_out_path = os.path.join(self.pkg_path, "resources_file", "tts_output.wav")
        elif self.regional_setting == "international":  # 如果是国际地区
            model_type = "XUNFEI_FOR_INTERNATIONAL"
            self.tts_out_path = os.path.join(self.pkg_path, "resources_file", "XUNFEI_TTS.mp3")
        else:
            while True:
                self.get_logger().info()(
                    'Please check the regional_setting parameter in yahboom.yaml file, it should be either "China" or "international".'
                )
                time.sleep(1)
        self.model_client.tts_model_init(model_type, self.language)
        self.get_logger().info(f'TTS initialized with {model_type} model')

    # Wake-up callback. / 唤醒回调。
    def wakeup_callback(self, msg):
        """Handle wake-up signals"""
        if msg.data:
            self.get_logger().info('Received wake-up signal, attempting to stop audio.')
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                self.get_logger().info('pygame.mixer.music stopped directly.')
            
            if self.current_thread and self.current_thread.is_alive():
                self.stop_event.set()

    def asr_callback(self,msg):
        """Callback function for handling ASR messages. / 处理ASR消息的回调函数。"""
        # 1. Load history from file. / 1. 从文件加载历史记录。
        messages_to_use = self.load_message_from_file()

        # 2. Check if the history is valid. If it's empty or doesn't contain a system prompt,
        #    it indicates a new conversation, so initialize with the template from memory.
        #/ 2. 检查历史记录是否有效。如果为空或不包含system prompt，
        #    则说明是一次全新的对话，使用内存中的模板进行初始化。
        if not messages_to_use or not any(d.get('role') == 'system' for d in messages_to_use):
            self.get_logger().info("No valid history in file, starting a new conversation with template.")
            messages_to_use = self.model_client.messages.copy()

        # Call the new unified interface. infer_with_text will append the current user input (msg.data).
        #/ 调用新的统一接口。infer_with_text会负责将当前用户输入(msg.data)追加进去
        result = self.model_client.infer_with_text(msg.data, message=messages_to_use)

        self.process_model_result(result)

    def process_model_result(self, result, from_seewhat=False):
        """Process the result returned by the model. / 处理模型返回的结果。"""
        response_text = ""
        tools_list = []

        if isinstance(result, dict):
            new_messages = result.get('messages')
            if new_messages:
                self.save_message_to_file(new_messages)
            response_text = result.get('response', '')
        else:
            self.clear_message_file()
            response_text = result

        # Extract tool calls and user-friendly responses. / 提取工具调用和用户友好的回复。
        user_friendly_response = response_text
        try:
            json_str = self.extract_json_content(response_text)
            response_json = json.loads(json_str)

            # Extract the tool list. / 提取工具列表。
            tools_list = response_json.get("tools", [])

            # Extract user-friendly response text instead of technical JSON. / 提取用户友好的回复文本，而不是技术性的JSON。
            extracted_response = response_json.get("response", "")
            #self.get_logger().info(f'extracted_response:  {extracted_response}')
            if extracted_response and not extracted_response.startswith('{'):
                # If the response field contains user-friendly text, use it. / 如果response字段包含用户友好的文本，使用它。
                user_friendly_response = extracted_response
            else:
                # Otherwise, generate a friendly response. / 否则生成一个友好的回复。
                if self.regional_setting == "international": 
                    if tools_list:
                        tool_names = [tool.get('name', 'unknown') if isinstance(tool, dict) else str(tool) for tool in tools_list]
                        user_friendly_response = f"Okay, I'll perform these operations for you：{', '.join(tool_names)}"
                    else:
                        user_friendly_response = "I am currently processing your request..."
                else:
                    if tools_list:
                        tool_names = [tool.get('name', 'unknown') if isinstance(tool, dict) else str(tool) for tool in tools_list]
                        user_friendly_response = f"好的，我来为您执行这些操作：{', '.join(tool_names)}"
                    else:
                        user_friendly_response = "我正在处理您的请求..."
            
            self.get_logger().info(f'JSON parsed successfully, extracted {len(tools_list)} tools')
        except Exception as e:
            self.get_logger().warning(f'JSON parsing from response failed: {e}. Using raw response.')
            tools_list = []

        # 统一使用 _provide_feedback 方法处理反馈，无论是否有工具要执行
        # 这样可以确保在语音模式下既播报又打印日志
        if user_friendly_response:
            self._provide_feedback(user_friendly_response)

    def _clean_text_for_speech(self, text):
        """
        Clean text from Markdown formatting symbols to make it suitable for speech synthesis.
        Simplified version for minimal cleaning.
        清理文本中的Markdown格式符号，使其适合语音播报
        简化版本，只进行最基本的清理
        """
        if not text:
            return text
        
        import re
        
        try:
            # Basic cleaning operations for common Markdown symbols
            # 基本的Markdown符号清理操作
            # Remove heading markers, list markers, and formatting symbols
            # 移除标题标记、列表标记和格式符号
            text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)  # Headings / 标题
            text = re.sub(r'^\s*[-+*]\s+', '', text, flags=re.MULTILINE)  # Unordered lists / 无序列表
            text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # Ordered lists / 有序列表
            text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)  # Bold and italic (***text***)
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold (**text**)
            text = re.sub(r'\*(.*?)\*', r'\1', text)  # Italic (*text*)
            text = re.sub(r'___(.*?)___', r'\1', text)  # Bold and italic (___text___)
            text = re.sub(r'__(.*?)__', r'\1', text)  # Bold (__text__)
            text = re.sub(r'_(.*?)_', r'\1', text)  # Italic (_text_)
            text = re.sub(r'```[\s\S]*?```', '', text)  # Code blocks / 代码块
            text = re.sub(r'`([^`]*)`', r'\1', text)  # Inline code / 行内代码
            text = re.sub(r'$([^\]]*)$$[^\)]*$$', r'\1', text)  # Links / 链接
            text = re.sub(r'!$([^\]]*)$$[^\)]*$$', '', text)  # Images / 图片
            text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)  # Blockquotes / 引用
            
            # Clean up extra whitespace and newlines
            # 清理多余的空白和换行
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            text = re.sub(r' +', ' ', text)
            text = text.strip()
            
            # Remove or replace special characters that may cause TTS issues
            # 移除或替换可能导致TTS问题的特殊字符
            text = re.sub(r'[\u2013\u2014]', '-', text)  # En/em dash
            text = re.sub(r'[\u2018\u2019]', "'", text)  # Single quotes
            text = re.sub(r'[\u201c\u201d]', '"', text)  # Double quotes
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Control characters
            
            # Limit text length to prevent TTS issues with very long texts
            # 限制文本长度以防止TTS处理超长文本时出现问题
            max_length = 2000
            if len(text) > max_length:
                text = text[:max_length].rsplit(' ', 1)[0] + '...'
            
        except Exception as e:
            self.get_logger().warning(f"Error during text cleaning for speech: {e}. Using original text.")
            return text[:2000] if len(text) > 2000 else text
        
        return text

    def _provide_feedback(self, message):
        """Unified feedback mechanism. / 统一的反馈机制。"""
        feedback_message = str(message)

        self.get_logger().info(f"{feedback_message}")
        # 发布文本消息
        text_msg = String(data=feedback_message)
        self.text_pub.publish(text_msg)

        # 清理文本中的Markdown格式符号，使其适合语音播报
        try:
            cleaned_message = self._clean_text_for_speech(feedback_message)
            
        except Exception as e:
            self.get_logger().error(f"Exception in _clean_text_for_speech: {e}")
            cleaned_message = feedback_message  # Use original message if cleaning fails
        
        # 合成并播放语音
        self._safe_play_audio(cleaned_message)

    def play_audio(self, file_path, feedback=False):
        """Play audio file synchronously. / 同步方式播放音频函数。"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if self.stop_event.is_set():
                    pygame.mixer.music.stop()
                    self.stop_event.clear()
                    return
                pygame.time.delay(100)
        except Exception as e:
            self.get_logger().error(f"Error playing audio: {e}")

    def play_audio_async(self, file_path, feedback=False):
        """Play audio asynchronously. / 异步方式播放音频函数。"""
        if self.current_thread and self.current_thread.is_alive():
            self.stop_event.set()
            self.current_thread.join()
            self.stop_event.clear()
        
        def target():
            self.play_audio(file_path, feedback)
        
        self.current_thread = threading.Thread(target=target)
        self.current_thread.daemon = True
        self.current_thread.start()

    def _safe_play_audio(self, text_to_speak: str):
        """
        Synthesizes and plays all non-empty messages only in non-text chat mode.
        /
        仅在非文字聊天模式下，对所有非空消息合成并播放语音。
        """
        if not self.text_chat_mode and text_to_speak:
            try:
                # Synthesize and broadcast all valid incoming feedback messages. / 对所有传入的有效反馈信息都进行语音播报。
                self.model_client.voice_synthesis(text_to_speak, self.tts_out_path)
                self.play_audio_async(self.tts_out_path)
            except Exception as e:
                self.get_logger().error(f"Safe audio playback failed: {e}")

    @staticmethod
    def extract_json_content(raw_content):
        """Extracts a JSON string from raw text content, handling various formats. / 从原始文本内容中提取JSON字符串，处理各种格式。"""
        try:
            # Method 1: Split the code block. / 方法一：分割代码块。
            if '```json' in raw_content:
                # Split the code block and take the middle part. / 分割代码块并取中间部分。
                json_str = raw_content.split('```json')[1].split('```')[0].strip()
            elif '```' in raw_content:
                # Handle code blocks without a specified type. / 处理没有指定类型的代码块。
                json_str = raw_content.split('```')[1].strip()
            else:
                # Method 2: Use a more powerful JSON extraction method. / 方法二：使用更强大的JSON提取方法。
                json_str = LargeModelService._extract_json_from_text(raw_content)

            # Method 3: Fallback simple regular expression (if the above methods fail). / 方法三：备用的简单正则表达式（如果上面的方法失败）。
            if not json_str or not json_str.strip().startswith('{'):
                import re
                match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if match:
                    json_str = match.group()

            # Check if possible JSON content was found. / 检查是否找到了可能的JSON内容。
            if not json_str or not json_str.strip().startswith('{'):
                # Handle special characters to make the text safe for JSON. / 处理特殊字符，使文本安全用于JSON。
                # Replace all characters that could cause JSON parsing errors. / 替换所有可能导致JSON解析错误的字符。
                safe_content = raw_content.replace('\\', '\\\\')  # Handle backslashes first. / 先处理反斜杠。
                safe_content = safe_content.replace('"', '\\"')    # Handle quotes. / 处理引号。
                safe_content = safe_content.replace('\n', '\\n')   # Handle newlines. / 处理换行。
                safe_content = safe_content.replace('\r', '\\r')   # Handle carriage returns. / 处理回车。
                safe_content = safe_content.replace('\t', '\\t')   # Handle tabs. / 处理制表符。
                safe_content = safe_content.replace('\b', '\\b')   # Handle backspaces. / 处理退格。
                safe_content = safe_content.replace('\f', '\\f')   # Handle form feeds. / 处理换页。

                return '{"response": "' + safe_content + '"}'

            return json_str

        except Exception as e:
            # Also handle special characters. / 同样处理特殊字符。
            if raw_content:
                safe_content = str(raw_content)
                safe_content = safe_content.replace('\\', '\\\\')
                safe_content = safe_content.replace('"', '\\"')
                safe_content = safe_content.replace('\n', '\\n')
                safe_content = safe_content.replace('\r', '\\r')
                safe_content = safe_content.replace('\t', '\\t')
                safe_content = safe_content.replace('\b', '\\b')
                safe_content = safe_content.replace('\f', '\\f')

                return '{"response": "' + safe_content + '"}'
            return '{}'

    @staticmethod
    def _extract_json_from_text(text):
        """Extract a complete JSON object from text, supporting nested structures. / 从文本中提取完整的JSON对象，支持嵌套结构。"""
        # Find the position of the first {. / 找到第一个 { 的位置。
        start_pos = text.find('{')
        if start_pos == -1:
            return ""

        # Starting from the first {, find the matching }. / 从第一个 { 开始，找到匹配的 }。
        brace_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start_pos:], start_pos):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # A complete JSON object was found. / 找到了完整的JSON对象。
                        return text[start_pos:i+1]

        # If a complete JSON object is not found, return an empty string. / 如果没有找到完整的JSON，返回空字符串。
        return ""

def main(args=None):
    rclpy.init(args=args)
    model_service = LargeModelService()
    try:
        rclpy.spin(model_service)
    except KeyboardInterrupt:
        model_service.get_logger().info("KeyboardInterrupt received, shutting down...")
    except Exception as e:
        model_service.get_logger().error(f"Unexpected error: {e}")
    finally:
        # Clean up temporary files. / 清理临时文件。
        model_service.cleanup_message_file()
        model_service.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
