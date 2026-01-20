"""
标题: helpers
说明: 通用工具函数
时间: 2026-01-14
@author: zhoujunyu
"""

import os
import re
from pathlib import Path


def ensure_dir(path: str) -> Path:
    """
    确保目录存在，不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        Path: 目录 Path 对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的安全文件名
    """
    # 移除 Windows 非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(illegal_chars, '_', filename)
    # 限制长度
    return sanitized[:200] if len(sanitized) > 200 else sanitized


def extract_video_info(url: str) -> dict:
    """
    从B站链接中提取视频完整信息
    
    Args:
        url: B站视频链接
        
    Returns:
        dict: {
            'video_id': 包含分P的完整ID，如 'BV1VE411q7dX_p11'
            'bv_id': 纯BV号，用于分组，如 'BV1VE411q7dX'
            'part': 分P号（整数），无则为 None
        }
    """
    import urllib.parse
    
    result = {
        'video_id': None,
        'bv_id': None,
        'part': None
    }
    
    # 匹配 BV 号
    bv_pattern = r'(BV[a-zA-Z0-9]+)'
    match = re.search(bv_pattern, url)
    if match:
        result['bv_id'] = match.group(1)
    else:
        # 匹配 AV 号
        av_pattern = r'av(\d+)'
        match = re.search(av_pattern, url, re.IGNORECASE)
        if match:
            result['bv_id'] = f"av{match.group(1)}"
    
    if not result['bv_id']:
        return result
    
    # 提取分P号
    try:
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query)
        if 'p' in query_params:
            part = int(query_params['p'][0])
            result['part'] = part
    except (ValueError, KeyError, IndexError):
        pass
    
    # 生成完整 video_id
    if result['part'] is not None:
        result['video_id'] = f"{result['bv_id']}_p{result['part']}"
    else:
        result['video_id'] = result['bv_id']
    
    return result


def extract_video_id(url: str) -> str:
    """
    从B站链接中提取视频 ID（包含分P信息）
    
    Args:
        url: B站视频链接
        
    Returns:
        str: 视频ID，如 'BV1VE411q7dX' 或 'BV1VE411q7dX_p11'
    """
    info = extract_video_info(url)
    return info.get('video_id')


def truncate_text(text: str, max_tokens: int = 8000) -> str:
    """
    截断文本以避免超出 Token 限制
    简单按字符估算，中文约 1.5 token/字
    
    Args:
        text: 原始文本
        max_tokens: 最大 Token 数
        
    Returns:
        str: 截断后的文本
    """
    # 粗略估算：中英混合约 2 字符/token
    max_chars = max_tokens * 2
    
    if len(text) <= max_chars:
        return text
    
    # 截断并添加提示
    truncated = text[:max_chars]
    return truncated + "\n\n[内容已截断...]"


def format_duration(seconds: float) -> str:
    """
    格式化时长显示
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化的时长字符串，如 "1:23:45"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def markdown_to_mermaid_mindmap(markdown_list: str) -> str:
    """
    将 Markdown 无序列表转换为 Mermaid mindmap 格式
    
    Args:
        markdown_list: Markdown 格式的无序列表
        
    Returns:
        str: Mermaid mindmap 格式的代码
    """
    lines = markdown_list.strip().split('\n')
    mermaid_lines = ['mindmap']
    
    for line in lines:
        if not line.strip():
            continue
        
        # 计算缩进级别（每 2 个空格为一级）
        stripped = line.lstrip()
        if not stripped.startswith('-'):
            continue
            
        indent = len(line) - len(stripped)
        level = indent // 2
        
        # 提取文本内容
        text = stripped.lstrip('- ').strip()
        if not text:
            continue
        
        # 清理文本中的特殊字符，避免 Mermaid 解析错误
        text = text.replace('"', "'").replace('(', '（').replace(')', '）')
        text = text.replace('[', '【').replace(']', '】')
        
        # Mermaid mindmap 使用缩进表示层级
        mermaid_indent = '  ' * (level + 1)
        mermaid_lines.append(f'{mermaid_indent}{text}')
    
    return '\n'.join(mermaid_lines)


def generate_mindmap_html(markdown_list: str, title: str = "思维导图") -> str:
    """
    生成可在浏览器中打开的思维导图 HTML 文件
    
    使用 markmap 库渲染，效果与 Streamlit 中一致
    
    Args:
        markdown_list: Markdown 格式的无序列表
        title: 页面标题
        
    Returns:
        str: 完整的 HTML 文档内容
    """
    # 转义 Markdown 内容中的特殊字符
    escaped_markdown = markdown_list.replace('`', '\\`').replace('${', '\\${')
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 思维导图</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 1.8rem;
            margin-bottom: 8px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .header p {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}
        .mindmap-container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        #markmap {{
            width: 100%;
            height: calc(100vh - 140px);
            min-height: 500px;
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 20px;
            opacity: 0.8;
            font-size: 0.85rem;
        }}
        .tip {{
            background: rgba(255,255,255,0.15);
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 {title}</h1>
            <p>由 VidInsight 自动生成</p>
        </div>
        <div class="mindmap-container">
            <svg id="markmap"></svg>
        </div>
        <div class="footer">
            <div class="tip">💡 提示：鼠标滚轮缩放，拖拽移动，点击节点展开/折叠</div>
        </div>
    </div>
    
    <!-- Markmap 库 -->
    <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
    <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.15.4"></script>
    <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.15.4"></script>
    
    <script>
        // Markdown 内容
        const markdown = `{escaped_markdown}`;
        
        // 解析并渲染
        const {{ Transformer }} = window.markmap;
        const {{ Markmap }} = window.markmap;
        
        const transformer = new Transformer();
        const {{ root }} = transformer.transform(markdown);
        
        const svg = document.getElementById('markmap');
        const mm = Markmap.create(svg, {{
            colorFreezeLevel: 2,
            initialExpandLevel: 3,
            maxWidth: 300,
            paddingX: 20
        }}, root);
        
        // 自适应窗口大小
        window.addEventListener('resize', () => {{
            mm.fit();
        }});
    </script>
</body>
</html>"""
    
    return html_content


