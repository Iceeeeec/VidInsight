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
from utils.api_key_manager import api_key_manager

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
                # 清空密钥缓存，下次登录需重新输入
                st.session_state.user_api_key = ''
                st.session_state.api_key_valid = False
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

        # 2. 转录模式切换
        st.markdown('<div class="sidebar-section-header">转录设置</div>', unsafe_allow_html=True)
        
        # 初始化转录模式 session state
        if 'transcribe_mode' not in st.session_state:
            st.session_state.transcribe_mode = 'local'
        
        transcribe_mode = st.radio(
            "🎤 语音转录模式",
            options=['local', 'remote'],
            format_func=lambda x: '🖥️ 服务器 自建 Whisper（慢）' if x == 'local' else '☁️ 远程 API（快）',
            key='transcribe_mode_radio',
            index=0 if st.session_state.transcribe_mode == 'local' else 1,
            horizontal=True,
            help='本地模式使用自建 Whisper 服务，远程模式使用 OpenAI 兼容 API'
        )
        
        # 更新 session state
        if transcribe_mode != st.session_state.transcribe_mode:
            st.session_state.transcribe_mode = transcribe_mode
        
        # 远程 API 密钥输入（当选择远程模式时显示）
        if transcribe_mode == 'remote':
            # 初始化密钥 session state
            if 'user_api_key' not in st.session_state:
                st.session_state.user_api_key = ''
            if 'api_key_valid' not in st.session_state:
                st.session_state.api_key_valid = False
            
            st.markdown("---")
            st.caption("🔑 使用远程 API 需要输入密钥")
            
            col_key, col_btn = st.columns([3, 1])
            with col_key:
                user_key = st.text_input(
                    "API 密钥",
                    value=st.session_state.user_api_key,
                    placeholder="VID-XXXX-XXXX-XXXX",
                    type="password",
                    label_visibility="collapsed",
                    key="user_api_key_input"
                )
            with col_btn:
                if st.button("验证", use_container_width=True, key="verify_key_btn"):
                    result = api_key_manager.validate_key(user_key, st.session_state.username)
                    if result['valid']:
                        st.session_state.user_api_key = user_key
                        st.session_state.api_key_valid = True
                        st.toast("✅ 密钥验证成功！", icon="✅")
                    else:
                        st.session_state.api_key_valid = False
                        st.toast(f"❌ {result['message']}", icon="❌")
            
            # 显示密钥状态
            if st.session_state.api_key_valid and st.session_state.user_api_key:
                result = api_key_manager.validate_key(st.session_state.user_api_key, st.session_state.username)
                if result['valid'] and result['key_info']:
                    expires_at = result['key_info'].get('expires_at', '永久')
                    st.success(f"✅ 密钥有效，到期: {expires_at if expires_at else '永久'}")
                else:
                    st.session_state.api_key_valid = False
                    st.warning(f"⚠️ {result['message']}")
            elif user_key and not st.session_state.api_key_valid:
                st.warning("⚠️ 请点击验证按钮验证密钥")
        
        # 管理员密钥管理面板
        if user_manager.is_admin(st.session_state.username):
            st.markdown("---")
            with st.expander("🔑 密钥管理 (管理员)", expanded=False):
                # 创建新密钥
                st.markdown("**➕ 创建新密钥**")
                col_days, col_btn = st.columns([2, 1])
                with col_days:
                    expires_days = st.selectbox(
                        "有效期",
                        options=[7, 30, 90, 365, None],
                        format_func=lambda x: f"{x}天" if x else "永久",
                        index=1,
                        label_visibility="collapsed",
                        key="new_key_expires"
                    )
                with col_btn:
                    create_clicked = st.button("🆕 创建", use_container_width=True, key="create_key_btn")
                
                if create_clicked:
                    # 自动生成名称（使用时间戳）
                    auto_name = datetime.now().strftime("%m%d_%H%M")
                    new_key_info = api_key_manager.create_key(auto_name, expires_days)
                    st.session_state.last_created_key = new_key_info['key']
                    st.toast("✅ 密钥已创建！", icon="🔑")
                    st.rerun()
                
                # 显示最近创建的密钥（带复制功能）
                if 'last_created_key' in st.session_state and st.session_state.last_created_key:
                    st.success("✅ 新密钥（点击复制）:")
                    st.code(st.session_state.last_created_key, language=None)
                    if st.button("清除显示", key="clear_new_key"):
                        st.session_state.last_created_key = None
                        st.rerun()
                
                # 密钥列表
                st.markdown("---")
                st.markdown("**📋 密钥列表**")
                all_keys = api_key_manager.get_all_keys()
                
                if not all_keys:
                    st.info("暂无密钥")
                else:
                    for key_info in all_keys:
                        key = key_info.get('key', '')
                        name = key_info.get('name', '')
                        enabled = key_info.get('enabled', True)
                        is_expired = key_info.get('is_expired', False)
                        expires_at = key_info.get('expires_at')
                        used_by = key_info.get('used_by', [])
                        usage_count = len(used_by)
                        
                        # 状态图标
                        if is_expired:
                            status_icon = "⏰"
                        elif not enabled:
                            status_icon = "🔒"
                        elif usage_count >= 2:
                            status_icon = "🈵"  # 已满
                        else:
                            status_icon = "✅"
                        
                        # 容器包裹每个密钥项
                        with st.container(border=True):
                            # 第一行：状态和过期时间
                            users_str = ", ".join(used_by) if used_by else "暂无用户"
                            st.caption(f"{status_icon} 创建于 {name} | 用户: {users_str} ({usage_count}/2) | 到期: {expires_at if expires_at else '永久'}")
                            
                            # 第二行：完整密钥（可复制）
                            st.code(key, language=None)
                            
                            # 第三行：操作按钮
                            col_toggle, col_del = st.columns(2)
                            with col_toggle:
                                btn_label = "🔓 启用" if not enabled else "🔒 禁用"
                                if st.button(btn_label, key=f"toggle_{key}", use_container_width=True):
                                    api_key_manager.toggle_key(key)
                                    st.rerun()
                            with col_del:
                                if st.button("🗑️ 删除", key=f"del_{key}", use_container_width=True):
                                    api_key_manager.delete_key(key)
                                    st.rerun()
        
        # 3. 数据管理
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
        
        # 获取分组后的历史记录
        grouped_history = history_manager.get_grouped_history()
        folders = grouped_history.get('folders', [])
        ungrouped = grouped_history.get('ungrouped', [])
        
        total_count = len(records)
        
        if total_count == 0:
            st.info("暂无记录")
        else:
            # 搜索框
            search_term = st.text_input("🔍 搜索", placeholder="输入标题关键词...", label_visibility="collapsed")
            
            st.caption(f"共 {total_count} 条记录，{len(folders)} 个分组")
            
            # 辅助函数：渲染单条记录
            def render_record_item(record, indent=False, show_part=False):
                video_id = record.get('video_id', '')
                title = record.get('title', '未知标题')
                part = record.get('part')
                
                # 搜索过滤
                if search_term and search_term.lower() not in title.lower():
                    return False
                
                # 使用两列布局：标题（点击加载） + 删除按钮
                col_title, col_del = st.columns([5, 1])
                
                with col_title:
                    # 显示分P信息
                    # show_part=True 时强制显示分P号（在分组内）
                    if show_part or part:
                        part_num = part if part else 1
                        display_title = f"P{part_num}: {title[:10]}..." if len(title) > 10 else f"P{part_num}: {title}"
                    else:
                        display_title = title[:16] + "..." if len(title) > 16 else title
                    
                    # 高亮当前选中的记录
                    is_active = st.session_state.current_result and st.session_state.current_result.get('video_id') == video_id
                    
                    if is_active:
                        btn_type = "primary"  # 选中状态用高亮色
                        label = f"👉 {display_title}"
                    elif video_id in st.session_state.get('processing_tasks', {}):
                        btn_type = "secondary"
                        label = f"⏳ {display_title}"
                    else:
                        btn_type = "secondary"
                        label = f"{'   ' if indent else ''}{display_title}"
                    
                    if st.button(label, key=f"hist_btn_{video_id}", type=btn_type, use_container_width=True, help=title):
                        st.session_state.current_result = record
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
                        if st.session_state.current_result and st.session_state.current_result.get('video_id') == video_id:
                            st.session_state.current_result = None
                        st.rerun()
                
                return True
            
            # 渲染分组（包）
            for folder in folders:
                folder_id = folder.get('id')
                folder_name = folder.get('name', '未命名分组')
                folder_records = folder.get('records', [])
                
                # 过滤搜索结果
                if search_term:
                    folder_records = [r for r in folder_records if search_term.lower() in r.get('title', '').lower()]
                    if not folder_records:
                        continue
                
                # 检查当前选中的记录是否在此分组内
                current_video_id = st.session_state.current_result.get('video_id') if st.session_state.current_result else None
                is_current_in_folder = any(r.get('video_id') == current_video_id for r in folder_records)
                
                # 使用 expander 显示包（当前选中记录所在分组自动展开）
                with st.expander(f"{folder_name} ({len(folder_records)})", expanded=is_current_in_folder):
                    # 包操作按钮：重命名和删除
                    # 检查是否正在编辑此分组名称
                    editing_key = f"editing_folder_{folder_id}"
                    if st.session_state.get(editing_key, False):
                        # 显示重命名输入框
                        new_name = st.text_input(
                            "新名称", 
                            value=folder_name.replace("📁 ", ""),
                            key=f"rename_input_{folder_id}",
                            max_chars=30
                        )
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("✅ 保存", key=f"save_rename_{folder_id}", use_container_width=True):
                                if new_name.strip():
                                    history_manager.rename_folder(folder_id, f"📁 {new_name.strip()}")
                                    st.session_state[editing_key] = False
                                    st.rerun()
                        with col_cancel:
                            if st.button("❌ 取消", key=f"cancel_rename_{folder_id}", use_container_width=True):
                                st.session_state[editing_key] = False
                                st.rerun()
                    else:
                        # 显示操作按钮
                        col_rename, col_del_folder = st.columns([1, 1])
                        with col_rename:
                            if st.button("✏️ 重命名", key=f"rename_folder_{folder_id}", use_container_width=True):
                                st.session_state[editing_key] = True
                                st.rerun()
                        with col_del_folder:
                            if st.button("🗑️ 删除", key=f"del_folder_{folder_id}", use_container_width=True):
                                history_manager.delete_folder(folder_id, delete_records=False)
                                st.rerun()
                    
                    # 渲染包内记录（按P号排序）
                    # 按分P号排序，无分P的放最前面
                    sorted_records = sorted(folder_records, key=lambda r: r.get('part') or 0)
                    for record in sorted_records:
                        render_record_item(record, indent=True, show_part=True)
            
            # 渲染未分组的记录
            if ungrouped:
                # 过滤搜索结果
                filtered_ungrouped = ungrouped
                if search_term:
                    filtered_ungrouped = [r for r in ungrouped if search_term.lower() in r.get('title', '').lower()]
                
                if filtered_ungrouped:
                    if folders:
                        st.markdown("---")
                        st.caption("📄 未分组")
                    
                    for record in filtered_ungrouped:
                        render_record_item(record)


def render_input_section():
    """
    渲染输入区域
    
    Returns:
        tuple: (url, submit_clicked, batch_urls, batch_submit)
    """
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col2:
        # 使用标签页区分单个分析和批量分析
        tab_single, tab_batch = st.tabs(["📺 单个视频", "📚 批量分析"])
        
        with tab_single:
            url = st.text_input(
                "🔗 输入B站视频链接",
                placeholder="https://www.bilibili.com/video/BVxxxxxxx",
                help="支持 BV 号或完整链接",
                key="single_url"
            )
            
            submit = st.button(
                "🚀 开始分析",
                type="primary",
                use_container_width=True,
                key="single_submit"
            )
        
        with tab_batch:
            st.caption("💡 输入BV号和分P数量，自动分析整个合集")
            
            batch_url = st.text_input(
                "🔗 视频链接或BV号",
                placeholder="https://www.bilibili.com/video/BVxxxxxxx 或 BVxxxxxxx",
                help="输入合集中任意一个视频的链接或BV号",
                key="batch_url"
            )
            
            col_start, col_end = st.columns(2)
            with col_start:
                start_p = st.number_input("起始分P", min_value=1, value=1, key="batch_start_p")
            with col_end:
                end_p = st.number_input("结束分P", min_value=1, value=10, key="batch_end_p")
            
            batch_submit = st.button(
                "🚀 批量分析全部",
                type="primary",
                use_container_width=True,
                key="batch_submit"
            )
            
            # 计算批量URL列表
            batch_urls = []
            if batch_submit and batch_url:
                # 提取BV号
                video_info = extract_video_info(batch_url)
                bv_id = video_info.get('bv_id')
                if bv_id and end_p >= start_p:
                    for p in range(int(start_p), int(end_p) + 1):
                        batch_urls.append(f"https://www.bilibili.com/video/{bv_id}?p={p}")
    
    return url, submit, batch_urls, batch_submit


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
    
    # 格式化摘要：将每个要点显示为单独一行
    formatted_summary = summary
    if summary:
        # 尝试将摘要按常见分隔符分割成列表项
        lines = []
        for line in summary.split('\n'):
            line = line.strip()
            if line:
                # 移除已有的列表标记
                if line.startswith(('-', '•', '*', '·')):
                    line = line[1:].strip()
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    line = line[2:].strip()
                lines.append(f"• {line}")
        formatted_summary = '<br>'.join(lines) if lines else summary
    
    st.markdown(f"""
    <div class="summary-card">
    {formatted_summary}
    </div>
    """, unsafe_allow_html=True)
    
    # 思维导图部分
    col_title, col_fullscreen = st.columns([6, 1])
    with col_title:
        st.markdown("### 🧠 思维导图")
    with col_fullscreen:
        # 全屏按钮 - 使用 session state 控制
        if st.button("🔍 全屏", key=f"fullscreen_btn_{video_id}", help="全屏查看思维导图"):
            st.session_state[f'mindmap_fullscreen_{video_id}'] = True
            st.rerun()
    
    st.caption("🖱️ 滚轮缩放 | 拖拽移动 | 点击节点展开/折叠")
    
    # 检查是否处于全屏模式
    is_fullscreen = st.session_state.get(f'mindmap_fullscreen_{video_id}', False)
    
    if is_fullscreen and mindmap:
        # 注入全屏样式 - 让 dialog 覆盖整个屏幕
        st.markdown("""
        <style>
            /* 全屏 dialog 样式 */
            div[data-testid="stModal"] > div {
                width: 95vw !important;
                max-width: 95vw !important;
                height: 90vh !important;
                max-height: 90vh !important;
                padding: 0 !important;
                margin: auto !important;
                top: 5vh !important;
                left: 2.5vw !important;
                transform: none !important;
            }
            div[data-testid="stModal"] > div > div {
                height: 100% !important;
                max-height: 100% !important;
                border-radius: 12px !important;
            }
            div[data-testid="stModal"] > div > div > div {
                height: calc(90vh - 80px) !important;
                overflow: auto !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # 全屏模式 - 使用 dialog
        @st.dialog("🧠 思维导图 - 全屏模式", width="large")
        def show_fullscreen_mindmap():
            st.caption("🖱️ 滚轮缩放 | 拖拽移动 | 点击节点展开/折叠")
            try:
                # 使用更大的高度填满屏幕
                markmap(mindmap, height=600)
            except Exception as e:
                st.warning(f"思维导图渲染失败: {e}")
                st.code(mindmap, language="markdown")
            if st.button("❌ 关闭全屏", type="primary", use_container_width=True):
                st.session_state[f'mindmap_fullscreen_{video_id}'] = False
                st.rerun()
        
        show_fullscreen_mindmap()
        # 重置全屏状态（dialog 关闭后）
        st.session_state[f'mindmap_fullscreen_{video_id}'] = False
    
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
from utils.helpers import extract_video_id, extract_video_info

# 全局任务追踪 (video_id -> {status, message, progress})
if 'processing_tasks' not in st.session_state:
    st.session_state.processing_tasks = {}

def background_process(url: str, video_id: str, username: str, task_tracker: dict, transcribe_mode: str = 'local'):
    """
    后台处理任务
    
    Args:
        url: 视频链接
        video_id: 视频 ID
        username: 用户名
        task_tracker: 任务追踪字典
        transcribe_mode: 转录模式，'local' 或 'remote'
    """
    try:
        processor = VideoProcessor(transcribe_mode=transcribe_mode)
        
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
        
        # 从URL中提取视频信息
        video_info = extract_video_info(url)
        
        # 保存完整结果到历史记录
        history_manager = HistoryManager(username)
        
        record = {
            'video_id': result.video_id,
            'bv_id': video_info.get('bv_id'),
            'part': video_info.get('part'),
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
    url, submit, batch_urls, batch_submit = render_input_section()
    
    # 辅助函数：启动单个视频的分析任务
    def start_analysis(video_url):
        """启动单个视频分析任务，返回占位记录"""
        video_info = extract_video_info(video_url)
        video_id = video_info.get('video_id')
        bv_id = video_info.get('bv_id')
        part = video_info.get('part')
        
        if not video_id:
            return None
        
        history_manager = st.session_state.history_manager
        existing_record = history_manager.get_record_by_video_id(video_id)
        
        # 如果正在处理或已完成，跳过
        if video_id in st.session_state.processing_tasks:
            return None
        if existing_record:
            return None
        
        # 创建占位记录
        placeholder_record = {
            'video_id': video_id,
            'bv_id': bv_id,
            'part': part,
            'title': f'正在分析中... (P{part})' if part else '正在分析中...',
            'status': 'processing',
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        history_manager.add_record(placeholder_record)
        
        # 初始化任务状态
        st.session_state.processing_tasks[video_id] = {
            'status': ProcessingStatus.DOWNLOADING,
            'message': '准备开始...',
            'progress': 0
        }
        
        # 启动后台线程
        thread = threading.Thread(
            target=background_process,
            args=(video_url, video_id, st.session_state.username, st.session_state.processing_tasks, st.session_state.transcribe_mode)
        )
        thread.start()
        
        return placeholder_record
    
    # 辅助函数：检查远程 API 密钥是否有效
    def check_remote_api_key():
        """检查远程 API 密钥是否有效，如果无效返回错误消息"""
        if st.session_state.transcribe_mode != 'remote':
            return True, ""
        
        user_key = st.session_state.get('user_api_key', '')
        if not user_key:
            return False, "使用远程 API 需要输入有效密钥，请在左侧边栏输入密钥"
        
        result = api_key_manager.validate_key(user_key, st.session_state.username)
        if not result['valid']:
            return False, f"密钥无效: {result['message']}"
        
        return True, ""
    
    # 批量分析处理
    if batch_submit and batch_urls:
        # 检查远程 API 密钥
        key_valid, key_error = check_remote_api_key()
        if not key_valid:
            st.error(f"⚠️ {key_error}")
        else:
            started_count = 0
            skipped_count = 0
            first_record = None
            
            for video_url in batch_urls:
                record = start_analysis(video_url)
                if record:
                    started_count += 1
                    if first_record is None:
                        first_record = record
                else:
                    skipped_count += 1
            
            if started_count > 0:
                st.toast(f"🚀 已启动 {started_count} 个视频的分析任务", icon="🚀")
                if skipped_count > 0:
                    st.toast(f"⏭️ 跳过 {skipped_count} 个已存在的记录", icon="⏭️")
                
                # 设置当前查看的记录
                st.session_state.current_result = first_record
                st.session_state.history_list = st.session_state.history_manager.get_all_records()
                st.rerun()
            elif batch_urls:
                st.toast("📚 所有视频都已有分析记录", icon="📚")
    
    elif batch_submit and not batch_urls:
        st.warning("⚠️ 请输入有效的视频链接和分P范围")
    
    # 单个视频分析处理
    if submit and url:
        # 检查远程 API 密钥
        key_valid, key_error = check_remote_api_key()
        if not key_valid:
            st.error(f"⚠️ {key_error}")
        else:
            # 使用 extract_video_info 获取完整信息
            video_info = extract_video_info(url)
            video_id = video_info.get('video_id')
            bv_id = video_info.get('bv_id')
            part = video_info.get('part')
            
            if not video_id:
                st.error("无效的 B站视频链接")
            else:
                # 检查该视频是否已有历史记录
                history_manager = st.session_state.history_manager
                existing_record = history_manager.get_record_by_video_id(video_id)
                
                # 检查是否正在处理中
                if video_id in st.session_state.processing_tasks:
                    st.toast("⏳ 该视频正在分析中，请稍候...", icon="⏳")
                    st.session_state.current_result = existing_record if existing_record else {'video_id': video_id}
                    st.rerun()
                
                # 只要已有记录就不重新分析，直接展示
                elif existing_record:
                    st.session_state.current_result = existing_record
                    st.session_state.history_list = history_manager.get_all_records()
                    if existing_record.get('status') == 'completed':
                        st.toast("📚 该视频已有分析记录，正在展示之前的结果", icon="📚")
                    else:
                        st.toast("⚠️ 该视频存在未完成的记录，如需重新分析请先删除", icon="⚠️")
                    st.rerun()
                
                else:
                    # 1. 创建占位历史记录（仅当不存在现有记录时）
                    # 包含 bv_id 和 part 信息以支持自动分组
                    placeholder_record = {
                        'video_id': video_id,
                        'bv_id': bv_id,
                        'part': part,
                        'title': f'正在分析中... (P{part})' if part else '正在分析中...',
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
                        args=(url, video_id, st.session_state.username, st.session_state.processing_tasks, st.session_state.transcribe_mode)
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
