"""
UI Package cho ứng dụng tra cứu từ Hán Việt
=========================================

Chứa các component giao diện người dùng sử dụng Gradio:
- gradio_app.py: Giao diện chính và tích hợp logic
"""

from .gradio_app import create_interface

__all__ = ["create_interface"]
