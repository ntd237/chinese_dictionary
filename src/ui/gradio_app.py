"""
Giao diện Gradio cho ứng dụng tra cứu từ Hán Việt
===============================================

Tạo giao diện web tương tác cho phép người dùng:
- Nhập từ/cụm từ tiếng Trung (chữ Hán)
- Xem phiên âm Pinyin với dấu thanh
- Xem bản dịch nghĩa tiếng Việt
- Xử lý batch input và hiển thị kết quả dạng bảng
"""

import logging
import gradio as gr
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
import sys
import os

# Thêm src vào Python path để import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pinyin_converter import get_converter, PinyinConverter
from api_handler import get_translation_handler, TranslationAPIHandler

# Cấu hình logging
logger = logging.getLogger(__name__)


class HanVietApp:
    """
    Class chính cho ứng dụng Gradio tra cứu từ Hán Việt.
    """

    def __init__(self):
        """Khởi tạo app với các components cần thiết."""
        self.pinyin_converter = get_converter()
        self.translation_handler = get_translation_handler()
        
        # Cấu hình UI
        self.title = "🔤 Từ điển Hán Việt - Pinyin & Dịch nghĩa"
        self.description = """
        **Tra cứu từ Hán Việt với phiên âm Pinyin chuẩn và dịch nghĩa tiếng Việt**
        
        ✨ **Tính năng:**
        - 🎯 Chuyển đổi chữ Hán sang Pinyin có dấu thanh
        - 🌏 Dịch nghĩa từ tiếng Trung sang tiếng Việt
        - 📝 Hỗ trợ từ đơn và cụm từ
        - ⚡ Xử lý nhanh với cache thông minh
        
        📌 **Cách sử dụng:** Nhập chữ Hán vào ô bên dưới và nhấn "Tra cứu"
        """
        
    def process_single_word(
        self, 
        chinese_input: str, 
        include_tone: bool = True,
        show_analysis: bool = False
    ) -> Tuple[str, str, str, str]:
        """
        Xử lý tra cứu cho một từ/cụm từ.

        Args:
            chinese_input (str): Input chữ Hán
            include_tone (bool): Bao gồm dấu thanh trong Pinyin
            show_analysis (bool): Hiển thị phân tích chi tiết

        Returns:
            Tuple[str, str, str, str]: (pinyin, translation, analysis, status)
        """
        if not chinese_input or not chinese_input.strip():
            return "", "", "", "❌ Vui lòng nhập chữ Hán cần tra cứu"

        chinese_text = chinese_input.strip()
        
        try:
            # Chuyển đổi Pinyin
            logger.info(f"Đang xử lý: '{chinese_text}'")
            pinyin_result = self.pinyin_converter.convert_to_pinyin(
                chinese_text, 
                with_tone=include_tone
            )
            
            # Dịch nghĩa
            success, translation, endpoint = self.translation_handler.translate_text(chinese_text)
            
            if not success:
                translation = f"[Không thể dịch: {translation}]"
                status = f"⚠️ Pinyin: OK, Dịch: Lỗi (endpoint: {endpoint})"
            else:
                status = f"✅ Thành công (dịch via: {endpoint})"
            
            # Phân tích chi tiết (nếu được yêu cầu và là ký tự đơn)
            analysis = ""
            if show_analysis and len(chinese_text) == 1:
                char_analysis = self.pinyin_converter.analyze_character(chinese_text)
                if "error" not in char_analysis:
                    analysis = f"""
**Phân tích chi tiết cho '{chinese_text}':**
- Pinyin có dấu: {char_analysis.get('pinyin_tone', 'N/A')}
- Pinyin không dấu: {char_analysis.get('pinyin_no_tone', 'N/A')}
- Số thanh: {char_analysis.get('tone_number', 'N/A')}
- Là chữ Hán: {char_analysis.get('is_chinese', 'N/A')}
                    """.strip()
            
            return pinyin_result, translation, analysis, status
            
        except Exception as e:
            logger.error(f"Lỗi xử lý '{chinese_text}': {e}")
            return "", f"[Lỗi: {e}]", "", f"❌ Lỗi xử lý: {e}"

    def process_batch_words(
        self, 
        batch_input: str, 
        include_tone: bool = True
    ) -> pd.DataFrame:
        """
        Xử lý batch nhiều từ.

        Args:
            batch_input (str): Input nhiều từ, mỗi từ một dòng
            include_tone (bool): Bao gồm dấu thanh

        Returns:
            pd.DataFrame: Kết quả dạng bảng
        """
        if not batch_input or not batch_input.strip():
            return pd.DataFrame({"Thông báo": ["Vui lòng nhập danh sách từ cần tra cứu (mỗi từ một dòng)"]})

        # Tách từng dòng
        lines = [line.strip() for line in batch_input.strip().split('\n') if line.strip()]
        
        if not lines:
            return pd.DataFrame({"Thông báo": ["Không có từ hợp lệ để xử lý"]})

        logger.info(f"Xử lý batch {len(lines)} từ")
        
        # Xử lý Pinyin
        pinyin_results = self.pinyin_converter.convert_word_list(lines, with_tone=include_tone)
        
        # Xử lý dịch
        translation_results = self.translation_handler.translate_batch(lines)
        
        # Kết hợp kết quả
        data = []
        for i, word in enumerate(lines):
            pinyin = pinyin_results[i]["pinyin"] if i < len(pinyin_results) else "[Lỗi]"
            
            translation_info = next((r for r in translation_results if r["original"] == word), None)
            if translation_info and translation_info["success"]:
                translation = translation_info["translation"]
                status = f"✅ ({translation_info['endpoint']})"
            else:
                translation = f"[Lỗi: {translation_info['error'] if translation_info else 'Không tìm thấy'}]"
                status = "❌ Lỗi"
            
            data.append({
                "STT": i + 1,
                "Chữ Hán": word,
                "Pinyin": pinyin,
                "Nghĩa tiếng Việt": translation,
                "Trạng thái": status
            })
        
        df = pd.DataFrame(data)
        logger.info(f"Hoàn thành batch: {len([d for d in data if d['Trạng thái'].startswith('✅')])}/{len(data)} thành công")
        
        return df

    def get_cache_info(self) -> Tuple[str, str]:
        """
        Lấy thông tin cache.

        Returns:
            Tuple[str, str]: (pinyin_info, translation_info)
        """
        try:
            # Translation cache stats
            trans_stats = self.translation_handler.get_cache_stats()
            trans_info = f"""
**Cache dịch thuật:**
- Số entries: {trans_stats['total_entries']}
- Kích thước file: {trans_stats['cache_file_size_bytes']} bytes
- File tồn tại: {'✅' if trans_stats['cache_file_exists'] else '❌'}
            """.strip()
            
            # Pinyin info (không có cache riêng, nhưng có thể hiển thị stats khác)
            pinyin_info = f"""
**Thông tin Pinyin converter:**
- Sử dụng thư viện: pypinyin
- Style mặc định: TONE (có dấu thanh)
- Hỗ trợ: Chữ Hán simplified & traditional
            """.strip()
            
            return pinyin_info, trans_info
            
        except Exception as e:
            logger.error(f"Lỗi lấy cache info: {e}")
            return f"Lỗi: {e}", f"Lỗi: {e}"

    def clear_translation_cache(self) -> str:
        """
        Xóa cache dịch thuật.

        Returns:
            str: Thông báo kết quả
        """
        try:
            cleared_count = self.translation_handler.clear_cache()
            return f"✅ Đã xóa {cleared_count} entries khỏi cache dịch thuật"
        except Exception as e:
            logger.error(f"Lỗi xóa cache: {e}")
            return f"❌ Lỗi xóa cache: {e}"


def create_interface() -> gr.Interface:
    """
    Tạo giao diện Gradio chính.

    Returns:
        gr.Interface: Gradio interface object
    """
    app = HanVietApp()
    
    # Custom CSS cho giao diện đẹp hơn
    custom_css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: auto !important;
    }
    .tab-nav {
        font-size: 16px !important;
    }
    .output-markdown {
        font-size: 14px !important;
    }
    """
    
    with gr.Blocks(
        title=app.title,
        css=custom_css,
        theme=gr.themes.Soft()
    ) as interface:
        
        # Header
        gr.Markdown(f"# {app.title}")
        gr.Markdown(app.description)
        
        with gr.Tabs():
            # Tab 1: Tra cứu đơn
            with gr.TabItem("🔍 Tra cứu từ đơn"):
                with gr.Row():
                    with gr.Column(scale=2):
                        chinese_input = gr.Textbox(
                            label="Nhập chữ Hán",
                            placeholder="Ví dụ: 你好, 中国, 学习...",
                            lines=2,
                            max_lines=3
                        )
                        
                        with gr.Row():
                            include_tone = gr.Checkbox(
                                label="Bao gồm dấu thanh trong Pinyin", 
                                value=True
                            )
                            show_analysis = gr.Checkbox(
                                label="Hiển thị phân tích chi tiết (chỉ cho ký tự đơn)",
                                value=False
                            )
                        
                        lookup_btn = gr.Button("🔍 Tra cứu", variant="primary", size="lg")
                    
                    with gr.Column(scale=3):
                        pinyin_output = gr.Textbox(
                            label="📝 Phiên âm Pinyin",
                            interactive=False,
                            lines=2
                        )
                        
                        translation_output = gr.Textbox(
                            label="🌏 Nghĩa tiếng Việt", 
                            interactive=False,
                            lines=3
                        )
                        
                        analysis_output = gr.Markdown(
                            label="🔬 Phân tích chi tiết",
                            visible=True
                        )
                        
                        status_output = gr.Textbox(
                            label="📊 Trạng thái",
                            interactive=False,
                            lines=1
                        )
                
                # Kết nối events
                lookup_btn.click(
                    fn=app.process_single_word,
                    inputs=[chinese_input, include_tone, show_analysis],
                    outputs=[pinyin_output, translation_output, analysis_output, status_output]
                )
                
                # Enter key support
                chinese_input.submit(
                    fn=app.process_single_word,
                    inputs=[chinese_input, include_tone, show_analysis],
                    outputs=[pinyin_output, translation_output, analysis_output, status_output]
                )
            
            # Tab 2: Tra cứu batch
            with gr.TabItem("📋 Tra cứu nhiều từ"):
                with gr.Row():
                    with gr.Column(scale=1):
                        batch_input = gr.Textbox(
                            label="Danh sách từ cần tra cứu",
                            placeholder="Nhập mỗi từ/cụm từ trên một dòng:\n你好\n中国\n学习\n...",
                            lines=10,
                            max_lines=15
                        )
                        
                        batch_tone = gr.Checkbox(
                            label="Bao gồm dấu thanh trong Pinyin",
                            value=True
                        )
                        
                        batch_btn = gr.Button("📋 Tra cứu tất cả", variant="primary", size="lg")
                    
                    with gr.Column(scale=2):
                        batch_output = gr.DataFrame(
                            label="📊 Kết quả tra cứu",
                            headers=["STT", "Chữ Hán", "Pinyin", "Nghĩa tiếng Việt", "Trạng thái"],
                            datatype=["number", "str", "str", "str", "str"],
                            interactive=False
                        )
                
                batch_btn.click(
                    fn=app.process_batch_words,
                    inputs=[batch_input, batch_tone],
                    outputs=[batch_output]
                )
            
            # Tab 3: Thông tin & Cài đặt
            with gr.TabItem("⚙️ Thông tin & Cache"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 📋 Thông tin hệ thống")
                        
                        cache_btn = gr.Button("🔄 Làm mới thông tin cache")
                        
                        pinyin_info = gr.Markdown(
                            label="📝 Pinyin Converter",
                            value="Click 'Làm mới thông tin cache' để xem"
                        )
                        
                        translation_info = gr.Markdown(
                            label="🌏 Translation Handler", 
                            value="Click 'Làm mới thông tin cache' để xem"
                        )
                    
                    with gr.Column():
                        gr.Markdown("### 🗑️ Quản lý Cache")
                        
                        clear_cache_btn = gr.Button("🗑️ Xóa cache dịch thuật", variant="secondary")
                        
                        cache_status = gr.Textbox(
                            label="Trạng thái",
                            value="Sẵn sàng",
                            interactive=False
                        )
                        
                        gr.Markdown("""
                        ### ℹ️ Hướng dẫn sử dụng
                        
                        1. **Tra cứu đơn**: Nhập một từ/cụm từ để xem Pinyin và nghĩa
                        2. **Tra cứu batch**: Nhập nhiều từ (mỗi dòng một từ) để xử lý hàng loạt
                        3. **Cache**: Hệ thống tự động lưu kết quả dịch để tăng tốc lần tra cứu tiếp theo
                        4. **Dấu thanh**: Bạn có thể chọn hiển thị Pinyin có hoặc không có dấu thanh
                        
                        **API sử dụng**: LibreTranslate (miễn phí), pypinyin
                        """)
                
                # Kết nối events
                cache_btn.click(
                    fn=app.get_cache_info,
                    inputs=[],
                    outputs=[pinyin_info, translation_info]
                )
                
                clear_cache_btn.click(
                    fn=app.clear_translation_cache,
                    inputs=[],
                    outputs=[cache_status]
                )
        
        # Footer
        gr.Markdown("""
        ---
        **🔤 Từ điển Hán Việt** | Được phát triển bằng Python, Gradio, pypinyin & LibreTranslate | 
        📧 Báo lỗi hoặc góp ý qua Issues
        """)
    
    return interface


def launch_app(
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    share: bool = False,
    debug: bool = False
) -> None:
    """
    Khởi chạy ứng dụng Gradio.

    Args:
        server_name (str): Địa chỉ server (mặc định localhost)
        server_port (int): Port (mặc định 7860)
        share (bool): Tạo public link không (mặc định False)
        debug (bool): Chế độ debug (mặc định False)
    """
    logger.info("Đang khởi động ứng dụng Gradio...")
    
    interface = create_interface()
    
    interface.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        debug=debug,
        show_error=True,
        quiet=not debug
    )


if __name__ == "__main__":
    # Cấu hình logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Khởi chạy với cấu hình mặc định
    launch_app(debug=True)
