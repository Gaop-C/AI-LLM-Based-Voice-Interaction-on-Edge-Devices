"""
Tool Adapters
Wraps existing tools into a standardized interface.
/
工具适配器
将现有工具包装成标准化接口。
"""

from typing import Dict, Any, List, Optional
import os
import json
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class ToolOutput:
    """Standardized tool output format. / 标准化的工具输出格式。"""
    tool_name: str
    success: bool
    data: Any  # Main output data / 主要输出数据
    metadata: Dict[str, Any]  # Metadata (e.g., file paths, coordinates) / 元数据（如文件路径、坐标等）
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format. / 转换为字典格式。"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "metadata": self.metadata,
            "error_message": self.error_message
        }

@dataclass
class ToolInput:
    """Standardized tool input format. / 标准化的工具输入格式。"""
    arguments: Dict[str, Any]  # Original parameters / 原始参数
    previous_outputs: List[ToolOutput]  # Outputs from preceding tools / 前置工具的输出
    context: Dict[str, Any]  # Global context / 全局上下文
    
    def get_previous_output_by_tool(self, tool_name: str) -> Optional[ToolOutput]:
        """Get previous output by tool name. / 根据工具名获取前置输出。"""
        for output in self.previous_outputs:
            if output.tool_name == tool_name:
                return output
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert ToolInput to a printable dictionary. / 将ToolInput转换为可打印的字典。"""
        return {
            "arguments": self.arguments,
            "previous_outputs": [o.to_dict() for o in self.previous_outputs],
            "context": self.context
        }
    
    def get_latest_output(self) -> Optional[ToolOutput]:
        """Get the latest tool output. / 获取最新的工具输出。"""
        return self.previous_outputs[-1] if self.previous_outputs else None

class ToolInterface(ABC):
    """Base class for tool interfaces. / 工具接口基类。"""
    
    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Tool name. / 工具名称。"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Input parameter schema definition. / 输入参数模式定义。"""
        pass
    
    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """Output data schema definition. / 输出数据模式定义。"""
        pass
    
    @abstractmethod
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Execute tool logic. / 执行工具逻辑。"""
        pass

class SeeWhatToolAdapter(ToolInterface):
    """seewhat tool adapter. / seewhat工具适配器。"""
    
    def __init__(self, tools_chain_manager):
        self.tools_chain_manager = tools_chain_manager
    
    @property
    def tool_name(self) -> str:
        return "seewhat"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "description": "Captures an image from the camera to analyze the current environment. Input: None. Output: The scene description can be found in the 'data' field. The image path can be found in the 'metadata.image_path' field.",
            "properties": {},
            "required": []
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "image_path": {"type": "string"}
            }
        }
    
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        try:
            # Call the seewhat method which now returns a structured dictionary. / 调用已返回结构化字典的seewhat方法。
            result = None

            if result and isinstance(result, dict):
                # Correctly wrap the structured data into ToolOutput. / 将结构化数据正确地包装到ToolOutput中。
                output = ToolOutput(
                    tool_name=self.tool_name,
                    success=True,
                    data=result.get("description"),
                    metadata={
                        "image_path": result.get("image_path"),
                        "analysis_type": "environment"
                    }
                )
                # self.tools_manager.node.get_logger().info(f"Tool {self.tool_name} successful output: {json.dumps(output.to_dict(), indent=2, ensure_ascii=False)}")
                return output
            else:
                return ToolOutput(
                    tool_name=self.tool_name,
                    success=False,
                    data=None,
                    metadata={},
                    error_message="Failed to get structured data from seewhat"
                )
        except Exception as e:
            return ToolOutput(
                tool_name=self.tool_name,
                success=False,
                data=None,
                metadata={},
                error_message=str(e)
            )


class AnalyzeVideoToolAdapter(ToolInterface):
    """analyze_video tool adapter. / analyze_video工具适配器。"""
    
    def __init__(self, tools_chain_manager):
        self.tools_chain_manager = tools_chain_manager
    
    @property
    def tool_name(self) -> str:
        return "analyze_video"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "description": "Analyzes the content of a video file from a given path. Input: 'video_path' (string). Output: The video description can be found in the 'data' field.",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Full path to the video file to be analyzed"
                }
            },
            "required": []
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "video_path": {"type": "string"}
            }
        }
    
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        try:
            result = None

            if result and isinstance(result, dict) and result.get("description"):
                output = ToolOutput(
                    tool_name=self.tool_name,
                    success=True,
                    data=result.get("description"),
                    metadata={
                        "video_path": result.get("video_path"),
                        "analysis_type": "video_content"
                    }
                )
                # self.tools_manager.node.get_logger().info(f"Tool {self.tool_name} successful output: {json.dumps(output.to_dict(), indent=2, ensure_ascii=False)}")
                return output
            else:
                error_msg = result.get("error", "Failed to get structured data from analyze_video")
                return ToolOutput(
                    tool_name=self.tool_name,
                    success=False,
                    data=None,
                    metadata={"video_path": result.get("video_path")},
                    error_message=error_msg
                )
        except Exception as e:
            return ToolOutput(
                tool_name=self.tool_name,
                success=False,
                data=None,
                metadata={},
                error_message=str(e)
            )


class WriteDocumentToolAdapter(ToolInterface):
    """write_document tool adapter. / write_document工具适配器。"""
    
    def __init__(self, tools_chain_manager):
        self.tools_chain_manager = tools_chain_manager
    
    @property
    def tool_name(self) -> str:
        return "write_document"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "description": "Creates and saves a text document. Input: 'content' (string), 'format' (string), 'title' (string, optional), 'filename' (string, optional). Output: The original content written to the file can be found in the 'data' field. The saved file path can be found in the 'metadata.file_path' field.",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename with extension (optional, auto-generated if not provided)"
                },
                "content": {
                    "type": "string",
                    "description": "Text content for creating documents, articles, poems, stories, reports, or any written content. ⚠️ IMPORTANT: This tool ONLY creates text/document content. It CANNOT and should NOT be used for image creation, artwork, or visual content. For any visual content, use generate_image tool instead."
                },
                "format": {
                    "type": "string",
                    "description": "Document format: md, txt, html, json",
                    "enum": ["md", "txt", "html", "json"]
                },
                "title": {
                    "type": "string",
                    "description": "Title of the document"
                }
            },
            "required": []
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"}
            }
        }
    
    
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        try:
            # Call the write_document method which now returns a structured dictionary. / 调用已返回结构化字典的write_document方法。
            result = None

            if result and isinstance(result, dict) and result.get("file_path"):
                # Correctly wrap the structured data into ToolOutput. / 将结构化数据正确地包装到ToolOutput中。
                output = ToolOutput(
                    tool_name=self.tool_name,
                    success=True,
                    data=result.get("content"),
                    metadata={
                        "file_path": result.get("file_path"),
                        "format": tool_input.arguments.get("format", "txt"),
                        "title": tool_input.arguments.get("title", "文档")
                    }
                )
                # self.tools_manager.node.get_logger().info(f"Tool {self.tool_name} successful output: {json.dumps(output.to_dict(), indent=2, ensure_ascii=False)}")
                return output
            else:
                return ToolOutput(
                    tool_name=self.tool_name,
                    success=False,
                    data=result.get("status_message", "Failed to write document"),
                    metadata={}
                )
        except Exception as e:
            return ToolOutput(
                tool_name=self.tool_name,
                success=False,
                data=None,
                metadata={},
                error_message=str(e)
            )


class GenerateImageToolAdapter(ToolInterface):
    """generate_image tool adapter. / generate_image工具适配器。"""
    
    def __init__(self, tools_chain_manager):
        self.tools_chain_manager = tools_chain_manager
    
    @property
    def tool_name(self) -> str:
        return "generate_image"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "description": "Generates an image based on a descriptive text prompt. Input: 'prompt' (string). Output: A JSON object containing the generation result is in the 'data' field. The local path of the saved image can be found in 'data.saved_paths'.",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Visual description for creating images, artwork, pictures, drawings, paintings, or any visual content. ⚠️ IMPORTANT: This tool ONLY creates visual/image content. It CANNOT and should NOT be used for text creation like poems, articles, stories, or documents. For any text-based content, use write_document tool instead."
                }
            },
            "required": ["prompt"]
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_urls": {"type": "array"},
                "status": {"type": "string"}
            }
        }
    
    
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        try:
            result = None

            # The generate_image method now returns a dictionary, which is placed directly in the data field. / 现在 generate_image 返回的是一个字典，直接放入 data 字段。
            # Determine success based on the returned result. / 根据返回结果判断成功与否。
            success = isinstance(result, dict) and result.get('status') == 'success'
            
            output = ToolOutput(
                tool_name=self.tool_name,
                success=success,
                data=result,  # Place the complete dictionary in the data field. / 将完整的字典放入 data 字段。
                metadata={"prompt": tool_input.arguments.get("prompt", "")}
            )
            if output.success:
                # self.tools_manager.node.get_logger().info(f"Tool {self.tool_name} successful output: {json.dumps(output.to_dict(), indent=2, ensure_ascii=False)}")
                pass # Log has been commented out. / 日志已注释。
            return output
        except Exception as e:
            return ToolOutput(
                tool_name=self.tool_name,
                success=False,
                data=None,
                metadata={},
                error_message=str(e)
            )


class ScanTableToolAdapter(ToolInterface):
    """scan_table tool adapter. / scan_table工具适配器。"""
    
    def __init__(self, tools_chain_manager):
        self.tools_chain_manager = tools_chain_manager
    
    @property
    def tool_name(self) -> str:
        return "scan_table"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "description": "Scans an image to find and extract tabular data. Input: 'image_path' (string). Output: The extracted table content in Markdown format can be found in the 'data' field. The path to the saved markdown file can be found in 'metadata.file_path'.",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to image file containing table (can be auto-filled from previous image capture)"
                }
            },
            "required": []
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "table_content": {"type": "string"},
                "file_path": {"type": "string"}
            }
        }
    
    
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        try:
            # Call the scan_table method which now returns a structured dictionary. / 调用已返回结构化字典的scan_table方法。
            result = None

            if result and isinstance(result, dict):
                # Correctly wrap the structured data into ToolOutput. / 将结构化数据正确地包装到ToolOutput中。
                output = ToolOutput(
                    tool_name=self.tool_name,
                    success=True,
                    data=result.get("table_content"),
                    metadata={
                        "file_path": result.get("file_path"),
                        "image_path": tool_input.arguments.get("image_path", "")
                    }
                )
                # self.tools_manager.node.get_logger().info(f"Tool {self.tool_name} successful output: {json.dumps(output.to_dict(), indent=2, ensure_ascii=False)}")
                return output
            else:
                return ToolOutput(
                    tool_name=self.tool_name,
                    success=False,
                    data=None,
                    metadata={},
                    error_message="Failed to get structured data from scan_table"
                )
        except Exception as e:
            return ToolOutput(
                tool_name=self.tool_name,
                success=False,
                data=None,
                metadata={},
                error_message=str(e)
            )


class VisualPositioningToolAdapter(ToolInterface):
    """visual_positioning tool adapter. / visual_positioning工具适配器。"""
    
    def __init__(self, tools_chain_manager):
        self.tools_chain_manager = tools_chain_manager
    
    @property
    def tool_name(self) -> str:
        return "visual_positioning"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "description": "Locates a specific object within an image. Input: 'image_path' (string), 'object_name' (string). Output: The coordinates of the found object can be found in the 'data' field. The path to the saved result file can be found in 'metadata.file_path'.",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file for visual positioning"
                },
                "object_name": {
                    "type": "string",
                    "description": "Name of the object to locate in the image"
                }
            },
            "required": ["object_name"]
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "coordinates": {"type": "string"},
                "file_path": {"type": "string"}
            }
        }
    
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        try:
            # Call the visual_positioning method which now returns a structured dictionary. / 调用已返回结构化字典的visual_positioning方法。
            result = None

            if result and isinstance(result, dict):
                # Correctly wrap the structured data into ToolOutput. / 将结构化数据正确地包装到ToolOutput中。
                output = ToolOutput(
                    tool_name=self.tool_name,
                    success=True,
                    data=result.get("coordinates_content"),
                    metadata={
                        "file_path": result.get("file_path"),
                        "explanation": result.get("explanation_content")
                    }
                )
                # self.tools_manager.node.get_logger().info(f"Tool {self.tool_name} successful output: {json.dumps(output.to_dict(), indent=2, ensure_ascii=False)}")
                return output
            else:
                return ToolOutput(
                    tool_name=self.tool_name,
                    success=False,
                    data=None,
                    metadata={},
                    error_message="Failed to get structured data from visual_positioning"
                )
        except Exception as e:
            return ToolOutput(
                tool_name=self.tool_name,
                success=False,
                data=None,
                metadata={},
                error_message=str(e)
            )
