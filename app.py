"""
标题: VidInsight App
说明: B站视频智能笔记助手 - Streamlit 前端应用
时间: 2026-01-14
@author: zhoujunyu
"""

import streamlit as st
from streamlit_markmap import markmap
from datetime import datetime
import json

from config import Config
from core import VideoProcessor, ProcessingStatus
from utils.helpers import format_duration, generate_mindmap_html
from utils.history import HistoryManager


from utils.user_manager import user_manager

from streamlit_cookies_manager import CookieManager

# 页面配置
st.set_page_config(
    page_title="VidInsight - B站视频智能笔记助手",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化 Cookie 管理器
cookies = CookieManager()
if not cookies.ready():
    st.stop()

# 初始化 session state
if 'username' not in st.session_state:
    st.session_state.username = None
    # 尝试从 Cookie 恢复登录
    token = cookies.get('vidinsight_token')
    if token:
        username = user_manager.validate_session(token)
        if username:
            st.session_state.username = username
            st.session_state.history_manager = HistoryManager(username)
            st.session_state.history_list = st.session_state.history_manager.get_all_records()

if 'history_manager' not in st.session_state:
    st.session_state.history_manager = None
if 'current_result' not in st.session_state:
    st.session_state.current_result = None
if 'history_list' not in st.session_state:
    st.session_state.history_list = []

# 自定义样式
st.markdown("""
<style>
    /* 主题色调 */
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
    }
    
    /* 标题样式 */
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* 摘要卡片 */
    .summary-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    /* 登录框样式 */
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 2rem;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .welcome-text {
        text-align: center;
        color: #333;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


def render_login_page():
    """
    渲染登录页面
    """
    st.markdown('<h1 class="main-title">🎬 VidInsight</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">B站视频智能笔记助手 - 自动生成摘要与思维导图</p>', unsafe_allow_html=True)
    
    # 居中的登录区域
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])
        
        with tab1:
            st.markdown("### 用户登录")
            login_user = st.text_input("用户名", key="login_user")
            login_pwd = st.text_input("密码", type="password", key="login_pwd")
            
            if st.button("登录", type="primary", use_container_width=True):
                success, msg = user_manager.login(login_user, login_pwd)
                if success:
                    # 创建会话并设置 Cookie
                    token = user_manager.create_session(login_user)
                    cookies['vidinsight_token'] = token
                    cookies.save()
                    
                    st.session_state.username = login_user
                    st.session_state.history_manager = HistoryManager(login_user)
                    st.session_state.history_list = st.session_state.history_manager.get_all_records()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        
        with tab2:
            st.markdown("### 新用户注册")
            reg_user = st.text_input("用户名", key="reg_user", help="2-20个字符")
            reg_pwd = st.text_input("密码", type="password", key="reg_pwd", help="至少4个字符")
            reg_pwd2 = st.text_input("确认密码", type="password", key="reg_pwd2")
            
            if st.button("注册并登录", type="primary", use_container_width=True):
                if reg_pwd != reg_pwd2:
                    st.error("两次输入的密码不一致")
                else:
                    success, msg = user_manager.register(reg_user, reg_pwd)
                    if success:
                        # 创建会话并设置 Cookie
                        token = user_manager.create_session(reg_user)
                        cookies['vidinsight_token'] = token
                        cookies.save()
                        
                        st.success(msg)
                        # 自动登录
                        st.session_state.username = reg_user
                        st.session_state.history_manager = HistoryManager(reg_user)
                        st.session_state.history_list = st.session_state.history_manager.get_all_records()
                        st.rerun()
                    else:
                        st.error(msg)


def check_config() -> bool:
    """
    检查配置是否有效
    
    Returns:
        bool: 配置是否有效
    """
    if not Config.validate():
        st.error("⚠️ 请先配置 LLM API Key！")
        st.info("""
        **配置步骤：**
        1. 在 `.env` 文件中填入你的 API Key:
           ```
           LLM_API_KEY=your_api_key_here
           ```
        2. 重新启动应用
        """)
        return False
    return True


def render_header():
    """
    渲染页面头部
    """
    st.markdown('<h1 class="main-title">🎬 VidInsight</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">B站视频智能笔记助手 - 自动生成摘要与思维导图</p>', unsafe_allow_html=True)


def render_sidebar():
    """
    渲染侧边栏 - 用户信息和历史记录
    """
    # 侧边栏样式
    st.markdown("""
    <style>
        .sidebar-profile {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }
        .sidebar-profile h3 {
            margin: 0;
            color: #333;
        }
        .sidebar-section-header {
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #555;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        # 1. 用户信息 (紧凑布局)
        col_user, col_logout = st.columns([3, 1])
        with col_user:
            st.markdown(f"### 👤 {st.session_state.username}")
        with col_logout:
            if st.button("🚪", help="退出登录", use_container_width=True):
                # 撤销会话并清除 Cookie
                user_manager.revoke_session(st.session_state.username)
                if 'vidinsight_token' in cookies:
                    del cookies['vidinsight_token']
                    cookies.save()
                
                st.session_state.username = None
                st.session_state.history_manager = None
                st.session_state.current_result = None
                st.session_state.history_list = []
                st.rerun()
        
        # 账户设置 (折叠)
        with st.expander("🔑 修改密码"):
            old_pwd = st.text_input("原密码", type="password", key="old_pwd")
            new_pwd = st.text_input("新密码", type="password", key="new_pwd", help="至少4个字符")
            if st.button("确认修改", use_container_width=True):
                success, msg = user_manager.change_password(st.session_state.username, old_pwd, new_pwd)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

        # 2. 数据管理
        st.markdown('<div class="sidebar-section-header">数据管理</div>', unsafe_allow_html=True)
        
        # 刷新历史记录
        history_manager = st.session_state.history_manager
        records = history_manager.get_all_records()
        st.session_state.history_list = records
        
        col_export, col_import = st.columns(2)
        with col_export:
            if records:
                export_data = json.dumps(records, ensure_ascii=False, indent=2)
                st.download_button(
                    "📤 导出",
                    export_data,
                    file_name=f"vidinsight_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="export_history",
                    help="导出所有历史记录"
                )
            else:
                st.button("📤 导出", disabled=True, use_container_width=True)
        
        with col_import:
            if st.button("📥 导入", use_container_width=True):
                st.session_state.show_import_uploader = not st.session_state.get('show_import_uploader', False)
        
        # 导入文件上传器
        if st.session_state.get('show_import_uploader', False):
            with st.container(border=True):
                st.caption("上传备份文件 (JSON)")
                uploaded_file = st.file_uploader(
                    "选择文件",
                    type=['json'],
                    key="import_history_file",
                    label_visibility="collapsed"
                )
                
                if uploaded_file is not None:
                    if st.button("确认导入", type="primary", use_container_width=True):
                        try:
                            import_data = json.load(uploaded_file)
                            if isinstance(import_data, list):
                                new_count = history_manager.import_records(import_data)
                                if new_count > 0:
                                    st.success(f"已导入 {new_count} 条")
                                    st.session_state.history_list = history_manager.get_all_records()
                                    st.session_state.show_import_uploader = False
                                    st.rerun()
                                else:
                                    st.info("无新记录")
                            else:
                                st.error("格式错误")
                        except Exception as e:
                            st.error(f"失败: {e}")

        # 3. 历史记录列表
        st.markdown('<div class="sidebar-section-header">历史记录</div>', unsafe_allow_html=True)
        
        if not records:
            st.info("暂无记录")
        else:
            # 搜索框
            search_term = st.text_input("🔍 搜索", placeholder="输入标题关键词...", label_visibility="collapsed")
            
            filtered_records = records
            if search_term:
                filtered_records = [r for r in records if search_term.lower() in r.get('title', '').lower()]
            
            st.caption(f"共 {len(filtered_records)} 条记录")
            
            # 列表显示
            for i, record in enumerate(filtered_records):
                video_id = record.get('video_id', '')
                title = record.get('title', '未知标题')
                
                # 使用两列布局：标题（点击加载） + 删除按钮
                col_title, col_del = st.columns([5, 1])
                
                with col_title:
                    display_title = title[:16] + "..." if len(title) > 16 else title
                    # 高亮当前选中的记录
                    is_active = st.session_state.current_result and st.session_state.current_result.get('video_id') == video_id
                    
                    # 选中状态：灰色按钮(secondary) + 特殊图标
                    # 未选中：灰色按钮(secondary) + 无图标
                    if is_active:
                        btn_type = "secondary"
                        label = f"👉 {display_title}"
                    elif video_id in st.session_state.get('processing_tasks', {}):
                        btn_type = "secondary"
                        label = f"⏳ {display_title}"
                    else:
                        btn_type = "secondary"
                        label = display_title
                    
                    if st.button(label, key=f"hist_btn_{video_id}", type=btn_type, use_container_width=True, help=title):
                        st.session_state.current_result = record
                        # 注入 JS 滚动到顶部
                        st.components.v1.html(
                            """
                            <script>
                                window.parent.document.querySelector('section.main').scrollTo(0, 0);
                            </script>
                            """,
                            height=0,
                            width=0
                        )
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️", key=f"del_btn_{video_id}", help="删除此记录"):
                        history_manager.delete_record(video_id)
                        # 如果删除的是当前显示的记录，清除显示
                        if st.session_state.current_result and st.session_state.current_result.get('video_id') == video_id:
                            st.session_state.current_result = None
                        st.rerun()


def render_input_section():
    """
    渲染输入区域
    
    Returns:
        tuple: (url, submit_clicked)
    """
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col2:
        url = st.text_input(
            "🔗 输入B站视频链接",
            placeholder="https://www.bilibili.com/video/BVxxxxxxx",
            help="支持 BV 号或完整链接"
        )
        
        submit = st.button(
            "🚀 开始分析",
            type="primary",
            use_container_width=True
        )
    
    return url, submit


def render_progress(status: ProcessingStatus, message: str, progress: int = 0):
    """
    渲染处理进度
    
    Args:
        status: 处理状态
        message: 状态消息
        progress: 进度百分比 (0-100)
    """
    status_icons = {
        ProcessingStatus.DOWNLOADING: "📥",
        ProcessingStatus.TRANSCRIBING: "🎤",
        ProcessingStatus.ANALYZING: "🧠",
        ProcessingStatus.COMPLETED: "✅",
        ProcessingStatus.ERROR: "❌"
    }
    
    icon = status_icons.get(status, "⏳")
    st.info(f"{icon} {message}")
    
    # 显示进度条
    if status != ProcessingStatus.ERROR and status != ProcessingStatus.IDLE:
        st.progress(progress / 100)


def render_result(result):
    """
    渲染处理结果
    
    Args:
        result: 结果字典
    """
    video_id = result.get('video_id', '')
    title = result.get('title', '')
    duration = result.get('duration', 0)
    has_subtitle = result.get('has_subtitle', False)
    summary = result.get('summary', '')
    mindmap = result.get('mindmap', '')
    mindmap_html = result.get('mindmap_html', '')
    notes = result.get('notes', '')
    transcript = result.get('transcript', '')
    
    # 视频信息
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📺 视频标题", title[:30] + "..." if len(title) > 30 else title)
    with col2:
        st.metric("⏱️ 时长", format_duration(duration))
    with col3:
        st.metric("📝 字幕来源", "原生字幕" if has_subtitle else "AI 转录")
    
    st.markdown("---")
    
    # 摘要部分
    st.markdown("### 📋 内容摘要")
    st.markdown(f"""
    <div class="summary-card">
    {summary}
    </div>
    """, unsafe_allow_html=True)
    
    # 思维导图部分
    st.markdown("### 🧠 思维导图")
    st.caption("🖱️ 滚轮缩放 | 拖拽移动 | 点击节点展开/折叠")
    
    if mindmap:
        with st.container(border=True):
            try:
                markmap(mindmap, height=500)
            except Exception as e:
                st.warning(f"思维导图渲染失败，显示原始格式: {e}")
                st.code(mindmap, language="markdown")
    else:
        st.warning("未能生成思维导图")
    
    # 原文折叠区
    with st.expander("📄 查看完整文本"):
        st.text_area(
            "视频文本内容",
            transcript,
            height=300,
            disabled=True
        )
    
    # 下载区
    st.markdown("---")
    st.markdown("### 📥 下载")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.download_button(
            "📋 摘要",
            summary,
            file_name=f"{video_id}_summary.txt",
            mime="text/plain",
            key=f"dl_summary_{video_id}"
        )
    
    with col2:
        st.download_button(
            "🧠 思维导图",
            mindmap_html,
            file_name=f"{video_id}_mindmap.html",
            mime="text/html",
            help="HTML 文件，在浏览器中打开可查看交互式思维导图",
            key=f"dl_mindmap_{video_id}"
        )
    
    with col3:
        st.download_button(
            "📝 完整笔记",
            notes,
            file_name=f"{video_id}_notes.md",
            mime="text/markdown",
            key=f"dl_notes_{video_id}"
        )
    
    with col4:
        st.download_button(
            "📄 原文",
            transcript,
            file_name=f"{video_id}_transcript.txt",
            mime="text/plain",
            key=f"dl_transcript_{video_id}"
        )


import threading
import time
from utils.helpers import extract_video_id

# 全局任务追踪 (video_id -> {status, message, progress})
if 'processing_tasks' not in st.session_state:
    st.session_state.processing_tasks = {}

def background_process(url: str, video_id: str, username: str, task_tracker: dict):
    """
    后台处理任务
    """
    try:
        processor = VideoProcessor()
        
        def on_status_change(status: ProcessingStatus, message: str, progress: int = 0):
            # 更新任务状态
            task_tracker[video_id] = {
                'status': status,
                'message': message,
                'progress': progress
            }
            
        processor.set_status_callback(on_status_change)
        
        # 执行处理
        result = processor.process(url)
        
        # 保存完整结果到历史记录
        history_manager = HistoryManager(username)
        
        record = {
            'video_id': result.video_id,
            'title': result.title,
            'duration': result.duration,
            'has_subtitle': result.has_subtitle,
            'transcript': result.transcript,
            'summary': result.summary,
            'mindmap': result.mindmap,
            'mindmap_html': result.mindmap_html,
            'notes': result.notes,
            'status': 'completed',  # 标记为完成
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 更新现有记录
        history_manager.update_record(video_id, record)
        
        # 标记任务完成
        if video_id in task_tracker:
            del task_tracker[video_id]
            
    except Exception as e:
        # 记录错误
        if video_id in task_tracker:
            task_tracker[video_id] = {
                'status': ProcessingStatus.ERROR,
                'message': f"失败: {str(e)}",
                'progress': 0
            }

def main():
    """
    主函数 - 应用入口
    """
    # 检查是否已登录
    if not st.session_state.username:
        render_login_page()
        return
    
    render_header()
    
    # 检查配置
    if not check_config():
        return
    
    # 渲染侧边栏
    render_sidebar()
    
    # 输入区
    url, submit = render_input_section()
    
    # 处理逻辑
    if submit and url:
        video_id = extract_video_id(url)
        if not video_id:
            st.error("无效的 B站视频链接")
            return
            
        # 1. 创建占位历史记录
        history_manager = st.session_state.history_manager
        placeholder_record = {
            'video_id': video_id,
            'title': '正在分析中...',
            'status': 'processing',
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        history_manager.add_record(placeholder_record)
        
        # 2. 初始化任务状态
        st.session_state.processing_tasks[video_id] = {
            'status': ProcessingStatus.DOWNLOADING,
            'message': '准备开始...',
            'progress': 0
        }
        
        # 3. 启动后台线程
        thread = threading.Thread(
            target=background_process,
            args=(url, video_id, st.session_state.username, st.session_state.processing_tasks)
        )
        thread.start()
        
        # 4. 设置当前查看的记录并刷新
        st.session_state.current_result = placeholder_record
        st.session_state.history_list = history_manager.get_all_records()
        st.rerun()
    
    elif submit and not url:
        st.warning("⚠️ 请输入视频链接")

    # 渲染当前结果或进度
    if st.session_state.current_result:
        current_record = st.session_state.current_result
        video_id = current_record.get('video_id')
        
        # 检查是否正在处理中
        if video_id in st.session_state.processing_tasks:
            task_info = st.session_state.processing_tasks[video_id]
            
            st.markdown("---")
            st.info(f"🔄 正在后台分析视频: {video_id}")
            
            status = task_info.get('status', ProcessingStatus.IDLE)
            message = task_info.get('message', '')
            progress = task_info.get('progress', 0)
            
            render_progress(status, message, progress)
            
            # 自动刷新以显示进度
            time.sleep(1)
            st.rerun()
            
        else:
            # 如果任务不在处理列表中，但状态仍为 processing，说明可能刚完成或出错
            # 尝试重新加载记录
            history_manager = st.session_state.history_manager
            updated_record = history_manager.get_record_by_video_id(video_id)
            
            if updated_record and updated_record.get('status') == 'completed':
                # 更新当前显示
                st.session_state.current_result = updated_record
                render_result(updated_record)
            elif updated_record and updated_record.get('status') == 'processing':
                 # 异常情况：任务消失但记录仍为 processing (可能是重启导致)
                 st.warning("⚠️ 任务似乎已中断。请重新开始分析。")
            else:
                # 正常显示结果
                render_result(current_record)


if __name__ == "__main__":
    main()
