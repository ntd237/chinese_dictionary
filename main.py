#!/usr/bin/env python3
"""
Ứng dụng tra cứu từ Hán Việt - Entry Point
=========================================

Ứng dụng web để tra cứu từ tiếng Trung (chữ Hán) với:
- Phiên âm Pinyin chuẩn (có dấu thanh)
- Dịch nghĩa sang tiếng Việt

Khởi chạy: python main.py
"""

import logging
import sys
import os
import argparse
from pathlib import Path

# Thêm src vào Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.ui.gradio_app import launch_app, create_interface
    from src.pinyin_converter import get_converter
    from src.api_handler import get_translation_handler
except ImportError as e:
    print(f"❌ Lỗi import module: {e}")
    print("🔧 Hãy đảm bảo đã cài đặt dependencies: pip install -r requirements.txt")
    sys.exit(1)


def setup_logging(debug: bool = False) -> None:
    """
    Cấu hình logging cho ứng dụng.
    
    Args:
        debug (bool): Chế độ debug với log level chi tiết
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Cấu hình format cho log
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Có thể thêm FileHandler nếu muốn log ra file
            # logging.FileHandler('hanviet_app.log', encoding='utf-8')
        ]
    )
    
    # Giảm log level cho một số thư viện bên ngoài
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('gradio').setLevel(logging.INFO)


def check_dependencies() -> bool:
    """
    Kiểm tra các dependencies cần thiết.
    
    Returns:
        bool: True nếu tất cả dependencies đều OK
    """
    required_packages = [
        'gradio',
        'pypinyin', 
        'requests',
        'pandas'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Thiếu packages: {', '.join(missing_packages)}")
        print(f"🔧 Cài đặt: pip install {' '.join(missing_packages)}")
        return False
    
    return True


def test_core_functions() -> bool:
    """
    Test các chức năng core trước khi khởi chạy UI.
    
    Returns:
        bool: True nếu tất cả tests pass
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Test Pinyin converter
        logger.info("🧪 Testing Pinyin converter...")
        pinyin_converter = get_converter()
        test_result = pinyin_converter.convert_to_pinyin("你好")
        
        if not test_result:
            logger.error("❌ Pinyin converter test failed")
            return False
        
        logger.info(f"✅ Pinyin test passed: '你好' -> '{test_result}'")
        
        # Test Translation handler (không gọi API thực để tránh rate limit)
        logger.info("🧪 Testing Translation handler initialization...")
        translation_handler = get_translation_handler()
        
        if not translation_handler:
            logger.error("❌ Translation handler initialization failed")
            return False
        
        logger.info("✅ Translation handler initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Core function test failed: {e}")
        return False


def print_startup_info() -> None:
    """In thông tin khởi động ứng dụng."""
    print("=" * 60)
    print("🔤 ỨNG DỤNG TRA CỨU TỪ HÁN VIỆT")
    print("=" * 60)
    print("📝 Tính năng:")
    print("   • Chuyển đổi chữ Hán sang Pinyin (có dấu thanh)")
    print("   • Dịch nghĩa từ tiếng Trung sang tiếng Việt") 
    print("   • Giao diện web thân thiện với Gradio")
    print("   • Hỗ trợ tra cứu đơn lẻ và hàng loạt")
    print()
    print("🔧 Công nghệ:")
    print("   • Pinyin: pypinyin (offline, nhanh)")
    print("   • Dịch nghĩa: LibreTranslate API (miễn phí)")
    print("   • UI: Gradio")
    print("=" * 60)


def main():
    """Hàm main - entry point của ứng dụng."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Ứng dụng tra cứu từ Hán Việt với Pinyin và dịch nghĩa",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python main.py                    # Chạy với cấu hình mặc định
  python main.py --port 8080        # Chạy trên port 8080
  python main.py --host 0.0.0.0     # Cho phép truy cập từ mạng ngoài
  python main.py --share            # Tạo public link (Gradio share)
  python main.py --debug            # Chế độ debug với log chi tiết
        """
    )
    
    parser.add_argument(
        '--host', 
        default='127.0.0.1',
        help='Địa chỉ host (mặc định: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--port', 
        type=int,
        default=7860,
        help='Port (mặc định: 7860)'
    )
    
    parser.add_argument(
        '--share',
        action='store_true',
        help='Tạo public link qua Gradio share'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true', 
        help='Chế độ debug với log chi tiết'
    )
    
    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Chỉ chạy tests, không khởi động UI'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)
    
    # In thông tin khởi động
    print_startup_info()
    
    # Kiểm tra dependencies
    logger.info("🔍 Kiểm tra dependencies...")
    if not check_dependencies():
        print("\n❌ Vui lòng cài đặt đầy đủ dependencies trước khi chạy:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    logger.info("✅ Dependencies OK")
    
    # Test core functions
    logger.info("🧪 Kiểm tra chức năng core...")
    if not test_core_functions():
        print("\n❌ Core function tests failed. Vui lòng kiểm tra cấu hình.")
        sys.exit(1)
    
    logger.info("✅ Core functions OK")
    
    # Nếu chỉ test thôi thì dừng ở đây
    if args.test_only:
        print("\n✅ Tất cả tests đều passed. Ứng dụng sẵn sàng chạy.")
        return
    
    # Khởi chạy ứng dụng
    try:
        print(f"\n🚀 Đang khởi động ứng dụng...")
        print(f"   📍 Host: {args.host}")
        print(f"   🔌 Port: {args.port}")
        print(f"   🌐 Share: {'Có' if args.share else 'Không'}")
        print(f"   🐛 Debug: {'Có' if args.debug else 'Không'}")
        print()
        print("⏳ Vui lòng chờ Gradio khởi động...")
        print("🌐 Sau khi khởi động, mở trình duyệt và truy cập URL được hiển thị")
        print("⛔ Nhấn Ctrl+C để dừng ứng dụng")
        print("-" * 60)
        
        launch_app(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            debug=args.debug
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Đã dừng ứng dụng theo yêu cầu người dùng")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khởi động ứng dụng: {e}")
        print(f"\n❌ Lỗi: {e}")
        print("🔧 Vui lòng kiểm tra log để biết thêm chi tiết")
        sys.exit(1)


if __name__ == "__main__":
    main()
