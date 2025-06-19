import streamlit as st
import time
from services.document_processor import convert_word_to_html, convert_word_to_html_with_math, simulate_analysis_with_toc

def render_processing_page():
    """渲染处理页面"""
    # 检查是否有上传的文件
    if not hasattr(st.session_state, 'uploaded_file') or st.session_state.uploaded_file is None:
        st.warning("请先上传文件")
        st.session_state.current_page = 'upload'
        st.rerun()
    
    # 显示处理进度
    st.markdown('<h1 class="main-header">⚙️ 文档处理中...</h1>', unsafe_allow_html=True)
    
    # 显示上传的文件信息
    st.markdown(f"""
    <div style="background: linear-gradient(to right, rgba(67, 97, 238, 0.05), rgba(76, 201, 240, 0.03)); 
                border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 2rem; 
                display: flex; align-items: center;">
        <div style="background-color: var(--primary-color); border-radius: 50%; width: 40px; height: 40px;
                    display: flex; align-items: center; justify-content: center; margin-right: 1rem;">
            <span style="color: white; font-size: 1.5rem;">📄</span>
        </div>
        <div>
            <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary);">
                {st.session_state.uploaded_file.name}
            </div>
            <div style="color: var(--text-secondary); font-size: 0.85rem;">
                正在处理文档，请稍候...
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 处理步骤
    steps = [
        "正在加载文档...",
        "分析章节内容...",
        "生成HTML预览...",
        "整合分析结果..."
    ]
    
    # 模拟处理过程
    for i, step in enumerate(steps):
        # 更新状态
        status_text.text(step)
        progress_bar.progress((i + 1) / len(steps))
        
        # 实际处理逻辑
        if i == 0:  # 加载文档
            time.sleep(0.5)
        elif i == 1:  # 分析章节内容 (占位)
            # 可在此插入快速预分析逻辑
            time.sleep(0.7)
        elif i == 2:  # 生成HTML预览
            # 使用增强版转换函数，支持数学公式和复杂格式
            html_content = convert_word_to_html_with_math(st.session_state.uploaded_file)
            st.session_state.word_html = html_content
            time.sleep(0.5)
        elif i == 3:  # 整合分析结果
            # 生成分析结果
            analysis_result = simulate_analysis_with_toc(st.session_state.uploaded_file)
            st.session_state.analysis_result = analysis_result
            
            # 更新toc_items，确保包含分析结果
            if analysis_result and 'chapters' in analysis_result:
                st.session_state.toc_items = analysis_result['chapters']
            
            time.sleep(0.5)
    
    # 处理完成，跳转到结果页面
    st.session_state.current_page = 'results'
    st.rerun() 