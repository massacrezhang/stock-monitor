import time
import logging
from datetime import datetime, time as dtime
from ..core.config import Config
from ..core.trader_client import TraderClient
from xtquant import xtconstant

class Monitor:
    """
    负责实时监控持仓盈亏并执行止损
    """
    def __init__(self, client: TraderClient):
        self.client = client
        self.config = Config
        self.running = False

    def _check_trading_time(self, now_time):
        """检查交易时间"""
        # 简单定义
        morning_start = dtime(9, 25, 0) # 9:25后开始监控
        morning_end = dtime(11, 30, 0)
        afternoon_start = dtime(13, 0, 0)
        afternoon_end = dtime(15, 0, 0)
        
        if (morning_start <= now_time <= morning_end) or (afternoon_start <= now_time <= afternoon_end):
            return 'RUN'
        elif now_time > afternoon_end:
            return 'STOP'
        else:
            return 'WAIT'

    def run_loop(self):
        """启动监控循环"""
        self.running = True
        logging.info("启动监控循环...")
        
        log_counter = 0
        
        while self.running:
            try:
                now = datetime.now()
                status = self._check_trading_time(now.time())
                
                if status == 'STOP':
                    logging.info("已收盘，监控停止。")
                    break
                elif status == 'WAIT':
                    if log_counter % 10 == 0:
                        logging.info("非交易时间，等待...")
                    time.sleep(60)
                    continue
                
                # RUN 状态
                if not self.client.connected:
                    self.client.start()
                
                positions = self.client.get_positions()
                valid_positions = [p for p in positions if p.can_use_volume > 0]
                
                if not valid_positions:
                    if log_counter % 10 == 0:
                        logging.info("无可用持仓，继续监控...")
                    time.sleep(self.config.MONITOR_INTERVAL)
                    continue

                # 获取行情
                codes = [p.stock_code for p in valid_positions]
                ticks = self.client.get_market_data(codes)
                
                # 排除列表
                exclude_codes = ['888880.SH', '131990.SZ']

                total_loss = 0.0
                portfolio_data = []
                
                for pos in valid_positions:
                    # 如果在排除列表中，跳过
                    if pos.stock_code in exclude_codes:
                        continue

                    tick = ticks.get(pos.stock_code)
                    if not tick: 
                        continue
                        
                    # 价格逻辑: 优先 bidPrice[0] (买一), 否则 lastPrice
                    # QMT full_tick returns list for bidPrice
                    bid_price = tick['bidPrice'][0] if tick['bidPrice'] and len(tick['bidPrice']) > 0 else 0.0
                    current_price = bid_price if bid_price > 0 else tick['lastPrice']
                    
                    if current_price <= 0:
                        continue
                        
                    profit = (current_price - pos.open_price) * pos.volume
                    total_loss += profit
                    
                    portfolio_data.append({
                        'code': pos.stock_code,
                        'volume': pos.can_use_volume,
                        'current_price': current_price,
                        'profit': profit
                    })

                # 止损逻辑
                # 1. 组合止损
                if total_loss < -self.config.PORTFOLIO_LOSS_LIMIT:
                    logging.warning(f"!!! 触发组合止损 !!! 总亏损: {total_loss:.2f}")
                    for item in portfolio_data:
                        self.client.order_stock(
                            item['code'], 
                            xtconstant.STOCK_SELL, 
                            item['volume'], 
                            xtconstant.LATEST_PRICE, 
                            item['current_price'], 
                            'stop_loss_portfolio', 
                            '组合止损卖出'
                        )
                    time.sleep(5)
                    continue

                # 2. 个股止损
                for item in portfolio_data:
                    if item['profit'] < -self.config.SINGLE_STOCK_LOSS_LIMIT:
                        logging.warning(f"!!! 触发个股止损 !!! {item['code']} 亏损: {item['profit']:.2f}")
                        self.client.order_stock(
                            item['code'],
                            xtconstant.STOCK_SELL,
                            item['volume'],
                            xtconstant.LATEST_PRICE,
                            item['current_price'],
                            'stop_loss_single',
                            '个股止损卖出'
                        )

                # 日志
                if log_counter % 6 == 0:
                     logging.info(f"监控中心: 持仓{len(portfolio_data)}只, 组合浮动盈亏 {total_loss:.2f} 元")

                log_counter += 1
                time.sleep(self.config.MONITOR_INTERVAL)

            except KeyboardInterrupt:
                logging.info("监控被手动停止")
                break
            except Exception as e:
                logging.error(f"监控循环异常: {e}")
                time.sleep(10)
