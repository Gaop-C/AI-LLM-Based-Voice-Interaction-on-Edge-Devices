"""
Tool chain data passing manager.
Implements a generic data flow mechanism between tools.
/
工具链数据传递管理器。
实现通用的工具间数据流转机制。
"""

from typing import Dict, Any, List, Optional, Union
import json
import logging
from utils.tool_adapters import (
    SeeWhatToolAdapter, AnalyzeVideoToolAdapter, WriteDocumentToolAdapter,
    GenerateImageToolAdapter, ScanTableToolAdapter,
    VisualPositioningToolAdapter, ToolInterface, 
    ToolInput, ToolOutput
)

class ToolChainManager:
    """Tool chain data passing manager. / 工具链数据传递管理器。"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.tools: Dict[str, ToolInterface] = {}
        self._setup_tool_chain()
        
    def register_tool(self, tool: ToolInterface):
        """Register a tool. / 注册工具。"""
        self.tools[tool.tool_name] = tool
    
    def _setup_tool_chain(self):
        """
        Register all tool adapters with tool chain manager.
        注册所有工具适配器到工具链管理器。
        """
        # Register tool adapters. / 注册工具适配器。
        self.register_tool(SeeWhatToolAdapter(self))
        self.register_tool(AnalyzeVideoToolAdapter(self))
        self.register_tool(WriteDocumentToolAdapter(self))
        self.register_tool(GenerateImageToolAdapter(self))
        self.register_tool(ScanTableToolAdapter(self))
        self.register_tool(VisualPositioningToolAdapter(self))
    
    def execute_tool_chain(self, tool_calls: List[Dict[str, Any]]) -> List[ToolOutput]:
        """Execute the tool chain. / 执行工具链。"""
        outputs = []
        context = {}
        
        for i, tool_call in enumerate(tool_calls):
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})
            
            if tool_name not in self.tools:
                self.logger.error(f"Tool not found: {tool_name}")
                continue
            
            # Create tool input. / 创建工具输入。
            tool_input = ToolInput(
                arguments=arguments,
                previous_outputs=outputs.copy(),
                context=context
            )
                        
            # Execute the tool. / 执行工具。
            try:
                # Debug log: print tool input. / 调试日志：打印工具输入。
                # self.logger.info(f"↓↓↓ [ToolChain] Executing Tool: {tool_name} ↓↓↓")
                # self.logger.info(f"ToolInput: {json.dumps(tool_input.to_dict(), indent=2, ensure_ascii=False)}")

                tool = self.tools[tool_name]
                output = tool.execute(tool_input)
                outputs.append(output)

                # Debug log: print tool output. / 调试日志：打印工具输出。
                # self.logger.info(f"ToolOutput: {json.dumps(output.to_dict(), indent=2, ensure_ascii=False)}")
                # self.logger.info(f"↑↑↑ [ToolChain] Finished Tool: {tool_name}, Success: {output.success} ↑↑↑")
                
                # Update context. / 更新上下文。
                context[f"{tool_name}_result"] = output.data
                
            except Exception as e:
                error_output = ToolOutput(
                    tool_name=tool_name,
                    success=False,
                    data=None,
                    metadata={},
                    error_message=str(e)
                )
                outputs.append(error_output)
                self.logger.error(f"Tool {tool_name} execution failed: {e}")
        
        return outputs
    

