"""
DOCX to HTML converter with math formula support
This module converts Microsoft Word documents (.docx) to HTML with MathJax for formula rendering.
"""

import os
import re
import docx
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from lxml import etree
from html import escape
from services.omml_to_latex import OmmlToLatexConverter

class Docx2HtmlConverter:
    """Converter class for DOCX to HTML transformation with math formula support."""
    
    def __init__(self, mathjax_url="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"):
        """
        Initialize the converter.
        
        Args:
            mathjax_url (str): URL to the MathJax library for rendering formulas.
        """
        self.mathjax_url = mathjax_url
        self.omml_converter = OmmlToLatexConverter()
        # OMML namespace for finding math elements
        self.ns_math = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
        self.ns_w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        self.ns_r = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
        self.ns_a = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
        # Statistics counter
        self.stats = {
            'images': 0,
            'inline_math': 0,
            'display_math': 0
        }
        # Set to track processed image IDs to avoid duplicates
        self.processed_image_ids = set()
    
    def convert_docx_to_html(self, docx_path, output_path=None, title=None, include_images=True):
        """
        Convert a DOCX file to HTML with math formula support.
        
        Args:
            docx_path (str): Path to the input DOCX file.
            output_path (str, optional): Path for the output HTML file. If None, uses the same path as docx_path but with .html extension.
            title (str, optional): Title for the HTML document. If None, uses the filename.
            include_images (bool): Whether to extract and include images from the DOCX file.
            
        Returns:
            str: Path to the generated HTML file.
        """
        if output_path is None:
            output_path = os.path.splitext(docx_path)[0] + '.html'
        
        if title is None:
            title = os.path.basename(os.path.splitext(docx_path)[0])
        
        # Load the document
        doc = docx.Document(docx_path)
        
        # Start building HTML content
        html_content = []
        
        # Reset statistics and processed image IDs
        self.stats = {
            'images': 0,
            'inline_math': 0,
            'display_math': 0
        }
        self.processed_image_ids = set()
        
        # Extract and save images if requested
        image_dir = None
        if include_images:
            image_dir = os.path.splitext(output_path)[0] + '_images'
            os.makedirs(image_dir, exist_ok=True)
        
        # Build a map of relationship IDs to relationships
        relationship_map = {}
        for rel_id, rel in doc.part.rels.items():
            relationship_map[rel_id] = rel
        
        # Process document blocks (paragraphs and tables) in order using the same iterator as docx2md
        for block in self._iter_block_items(doc):
            if isinstance(block, Paragraph):
                html_para = self._convert_paragraph_to_html_improved(block, image_dir, relationship_map)
                if html_para:
                    html_content.append(html_para)
            elif isinstance(block, Table):
                html_table = self._convert_table_to_html(block, image_dir, relationship_map)
                if html_table:
                    html_content.append(html_table)
        
        # Generate the final HTML document
        html_doc = self._create_html_document(title, '\n'.join(html_content))
        
        # Write the HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_doc)
            
        # Print statistics
        print(f"Converted document saved to: {output_path}")
        if include_images:
            print(f"Images saved to: {image_dir}")
            print(f"Total images extracted: {self.stats['images']}")
        print(f"Math formulas converted: {self.stats['inline_math'] + self.stats['display_math']}")
        print(f"  - Inline formulas: {self.stats['inline_math']}")
        print(f"  - Display formulas: {self.stats['display_math']}")
        
        return output_path

    def _iter_block_items(self, parent):
        """
        Generator to iterate through all block items (paragraphs and tables) in order.
        This ensures we process elements in the same order as they appear in the document.
        """
        if isinstance(parent, _Document):
            parent_elm = parent.element.body
        elif isinstance(parent, _Cell):
            parent_elm = parent._tc
        else:
            raise ValueError("Expected a Document or a Cell")
            
        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    def _find_omath_elements(self, element):
        """Find all oMath elements in the given XML element."""
        if hasattr(element, 'iter'):
            return [e for e in element.iter() if e.tag == f"{self.ns_math}oMath"]
        return []
    
    def _find_drawing_elements(self, element):
        """Find all drawing elements in the given XML element."""
        if hasattr(element, 'iter'):
            return [e for e in element.iter() if e.tag == f"{self.ns_w}drawing"]
        return []
    
    def _find_blip_elements(self, element):
        """Find all blip elements (images) in the given XML element."""
        if hasattr(element, 'iter'):
            return [e for e in element.iter() if e.tag == f"{self.ns_a}blip"]
        return []
        
    def _find_embedded_image_ids(self, element):
        """Find embedded image IDs in an element."""
        image_ids = []
        
        for child in element.iter():
            if child.tag.endswith('}drawing'):
                # Look for blip elements that contain image references
                for subchild in child.iter():
                    if subchild.tag.endswith('}blip'):
                        # Get the embed attribute which is the relationship ID
                        for key, value in subchild.attrib.items():
                            if key.endswith('}embed'):
                                image_ids.append(value)
        
        return image_ids
    
    def _convert_paragraph_to_html_improved(self, paragraph, image_dir, relationship_map):
        """
        Convert a docx paragraph to HTML with improved ordering of elements.
        
        Args:
            paragraph: A docx paragraph object.
            image_dir (str): Directory to save extracted images.
            relationship_map (dict): Map of relationship IDs to relationships.
            
        Returns:
            str: HTML representation of the paragraph.
        """
        # Skip empty paragraphs with no special elements
        if not paragraph.text.strip() and not self._has_math_or_images(paragraph):
            return ""
        
        # Determine paragraph style for HTML mapping
        style_name = paragraph.style.name.lower() if paragraph.style.name else "normal"
        
        # Map common Word styles to HTML elements
        style_mapping = {
            "heading 1": "h1",
            "heading 2": "h2",
            "heading 3": "h3",
            "heading 4": "h4",
            "heading 5": "h5",
            "heading 6": "h6",
            "title": "h1",
            "subtitle": "h2",
        }
        
        html_tag = style_mapping.get(style_name, "p")
        
        # For heading styles, use a simplified approach
        if html_tag.startswith('h') and paragraph.text.strip():
            return f"<{html_tag}>{escape(paragraph.text.strip())}</{html_tag}>"
        
        # Process the paragraph element recursively to maintain proper order
        content = self._process_paragraph_element_recursively(paragraph._element, image_dir, relationship_map)
        
        # Wrap the content with the appropriate HTML tag if not empty
        if content:
            return f"<{html_tag}>{content}</{html_tag}>"
        else:
            return ""
    
    def _process_paragraph_element_recursively(self, element, image_dir, relationship_map):
        """
        Process paragraph element recursively, maintaining the proper order of text, math, and images.
        
        Args:
            element: XML element to process.
            image_dir (str): Directory to save images.
            relationship_map (dict): Map of relationship IDs to relationships.
            
        Returns:
            str: HTML content with properly ordered elements.
        """
        result_parts = []
        
        # 处理段落级别的图片，确保不在运行级别重复处理
        # 我们只处理直接属于段落的图片，而不是嵌套在run中的图片
        # 这样可以避免重复处理同一图片
        if element.tag.endswith('}p'):  # 只在段落元素上处理图片
            for child in element:
                # 只检查段落的直接子元素中的图片
                if child.tag.endswith('}r'):
                    continue  # 跳过运行元素，这些将在 _process_run_element 中处理
                    
                image_ids = self._find_embedded_image_ids(child)
                for image_id in image_ids:
                    if image_id not in self.processed_image_ids and image_id in relationship_map:
                        rel = relationship_map[image_id]
                        image_filename = self._save_image(rel, image_dir, image_id)
                        if image_filename:
                            img_rel_path = f"{os.path.basename(image_dir)}/{image_filename}"
                            result_parts.append(f'<img src="{img_rel_path}" alt="Image" />')
                            self.stats['images'] += 1
                            self.processed_image_ids.add(image_id)
        
        # Process all child elements in order
        for child in element:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            if tag == 'r':  # Run element
                run_content = self._process_run_element(child, image_dir, relationship_map)
                if run_content:
                    result_parts.append(run_content)
                    
            elif tag == 'oMath':  # Math element
                latex_formula = self.omml_converter.omml_to_latex(child)
                if latex_formula and latex_formula != "[Math Formula]":
                    # 预处理LaTeX公式，确保大括号和特殊符号正确处理
                    latex_formula = self._preprocess_latex(latex_formula)
                    
                    # Determine if it's inline or display math
                    if '\n' in latex_formula or latex_formula.strip().startswith('\\begin{') or len(latex_formula) > 50 or \
                       any(cmd in latex_formula for cmd in ['\\frac', '\\sum', '\\int', '\\prod']):
                        # Display math
                        math_html = f"\\[{latex_formula}\\]"
                        self.stats['display_math'] += 1
                    else:
                        # Inline math
                        math_html = f"\\({latex_formula}\\)"
                        self.stats['inline_math'] += 1
                    
                    result_parts.append(math_html)
                    
            else:
                # Recursively process other elements
                child_content = self._process_paragraph_element_recursively(child, image_dir, relationship_map)
                if child_content:
                    result_parts.append(child_content)
        
        return ''.join(result_parts)
    
    def _process_run_element(self, run_element, image_dir, relationship_map):
        """
        Process a run element to extract text, math, and images in proper order.
        
        Args:
            run_element: XML element representing a run.
            image_dir (str): Directory to save images.
            relationship_map (dict): Map of relationship IDs to relationships.
            
        Returns:
            str: HTML representation of the run content.
        """
        result_parts = []
        
        # 只处理尚未处理过的图片
        image_ids = self._find_embedded_image_ids(run_element)
        for image_id in image_ids:
            # 检查图片ID是否已处理过
            if image_id not in self.processed_image_ids and image_id in relationship_map:
                rel = relationship_map[image_id]
                image_filename = self._save_image(rel, image_dir, image_id)
                if image_filename:
                    img_rel_path = f"{os.path.basename(image_dir)}/{image_filename}"
                    result_parts.append(f'<img src="{img_rel_path}" alt="Image" />')
                    self.stats['images'] += 1
                    self.processed_image_ids.add(image_id)  # 标记图片ID为已处理
        
        # Process all child elements in order
        for child in run_element:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            if tag == 't':  # Text element
                if child.text:
                    # Apply text formatting
                    content = escape(child.text)
                    
                    # Get the run properties (rPr) to determine formatting
                    run_props = run_element.find('.//{' + self.ns_w + '}rPr')
                    if run_props is not None:
                        # Bold
                        if run_props.find('.//{' + self.ns_w + '}b') is not None:
                            content = f"<strong>{content}</strong>"
                        
                        # Italic
                        if run_props.find('.//{' + self.ns_w + '}i') is not None:
                            content = f"<em>{content}</em>"
                        
                        # Underline
                        if run_props.find('.//{' + self.ns_w + '}u') is not None:
                            content = f"<u>{content}</u>"
                        
                        # Strike
                        if run_props.find('.//{' + self.ns_w + '}strike') is not None:
                            content = f"<s>{content}</s>"
                        
                        # Superscript
                        if run_props.find('.//{' + self.ns_w + '}vertAlign[@w:val="superscript"]') is not None:
                            content = f"<sup>{content}</sup>"
                        
                        # Subscript
                        if run_props.find('.//{' + self.ns_w + '}vertAlign[@w:val="subscript"]') is not None:
                            content = f"<sub>{content}</sub>"
                    
                    result_parts.append(content)
                    
            elif tag == 'oMath':  # Math element in run
                latex_formula = self.omml_converter.omml_to_latex(child)
                if latex_formula and latex_formula != "[Math Formula]":
                    # 预处理LaTeX公式，确保大括号和特殊符号正确处理
                    latex_formula = self._preprocess_latex(latex_formula)
                    
                    # For math in runs, generally use inline format
                    math_html = f"\\({latex_formula}\\)"
                    self.stats['inline_math'] += 1
                    result_parts.append(math_html)
                    
            else:
                # Recursively process other elements
                child_content = self._process_run_element(child, image_dir, relationship_map)
                if child_content:
                    result_parts.append(child_content)
        
        return ''.join(result_parts)
    
    def _preprocess_latex(self, latex):
        """
        预处理LaTeX公式，确保大括号和特殊符号正确处理。
        
        Args:
            latex (str): 原始LaTeX公式
            
        Returns:
            str: 处理后的LaTeX公式
        """
        if not latex or latex == "[Math Formula]":
            return latex
            
        # 移除对掩码矩阵（2-9）公式的特殊处理，直接显示原始公式

        # 3. 修复常见的错误符号
        # 修复无穷大符号
        latex = latex.replace('−\\infty', '-\\infty')
        latex = latex.replace('−∞', '-\\infty')
        latex = latex.replace('−\infty', '-\\infty')
        
        # 4. 确保 \left 和 \right 配对
        left_count = latex.count('\\left')
        right_count = latex.count('\\right')
        if left_count > right_count:
            # 添加缺少的 \right.
            diff = left_count - right_count
            latex += ' ' + '\\right. ' * diff
        
        # 5. 检查并修复数学表达式中的空格问题
        # 这部分使用简单的替换而不是正则表达式
        for symbol in ['\\geq', '\\leq', '>', '<', '=']:
            # 简单替换常见模式，避免使用正则表达式
            latex = latex.replace(f'i{symbol}j', f'i {symbol} j')
            latex = latex.replace(f'x{symbol}y', f'x {symbol} y')
            latex = latex.replace(f'a{symbol}b', f'a {symbol} b')
            latex = latex.replace(f'n{symbol}m', f'n {symbol} m')
        
        # 6. Remove formula numbering
        latex = self._remove_formula_numbering(latex)
        
        # 7. 确保数学环境正确闭合
        if '\\begin{' in latex:
            for env in ['cases', 'align', 'matrix', 'pmatrix', 'bmatrix']:
                if f'\\begin{{{env}}}' in latex and f'\\end{{{env}}}' not in latex:
                    latex += f'\\end{{{env}}}'
        
        return latex
    
    def _remove_formula_numbering(self, latex_text):
        """
        Removes formula numbering like (2-9) from a LaTeX string.
        
        Args:
            latex_text (str): The LaTeX string.
            
        Returns:
            str: LaTeX string with numbering removed.
        """
        # Pattern to find formula numbers like (2-9), (1), etc., at the end of the string.
        # Handles spaces and different dash characters. Also handles \left( \right).
        patterns_to_remove = [
            r'\\left\(\s*\d+\s*[-−–—]\s*\d+\s*\s*\\right\)\s*$',  # e.g., \left(2-1\right)
            r'\(\s*\d+\s*[-−–—]\s*\d+\s*\)\s*$',  # e.g., (2-1)
            r'\\left\(\s*\d+\s*\\right\)\s*$',  # e.g., \left(1\right)
            r'\(\s*\d+\s*\)\s*$',  # e.g., (1)
        ]
        
        processed_latex = latex_text
        for pattern in patterns_to_remove:
            processed_latex = re.sub(pattern, '', processed_latex).strip()
            
        return processed_latex
    
    def _save_image(self, rel, image_dir, image_id):
        """
        Save image from relationship and return the filename.
        
        Args:
            rel: Relationship object containing the image.
            image_dir (str): Directory to save the image.
            image_id (str): Unique ID for the image.
            
        Returns:
            str: Filename of the saved image.
        """
        try:
            image_bytes = rel.target_part.blob
            image_ext = os.path.splitext(rel.target_ref)[-1]
            if not image_ext:
                image_ext = '.png'  # Default extension if none found
                
            image_filename = f"image_{image_id}{image_ext}"
            image_path = os.path.join(image_dir, image_filename)
            
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
                
            return image_filename
        except Exception as e:
            print(f"Error extracting image: {e}")
            return None
    
    def _has_math_or_images(self, paragraph):
        """Check if a paragraph contains math elements or images."""
        # Check for math elements
        math_elements = self._find_omath_elements(paragraph._element)
        if math_elements:
            return True
        
        # Check for images
        drawing_elements = self._find_drawing_elements(paragraph._element)
        if drawing_elements:
            return True
        
        return False
    
    def _convert_table_to_html(self, table, image_dir=None, relationship_map=None):
        """
        Convert a docx table to HTML, preserving content order.
        
        Args:
            table: A docx table object.
            image_dir (str, optional): Directory to save extracted images.
            relationship_map (dict, optional): Map of relationship IDs to relationships.
            
        Returns:
            str: HTML representation of the table.
        """
        html_rows = []
        
        for row in table.rows:
            html_cells = []
            
            for cell in row.cells:
                cell_content = []
                
                # Process each paragraph in the cell using our improved conversion
                for paragraph in cell.paragraphs:
                    para_html = self._convert_paragraph_to_html_improved(paragraph, image_dir, relationship_map)
                    if para_html:
                        # Remove the paragraph tags for better table formatting
                        para_html = para_html.replace('<p>', '').replace('</p>', '<br/>')
                        cell_content.append(para_html)
                
                # Remove the last <br/> if present
                if cell_content and cell_content[-1].endswith('<br/>'):
                    cell_content[-1] = cell_content[-1][:-5]
                
                cell_html = f"<td>{''.join(cell_content)}</td>"
                html_cells.append(cell_html)
            
            html_rows.append(f"<tr>{''.join(html_cells)}</tr>")
        
        return f"<table border='1'>{''.join(html_rows)}</table>"
    
    def _wrap_latex_in_mathjax(self, latex):
        """
        Wrap a LaTeX formula in MathJax delimiters for rendering in HTML.
        
        Args:
            latex (str): LaTeX formula string.
            
        Returns:
            str: HTML with LaTeX wrapped for MathJax rendering.
        """
        # Determine if this is an inline or display math formula
        if '\n' in latex or latex.strip().startswith('\\begin{') or len(latex) > 50 or \
           any(cmd in latex for cmd in ['\\frac', '\\sum', '\\int', '\\prod']):
            # Display math (centered, larger equation)
            self.stats['display_math'] += 1
            return f"\\[{latex}\\]"
        else:
            # Inline math
            self.stats['inline_math'] += 1
            return f"\\({latex}\\)"
    
    def _create_html_document(self, title, content):
        """
        Create a complete HTML document with necessary headers and MathJax integration.
        
        Args:
            title (str): Title for the HTML document.
            content (str): HTML content to include in the body.
            
        Returns:
            str: Complete HTML document.
        """
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        td, th {{
            border: 1px solid #ddd;
            padding: 8px;
        }}
        img {{
            max-width: 100%;
        }}
        .math-display {{
            overflow-x: auto;
            margin: 1em 0;
        }}
    </style>
    <!-- MathJax configuration -->
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
    <script src="{self.mathjax_url}" id="MathJax-script" async></script>
</head>
<body>
    <h1>{escape(title)}</h1>
    {content}
</body>
</html>
"""
        return html


def convert_docx_to_html(docx_path, output_path=None, title=None, include_images=True):
    """
    Convenience function to convert a DOCX file to HTML with math formula support.
    
    Args:
        docx_path (str): Path to the input DOCX file.
        output_path (str, optional): Path for the output HTML file. If None, uses the same path as docx_path but with .html extension.
        title (str, optional): Title for the HTML document. If None, uses the filename.
        include_images (bool): Whether to extract and include images from the DOCX file.
        
    Returns:
        str: Path to the generated HTML file.
    """
    converter = Docx2HtmlConverter()
    return converter.convert_docx_to_html(docx_path, output_path, title, include_images)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python docx2html.py input.docx [output.html] [--no-images]")
        sys.exit(1)
    
    docx_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
    include_images = '--no-images' not in sys.argv
    
    output_file = convert_docx_to_html(docx_path, output_path, include_images=include_images)
    print(f"Converted document saved to: {output_file}") 