import time
from datetime import datetime
import logging
import json
import os
import pandas as pd
from xtquant import xtconstant
from ..core.config import Config
from ..core.trader_client import TraderClient
from ..dataprocess.storage import Storage

class Executor:
    """
    负责执行交易 (买入或卖出)
    """
    def __init__(self, client: TraderClient):
        self.client = client
        self.config = Config

    def _check_marker(self, marker_path: str) -> bool:
        """检查标记文件是否存在"""
        return os.path.exists(marker_path)

    def _create_marker(self, marker_path: str):
        """创建标记文件"""
        try:
            with open(marker_path, 'w') as f:
                f.write(f"Executed at {datetime.now()}")
        except Exception as e:
            logging.error(f"创建标记文件失败 {marker_path}: {e}")

    def _should_execute(self, plan_date, marker_file: str) -> bool:
        """
        判断是否需要执行:
        1. plan_date == today
        2. marker_file 不存在
        """
        today = datetime.now().date()
        if plan_date != today:
            logging.info(f"计划日期 ({plan_date}) 不是今天 ({today})，跳过")
            return False
            
        if self._check_marker(marker_file):
            logging.info("今日已执行过，跳过")
            return False
            
        return True

    def run_buy(self):
        """执行买入任务"""
        marker_file = os.path.join(self.config.TRADE_PLAN_DIR, 'buy_marker.log')
        plan_df = Storage.load_csv(self.config.TRADE_PLAN_DIR + '/买入计划.csv')
        
        if plan_df.empty:
            logging.warning("买入计划为空")
            return

        # 获取计划日期 (假设所有行同一天)
        plan_date = pd.to_datetime(plan_df['计划买入日期'].iloc[0]).date()
        
        if not self._should_execute(plan_date, marker_file):
            return

        logging.info("开始执行买入计划...")
        if not self.client.connected:
            self.client.start()

        for _, row in plan_df.iterrows():
            stock_code = row['股票代码']
            price = row['预计买入最大价格']
            volume = row['预计买入股票数量']
            
            if volume <= 0:
                continue

            order_id = self.client.order_stock(
                stock_code, 
                xtconstant.STOCK_BUY, 
                volume, 
                self.config.PRICE_TYPE, 
                price, 
                'strategy_buy', 
                '自动买入'
            )
            logging.info(f"买入下单: {stock_code}, 数量: {volume}, 价格: {price}, 订单号: {order_id}")
            time.sleep(0.5) # 避免太快

        self._create_marker(marker_file)
        logging.info("买入计划执行完毕")

    def run_sell(self):
        """执行卖出任务 (处理持仓卖出 + 盘中待办)"""
        marker_file = os.path.join(self.config.TRADE_PLAN_DIR, 'sell_marker.log')
        pending_file = os.path.join(self.config.TRADE_PLAN_DIR, 'pending_sell_orders.json')
        
        plan_df = Storage.load_csv(self.config.TRADE_PLAN_DIR + '/卖出计划.csv')
        
        if plan_df.empty:
             logging.warning("卖出计划为空")
             return

        plan_date = pd.to_datetime(plan_df['计划卖出日期'].iloc[0]).date()

        if not self._should_execute(plan_date, marker_file):
             return

        logging.info("开始执行卖出计划...")
        if not self.client.connected:
            self.client.start()
            
        # 1. 获取持仓
        positions = self.client.get_positions()
        pos_dict = {p.stock_code: p.can_use_volume for p in positions}
        
        # 2. 遍历计划
        pending_orders = []
        executed_any = False
        
        for _, row in plan_df.iterrows():
            stock_code = row['股票代码']
            plan_volume = row['预计卖出股票数量']
            
            # 检查持仓是否足够
            available = pos_dict.get(stock_code, 0)
            
            if available >= plan_volume and plan_volume > 0:
                # 执行卖出
                # 价格设为 latest? 或者 跌停价确保成交？ 原代码使用 LATEST_PRICE
                # 这里使用对手价卖出
                order_id = self.client.order_stock(
                    stock_code,
                    xtconstant.STOCK_SELL,
                    plan_volume,
                    xtconstant.LATEST_PRICE,
                    0, # 市价/对手价时价格无效
                    'strategy_sell',
                    '到期卖出'
                )
                logging.info(f"卖出下单: {stock_code}, 数量: {plan_volume}, 订单号: {order_id}")
                executed_any = True
            elif available < plan_volume:
                # 持仓不足，可能是还没买入或者已经卖出
                # 如果是T+1，昨天买的今天卖？如果是持有一周，应该是持仓有的。
                # 如果是因为涨停没买进导致没持仓，这里就会不足。
                logging.warning(f"持仓不足: {stock_code}, 计划卖: {plan_volume}, 可用: {available}, 加入待办")
                if plan_volume > 0:
                    pending_orders.append({
                        'stock_code': stock_code,
                        'volume': plan_volume, # 暂存计划量，实际卖出时再check
                        'plan_date': str(plan_date)
                    })

        # 3. 保存待办
        if pending_orders:
             with open(pending_file, 'w') as f:
                 json.dump(pending_orders, f)
             logging.info(f"保存了 {len(pending_orders)} 个待办卖出订单")
        
        self._create_marker(marker_file)
        logging.info("卖出计划执行完毕") 
