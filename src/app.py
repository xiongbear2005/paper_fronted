import streamlit as st
from utils.session_state import init_session_state, reset_session_state
from components.upload_page import render_upload_page
from components.processing_page import render_processing_page
from components.results_page import render_results_page
from styles.custom_styles import apply_custom_styles

# 页面配置必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="Word文档分析器",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def main():
    """主应用入口函数"""
    # 初始化会话状态
    init_session_state()
    
    # 应用自定义样式
    apply_custom_styles()
    
    # 创建页面容器
    page_container = st.container()
    
    # 清除之前的内容
    page_container.empty()
    
    # 页面路由
    with page_container:
        if st.session_state.current_page == 'upload':
            render_upload_page()
        elif st.session_state.current_page == 'processing':
            render_processing_page()
        elif st.session_state.current_page == 'results':
            render_results_page()

if __name__ == "__main__":
    main() 