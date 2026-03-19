import requests
import json
import logging
from typing import List, Optional

class WeChatNotifier:
    """
    企业微信消息通知服务
    """
    def __init__(self, keys: List[str], enabled: bool = True):
        self.keys = keys
        self.enabled = enabled
        self.headers = {"Content-Type": "application/json"}

    def send_message(self, content: str, specified_keys: Optional[List[str]] = None) -> None:
        """
        发送消息
        :param content: 消息内容
        :param specified_keys: 指定发送的key列表，如果为None则使用初始化时的keys
        """
        if not self.enabled:
            return

        keys_to_use = specified_keys if specified_keys else self.keys

        for key in keys_to_use:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            try:
                response = requests.post(url, headers=self.headers, data=json.dumps(data), timeout=5)
                if response.status_code != 200:
                    logging.warning(f"Warning: 机器人({key})发送失败 Status: {response.status_code}")
            except Exception as e:
                logging.warning(f"Warning: 机器人({key})连接异常: {e}")

class WeChatLogHandler(logging.Handler):
    """
    logging Handler 用于集成到 logging 模块中
    """
    def __init__(self, notifier: WeChatNotifier):
        super().__init__()
        self.notifier = notifier

    def emit(self, record):
        try:
            msg_content = record.getMessage()
            
            # 1. 严重警告 (WARNING/ERROR)：全部推送
            if record.levelno >= logging.WARNING:
                formatted_msg = self.format(record)
                self.notifier.send_message(f"【⚠️ 策略警报】\n{formatted_msg}")
                
            # 2. 资金播报 (INFO)：只推送包含 "监控中心:" 的汇总信息
            elif record.levelno == logging.INFO and "监控中心:" in msg_content:
                from datetime import datetime
                current_time = datetime.now().strftime('%H:%M:%S')
                self.notifier.send_message(f"【📊 资金播报 {current_time}】\n{msg_content}")
                
        except Exception:
            self.handleError(record)
