# 🔧 Cleaned import statements - only keep used imports / 清理后的导入语句 - 只保留实际使用的导入
# from openai import OpenAI
# from sparkai.llm.llm import ChatSparkLLM
# from sparkai.core.messages import ChatMessage
# from dashscope.audio.asr import Recognition, TranslationRecognizerRealtime
from ollama import Client
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
import piper
from funasr import AutoModel
import os
import wave
from ament_index_python.packages import get_package_share_directory
import yaml
# import base64
import json
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError
# import datetime
# import time
# from datetime import datetime
# from wsgiref.handlers import format_date_time
# from time import mktime
# import hmac
# import hashlib
# import websocket
# import _thread as thread
# import ssl

class model_interface:
    def __init__(self, llm_platform='ollama', logger=None, mcp_server=None):
        self.llm_platform = llm_platform
        self.client = None
        self.logger = logger  # Save logger instance / 保存logger实例
        self.mcp_server = mcp_server  # Save mcp_server instance / 保存mcp_server实例
        self.init_config_param()
        dashscope.api_key = self.tongyi_api_key

    def init_config_param(self):
        self.pkg_path=get_package_share_directory('largemodel')      
        config_param_file = os.path.join(self.pkg_path, "config", "large_model_interface.yaml")
        with open(config_param_file, 'r') as file:
            config_param = yaml.safe_load(file)
        
        self.ANYTHINGLLM_BASE_URL = config_param.get("ANYTHINGLLM_BASE_URL")
        self.API_KEY = config_param.get("API_KEY")

        
        # Tongyi Qianwen configuration / 通义千问配置
        self.tongyi_api_key =config_param.get('tongyi_api_key')
        self.tongyi_base_url=config_param.get('tongyi_base_url')
        self.tongyi_model = config_param.get('tongyi_model')
        self.tongyi_media_model = config_param.get('tongyi_media_model', 'wanx-v1')

        # iFlytek Spark configuration / 讯飞星火配置
        self.spark_app_id = config_param.get('spark_app_id')
        self.spark_api_key = config_param.get('spark_api_key')
        self.spark_api_secret = config_param.get('spark_api_secret')
        self.spark_model = config_param.get('spark_model')
        self.spark_model_url = config_param.get('spark_model_url')
        self.spark_media_model = config_param.get('spark_media_model', 'image_understanding')

        # Baidu Qianfan configuration / 百度千帆配置
        self.qianfan_api_key = config_param.get('qianfan_api_key')
        self.qianfan_base_url = config_param.get('qianfan_base_url')
        self.qianfan_model = config_param.get('qianfan_model')
        self.qianfan_media_model = config_param.get('qianfan_media_model', 'ernie-vilg-v2')

        # OpenRouter configuration / OpenRouter配置
        self.openrouter_api_key = config_param.get('openrouter_api_key')
        self.openrouter_model = config_param.get('openrouter_model')

        # Ollama configuration / Ollama配置
        self.ollama_host = config_param.get('ollama_host', 'http://localhost:11434')
        self.ollama_model = config_param.get('ollama_model', 'llava')

        # ASR & TTS configuration / ASR & TTS 配置
        self.oline_asr_model=config_param.get('oline_asr_model')
        self.zh_tts_model=config_param.get('zh_tts_model')
        self.zh_tts_json=config_param.get('zh_tts_json')
        self.en_tts_model=config_param.get('en_tts_model')
        self.en_tts_json=config_param.get('en_tts_json')
        self.oline_asr_sample_rate=config_param.get('oline_asr_sample_rate')
        self.oline_tts_model=config_param.get('oline_tts_model')
        self.voice_tone=config_param.get('voice_tone')
        self.local_asr_model=config_param.get('local_asr_model')
        self.tts_supplier=config_param.get('tts_supplier')
        self.baidu_API_KEY=config_param.get('baidu_API_KEY')
        self.baidu_SECRET_KEY=config_param.get('baidu_SECRET_KEY')
        self.CUID=config_param.get('CUID')
        self.PER=config_param.get('PER')
        self.SPD=config_param.get('SPD')
        self.PIT=config_param.get('PIT')
        self.VOL=config_param.get('VOL')

    def init_llm(self):
        """Initialize the corresponding model client based on the platform name. / 根据平台名称初始化对应的模型客户端。"""
        if self.llm_platform == 'ollama':
            self.init_ollama()
        elif self.llm_platform == 'tongyi':
            self.init_tongyi()
        elif self.llm_platform == 'spark':
            self.init_spark()
        elif self.llm_platform == 'qianfan':
            self.init_qianfan()
        elif self.llm_platform == 'openrouter':
            self.init_openrouter()
        else:
            print(f"Unsupported LLM platform: {self.llm_platform}, defaulting to Ollama.")
            self.init_ollama()

    def init_language(self,language):
        self.system_text={}
        if language=='zh':
            self.system_text['text1']="请分析这个图像或视频"
            self.system_text['text2']="我已经准备好，请开始您的指令吧"        
        elif language=='en':
            self.system_text['text1']="Please analyze this image or video"        
            self.system_text['text2']="I am ready. Please start your instructions" 
        
    def init_messages(self):
        """General message history initialization. / 通用消息历史初始化。"""
        # Directly use the internally saved mcp_server instance / 直接使用内部保存的 mcp_server 实例
        self.messages = [
            {"role": "system", "content": self._generate_system_prompt(self.mcp_server)},
            {"role": "assistant", "content": self.system_text.get('text2', "I am ready.")}
        ]
    def _generate_system_prompt(self, mcp_server):
        """
        Dynamically generate the System Prompt.
        /
        动态生成系统级指令 (System Prompt)。
        """
        if not mcp_server:
            # Return a minimal system prompt without any tool descriptions.
            # /
            # 返回一个最简单的、不包含任何工具描述的系统提示。
            return "You are a helpful AI assistant."

        tools_description = mcp_server.get_tools_json_schema()

        # Check if language is set to English
        # 检查语言是否设置为英文
        is_english = hasattr(self, 'system_text') and 'text2' in self.system_text and 'Please start your instructions' in self.system_text['text2']
        
        # Fallback check using the node's language setting
        # 回退检查使用节点的语言设置
        if not is_english and hasattr(self, 'node') and hasattr(self.node, 'language'):
            is_english = self.node.language == 'en'

        # Return a more flexible Prompt that supports conversation, with bilingual comments.
        # /
        # 返回一个更灵活、支持对话的Prompt，并附带双语注释。
        if is_english:
            # English version of the system prompt
            # 英文版本的系统提示
            # Generate tool definitions separately to avoid f-string nesting issues
            
            return f'''You are the control hub for a robot, an AI capable of accurately converting natural language commands into JSON format, or engaging in natural conversation when no tools are available.

# Primary Rule
Your sole output must be a well-formed JSON object. Absolutely no text, explanations, or Markdown tags are allowed outside of the JSON.

# Tool Definition
The tools you can use are defined below. You must strictly adhere to their parameter schema:```json
{json.dumps(tools_description, indent=2, ensure_ascii=False)}
```

# Output Formats
Based on the user's intent, choose the most appropriate of the following three JSON structures for your response:

## Format 1: Direct Tool Call (For simple, explicit instructions)
```json
{{
  "response": "A confirmation or a brief reply to the user's command.",
  "tools": [
    {{
      "name": "Tool Name",
      "arguments": {{
        "parameter_name_1": "parameter_value_1"
      }}
    }}
  ]
}}
```

## Format 2: AI Agent Call (For complex, ambiguous, or multi-step instructions)
```json
{{
  "response": "Okay, this task requires some planning. Please wait a moment.",
  "tools": [
    {{
      "name": "agent_call",
      "arguments": {{
        "task": "This must be populated with the user's original, complete, and unmodified instruction."
      }}
    }}
  ]
}}```

## Format 3: General Conversation (When no tools are applicable)
```json
{{
  "response": "This is the model's direct answer, e.g., for weather conditions, general knowledge questions, etc.",
  "tools": []
}}
```

# Core Instructions & Logic

1.  **Parameter Extraction**:
    *   **Mandatory**: You **must** find a value for every required argument of a tool.
    *   **Intelligent Filling**: If the user's instruction is vague (e.g., "draw me a picture"), you must use the user's descriptive text ("draw a picture") as the value for the core parameter (e.g., the `prompt` parameter for the `generate_image` tool). **Never leave the parameter value empty.**
    *   **Default Values**: For path parameters like `image_path` or `video_path`, if the user does not explicitly provide one, you can leave it as an empty string (`""`). The system will automatically use a default file.

2.  **Decision Logic**:
    *   **First Priority**: If the user's instruction is clear, the intent is explicit, and a single tool can complete the task -> Use **Format 1**.
    *   **Second Priority**: If the user's instruction is ambiguous, broad, or clearly requires multiple steps (e.g., "look around and then draw what you see") -> Use **Format 2** by calling `agent_call`.
    *   **Third Priority (Fallback)**: If the user is just making small talk or asking questions (like about weather, news, or general knowledge) and **no tool can fulfill the request** -> Use **Format 3**, providing a direct answer in the `response` field and keeping the `tools` field empty.

3.  **Response Content (`response` field)**:
    *   This field is used for natural language interaction with the user and should be concise and friendly.

# Examples

```json
{{
  "response": "Okay, generating an image of a cyberpunk city at sunset for you.",
  "tools": [
    {{
      "name": "generate_image",
      "arguments": {{
        "prompt": "A cyberpunk city at sunset"
      }}
    }}
  ]
}}
```

**User Instruction**: "First, look at the surrounding environment, then write a document summarizing what you see"
**Your Output**:
```json
{{
  "response": "Okay, this task requires some planning. Please wait a moment.",
  "tools": [
    {{
      "name": "agent_call",
      "arguments": {{
        "task": "First, look at the surrounding environment, then write a document summarizing what you see"
      }}
    }}
  ]
}}
```

**User Instruction**: "Tell me a joke"
**Your Output**:
```json
{{
  "response": "Why are math books always so melancholic? Because it has too many problems.",
  "tools": [
    {{
      
    }}
  ]
}}
```

'''
        else:
            # Chinese version of the system prompt (original)
            # 中文版本的系统提示（原始版本）
            return f'''你是机器人的控制中枢，一个能将自然语言指令精确转换为JSON格式，或在无工具可用时进行自然对话的AI。

# 首要规则
你的唯一输出必须是一个结构完整的JSON对象。绝对禁止输出任何JSON之外的文本、解释或Markdown标记。

# 工具定义
你可使用的工具如下，请严格遵守其参数schema：
```json
{json.dumps(tools_description, indent=2, ensure_ascii=False)}
```

# 输出格式 / Output Formats
根据用户意图，从以下三种JSON结构中选择最合适的一种进行回复：

## 格式一：直接工具调用 (适用于简单、明确的指令)
```json
{{
  "response": "对用户指令的确认或简短回复。",
  "tools": [
    {{
      "name": "工具名称",
      "arguments": {{
        "参数名1": "参数值1"
      }}
    }}
  ]
}}
```

## 格式二：调用AI Agent (适用于复杂、模糊或多步指令)
```json
{{
  "response": "好的，这个任务需要我规划一下，请稍候。",
  "tools": [
    {{
      "name": "agent_call",
      "arguments": {{
        "task": "这里必须填充用户原始的、完整的、未经修改的指令。"
      }}
    }}
  ]
}}
```

## 格式三：常规对话 (当没有工具适用时)
```json
{{
  "response": "这里是模型的直接回答，例如天气情况、常识问答等。",
  "tools": []
}}
```

# 核心指令与逻辑

1.  **参数提取:
    *   **强制性**: **必须**为工具的每一个必需参数（required arugments）找到一个值。
    *   **智能填充**: 如果用户指令很模糊（例如“给我画张画”），你必须将用户的描述性文本（“画张画”）作为核心参数的值（例如 `generate_image` 工具的 `prompt` 参数）。**绝对不能将参数值留空。**
    *   **默认值**: 对于 `image_path` 或 `video_path`这类路径参数，如果用户没有明确提供，可以留空（`""`），系统会自动使用默认文件。

2.  **决策逻辑**:
    *   **第一顺位**: 如果用户指令清晰，意图明确，且单个工具就能完成 -> 使用**格式一**。
    *   **第二顺位**: 如果用户指令模糊、宽泛，或明显需要多个步骤（例如“看看周围有什么，然后画出来”） -> 使用**格式二**，调用`agent_call`。
    *   **第三顺位 (Fallback)**: 如果用户只是在进行日常对话、提问（如天气、新闻、常识），并且**没有任何工具能满足需求** -> 使用**格式三**，在 `response` 字段中直接回答，并保持 `tools` 字段为空。

3.  **回复内容 (`response`字段)**:
    *   此字段是用于与用户进行自然语言交互的，应简洁、友好。

# 示例

```json
{{
  "response": "好的，正在为您生成一张关于日落时分赛博朋克城市的图片。",
  "tools": [
    {{
      "name": "generate_image",
      "arguments": {{
        "prompt": "日落时分的赛博朋克城市"
      }}
    }}
  ]
}}
```

**用户指令**: "先看看周围环境，然后写一份文档总结你看到了什么"
**你的输出**:
```json
{{
  "response": "好的，这个任务需要我规划一下，请稍候。",
  "tools": [
    {{
      "name": "agent_call",
      "arguments": {{
        "task": "先看看周围环境，然后写一份文档总结你看到了什么"
      }}
    }}
  ]
}}
```
'''


    def init_ollama(self):
        """Initialize Ollama client"""
        try:
            self.client = Client(host=self.ollama_host)
            self.logger.info(f"Ollama client initialized successfully. Using model {self.ollama_model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama client: {e}")
            self.client = None

    def init_tongyi(self):
        """Initialize Tongyi client"""


    def init_spark(self):
        """Initialize Spark client"""


    def init_qianfan(self):
        """Initialize Qianfan client using OpenAI compatible mode"""


    def init_openrouter(self):
        """Initialize OpenRouter client"""


    def infer_with_text(self, prompt, message=None):
        """Unified text inference interface. / 统一的文本推理接口。"""
        self.messages = message if message is not None else self.messages
        self.messages.append({"role": "user", "content": prompt})

        if not self.client:
            return {'response': f"Client for platform {self.llm_platform} is not initialized.", 'messages': self.messages}

        try:
            if self.llm_platform == 'ollama':
                response_content = self.ollama_infer(self.messages)
            elif self.llm_platform in ['tongyi', 'qianfan', 'openrouter']:
                response_content = self.openai_compatible_infer(self.messages)
            elif self.llm_platform == 'spark':
                response_content = self.spark_infer(self.messages)
            else:
                response_content = f"Unsupported LLM platform: {self.llm_platform}"
        except Exception as e:
            response_content = f"Inference error on platform {self.llm_platform}: {e}"
        self.messages.append({"role": "assistant", "content": response_content})
        return {'response': response_content, 'messages': self.messages.copy()}


    def ollama_infer(self, messages, image_path=None, video_path=None):
        """Infer using Ollama, supporting tool calls and video analysis. / 使用Ollama推理，支持工具调用和视频分析。"""
        if not self.client:
            return "Error: Ollama client not initialized"

        if image_path:
            image_data = self.encode_file_to_base64(image_path)
            messages[-1]['images'] = [image_data]
        elif video_path:
            # For videos, extract keyframes for analysis / 对于视频，提取关键帧进行分析
            print(f"Starting to extract video frames: {video_path}")
            frame_images = self._extract_video_frames(video_path)
            if frame_images:
                print(f"Successfully extracted {len(frame_images)} video frames")
                messages[-1]['images'] = frame_images
            else:
                print("Failed to extract video frames")
                return "Error: Failed to extract frames from video"

        # Check if tool call support is needed / 检查是否需要工具调用支持
        # If it's video or image analysis, use normal mode to get a natural language description / 如果是视频或图像分析，使用普通模式获取自然语言描述
        if image_path or video_path:
            try:
                response = self.client.chat(model=self.ollama_model, messages=messages)
                return response['message']['content']
            except Exception as e:
                return f"Ollama multimedia analysis failed: {e}"
        else:
            # For text dialogues, try to use the tool call feature / 文本对话时尝试使用工具调用功能
            try:
                response = self.client.chat(
                    model=self.ollama_model,
                    messages=messages,
                    format='json'  # Request JSON format output to parse tool calls / 要求JSON格式输出以便解析工具调用
                )
                return response['message']['content']
            except Exception as e:
                print(f"Ollama tool call failed, falling back to normal mode: {e}")
                # Fallback to normal mode / 回退到普通模式
                try:
                    response = self.client.chat(model=self.ollama_model, messages=messages)
                    return response['message']['content']
                except Exception as e2:
                    return f"Ollama inference failed: {e2}"


    def init_local_asr_model(self):
        self.model_senceVoice = AutoModel(model=self.local_asr_model, trust_remote_code=False,disable_update=True)

    def tts_model_init(self,model_type='oline',language='zh'):
        if model_type=='oline':
            if self.tts_supplier=='baidu':
                self.token=self.fetch_token()
    
            self.model_type='oline'      
        elif model_type=='local':
            self.model_type='local'
            if language=='zh':
                tts_model=self.zh_tts_model
                tts_json=self.zh_tts_json
            elif language=='en':
                tts_model=self.en_tts_model
                tts_json=self.en_tts_json
            self.synthesizer = piper.PiperVoice.load(tts_model, config_path=tts_json, use_cuda=False)      

        elif model_type == "XUNFEI_FOR_INTERNATIONAL":
            self.model_type = "XUNFEI_FOR_INTERNATIONAL"

    def SenseVoiceSmall_ASR(self, input_file,language='zn'):
        res = self.model_senceVoice.generate(
            input=input_file,
            cache={},
            language=language,
            use_itn=False,
        )
        prompt = res[0]['text'].split(">")[-1]
        return ['ok', prompt]

    def voice_synthesis(self,text,path):
        if self.model_type=='oline':
            if self.tts_supplier=='baidu':
                TTS_URL = 'http://tsn.baidu.com/text2audio'
                tex = quote_plus(text)  
                params = {'tok': self.token, 'tex': tex, 'per': self.PER, 'spd': self.SPD, 'pit': self.PIT, 'vol': self.VOL, 'aue': 3, 'cuid': self.CUID,
                            'lan': 'zh', 'ctp': 1}

                data = urlencode(params)
                req = Request(TTS_URL, data.encode('utf-8'))
                try:
                    f = urlopen(req)
                    result_str = f.read()
                except  URLError as err:
                    print('asr http response http code : ' + str(err.code))
                    result_str = err.read()
                    return  1
                with open(path, 'wb') as of:
                    of.write(result_str)
                    return 0
            
            elif self.tts_supplier=='aliyun':
                self.synthesizer = SpeechSynthesizer(model= self.oline_tts_model, voice=self.voice_tone,volume=100)
                audio = self.synthesizer.call(text)
                if audio is None:
                    return 1
                else:
                    with open(path, 'wb') as f:
                        f.write(audio)  
                    return 0                                 
        elif self.model_type=='local':
            with wave.open(path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.synthesizer.config.sample_rate)
                self.synthesizer.synthesize(text, wav_file)    

        elif self.model_type == "XUNFEI_FOR_INTERNATIONAL":
            Xinghou_speaktts(text)       
