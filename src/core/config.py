import os
from datetime import datetime
from xtquant import xtconstant

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip()

_load_env()

class Config:
    """
    全局配置类
    """
    # 基础路径
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(PROJECT_ROOT, 'Data')
    LOG_DIR = os.path.join(PROJECT_ROOT, 'log')
    TRADE_PLAN_DIR = os.path.join(DATA_DIR, '交易计划')

    # 确保目录存在
    for d in [DATA_DIR, LOG_DIR, TRADE_PLAN_DIR]:
        os.makedirs(d, exist_ok=True)

    # QMT 配置
    QMT_PATH = os.environ.get("QMT_PATH", "")
    ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "")
    ACCOUNT_TYPE = 'STOCK'

    # 交易参数
    PRICE_TYPE = xtconstant.LATEST_PRICE
    HOLDING_PERIOD = '一周'
    
    # 资金管理
    # 从CSV文件读取最新的'择时信号'作为乘数 (逻辑迁移这部分将在 Strategy 类中处理，这里保留默认值)
    DEFAULT_MULTIPLIER = 1.0
    
    # 选股结果路径
    SELECT_STOCK_PATH = os.path.join(DATA_DIR, '最新选股结果.csv')
    
    # 企业微信配置
    ENABLE_WECHAT = os.environ.get("ENABLE_WECHAT", "True").lower() == "true"
    WECHAT_KEYS = [
        os.environ.get("WECHAT_KEY", ""),
    ]

    #STEP3 监控配置
    PRINCIPAL = 40000.0
    SINGLE_STOCK_LOSS_LIMIT = PRINCIPAL * 0.01  # 400元
    PORTFOLIO_LOSS_LIMIT = PRINCIPAL * 0.05     # 2000元
    MONITOR_INTERVAL = 30                       # 秒

    @classmethod
    def get_session_id(cls):
        """生成一个新的 Session ID"""
        import time
        return int(time.time() * 1000)

