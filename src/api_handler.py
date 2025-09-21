"""
Module xử lý API cho dịch nghĩa tiếng Trung - tiếng Việt
======================================================

Sử dụng LibreTranslate API (miễn phí, open-source) để dịch nghĩa
từ tiếng Trung sang tiếng Việt với retry logic và error handling.

Features:
- Gọi LibreTranslate API với fallback servers
- Retry logic với exponential backoff
- Cache kết quả để tối ưu performance
- Rate limiting để tránh spam API
"""

import logging
import time
import json
from typing import Dict, List, Optional, Tuple, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
import os
from urllib.parse import quote

# Cấu hình logging
logger = logging.getLogger(__name__)


class TranslationAPIHandler:
    """
    Handler cho việc dịch nghĩa sử dụng LibreTranslate API.
    """

    def __init__(self, cache_dir: str = "data"):
        """
        Khởi tạo API handler.

        Args:
            cache_dir (str): Thư mục lưu cache (mặc định "data")
        """
        # API endpoints miễn phí cho dịch thuật
        self.api_endpoints = [
            # MyMemory API - miễn phí, không cần key
            {
                "url": "https://api.mymemory.translated.net/get",
                "type": "mymemory",
                "description": "MyMemory Free API"
            },
            # LibreTranslate instances đang hoạt động
            {
                "url": "https://libretranslate.de/translate", 
                "type": "libretranslate",
                "description": "LibreTranslate Germany"
            },
            {
                "url": "https://translate.argosopentech.com/translate",
                "type": "libretranslate", 
                "description": "Argos Open Tech"
            },
            # Lingva Translate (Google Translate proxy)
            {
                "url": "https://lingva.ml/api/v1",
                "type": "lingva",
                "description": "Lingva Translate"
            }
        ]
        
        # Cấu hình API
        self.source_lang = "zh"  # Chinese
        self.target_lang = "vi"  # Vietnamese
        self.timeout = 10  # seconds
        self.max_retries = 3
        
        # Cache configuration
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "translation_cache.json")
        self.cache = self._load_cache()
        
        # Rate limiting (để tránh spam)
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds
        
        # Tạo session với retry strategy
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Tạo requests session với retry strategy.

        Returns:
            requests.Session: Session đã cấu hình
        """
        session = requests.Session()
        
        # Cấu hình retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'HanViet-Lookup-App/1.0'
        })
        
        return session

    def _load_cache(self) -> Dict[str, str]:
        """
        Load translation cache từ file.

        Returns:
            Dict[str, str]: Cache dictionary
        """
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} cached translations")
                return cache
        except Exception as e:
            logger.warning(f"Không thể load cache: {e}")
        
        return {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug("Cache saved successfully")
        except Exception as e:
            logger.error(f"Không thể save cache: {e}")

    def _get_cache_key(self, text: str) -> str:
        """
        Tạo cache key từ text.

        Args:
            text (str): Text cần hash

        Returns:
            str: Hash key
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _rate_limit(self) -> None:
        """Apply rate limiting."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _try_endpoint(self, text: str, endpoint_config: Dict[str, str]) -> Tuple[bool, str]:
        """
        Thử dịch với một endpoint cụ thể.
        
        Args:
            text (str): Text cần dịch
            endpoint_config (Dict[str, str]): Cấu hình endpoint
            
        Returns:
            Tuple[bool, str]: (success, translation_or_error)
        """
        endpoint_type = endpoint_config["type"]
        endpoint_url = endpoint_config["url"]
        
        try:
            if endpoint_type == "mymemory":
                return self._try_mymemory(text, endpoint_url)
            elif endpoint_type == "libretranslate":
                return self._try_libretranslate(text, endpoint_url)
            elif endpoint_type == "lingva":
                return self._try_lingva(text, endpoint_url)
            else:
                return False, f"Unknown endpoint type: {endpoint_type}"
                
        except Exception as e:
            return False, f"Error: {e}"

    def _try_mymemory(self, text: str, endpoint_url: str) -> Tuple[bool, str]:
        """Thử MyMemory API."""
        params = {
            "q": text,
            "langpair": f"{self.source_lang}|{self.target_lang}"
        }
        
        response = self.session.get(endpoint_url, params=params, timeout=self.timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("responseStatus") == 200:
                translation = data.get("responseData", {}).get("translatedText", "").strip()
                if translation and translation.lower() != text.lower():
                    return True, translation
                
        return False, f"MyMemory failed: {response.status_code}"

    def _try_libretranslate(self, text: str, endpoint_url: str) -> Tuple[bool, str]:
        """Thử LibreTranslate API."""
        data = {
            "q": text,
            "source": self.source_lang,
            "target": self.target_lang,
            "format": "text"
        }
        
        response = self.session.post(endpoint_url, json=data, timeout=self.timeout)
        
        if response.status_code == 200:
            result = response.json()
            if "translatedText" in result:
                translation = result["translatedText"].strip()
                if translation:
                    return True, translation
        
        return False, f"LibreTranslate failed: {response.status_code} - {response.text[:100]}"

    def _try_lingva(self, text: str, endpoint_url: str) -> Tuple[bool, str]:
        """Thử Lingva Translate API."""
        # Lingva format: /api/v1/{source}/{target}/{text}
        encoded_text = quote(text)
        url = f"{endpoint_url}/{self.source_lang}/{self.target_lang}/{encoded_text}"
        
        response = self.session.get(url, timeout=self.timeout)
        
        if response.status_code == 200:
            data = response.json()
            if "translation" in data:
                translation = data["translation"].strip()
                if translation:
                    return True, translation
        
        return False, f"Lingva failed: {response.status_code}"

    def _try_googletrans_fallback(self, text: str) -> Tuple[bool, str]:
        """
        Fallback cuối cùng sử dụng googletrans library.
        
        Args:
            text (str): Text cần dịch
            
        Returns:
            Tuple[bool, str]: (success, translation_or_error)
        """
        try:
            from googletrans import Translator
            
            translator = Translator()
            result = translator.translate(text, src=self.source_lang, dest=self.target_lang)
            
            if result and result.text and result.text.strip():
                translation = result.text.strip()
                # Kiểm tra không phải là text gốc
                if translation.lower() != text.lower():
                    return True, translation
                    
            return False, "No translation returned"
            
        except ImportError:
            return False, "googletrans not installed"
        except Exception as e:
            return False, f"googletrans error: {e}"

    def translate_text(self, chinese_text: str) -> Tuple[bool, str, str]:
        """
        Dịch văn bản từ tiếng Trung sang tiếng Việt.

        Args:
            chinese_text (str): Văn bản tiếng Trung cần dịch

        Returns:
            Tuple[bool, str, str]: (success, translation/error_message, used_endpoint)

        Example:
            >>> handler = TranslationAPIHandler()
            >>> success, result, endpoint = handler.translate_text("你好")
            >>> if success:
            ...     print(f"Dịch: {result}")
        """
        if not chinese_text or not chinese_text.strip():
            return False, "Văn bản đầu vào trống", "none"

        text = chinese_text.strip()
        cache_key = self._get_cache_key(text)

        # Kiểm tra cache trước
        if cache_key in self.cache:
            logger.info(f"Cache hit cho: '{text}'")
            return True, self.cache[cache_key], "cache"

        # Apply rate limiting
        self._rate_limit()

        # Thử từng endpoint
        for endpoint_config in self.api_endpoints:
            try:
                endpoint_url = endpoint_config["url"]
                endpoint_type = endpoint_config["type"]
                endpoint_desc = endpoint_config["description"]
                
                logger.info(f"Đang thử translate với: {endpoint_desc} ({endpoint_type})")
                
                success, translation = self._try_endpoint(text, endpoint_config)
                
                if success:
                    # Lưu vào cache
                    self.cache[cache_key] = translation
                    self._save_cache()
                    
                    logger.info(f"Dịch thành công: '{text}' -> '{translation}'")
                    return True, translation, endpoint_desc
                else:
                    logger.warning(f"Thất bại với {endpoint_desc}: {translation}")
                    continue

            except Exception as e:
                logger.error(f"Unexpected error với {endpoint_config['description']}: {e}")
                continue

        # Fallback cuối cùng: thử googletrans
        try:
            logger.info("Đang thử fallback với googletrans...")
            success, translation = self._try_googletrans_fallback(text)
            if success:
                # Lưu vào cache
                self.cache[cache_key] = translation
                self._save_cache()
                logger.info(f"Dịch thành công với fallback: '{text}' -> '{translation}'")
                return True, translation, "googletrans-fallback"
        except Exception as e:
            logger.error(f"Googletrans fallback failed: {e}")

        # Nếu tất cả endpoints đều fail
        error_msg = f"Không thể dịch '{text}' - tất cả API endpoints và fallback đều không khả dụng"
        logger.error(error_msg)
        return False, error_msg, "failed"

    def translate_batch(self, text_list: List[str]) -> List[Dict[str, Any]]:
        """
        Dịch batch nhiều văn bản.

        Args:
            text_list (List[str]): Danh sách văn bản cần dịch

        Returns:
            List[Dict[str, Any]]: Danh sách kết quả dịch

        Example:
            >>> handler = TranslationAPIHandler()
            >>> results = handler.translate_batch(["你好", "中国"])
            >>> for result in results:
            ...     if result["success"]:
            ...         print(f"{result['original']} -> {result['translation']}")
        """
        results = []
        
        for i, text in enumerate(text_list):
            if not text.strip():
                results.append({
                    "index": i,
                    "original": text,
                    "success": False,
                    "translation": "",
                    "error": "Văn bản trống",
                    "endpoint": "none"
                })
                continue
            
            success, result, endpoint = self.translate_text(text)
            
            results.append({
                "index": i,
                "original": text.strip(),
                "success": success,
                "translation": result if success else "",
                "error": result if not success else "",
                "endpoint": endpoint
            })
            
            # Thêm delay nhỏ giữa các requests để tránh rate limit
            if i < len(text_list) - 1:
                time.sleep(0.1)
        
        logger.info(f"Hoàn thành batch translation: {sum(1 for r in results if r['success'])}/{len(results)} thành công")
        return results

    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Lấy danh sách ngôn ngữ được hỗ trợ từ API.

        Returns:
            List[Dict[str, str]]: Danh sách languages
        """
        for endpoint_config in self.api_endpoints:
            try:
                endpoint_url = endpoint_config["url"]
                endpoint_type = endpoint_config["type"]
                
                if endpoint_type == "libretranslate":
                    # Thay /translate bằng /languages cho LibreTranslate
                    lang_endpoint = endpoint_url.replace("/translate", "/languages")
                    
                    response = self.session.get(lang_endpoint, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        languages = response.json()
                        logger.info(f"Lấy được {len(languages)} ngôn ngữ từ {endpoint_config['description']}")
                        return languages
                        
            except Exception as e:
                logger.error(f"Không thể lấy languages từ {endpoint_config['description']}: {e}")
                continue
        
        # Fallback - return basic info
        return [
            {"code": "zh", "name": "Chinese"},
            {"code": "vi", "name": "Vietnamese"}
        ]

    def clear_cache(self) -> int:
        """
        Xóa cache translations.

        Returns:
            int: Số lượng entries đã xóa
        """
        cache_size = len(self.cache)
        self.cache.clear()
        
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except Exception as e:
            logger.error(f"Không thể xóa cache file: {e}")
        
        logger.info(f"Đã xóa {cache_size} cached translations")
        return cache_size

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê cache.

        Returns:
            Dict[str, Any]: Thống kê cache
        """
        cache_size_bytes = 0
        if os.path.exists(self.cache_file):
            cache_size_bytes = os.path.getsize(self.cache_file)
        
        return {
            "total_entries": len(self.cache),
            "cache_file_size_bytes": cache_size_bytes,
            "cache_file_exists": os.path.exists(self.cache_file)
        }


# Singleton instance
_handler_instance: Optional[TranslationAPIHandler] = None


def get_translation_handler() -> TranslationAPIHandler:
    """
    Lấy singleton instance của TranslationAPIHandler.

    Returns:
        TranslationAPIHandler: Instance duy nhất
    """
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = TranslationAPIHandler()
    return _handler_instance


# Convenience functions
def quick_translate(chinese_text: str) -> str:
    """
    Hàm tiện ích để dịch nhanh.

    Args:
        chinese_text (str): Văn bản tiếng Trung

    Returns:
        str: Bản dịch tiếng Việt hoặc error message
    """
    handler = get_translation_handler()
    success, result, _ = handler.translate_text(chinese_text)
    return result


if __name__ == "__main__":
    # Test code
    logging.basicConfig(level=logging.INFO)
    
    handler = TranslationAPIHandler()
    
    # Test single translation
    test_words = ["你好", "中国", "学习", "北京大学"]
    
    print("=== Test Single Translations ===")
    for word in test_words:
        success, translation, endpoint = handler.translate_text(word)
        if success:
            print(f"✓ {word} -> {translation} (via {endpoint})")
        else:
            print(f"✗ {word} -> ERROR: {translation}")
    
    print("\n=== Test Batch Translation ===")
    batch_results = handler.translate_batch(["人民", "共和国", "友谊"])
    for result in batch_results:
        if result["success"]:
            print(f"✓ {result['original']} -> {result['translation']}")
        else:
            print(f"✗ {result['original']} -> ERROR: {result['error']}")
    
    print("\n=== Cache Stats ===")
    stats = handler.get_cache_stats()
    print(f"Cache entries: {stats['total_entries']}")
    print(f"Cache file size: {stats['cache_file_size_bytes']} bytes")
