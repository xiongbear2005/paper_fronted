import streamlit as st

def apply_custom_styles():
    """应用自定义CSS样式"""
    st.markdown("""
    <style>
        /* 全局变量 */
        :root {
            --primary-color: #4361ee;
            --primary-light: #4cc9f0;
            --secondary-color: #7209b7;
            --accent-color: #f72585;
            --warning-color: #fb8b24;
            --success-color: #06d6a0;
            --success-light: rgba(6, 214, 160, 0.15);
            --text-primary: #333;
            --text-secondary: #666;
            --bg-color: #f8f9fa;
            --card-bg: #fff;
            --border-color: rgba(0,0,0,0.1);
            --sidebar-width: 280px;
        }
        
        /* 重置页面样式，确保每次切换页面都是干净的 */
        div[data-testid="stVerticalBlock"] {
            position: relative;
        }
        
        /* 基础样式 */
        body {
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
        }
        
        /* 标题样式 */
        h1.main-header {
            color: var(--primary-color);
            font-weight: 800;
            font-size: 2.5rem;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        /* 上传区样式 */
        .upload-area {
            background-color: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.08);
        }
        
        /* 处理页面样式 */
        .processing-container {
            background-color: white;
            padding: 3rem 2rem;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.08);
            text-align: center;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .progress-text {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--primary-color);
            margin-bottom: 2rem;
        }
        
        /* 结果页面样式 */
        .word-preview {
            background-color: white;
            padding: 2rem;
            border-radius: 0 0 12px 12px;
            overflow-y: auto;
            max-height: 600px;
            line-height: 1.8;
        }
        
        .word-preview h1, .word-preview h2, .word-preview h3 {
            color: var(--primary-color);
            margin-top: 1.5em;
            margin-bottom: 0.75em;
        }
        
        .word-preview p {
            margin-bottom: 1em;
        }
        
        .word-preview table {
            border-collapse: collapse;
            width: 100%;
            margin: 1.5em 0;
        }
        
        .word-preview th, .word-preview td {
            border: 1px solid var(--border-color);
            padding: 8px 12px;
        }
        
        .word-preview th {
            background-color: rgba(67, 97, 238, 0.05);
            font-weight: 600;
        }
        
        /* Streamlit组件的自定义样式 */
        div.stButton > button {
            border-radius: 50px;
            font-weight: 600;
            padding: 0.5em 1.5em;
            transition: all 0.3s ease;
        }
        
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        /* 文件上传器样式 */
        .uploadedFile {
            border-radius: 12px !important;
            border: 1px dashed var(--border-color) !important;
            padding: 1.5rem !important;
            background-color: rgba(67, 97, 238, 0.03) !important;
        }
        
        /* 侧边栏样式 */
        .css-1oe6o1r {
            background-color: white;
            border-right: 1px solid var(--border-color);
        }
        
        /* 进度条样式 */
        .stProgress > div > div {
            background-color: var(--primary-color);
        }
    </style>
    """, unsafe_allow_html=True) 