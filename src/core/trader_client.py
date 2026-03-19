import time
import logging
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount
from xtquant import xtdata
from .config import Config

class TraderClient:
    """
    QMT 交易客户端封装
    """
    def __init__(self):
        self.session_id = Config.get_session_id()
        self.trader = XtQuantTrader(Config.QMT_PATH, self.session_id)
        self.account = StockAccount(Config.ACCOUNT_ID, Config.ACCOUNT_TYPE)
        self.connected = False
        
        # 关闭 xtdata 默认输出
        xtdata.enable_hello = False

    def start(self):
        """启动交易线程并连接"""
        if self.connected:
            return

        logging.info("正在启动交易客户端...")
        self.trader.start()
        
        connect_result = self.trader.connect()
        if connect_result == 0:
            logging.info(f"交易终端连接成功 (Session: {self.session_id})")
            self.connected = True
            
            # 订阅账户回调
            sub_res = self.trader.subscribe(self.account)
            if sub_res == 0:
                logging.info(f"账户订阅成功: {Config.ACCOUNT_ID}")
            else:
                logging.error(f"账户订阅失败: {sub_res}")
        else:
            logging.error(f"交易终端连接失败，错误码: {connect_result}")
            raise ConnectionError("无法连接到 QMT 交易终端")

    def stop(self):
        """停止交易线程"""
        if self.connected:
            self.trader.stop()
            self.connected = False
            logging.info("交易客户端已停止")

    def get_asset(self):
        """查询资产"""
        if not self.connected:
            logging.warning("交易客户端未连接，正在尝试连接...")
            self.start()
            
        return self.trader.query_stock_asset(self.account)

    def get_positions(self):
        """查询持仓"""
        if not self.connected:
            self.start()
        return self.trader.query_stock_positions(self.account)

    def order_stock(self, stock_code, order_type, order_volume, price_type, price, strategy_name, order_remark):
        """下单"""
        if not self.connected:
            self.start()
            
        return self.trader.order_stock(
            self.account,
            stock_code,
            order_type,
            int(order_volume),
            price_type,
            float(price),
            strategy_name,
            order_remark
        )
    
    def get_market_data(self, stock_codes: list, period='tick'):
        """
        获取行情数据的封装 (wrapper around xtdata)
        """
        # 简单封装，后续可以在 src/data 中做更复杂的逻辑
        for code in stock_codes:
            xtdata.subscribe_quote(code, period=period)
        
        # 简单等待订阅生效
        # time.sleep(0.5) 
        
        return xtdata.get_full_tick(stock_codes)
