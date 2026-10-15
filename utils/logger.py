import os
import logging
from utils.helpers import get_data_path

def setup_logger():
    """
    إعداد نظام التسجيل لحفظ التحذيرات والأخطاء في ملف داخل مجلد بيانات التطبيق.
    """
    log_dir = get_data_path('logs')
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception:
            pass

    log_file = os.path.join(log_dir, 'app_errors.log')
    
    logger = logging.getLogger('AHS-MediaDL')
    if not logger.handlers:
        logger.setLevel(logging.WARNING)
        try:
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        except Exception:
            # Fallback to console if file logging fails
            handler = logging.StreamHandler()
            logger.addHandler(handler)
            
    return logger

logger = setup_logger()