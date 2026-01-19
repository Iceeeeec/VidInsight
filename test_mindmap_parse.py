"""
测试脚本：诊断思维导图生成问题
"""

# 模拟 LLM 响应的几种可能格式
test_responses = [
    # 格式1：标准格式
    """## 摘要
1. 第一个要点
2. 第二个要点
3. 第三个要点

## 思维导图
- 主题
  - 子主题1
    - 详细点1
    - 详细点2
  - 子主题2
    - 详细点3
""",
    
    # 格式2：带代码块
    """## 摘要
1. 第一个要点
2. 第二个要点

## 思维导图
```
- 主题
  - 子主题1
  - 子主题2
```
""",
    
    # 格式3：没有空格
    """##摘要
1. 第一个要点

##思维导图
- 主题
  - 子主题1
""",
]

def test_parse(response):
    """测试解析逻辑"""
    summary = ""
    mindmap = ""
    
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
    
    return summary.strip(), mindmap.strip()

# 测试所有格式
for i, response in enumerate(test_responses, 1):
    print(f"\n{'='*50}")
    print(f"测试格式 {i}:")
    print(f"{'='*50}")
    summary, mindmap = test_parse(response)
    print(f"摘要长度: {len(summary)}")
    print(f"思维导图长度: {len(mindmap)}")
    print(f"\n摘要内容:\n{summary}")
    print(f"\n思维导图内容:\n{mindmap}")
    print(f"\n思维导图为空: {not mindmap}")
