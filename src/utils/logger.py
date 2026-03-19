import logging
import sys
import os
from .notifier import WeChatNotifier, WeChatLogHandler
from ..core.config import Config

class LoggerSetup:
    @staticmethod
    def setup_logging(log_filename: str = 'system.log', notifier: WeChatNotifier = None):
        """
        配置日志系统
        :param log_filename: 日志文件名
        :param notifier: 如果提供，将添加微信推送handler
        """
        log_path = os.path.join(Config.LOG_DIR, log_filename)
        
        # 创建 logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # 清除旧的处理器
        logger.handlers.clear()

        # 1. 文件处理器 (覆盖模式)
        file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 2. 控制台处理器
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # 3. 微信处理器
        if notifier and notifier.enabled:
            wechat_handler = WeChatLogHandler(notifier)
            wechat_handler.setLevel(logging.INFO) 
            wechat_handler.setFormatter(formatter)
            logger.addHandler(wechat_handler)
            
        logging.info(f"日志系统已启动，日志文件: {log_path}")
        return logger
