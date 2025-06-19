import streamlit as st

def render_feature_card(emoji, title, description, color):
    return f"""
    <div style="flex: 1; min-width: 300px; background: white; padding: 2rem; border-radius: 12px; 
                box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: left; margin: 1rem;">
        <div style="font-size: 2.5rem; color: var({color}); margin-bottom: 1rem;">{emoji}</div>
        <h4 style="font-weight: 600; margin-bottom: 1rem; font-size: 1.2rem;">{title}</h4>
        <p style="color: var(--text-secondary); font-size: 1rem; line-height: 1.6;">{description}</p>
    </div>
    """

def render_upload_page():
    """渲染上传页面"""
    st.markdown('<h1 class="main-header">📄 Word文档分析器</h1>', unsafe_allow_html=True)
    
    # 上传区域
    st.markdown("""
    <div style="background: white; padding: 2rem; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); margin-bottom: 3rem;">
        <div style="display: flex; align-items: flex-start; gap: 2rem;">
            <div style="flex: 0 0 auto; text-align: center;">
                <div style="width: 100px; height: 100px; margin: 0 auto; background: linear-gradient(45deg, var(--primary-color), var(--primary-light)); 
                            border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 3rem;">📤</span>
                </div>
            </div>
            <div style="flex: 1;">
                <h3 style="font-weight: 700; margin-bottom: 1rem; color: var(--primary-color);">
                    上传文档
                </h3>
                <p style="color: var(--text-secondary); margin-bottom: 1rem; font-size: 0.95rem; line-height: 1.6;">
                    支持.docx格式文档，自动识别图片、表格和复杂排版
                </p>
                <div class="supported-features" style="display: flex; gap: 1.5rem; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: var(--success-color);">✓</span>
                        <span style="color: var(--text-secondary); font-size: 0.9rem;">图片和表格</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: var(--success-color);">✓</span>
                        <span style="color: var(--text-secondary); font-size: 0.9rem;">数学公式</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: var(--success-color);">✓</span>
                        <span style="color: var(--text-secondary); font-size: 0.9rem;">章节结构</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: var(--success-color);">✓</span>
                        <span style="color: var(--text-secondary); font-size: 0.9rem;">智能优化</span>
                    </div>
                </div>
            </div>
            <div style="flex: 0 0 200px; display: flex; flex-direction: column; gap: 1rem;">
    """, unsafe_allow_html=True)
    
    # 文件上传组件和按钮放在右侧
    uploaded_file = st.file_uploader(
        "选择Word文档",
        type=['docx'],
        help="支持包含图片和复杂格式的Word文档",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        st.markdown("""
        <div style="background: var(--success-light); border-radius: 12px; padding: 0.75rem; margin-bottom: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 20px; height: 20px; background: var(--success-color); border-radius: 50%; 
                            display: flex; align-items: center; justify-content: center; color: white; font-size: 0.8rem;">✓</div>
                <div style="font-size: 0.9rem; color: var(--success-color);">文件已上传</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state.uploaded_file = uploaded_file
        
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            st.session_state.current_page = 'processing'
            st.rerun()
    
    st.markdown("</div></div></div>", unsafe_allow_html=True)