"""
标题: LLMProcessor
说明: LLM 智能分析处理器，负责调用大模型生成摘要和思维导图
时间: 2026-01-14
@author: zhoujunyu
"""

import json
from typing import Tuple, Optional
from dataclasses import dataclass

from openai import OpenAI

from config import Config
from utils.helpers import truncate_text


@dataclass
class AnalysisResult:
    """
    分析结果数据类
    """
    summary: str        # 视频摘要
    mindmap: str        # 思维导图 Markdown 列表
    raw_response: str   # LLM 原始响应
    notes: str = ""     # 完整 Markdown 笔记


class LLMProcessor:
    """
    LLM 智能分析处理器
    支持 OpenAI 兼容接口（DeepSeek、OpenAI 等）
    """
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一位专业的视频内容分析专家。你的任务是分析视频文本内容，生成结构化的摘要和思维导图。

请严格按照以下格式输出，不要添加任何额外的解释或标记：

## 摘要
[在这里输出 3-5 个核心要点，每个要点用数字编号，不要使用粗体格式]

## 思维导图
[在这里输出 Markdown 无序列表格式的思维导图数据]

### 思维导图格式要求：
1. 必须使用 Markdown 无序列表格式（使用 - 符号）
2. 使用缩进表示层级关系（每级缩进 2 个空格）
3. 第一级是视频主题
4. 第二级是主要章节/话题
5. 第三级及以下是具体内容点
6. 不要使用代码块包裹，直接输出列表
7. 确保缩进正确，这对于思维导图渲染至关重要

### 示例输出格式：
## 摘要
1. 第一个核心要点
2. 第二个核心要点
3. 第三个核心要点

## 思维导图
- 视频主题
  - 第一部分
    - 要点1
    - 要点2
  - 第二部分
    - 要点1
    - 要点2
      - 子要点
"""

    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        初始化 LLM 处理器
        
        Args:
            api_key: API 密钥，默认从配置读取
            base_url: API 基础 URL，默认从配置读取
            model: 模型名称，默认从配置读取
        """
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_API_BASE
        self.model = model or Config.LLM_MODEL
        
        if not self.api_key:
            raise ValueError("未配置 LLM API Key，请在 .env 文件中设置 LLM_API_KEY")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def analyze(self, text: str, video_title: str = "") -> AnalysisResult:
        """
        分析视频文本内容，生成摘要和思维导图
        
        Args:
            text: 视频文本内容（字幕或转录文本）
            video_title: 视频标题，用于上下文
            
        Returns:
            AnalysisResult: 包含摘要和思维导图的分析结果
            
        Raises:
            RuntimeError: API 调用失败
        """
        # 截断过长文本
        truncated_text = truncate_text(text, Config.MAX_INPUT_TOKENS)
        
        # 构建用户消息
        user_message = self._build_user_prompt(truncated_text, video_title)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=8000,  # 增加到 8000 以支持更长的视频内容分析
                timeout=None  # 禁用超时限制
            )
            
            raw_response = response.choices[0].message.content
            summary, mindmap = self._parse_response(raw_response)
            
            return AnalysisResult(
                summary=summary,
                mindmap=mindmap,
                raw_response=raw_response,
                notes=""  # 笔记将在 VideoProcessor 中生成
            )
            
        except Exception as e:
            raise RuntimeError(f"LLM API 调用失败: {e}")
    
    def _build_user_prompt(self, text: str, title: str) -> str:
        """
        构建用户提示词
        
        Args:
            text: 视频文本
            title: 视频标题
            
        Returns:
            str: 格式化的用户提示词
        """
        prompt = f"""请分析以下视频内容：

**视频标题**: {title if title else "未知"}

**视频文本内容**:
{text}

请根据上述内容生成：
1. 3-5 个核心要点的摘要
2. Markdown 无序列表格式的思维导图（用于 Markmap 渲染）

注意：思维导图必须是标准的 Markdown 无序列表格式，不要使用代码块包裹。"""
        
        return prompt
    
    def _parse_response(self, response: str) -> Tuple[str, str]:
        """
        解析 LLM 响应，提取摘要和思维导图
        
        Args:
            response: LLM 原始响应
            
        Returns:
            Tuple[str, str]: (摘要, 思维导图)
        """
        summary = ""
        mindmap = ""
        
        # 分割响应
        lines = response.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            stripped = line.strip()
            
            # 检测章节标题
            if stripped.startswith('## 摘要') or stripped.startswith('##摘要'):
                if current_section == 'mindmap':
                    mindmap = '\n'.join(section_content)
                current_section = 'summary'
                section_content = []
            elif stripped.startswith('## 思维导图') or stripped.startswith('##思维导图'):
                if current_section == 'summary':
                    summary = '\n'.join(section_content)
                current_section = 'mindmap'
                section_content = []
            elif current_section:
                # 跳过空行和代码块标记
                if stripped and not stripped.startswith('```'):
                    section_content.append(line)
        
        # 处理最后一个章节
        if current_section == 'summary':
            summary = '\n'.join(section_content)
        elif current_section == 'mindmap':
            mindmap = '\n'.join(section_content)
        
        # 清理思维导图格式
        mindmap = self._clean_mindmap(mindmap)
        
        # 调试输出
        print(f"[DEBUG] 原始响应长度: {len(response)}")
        print(f"[DEBUG] 摘要长度: {len(summary)}")
        print(f"[DEBUG] 思维导图长度: {len(mindmap)}")
        print(f"[DEBUG] 思维导图内容预览: {mindmap[:200] if mindmap else '(空)'}")
        
        return summary.strip(), mindmap.strip()
    
    def _clean_mindmap(self, mindmap: str) -> str:
        """
        清理思维导图格式
        
        Args:
            mindmap: 原始思维导图文本
            
        Returns:
            str: 清理后的思维导图
        """
        if not mindmap:
            return ""
            
        lines = []
        for line in mindmap.split('\n'):
            stripped = line.strip()
            # 移除代码块标记
            if stripped.startswith('```'):
                continue
            # 保留有效的列表行（包括空行用于格式化）
            if stripped.startswith('-') or stripped == '':
                lines.append(line)
            # 如果行不是以 - 开头但包含内容，可能是格式问题，尝试修复
            elif stripped and not stripped.startswith('#'):
                # 如果看起来像是列表项但缺少 -，添加它
                if len(stripped) > 0:
                    # 计算原始缩进
                    indent = len(line) - len(line.lstrip())
                    lines.append(' ' * indent + '- ' + stripped)
        
        result = '\n'.join(lines).strip()
        
        # 如果结果为空，返回一个默认的思维导图结构
        if not result:
            print("[DEBUG] 思维导图为空，返回默认结构")
            return "- 视频内容\n  - 暂无详细结构"
        
        return result
