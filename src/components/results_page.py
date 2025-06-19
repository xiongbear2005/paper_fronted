import streamlit as st
from services.document_processor import convert_word_to_html, convert_word_to_html_with_math, extract_toc_from_docx, simulate_analysis_with_toc
from utils.session_state import reset_session_state
import re
import streamlit.components.v1 as components
import plotly.graph_objects as go
import textwrap
import json
import plotly.utils

# -------- 示例 JSON ---------

EXAMPLE_ANALYSIS = {
    "summary": "示例：本章节主要介绍研究背景与动机，包括相关工作综述。",
    "strengths": [
        "结构逻辑清晰，层次分明",
        "引用文献充分，论据充足",
    ],
    "weaknesses": [
        "部分段落表述略显冗长，可适当精简",
        "缺少对关键概念的图示说明，阅读门槛较高",
    ],
    "subchapter_advice": "可在'相关工作'子章节中加入最新的综述文章，提高时效性。",
}

def render_results_page():
    """渲染结果展示页面"""
    # 创建新容器以替换旧内容
    main_container = st.container()
    
    with main_container:
        st.markdown('<h1 class="main-header">📊 文档分析结果</h1>', unsafe_allow_html=True)
    
    # 顶部信息面板
    if st.session_state.uploaded_file:
        st.markdown(f"""
        <div style="background: linear-gradient(to right, rgba(67, 97, 238, 0.05), rgba(76, 201, 240, 0.03)); 
                    border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 2rem; 
                    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
            <div style="display: flex; align-items: center;">
                <div style="background-color: var(--primary-color); border-radius: 50%; width: 40px; height: 40px;
                            display: flex; align-items: center; justify-content: center; margin-right: 1rem;">
                    <span style="color: white; font-size: 1.5rem;">📄</span>
                </div>
                <div>
                    <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary);">
                        {st.session_state.uploaded_file.name}
                    </div>
                    <div style="color: var(--text-secondary); font-size: 0.85rem;">
                        分析完成 · {len(st.session_state.toc_items) if hasattr(st.session_state, 'toc_items') else 0} 个章节
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 操作按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔙 重新上传", key="reload_btn", help="重新上传Word文档", use_container_width=True):
            reset_session_state()
            st.session_state.current_page = 'upload'
            st.rerun()
    
    with col3:
        if st.button("📥 导出报告", key="export_btn", help="导出分析报告", use_container_width=True):
            st.info("导出功能开发中...")
    
    # 文档预览和分析区域
    container = st.container()
    with container:
        
        # 状态提示
        st.markdown("""
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="height: 6px; flex-grow: 1; background: linear-gradient(90deg, var(--primary-color), var(--primary-light), transparent);
                           border-radius: 3px;"></div>
                <span style="color: var(--text-secondary); font-size: 0.9rem;">文档分析已完成</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 文档内容区域（仅 HTML 预览）
        if hasattr(st.session_state, 'word_html') and st.session_state.word_html:
            # 使用辅助函数生成可展示的 HTML
            html_content = generate_html_preview(st.session_state.word_html)
            
            # 创建包含导航和内容的完整HTML文档
            complete_html = create_complete_html_document(
                html_content, 
                st.session_state.toc_items if hasattr(st.session_state, 'toc_items') else None
            )

            # Use st.components.v1.html to render the full HTML document
            components.html(
                complete_html,
                height=800,
                scrolling=True,
            )
            
            # 在 HTML 预览下方展示整体数据分析卡片
            if hasattr(st.session_state, 'analysis_result') and st.session_state.analysis_result:
                _render_data_analysis_card(st.session_state.analysis_result)
            
        else:
            # 处理没有内容的情况
            st.warning("无法显示文档内容，请重新上传文档。")
    
    # 废弃 Streamlit 原侧边栏，全部改为 iframe 内部优化建议
    # 旧侧边栏代码已移除

# 为HTML内容添加章节锚点
def add_chapter_anchors_to_html(html_content, toc_items):
    """为HTML内容添加基于目录的锚点，支持章节和子章节"""
    if not toc_items:
        return html_content
    
    enhanced_html = html_content
    anchors_added = []
    
    print("开始向HTML内容添加章节锚点...")
    
    # 为每个目录项在HTML中查找对应位置并添加锚点
    for i, chapter in enumerate(toc_items):
        # 使用原始文本(original_text)进行匹配，而不是可能被截断的显示文本(text)
        chapter_text = chapter.get('original_text', chapter['text'])
        chapter_id = chapter.get('id', f"section-{i}")
        
        # 检查文本是否在HTML中
        if chapter_text in enhanced_html:
            # 查找文本在HTML中的位置并添加锚点
            pattern = re.escape(chapter_text)
            replacement = f'<div id="{chapter_id}" class="chapter-anchor" style="scroll-margin-top: 60px;"></div>{chapter_text}'
            
            # 在第一次出现的位置添加锚点
            new_html = re.sub(pattern, replacement, enhanced_html, count=1)
            
            # 确认锚点添加成功
            if new_html != enhanced_html:
                enhanced_html = new_html
                anchors_added.append(chapter_id)
                print(f"已添加主章节锚点: '{chapter['text']}' (ID: {chapter_id})")
            else:
                # 如果简单替换失败，尝试在段落或标题标签上下文中匹配
                p_pattern = r'<(p|h[1-6])[^>]*>' + re.escape(chapter_text) + r'</\1>'
                
                # 更复杂的替换，保留原始标签
                new_html = re.sub(
                    p_pattern,
                    lambda m: f'<div id="{chapter_id}" class="chapter-anchor" style="scroll-margin-top: 60px;"></div>{m.group(0)}',
                    enhanced_html,
                    count=1
                )
                
                if new_html != enhanced_html:
                    enhanced_html = new_html
                    anchors_added.append(chapter_id)
                    print(f"已添加主章节锚点(带标签): '{chapter['text']}' (ID: {chapter_id})")
        
        # 处理子章节
        if 'children' in chapter:
            for j, subchapter in enumerate(chapter['children']):
                subchapter_text = subchapter.get('original_text', subchapter['text'])
                subchapter_id = subchapter.get('id', f"subsection-{i}-{j}")
                
                if subchapter_text in enhanced_html:
                    # 查找文本在HTML中的位置并添加锚点
                    pattern = re.escape(subchapter_text)
                    replacement = f'<div id="{subchapter_id}" class="chapter-anchor" style="scroll-margin-top: 60px;"></div>{subchapter_text}'
                    
                    # 在第一次出现的位置添加锚点
                    new_html = re.sub(pattern, replacement, enhanced_html, count=1)
                    
                    # 确认锚点添加成功
                    if new_html != enhanced_html:
                        enhanced_html = new_html
                        anchors_added.append(subchapter_id)
                        print(f"已添加子章节锚点: '{subchapter['text']}' (ID: {subchapter_id})")
    
    print(f"共添加了 {len(anchors_added)} 个章节锚点")
    return enhanced_html


# 新增: HTML 预览处理函数

def generate_html_preview(raw_html: str) -> str:
    """根据传入的 HTML 字符串添加章节锚点并处理 LaTeX，返回可直接展示的 HTML。
    
    参数
    -------
    raw_html : str
        由 Word 转换得到的原始 HTML 字符串

    返回
    -------
    str
        处理后的 HTML，可直接用于 st.markdown(…, unsafe_allow_html=True) 显示。
    """
    if not raw_html:
        return ""

    # 在最顶部插入目录锚点，供"置顶"按钮使用
    raw_html = '<a id="top-anchor"></a>' + raw_html
    
    # 注意：将不再在这里添加章节锚点，而是在create_complete_html_document函数中处理
    
    return raw_html

def create_complete_html_document(content_html, toc_items=None):
    """
    创建一个完整的HTML文档，包含内容和导航栏
    
    参数
    -------
    content_html : str
        主要内容的HTML
    toc_items : list
        目录结构列表
        
    返回
    -------
    str
        完整的HTML文档
    """
    # 提取原始内容中的所有内容（去除DOCTYPE和html/head/body标签）
    content_html = re.sub(r'<!DOCTYPE.*?>', '', content_html, flags=re.DOTALL)
    content_html = re.sub(r'<html.*?>.*?<body.*?>', '', content_html, flags=re.DOTALL)
    content_html = re.sub(r'</body>.*?</html>', '', content_html, flags=re.DOTALL)
    
    # 查找正文开始的位置 - 第二次出现"第一章"或类似章节标题的位置
    # 支持不同的章节标题格式: "第一章", "第1章", "1. ", "一、"等
    chapter_patterns = [
        r'<[^>]*>第一章[^<]*</[^>]*>',
        r'<[^>]*>第1章[^<]*</[^>]*>',
        r'<[^>]*>1[\.、]\s*[^<]*</[^>]*>',
        r'<[^>]*>一[\.、]\s*[^<]*</[^>]*>'
    ]
    
    # 尝试查找每个模式的第二次出现
    filtered_content = content_html
    for pattern in chapter_patterns:
        matches = list(re.finditer(pattern, content_html, re.IGNORECASE))
        if len(matches) >= 2:  # 至少有两次出现
            # 找到第二次出现的位置，从该位置开始截取
            second_occurrence_pos = matches[1].start()
            filtered_content = content_html[second_occurrence_pos:]
            print(f"找到第二次出现的章节标题，从位置 {second_occurrence_pos} 开始截取内容")
            break
    
    # 如果没有找到第二次出现的章节标题，就使用原始内容
    if filtered_content == content_html:
        print("未找到重复的章节标题，显示全部内容")
    
    # 现在在裁剪后的内容上添加章节锚点
    enhanced_content = filtered_content
    if toc_items:
        enhanced_content = add_chapter_anchors_to_html(filtered_content, toc_items)
    
    # 生成优化建议HTML
    analysis_sidebar_html = ""
    if toc_items:
        analysis_sidebar_html = """
        <div class="analysis-header">
            <h3>📝 内容优化建议</h3>
            <p class="analysis-subtitle">点击章节查看详细分析</p>
        </div>
        <div class="analysis-content">
        """
        
        for i, chapter in enumerate(toc_items):
            chapter_id = chapter.get('id', f"section-{i}")
            chapter_text = chapter.get('text', '')
            
            # 获取分析数据
            analysis = chapter.get('analysis', {})
            summary = analysis.get("summary", f"本章节主要讨论{chapter_text}相关内容。")
            strengths = analysis.get("strengths", [])
            weaknesses = analysis.get("weaknesses", [])
            subchapter_advice = analysis.get("subchapter_advice", "")
            
            # 生成优点和缺点列表
            strengths_html = "".join([f"<li>{item}</li>" for item in strengths]) if strengths else "<li>暂无明确优点</li>"
            weaknesses_html = "".join([f"<li>{item}</li>" for item in weaknesses]) if weaknesses else "<li>暂无明确不足</li>"
            
            # 生成章节优化建议卡片
            analysis_sidebar_html += f"""
            <div class="chapter-card" data-chapter-id="{chapter_id}">
                <div class="chapter-card-header" onclick="jumpToChapter('{chapter_id}', this)">
                    <div class="chapter-title">{chapter_text}</div>
                    <div class="chapter-indicator">▼</div>
                </div>
                <div class="chapter-details">
                    <div class="detail-section">
                        <div class="detail-header">📋 内容摘要</div>
                        <div class="detail-content">{summary}</div>
                    </div>
                    <div class="detail-section">
                        <div class="detail-header green">✅ 优点</div>
                        <ul class="detail-list">
                            {strengths_html}
                        </ul>
                    </div>
                    <div class="detail-section">
                        <div class="detail-header orange">⚠️ 不足之处</div>
                        <ul class="detail-list">
                            {weaknesses_html}
                        </ul>
                    </div>
            """
            
            # 添加子章节建议（如果有）
            if subchapter_advice:
                analysis_sidebar_html += f"""
                    <div class="detail-section">
                        <div class="detail-header blue">💡 子章节建议</div>
                        <div class="detail-content">{subchapter_advice}</div>
                    </div>
                """
                
            analysis_sidebar_html += """
                </div>
            </div>
            """
            
        analysis_sidebar_html += "</div>"

    # 完整HTML文档
    complete_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>文档预览</title>
        <!-- MathJax配置 -->
        <script>
            window.MathJax = {{
                tex: {{
                    inlineMath: [['\\\\(', '\\\\)']],
                    displayMath: [['\\\\[', '\\\\]']],
                    processEscapes: true
                }},
                options: {{
                    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
                    ignoreHtmlClass: 'tex2jax_ignore',
                    processHtmlClass: 'tex2jax_process'
                }}
            }};
        </script>
        <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" id="MathJax-script" async></script>
        <script>
            // 滚动到指定元素的函数
            function scrollToElement(elementId) {{
                const element = document.getElementById(elementId);
                if (element) {{
                    // 使用平滑滚动效果
                    document.querySelector('.content').scrollTo({{
                        top: element.offsetTop - 20,
                        behavior: 'smooth'
                    }});
                    // 高亮显示目标元素（可选）
                    element.classList.add('highlight-target');
                    setTimeout(() => {{
                        element.classList.remove('highlight-target');
                    }}, 2000);
                }} else {{
                    console.log('Element not found:', elementId);
                }}
            }}
            
            // 跳转到章节并展开对应的详情
            function jumpToChapter(chapterId, headerElement) {{
                // 跳转到章节
                scrollToElement(chapterId);
                
                // 展开/折叠详情
                const detailsDiv = headerElement.nextElementSibling;
                const allDetails = document.querySelectorAll('.chapter-details');
                const indicator = headerElement.querySelector('.chapter-indicator');
                const card = headerElement.parentElement;
                
                // 收起其他所有章节
                allDetails.forEach(detail => {{
                    if (detail !== detailsDiv) {{
                        detail.style.height = '0';
                        detail.parentElement.querySelector('.chapter-indicator').textContent = '▼';
                        detail.parentElement.classList.remove('active');
                    }}
                }});
                
                // 展开/折叠当前章节
                if (card.classList.contains('active')) {{
                    detailsDiv.style.height = '0';
                    indicator.textContent = '▼';
                    card.classList.remove('active');
                }} else {{
                    // 动态计算高度
                    const height = getDetailsHeight(detailsDiv);
                    detailsDiv.style.height = `${{height}}px`;
                    indicator.textContent = '▲';
                    card.classList.add('active');
                    
                    // 监听过渡结束事件，确保内容完全展示
                    detailsDiv.addEventListener('transitionend', function onTransitionEnd() {{
                        // 过渡结束后检查是否需要调整高度
                        const scrollHeight = detailsDiv.scrollHeight;
                        if (parseInt(detailsDiv.style.height) < scrollHeight) {{
                            detailsDiv.style.height = `${{scrollHeight}}px`;
                        }}
                        detailsDiv.removeEventListener('transitionend', onTransitionEnd);
                    }}, {{once: true}});
                }}
            }}
            
            // 计算内容区域的实际高度
            function getDetailsHeight(element) {{
                // 克隆元素用于测量
                const clone = element.cloneNode(true);
                clone.style.height = 'auto';
                clone.style.position = 'absolute';
                clone.style.visibility = 'hidden';
                clone.style.display = 'block';
                clone.style.width = `${{element.parentElement.clientWidth}}px`; // 确保宽度一致
                document.body.appendChild(clone);
                const height = clone.scrollHeight; // 使用scrollHeight代替offsetHeight
                document.body.removeChild(clone);
                return height;
            }}
            
            // 处理回到顶部的函数
            function scrollToTop() {{
                document.querySelector('.content').scrollTo({{
                    top: 0,
                    behavior: 'smooth'
                }});
            }}
            
            // 切换侧边栏显示/隐藏
            function toggleSidebar() {{
                // 仅在全屏模式下切换
                if (!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement)) return;
                document.getElementById('document-container').classList.toggle('hide-sidebar');
            }}
            
            // 全屏查看功能
            function toggleFullScreen() {{
                const container = document.getElementById('document-container');
                
                if (!document.fullscreenElement && 
                    !document.mozFullScreenElement && 
                    !document.webkitFullscreenElement && 
                    !document.msFullscreenElement) {{
                    // 进入全屏
                    if (container.requestFullscreen) {{
                        container.requestFullscreen();
                    }} else if (container.msRequestFullscreen) {{ // IE11
                        container.msRequestFullscreen();
                    }} else if (container.mozRequestFullScreen) {{ // Firefox
                        container.mozRequestFullScreen();
                    }} else if (container.webkitRequestFullscreen) {{ // Chrome, Safari
                        container.webkitRequestFullscreen();
                    }}
                    
                    document.querySelector('#fullscreen-btn').textContent = '退出全屏';
                    console.log('进入全屏模式');
                }} else {{
                    // 退出全屏
                    if (document.exitFullscreen) {{
                        document.exitFullscreen();
                    }} else if (document.msExitFullscreen) {{
                        document.msExitFullscreen();
                    }} else if (document.mozCancelFullScreen) {{
                        document.mozCancelFullScreen();
                    }} else if (document.webkitExitFullscreen) {{
                        document.webkitExitFullscreen();
                    }}
                    
                    document.querySelector('#fullscreen-btn').textContent = '全屏查看';
                    console.log('退出全屏模式');
                }}
            }}
            
            // 监听全屏变化事件，以便更新按钮状态
            document.addEventListener('fullscreenchange', updateFullScreenButton);
            document.addEventListener('webkitfullscreenchange', updateFullScreenButton);
            document.addEventListener('mozfullscreenchange', updateFullScreenButton);
            document.addEventListener('MSFullscreenChange', updateFullScreenButton);
            
            function updateFullScreenButton() {{
                const btn = document.querySelector('#fullscreen-btn');
                if (document.fullscreenElement || 
                    document.mozFullScreenElement || 
                    document.webkitFullscreenElement || 
                    document.msFullscreenElement) {{
                    btn.textContent = '退出全屏';
                    document.getElementById('toggle-sidebar-btn').style.opacity = '1';
                    console.log('全屏状态更新: 全屏模式');
                }} else {{
                    btn.textContent = '全屏查看';
                    document.getElementById('toggle-sidebar-btn').style.opacity = '0';
                    // 退出全屏时恢复侧边栏
                    document.getElementById('document-container').classList.remove('hide-sidebar');
                    console.log('全屏状态更新: 非全屏模式');
                }}
            }}
            
            // 页面加载完成后初始化
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('Document loaded, initializing...');
                
                // 初始化所有章节详情的高度
                document.querySelectorAll('.chapter-details').forEach(detail => {{
                    detail.style.height = '0';
                }});
                
                // 调试：列出所有带id的元素
                document.querySelectorAll('[id]').forEach(el => {{
                    console.log('Found element with ID:', el.id);
                }});
                
                // 处理段落缩进与公式居中
                document.querySelectorAll('.content p').forEach(function(p) {{
                    // 克隆段落并移除公式 / 图片节点，用于检测剩余文本
                    const clone = p.cloneNode(true);
                    clone.querySelectorAll('img, math, .math, .katex, .mml-equation').forEach(el => el.remove());
                    const remainingText = clone.textContent.replace(/\s+/g, '');

                    const hasFormulaOrImg = p.querySelector('img, math, .math, .katex, .mml-equation');

                    // 仅当段落中除公式/图片外无其他可见文本时居中
                    if (hasFormulaOrImg && remainingText === '') {{
                        p.classList.add('center-text');
                    }}
                }});
                
                // 隐藏加载指示器
                document.getElementById('loading-indicator').style.display = 'none';
            }});
            
            // 监听窗口大小变化，重新计算已展开章节的高度
            window.addEventListener('resize', function() {{
                // 查找所有已展开的章节
                document.querySelectorAll('.chapter-card.active .chapter-details').forEach(detail => {{
                    // 获取实际内容高度
                    detail.style.height = 'auto';
                    const height = detail.scrollHeight;
                    detail.style.height = `${{height}}px`;
                }});
            }});
            
            // 显示加载指示器
            document.addEventListener('fullscreenchange', function() {{
                if (document.fullscreenElement) {{
                    document.getElementById('loading-indicator').style.display = 'flex';
                    setTimeout(function() {{
                        document.getElementById('loading-indicator').style.display = 'none';
                    }}, 800);
                }}
            }});
        </script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Segoe UI', Arial, sans-serif;
                display: flex;
                height: 100vh;
                overflow: hidden;
                background-color: white;
            }}
            .sidebar {{
                width: 280px;
                min-width: 280px;
                flex: 0 0 280px;
                height: 100%;
                overflow-y: scroll; /* always show scrollbar to prevent width shift */
                scrollbar-gutter: stable; /* reserve space for scrollbar in supporting browsers */
                background-color: #f8f9fa;
                border-right: 1px solid #ddd;
                box-sizing: border-box;
                transform: translateX(0);
                transition: transform 0.3s ease, opacity 0.3s ease;
                padding: 0;
            }}
            .content {{
                flex: 1;
                height: 100%;
                overflow-y: auto;
                padding: 20px;
                background-color: white;
            }}
            
            /* 分析建议模块样式 */
            .analysis-header {{
                padding: 15px;
                background: linear-gradient(45deg, #4361ee, #3f89e8);
                color: white;
                border-radius: 10px;
                text-align: center;
                position: sticky;
                top: 0;
                z-index: 10;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .analysis-header h3 {{
                margin: 0;
                font-size: 1.3rem;
            }}
            .analysis-subtitle {{
                margin: 5px 0 0;
                font-size: 0.85rem;
                opacity: 0.9;
            }}
            .analysis-content {{
                padding: 15px;
            }}
            .chapter-card {{
                margin-bottom: 15px;
                border-radius: 8px;
                background-color: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                overflow: hidden;
                transition: box-shadow 0.2s ease;
            }}
            .chapter-card:hover {{
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            }}
            .chapter-card.active {{
                box-shadow: 0 3px 10px rgba(67, 97, 238, 0.25);
            }}
            .chapter-card-header {{
                padding: 12px 15px;
                background-color: #f1f3f9;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: pointer;
                transition: background-color 0.2s ease;
                box-sizing: border-box;
            }}
            .chapter-card-header:hover {{
                background-color: #e6ebf7;
            }}
            .chapter-card.active .chapter-card-header {{
                background-color: #e1e7f7;
                border-left: 4px solid #4361ee;
                padding-left: 15px;
                box-sizing: border-box;
            }}
            .chapter-title {{
                font-weight: 600;
                color: #333;
                font-size: 0.95rem;
            }}
            .chapter-indicator {{
                color: #666;
                font-size: 0.8rem;
            }}
            .chapter-details {{
                height: 0;
                overflow: hidden;
                transition: height 0.3s ease-out;
                background-color: white;
            }}
            .detail-section {{
                padding: 12px 15px;
                border-top: 1px solid #eee;
            }}
            .detail-header {{
                font-weight: 600;
                color: #444;
                margin-bottom: 8px;
                font-size: 0.9rem;
            }}
            .detail-header.green {{ color: #2e8b57; }}
            .detail-header.orange {{ color: #e67e22; }}
            .detail-header.blue {{ color: #3498db; }}
            .detail-content {{
                font-size: 0.9rem;
                line-height: 1.5;
                color: #555;
            }}
            .detail-list {{
                margin: 5px 0;
                padding-left: 20px;
                font-size: 0.9rem;
                line-height: 1.5;
                color: #555;
            }}
            .detail-list li {{
                margin-bottom: 5px;
            }}
            
            /* 按钮样式 */
            .top-button {{
                background-color: #4361ee;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                cursor: pointer;
                font-size: 13px;
                margin-left: 5px;
            }}
            #fullscreen-btn {{
                background-color: #2e8b57;
            }}
            .button-group {{
                position: sticky;
                bottom: 0;
                display: flex;
                gap: 5px;
                align-items: center;
                justify-content: center;
                padding: 8px 0;
                background: #f8f9fa; /* 与侧边栏背景一致，避免遮挡 */
                border-top: 1px solid #ddd;
                box-sizing: border-box;
            }}
            
            /* 全屏样式 */
            #document-container {{
                display: flex;
                width: 100%;
                height: 100vh;
                background-color: white;
                position: relative;
            }}
            #document-container:fullscreen {{
                background-color: white;
                padding: 20px;
                overflow: hidden;
            }}
            #document-container:fullscreen .content {{
                padding: 40px;
                max-width: 1000px;
                margin: 0 auto;
                background-color: white;
                overflow-y: auto;
            }}
            
            /* Firefox全屏样式 */
            #document-container:-moz-full-screen {{
                background-color: white;
                padding: 20px;
                overflow: hidden;
            }}
            /* Chrome全屏样式 */
            #document-container:-webkit-full-screen {{
                background-color: white;
                padding: 20px;
                overflow: hidden;
            }}
            /* 添加切换侧边栏按钮 */
            #toggle-sidebar-btn {{
                position: fixed;
                top: 10px;
                left: 10px;
                z-index: 100;
                background: rgba(67, 97, 238, 0.8);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                cursor: pointer;
                opacity: 0;
                transition: opacity 0.3s ease;
            }}
            #document-container:fullscreen #toggle-sidebar-btn {{
                opacity: 1;
            }}
            
            /* 加载指示器 */
            #loading-indicator {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: rgba(255, 255, 255, 0.8);
                z-index: 1000;
            }}
            .spinner {{
                width: 40px;
                height: 40px;
                border-radius: 50%;
                border: 4px solid rgba(67, 97, 238, 0.3);
                border-top-color: #4361ee;
                animation: spin 1s linear infinite;
            }}
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            
            /* 仅在全屏模式下允许隐藏侧边栏 */
            #document-container.hide-sidebar:fullscreen .sidebar, 
            #document-container:fullscreen.hide-sidebar .sidebar {{
                transform: translateX(-100%);
                opacity: 0;
                pointer-events: none;
            }}
            
            /* 高亮样式 */
            .highlight-target {{
                animation: highlight 2s;
            }}
            @keyframes highlight {{
                0% {{ background-color: rgba(67, 97, 238, 0.2); }}
                100% {{ background-color: transparent; }}
            }}
            
            h1, h2, h3, h4, h5, h6 {{
                scroll-margin-top: 20px;
            }}
            .chapter-anchor {{
                scroll-margin-top: 20px;
            }}
            
            @media (max-width: 768px) {{
                body {{
                    flex-direction: column;
                }}
                .sidebar {{
                    width: 100%;
                    height: auto;
                    max-height: 45%;
                }}
                .content {{
                    height: 55%;
                }}
                body.in-fullscreen .sidebar {{
                    max-height: 0;
                }}
                #document-container:fullscreen {{
                    flex-direction: column;
                }}
                #document-container:fullscreen .sidebar {{
                    width: 100%;
                    max-width: 100%;
                    height: auto;
                    max-height: 45%;
                    overflow-y: auto;
                    padding: 10px;
                }}
                #toggle-sidebar-btn {{
                    top: 5px;
                    left: 5px;
                    font-size: 12px;
                }}
                .chapter-card-header {{
                    padding: 10px;
                }}
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 1rem 0;
            }}
            table, th, td {{
                border: 1px solid #ddd;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
            }}
            img {{
                max-width: 65%;
                height: auto;
                display: block;
                margin: 0.5rem auto;
            }}

            /* 段落首行缩进 */
            .content p {{
                text-indent: 2em;
                line-height: 1.8;
                margin: 0.8rem 0;
            }}

            /* 居中公式段落（通过JS动态添加 center-text 类）*/
            .content p.center-text {{
                text-indent: 0;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div id="document-container">
            <!-- 加载指示器 -->
            <div id="loading-indicator">
                <div class="spinner"></div>
            </div>
            
            <button id="toggle-sidebar-btn" onclick="toggleSidebar()">
                ☰ 显示/隐藏建议
            </button>
            <div class="sidebar">
                <!-- 内容优化建议 -->
                {analysis_sidebar_html}
                
                <!-- 控制按钮区域 -->
                <div class="button-group">
                    <button class="top-button" onclick="scrollToTop()">回到顶部</button>
                    <button id="fullscreen-btn" class="top-button" onclick="toggleFullScreen()">全屏查看</button>
                </div>
            </div>
            <div class="content">
                {enhanced_content}
            </div>
        </div>
    </body>
    </html>
    """
    return complete_html

# -------- 分析渲染辅助函数 ---------

def generate_analysis_html(chapter_text: str, analysis: dict | None = None) -> str:
    """根据传入的章节标题和分析 JSON 生成侧边栏 HTML。

    参数
    ----
    chapter_text : str
        章节标题（用于默认文案占位）。
    analysis : dict | None
        JSON 格式的分析数据，可能包含以下键：

        - summary : str           内容摘要
        - strengths : list[str]   优点列表
        - weaknesses : list[str]  不足之处列表
        - subchapter_advice : str 子章节建议（可选）

    返回
    ----
    str
        已拼接完成的 HTML 字符串，可直接用 `st.markdown(..., unsafe_allow_html=True)` 渲染。
    """

    # 若未传入分析数据，则使用示例 JSON
    if not analysis:
        analysis = EXAMPLE_ANALYSIS

    summary = analysis.get("summary") or f"本章节主要讨论{chapter_text}相关内容，包含了相关理论基础和研究方法。"
    strengths = analysis.get("strengths") or []
    weaknesses = analysis.get("weaknesses") or []
    subchapter_advice = analysis.get("subchapter_advice")
        
    # 构造列表项 HTML
    def _list_html(items):
        if not items:
            return "<li>暂无</li>"
        return "".join(f"<li>{st}</li>" for st in items)

    strengths_html = _list_html(strengths)
    weaknesses_html = _list_html(weaknesses)

    # 主 HTML 模板
    html_parts = [
        # 内容摘要
        f"""
        <div style="background: var(--card-bg); border-radius: 10px; padding: 1rem; 
                   box-shadow: 0 2px 8px rgba(0,0,0,0.03); margin-bottom: 1rem;">
            <div style="font-weight: 600; color: var(--primary-color); 
                       display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>📋 内容摘要</span>
            </div>
            <div style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6;">
                {summary}
            </div>
        </div>
        """,

        # 优点
        f"""
        <div style="background: var(--card-bg); border-radius: 10px; padding: 1rem; 
                   box-shadow: 0 2px 8px rgba(0,0,0,0.03); margin-bottom: 1rem;">
            <div style="font-weight: 600; color: var(--success-color); 
                       display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>✅ 优点</span>
            </div>
            <div style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6;">
                <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                    {strengths_html}
                </ul>
            </div>
        </div>
        """,

        # 不足之处
        f"""
        <div style="background: var(--card-bg); border-radius: 10px; padding: 1rem; 
                   box-shadow: 0 2px 8px rgba(0,0,0,0.03); margin-bottom: 1rem;">
            <div style="font-weight: 600; color: var(--warning-color); 
                       display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>⚠️ 不足之处</span>
            </div>
            <div style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6;">
                <ul style="margin-top: 0.5rem; padding-left: 1.5rem;">
                    {weaknesses_html}
                </ul>
            </div>
        </div>
        """,
    ]

    # 可选子章节建议
    if subchapter_advice:
        html_parts.append(
            f"""
            <div style="background: var(--card-bg); border-radius: 10px; padding: 1rem; 
                       box-shadow: 0 2px 8px rgba(0,0,0,0.03); margin-bottom: 1rem;">
                <div style="font-weight: 600; color: var(--info-color); 
                           display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span>💡 子章节建议</span>
                </div>
                <div style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6;">
                    {subchapter_advice}
                </div>
            </div>
            """,
        )
    
    return "\n".join(html_parts)

# -------- 页面级数据分析卡片渲染 ---------

def _render_data_analysis_card(analysis_result: dict):
    """渲染文档整体数据分析卡片。包含：
    1. 基本统计（字数、章节数、关键词）
    2. 多维度评分表
    3. 评分维度雷达图
    """

    if not analysis_result:
        return

    # -------- 多维度评分 ---------
    # 如果后端分析已生成评分数据，则使用；否则给出示例占位
    # 添加默认总结文本
    default_summary = {
        "overall_comment": "本论文整体表现良好，研究问题明确，方法创新，实验设计合理，结果可靠。",
        "strengths": [
            "研究选题具有重要理论和现实意义，切合学科发展前沿",
            "创新性方法设计合理，模型结构清晰，技术路线可行",
            "实验设计完整，数据分析全面，结果呈现清晰直观"
        ],
        "weaknesses": [
            "引言部分对研究背景的阐述可进一步加强",
            "相关工作综述部分对最新研究的涵盖不够全面",
            "对研究局限性的讨论可以更加深入"
        ],
        "suggestions": [
            "建议补充更多最新文献，特别是近一年发表的相关工作",
            "可增加对方法在不同场景下适用性的讨论",
            "建议进一步完善结论部分，更清晰地指出未来研究方向"
        ]
    }

    default_scores = [
        {'index': 1, 'module': '摘要', 'full_score': 5, 'score': 4},
        {'index': 2, 'module': '选题背景和意义', 'full_score': 5, 'score': 4},
        {'index': 3, 'module': '选题的理论意义与应用价值', 'full_score': 5, 'score': 4},
        {'index': 4, 'module': '相关工作的国内外现状综述', 'full_score': 5, 'score': 4},
        {'index': 5, 'module': '主要工作和贡献总结', 'full_score': 5, 'score': 4},
        {'index': 6, 'module': '相关工作或相关技术的介绍', 'full_score': 5, 'score': 4},
        {'index': 7, 'module': '论文的创新性', 'full_score': 25, 'score': 20},
        {'index': 8, 'module': '实验完成度', 'full_score': 20, 'score': 15},
        {'index': 9, 'module': '总结和展望', 'full_score': 5, 'score': 4},
        {'index': 10, 'module': '工作量', 'full_score': 5, 'score': 4},
        {'index': 11, 'module': '论文撰写质量', 'full_score': 10, 'score': 7},
        {'index': 12, 'module': '参考文献', 'full_score': 5, 'score': 4},
    ]

    scores_data = analysis_result.get('overall_scores', default_scores)

    # -------- 总得分 ---------
    total_full_score = sum(item.get('full_score', 0) for item in scores_data)
    total_score = sum(item.get('score', item.get('full_score', 0)) for item in scores_data)
    total_score_html = f"""
    <div class='total-score'>总得分：<strong>{total_score}</strong> / {total_full_score}</div>
    """

    # 生成带进度条的行
    eval_html_parts = []
    for item in scores_data:
        full_score = item.get('full_score', 0)
        score = item.get('score', full_score)
        pct = 0 if full_score == 0 else round(score / full_score * 100, 1)
        bar_html = f"<div class='score-bar'><div class='score-fill' style='width:{pct}%;'></div></div>"
        eval_html_parts.append(
            f"""
            <div class='eval-row'>
                <div class='eval-name'><span class='eval-index'>{item.get('index','')}</span>{item['module']}</div>
                <div class='eval-score'>{bar_html}<span class='score-num'>{score}/{full_score}</span></div>
            </div>
            """
        )
    evaluations_html = total_score_html + "".join(eval_html_parts)

    # -------- 生成雷达图 HTML ---------
    try:
        modules = [item['module'] for item in scores_data]
        raw_scores = [item.get('score', item.get('full_score', 0)) for item in scores_data]
        norm_scores = [round((s / item.get('full_score',1))*10,2) for s,item in zip(raw_scores, scores_data)]
        modules.append(modules[0])
        norm_scores.append(norm_scores[0])

        # 设置主色调为蓝色（与整体主题保持一致）
        primary_color_rgba = 'rgba(67,97,238,1)'        # 纯色线条
        primary_fill_rgba = 'rgba(67,97,238,0.2)'       # 20% 不透明度填充

        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=norm_scores,
                theta=modules,
                fill='toself',
                name='得分(10分制)',
                line=dict(color=primary_color_rgba, width=2),
                fillcolor=primary_fill_rgba,
                marker=dict(color=primary_color_rgba)
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            height=350
        )

        fig_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        fig_html = f"""
        <div id='radar-chart'></div>
        <script>
        function drawRadar(){{
            const fig = {fig_json};
            Plotly.newPlot('radar-chart', fig.data, fig.layout, {{displayModeBar: false}});
        }}
        if(window.Plotly){{drawRadar();}}else{{
            const s=document.createElement('script');
            s.src='https://cdn.plot.ly/plotly-latest.min.js';
            s.onload=drawRadar;
            document.head.appendChild(s);
        }}
        </script>
        """
    except Exception as e:
        print(f"Radar chart rendering error: {e}")
        fig_html = "<p>图表渲染失败</p>"

    # -------- 渲染论文总结卡片 ---------
    summary_data = analysis_result.get('paper_summary', default_summary)
    
    # 生成优点、缺点和建议的HTML列表
    strengths_list = summary_data.get("strengths", [])
    weaknesses_list = summary_data.get("weaknesses", [])
    suggestions_list = summary_data.get("suggestions", [])

    strengths_html = "".join([f"<li>{item}</li>" for item in strengths_list])
    weaknesses_html = "".join([f"<li>{item}</li>" for item in weaknesses_list])
    suggestions_html = "".join([f"<li>{item}</li>" for item in suggestions_list])
    
    # -------- 动态计算高度 ---------
    # 基础高度 300px，加上每条列表项约 32px
    item_count = len(strengths_list) + len(weaknesses_list) + len(suggestions_list)
    dynamic_height = 360 + item_count * 32  # 额外空间防止阴影被裁剪

    summary_html = f"""
    <style>
        .summary-card {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid rgba(67,97,238,0.2);
            box-shadow: none;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
            padding: 1.8rem;
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
            width: 100%;
            box-sizing: border-box;
        }}
        .summary-card:hover {{
            transform: translateY(-6px);
            box-shadow: 0 6px 18px rgba(0,0,0,0.08), 0 12px 24px -6px rgba(0,0,0,0.12);
        }}
        .summary-header {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 1.2rem;
        }}
        .summary-header h3 {{
            margin: 0;
            font-weight: 700;
            font-size: 1.3rem;
            color: var(--primary-color);
        }}
        .overall-comment {{
            padding: 0.8rem 1rem;
            background: rgba(67, 97, 238, 0.05);
            border-left: 4px solid var(--primary-color);
            border-radius: 4px;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
            font-size: 1rem;
            line-height: 1.5;
        }}
        .section-title {{
            font-weight: 600;
            font-size: 1rem;
            color: var(--text-primary);
            margin-top: 1.2rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .section-icon {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            color: white;
        }}
        .icon-strength {{ background-color: #06d6a0; }}
        .icon-weakness {{ background-color: #f94144; }}
        .icon-suggestion {{ background-color: #3a86ff; }}
        .summary-list {{
            margin: 0;
            padding-left: 1.5rem;
            color: var(--text-secondary);
        }}
        .summary-list li {{
            margin-bottom: 0.5rem;
            line-height: 1.5;
        }}
    </style>
    
    <div class="summary-card">
        <div class="summary-header">
            <span style="font-size:1.5rem;">📝</span>
            <h3>论文整体评价</h3>
        </div>
        
        <div class="overall-comment">
            {summary_data.get("overall_comment", "论文整体结构完整，内容充实，研究方法合理，结果可靠。")}
        </div>
        
        <div class="section-title">
            <span class="section-icon icon-strength">✓</span>
            优势与亮点
        </div>
        <ul class="summary-list">
            {strengths_html}
        </ul>
        
        <div class="section-title">
            <span class="section-icon icon-weakness">!</span>
            不足之处
        </div>
        <ul class="summary-list">
            {weaknesses_html}
        </ul>
        
        <div class="section-title">
            <span class="section-icon icon-suggestion">+</span>
            改进建议
        </div>
        <ul class="summary-list">
            {suggestions_html}
        </ul>
    </div>
    """
    
    # -------- CSS 样式 & 卡片 HTML ---------
    card_html = f"""
    <style>
        .analysis-card {{
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid rgba(67,97,238,0.2);
            box-shadow: none;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
            padding: 1.8rem;
            margin-top: 2rem;
            margin-bottom: 1.5rem;
            width: 100%;
            box-sizing: border-box;
        }}
        .analysis-card:hover {{
            transform: translateY(-6px);
            box-shadow: 0 6px 18px rgba(0,0,0,0.08), 0 12px 24px -6px rgba(0,0,0,0.12);
        }}
        .analysis-card .header {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 1.2rem;
        }}
        .analysis-card .header h3 {{
            margin: 0;
            font-weight: 700;
            font-size: 1.3rem;
            color: var(--primary-color);
        }}
        .analysis-flex {{ display:flex; flex-wrap:wrap; gap:1rem; }}
        .eval-list {{ flex:1; min-width:300px; max-width:700px; }}
        .radar-container {{ flex:1; min-width:240px; max-height:350px; }}
        .eval-row {{ display:flex; align-items:center; margin-bottom:0.6rem; }}
        .eval-name {{ flex:1; font-size:0.9rem; font-weight:600; color:var(--text-primary); display:flex; align-items:center; }}
        .eval-index {{ 
            background: #4361ee; 
            color: #fff; 
            border-radius: 50%; 
            width: 22px; 
            height: 22px; 
            font-size: 0.75rem; 
            margin-right: 8px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            flex-shrink: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .eval-score {{ width:220px; display:flex; align-items:center; gap:6px; }}
        .score-bar {{ flex:1; background:#e9ecef; border-radius:6px; height:8px; position:relative; }}
        .score-fill {{ height:100%; border-radius:6px; background:linear-gradient(90deg,#4cc9f0,#4361ee); }}
        .score-num {{ font-weight:600; color:var(--text-secondary); font-size:0.8rem; white-space:nowrap; }}
        .total-score {{ font-size:1.05rem; font-weight:700; color:var(--primary-color); margin-bottom:0.8rem; }}
    </style>

    <div class="analysis-card">
        <div class="header"><span style="font-size:1.5rem;">📈</span><h3>文档整体数据分析</h3></div>
        <div class="analysis-flex">
            <div class="eval-list">
                {evaluations_html}
            </div>
            <div class="radar-container">
                {fig_html}
            </div>
        </div>
    </div>
    """

    # 渲染卡片和表格
    cleaned_html = re.sub(r'^\s+', '', textwrap.dedent(card_html), flags=re.MULTILINE)

    # -------- 动态计算分析卡片高度 ---------
    analysis_row_height = 32
    base_analysis_height = 160  # header + padding 约 160
    row_count = len(scores_data) + 1  # 额外 1 行用于总得分
    analysis_height = max(480, base_analysis_height + row_count*analysis_row_height)

    components.html(
        f"""
        <div style=\"max-width: 100%; margin: 0 auto; overflow: visible;\">
            {cleaned_html}
        </div>
        """, 
        height=analysis_height, 
        scrolling=False
    )

    # ----- 在数据分析卡片之后渲染论文总结卡片 -----
    cleaned_summary_html = re.sub(r'^\s+', '', textwrap.dedent(summary_html), flags=re.MULTILINE)
    components.html(
        f"""
        <div style="max-width: 100%; margin: 0 auto; overflow: visible;">
            {cleaned_summary_html}
        </div>
        """,
        height=dynamic_height,
        scrolling=False
    ) 