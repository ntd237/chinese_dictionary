"""
Module chuyển đổi chữ Hán sang phiên âm Pinyin
============================================

Sử dụng thư viện pypinyin để chuyển đổi chữ Hán (simplified/traditional)
sang phiên âm Pinyin chuẩn với dấu thanh (tones).

Tính năng:
- Hỗ trợ chữ Hán đơn lẻ và từ ghép
- Phiên âm Pinyin với dấu thanh đầy đủ
- Xử lý lỗi và fallback cho ký tự không nhận dạng được
"""

import logging
from typing import List, Optional, Dict, Any
from pypinyin import lazy_pinyin, Style
import pypinyin

# Cấu hình logging
logger = logging.getLogger(__name__)


class PinyinConverter:
    """
    Class chuyển đổi chữ Hán sang Pinyin với các tùy chọn linh hoạt.
    """

    def __init__(self):
        """Khởi tạo converter với cấu hình mặc định."""
        # Cấu hình pypinyin để sử dụng dấu thanh (tones)
        self.default_style = Style.TONE
        self.errors = "default"  # Xử lý lỗi: 'default', 'ignore', 'strict'

    def convert_to_pinyin(
        self, 
        chinese_text: str, 
        with_tone: bool = True,
        separator: str = " "
    ) -> str:
        """
        Chuyển đổi văn bản tiếng Trung sang Pinyin.

        Args:
            chinese_text (str): Văn bản chữ Hán cần chuyển đổi
            with_tone (bool): Có bao gồm dấu thanh hay không (mặc định True)
            separator (str): Ký tự phân cách giữa các âm tiết (mặc định " ")

        Returns:
            str: Chuỗi Pinyin đã chuyển đổi

        Example:
            >>> converter = PinyinConverter()
            >>> converter.convert_to_pinyin("你好")
            'nǐ hǎo'
            >>> converter.convert_to_pinyin("中国", with_tone=False)
            'zhong guo'
        """
        if not chinese_text or not chinese_text.strip():
            logger.warning("Input text trống hoặc chỉ chứa khoảng trắng")
            return ""

        try:
            # Chọn style dựa trên tùy chọn dấu thanh
            style = Style.TONE if with_tone else Style.NORMAL
            
            # Chuyển đổi sang Pinyin
            pinyin_list = lazy_pinyin(
                chinese_text.strip(),
                style=style,
                errors=self.errors
            )
            
            # Kết hợp thành chuỗi với separator
            result = separator.join(pinyin_list)
            
            logger.info(f"Chuyển đổi thành công: '{chinese_text}' -> '{result}'")
            return result

        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi Pinyin: {e}")
            return f"[Lỗi chuyển đổi: {chinese_text}]"

    def convert_word_list(
        self, 
        word_list: List[str], 
        with_tone: bool = True
    ) -> List[Dict[str, str]]:
        """
        Chuyển đổi danh sách các từ thành Pinyin với metadata.

        Args:
            word_list (List[str]): Danh sách các từ tiếng Trung
            with_tone (bool): Có bao gồm dấu thanh hay không

        Returns:
            List[Dict[str, str]]: Danh sách dict chứa từ gốc và Pinyin

        Example:
            >>> converter = PinyinConverter()
            >>> converter.convert_word_list(["人", "中国"])
            [
                {"original": "人", "pinyin": "rén"},
                {"original": "中国", "pinyin": "zhōng guó"}
            ]
        """
        results = []
        
        for word in word_list:
            if not word.strip():
                continue
                
            pinyin_result = self.convert_to_pinyin(word.strip(), with_tone=with_tone)
            
            results.append({
                "original": word.strip(),
                "pinyin": pinyin_result,
                "has_tone": with_tone
            })
        
        logger.info(f"Chuyển đổi batch {len(results)} từ thành công")
        return results

    def get_tone_numbers(self, chinese_text: str) -> List[int]:
        """
        Lấy thông tin về số thanh (1-5) của từng âm tiết.

        Args:
            chinese_text (str): Văn bản chữ Hán

        Returns:
            List[int]: Danh sách số thanh (1-5, 5 = không dấu)

        Example:
            >>> converter = PinyinConverter()
            >>> converter.get_tone_numbers("你好")
            [3, 3]  # nǐ (thanh 3), hǎo (thanh 3)
        """
        if not chinese_text or not chinese_text.strip():
            return []

        try:
            # Sử dụng Style.TONE3 để lấy số thanh
            pinyin_with_numbers = lazy_pinyin(
                chinese_text.strip(),
                style=Style.TONE3,
                errors=self.errors
            )
            
            tone_numbers = []
            for syllable in pinyin_with_numbers:
                # Trích xuất số thanh từ cuối âm tiết
                if syllable[-1].isdigit():
                    tone_numbers.append(int(syllable[-1]))
                else:
                    tone_numbers.append(5)  # Không dấu (neutral tone)
            
            return tone_numbers

        except Exception as e:
            logger.error(f"Lỗi khi lấy tone numbers: {e}")
            return []

    def analyze_character(self, character: str) -> Dict[str, Any]:
        """
        Phân tích chi tiết một ký tự Hán.

        Args:
            character (str): Một ký tự Hán đơn

        Returns:
            Dict[str, Any]: Thông tin chi tiết về ký tự

        Example:
            >>> converter = PinyinConverter()
            >>> converter.analyze_character("中")
            {
                "character": "中",
                "pinyin_tone": "zhōng",
                "pinyin_no_tone": "zhong",
                "tone_number": 1,
                "is_chinese": True
            }
        """
        if not character or len(character) != 1:
            return {
                "character": character,
                "error": "Input phải là một ký tự đơn"
            }

        try:
            # Kiểm tra có phải chữ Hán không
            is_chinese = '\u4e00' <= character <= '\u9fff'
            
            if not is_chinese:
                return {
                    "character": character,
                    "is_chinese": False,
                    "error": "Không phải ký tự chữ Hán"
                }

            # Lấy thông tin Pinyin
            pinyin_tone = self.convert_to_pinyin(character, with_tone=True)
            pinyin_no_tone = self.convert_to_pinyin(character, with_tone=False)
            tone_numbers = self.get_tone_numbers(character)
            
            return {
                "character": character,
                "pinyin_tone": pinyin_tone,
                "pinyin_no_tone": pinyin_no_tone,
                "tone_number": tone_numbers[0] if tone_numbers else 5,
                "is_chinese": True
            }

        except Exception as e:
            logger.error(f"Lỗi khi phân tích ký tự '{character}': {e}")
            return {
                "character": character,
                "error": f"Lỗi phân tích: {e}"
            }


# Singleton instance để tái sử dụng
_converter_instance: Optional[PinyinConverter] = None


def get_converter() -> PinyinConverter:
    """
    Lấy singleton instance của PinyinConverter.
    
    Returns:
        PinyinConverter: Instance duy nhất của converter
    """
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = PinyinConverter()
    return _converter_instance


# Convenience functions
def quick_convert(chinese_text: str, with_tone: bool = True) -> str:
    """
    Hàm tiện ích để chuyển đổi nhanh chữ Hán sang Pinyin.
    
    Args:
        chinese_text (str): Văn bản chữ Hán
        with_tone (bool): Có dấu thanh hay không
        
    Returns:
        str: Pinyin đã chuyển đổi
    """
    converter = get_converter()
    return converter.convert_to_pinyin(chinese_text, with_tone=with_tone)


if __name__ == "__main__":
    # Test code
    logging.basicConfig(level=logging.INFO)
    
    converter = PinyinConverter()
    
    # Test cases
    test_words = ["你好", "中国", "人", "学习", "北京大学"]
    
    print("=== Test Pinyin Conversion ===")
    for word in test_words:
        pinyin = converter.convert_to_pinyin(word)
        print(f"{word} -> {pinyin}")
    
    print("\n=== Test Character Analysis ===")
    test_char = "中"
    analysis = converter.analyze_character(test_char)
    print(f"Phân tích ký tự '{test_char}': {analysis}")
    
    print("\n=== Test Batch Conversion ===")
    batch_results = converter.convert_word_list(["人民", "共和国"])
    for result in batch_results:
        print(f"{result['original']} -> {result['pinyin']}")
