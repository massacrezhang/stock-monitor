import pandas as pd
import math
import logging
from datetime import datetime
from ..core.config import Config
from ..dataprocess.data_provider import DataProvider
from ..dataprocess.storage import Storage

class PlanComponents:
    """
    计划生成的组件：日期计算、仓位计算
    """
    
    @staticmethod
    def calculate_buy_quantities(prices: list, total_fund: float) -> list:
        """
        根据资金和价格计算买入数量 (向下取整到100股)
        """
        # 跳过价格为0的股票
        total_amounts = [total_fund / price if price > 0 else 0 for price in prices]
        min_buy_amount = 100
        buy_quantities = [math.floor(amount / min_buy_amount) * min_buy_amount for amount in total_amounts]
        return buy_quantities

    @staticmethod
    def get_first_trade_date_after(trading_days: pd.Series, target_date: datetime):
        """
        找到第一个 >= target_date 的交易日
        """
        future_trading_days = trading_days[trading_days >= target_date]
        if not future_trading_days.empty:
            return future_trading_days.iloc[0].date() # returns datetime.date
        return None

    @staticmethod
    def calculate_sell_date(buy_date, trading_days_list, holding_period_str):
        """
        计算卖出日期：根据设定的持仓周期，寻找目标周的最后一个交易日作为卖出日。
        (例如: '一周' 意味着在本周最后一个交易日卖出；如果周一买入，则本周五卖出)
        """
        try:
            # 1. 计算买入日的年份和周数 (ISO标准周)
            buy_dt = pd.Timestamp(buy_date)
            buy_year, buy_week, _ = buy_dt.isocalendar()
            
            # 2. 根据持有周期增加目标周数
            weeks_to_add = 0
            if holding_period_str == '两周':
                weeks_to_add = 1  # 下周的最后一个交易日
            elif holding_period_str == '一个月':
                weeks_to_add = 3  # 下下下周的最后一个交易日
            
            target_out_week = buy_week + weeks_to_add
            # 简单处理跨年周数 (ISO大概52或53周，不考虑极端跨年溢出的精准算法，可做大致兼容)
            target_year = buy_year
            if target_out_week > 52:
                target_out_week -= 52
                target_year += 1

            # 3. 在交易日历中往后寻找属于 target_year 和 target_out_week 的所有交易日
            candidate_sell_dates = []
            
            # 转为 DataFrame 处理会更加方便和高效
            # 将列表转为 Series 后利用 dt 属性提取周数
            trading_series = pd.Series(trading_days_list)
            
            # 过滤出大于等于买入日的交易日
            future_trades = trading_series[trading_series >= buy_dt]
            
            for t_date in future_trades:
                t_year, t_week, t_dayofweek = t_date.isocalendar()
                
                # 特殊跨年处理（年末那几天可能被算作下一年的第1周，或者年初算作上一年的52周）
                # 为了严谨我们直接比较年份和周次
                if t_year == target_year and t_week == target_out_week:
                    candidate_sell_dates.append(t_date)
                elif t_year > target_year or (t_year == target_year and t_week > target_out_week):
                    # 已经超越了目标周，停止寻找
                    break
                    
            if candidate_sell_dates:
                # 取得目标周内的最后一天 (通常是周五)
                return candidate_sell_dates[-1].date()
            else:
                logging.error(f"无法找到 {buy_date} 对应的平仓周 ({target_year}年第{target_out_week}周) 交易日")
                # 兜底：如果没有找到，老办法找未来第4个交易日（凑合一周）
                buy_idx = trading_series[trading_series == buy_dt].index[0]
                fallback_idx = min(buy_idx + 4, len(trading_series) - 1)
                return trading_series.iloc[fallback_idx].date()

        except Exception as e:
            logging.error(f"计算卖出日期失败: {e}")
            return None

class PlanGenerator:
    def __init__(self):
        self.config = Config
        
    def run(self):
        logging.info("开始生成交易计划...")
        
        # 1. 准备范围
        current_year = str(datetime.now().year)
        start_date = current_year + '-01-01'
        end_date = current_year + "-12-31"

        # 2. 获取交易日历
        logging.info(f"获取交易日历 ({start_date} ~ {end_date})...")
        date_df = DataProvider.get_trade_calendar(start_date, end_date)
        
        # 提取有效交易日列表 (Series of Timestamp)
        date_df['calendar_date'] = pd.to_datetime(date_df['date'])
        trading_days = date_df[date_df['is_trade'] == 1]['calendar_date'].sort_values().reset_index(drop=True)
        
        # 3. 读取选股结果
        selection_df = Storage.load_csv(self.config.SELECT_STOCK_PATH)
        if selection_df.empty:
            logging.error("选股结果为空或文件不存在，无法生成计划。")
            return
        
        # 获取最新的择时信号
        if '择时信号' in selection_df.columns:
            try:
                multiplier = float(selection_df['择时信号'].iloc[-1])
            except:
                multiplier = 1.0
        else:
            multiplier = 1.0
            
        # 限制 multiplier
        multiplier = max(0.0, min(1.0, multiplier))
        logging.info(f"使用择时信号乘数: {multiplier}")
        
        # 获取最新一天的选股
        # 假设 '交易日期' 列存在. 原代码: trade_plan['交易日期'] == trade_plan['交易日期'].max()
        if '交易日期' not in selection_df.columns:
            logging.error("选股结果缺少 '交易日期' 列")
            return
            
        latest_date = selection_df['交易日期'].max()
        latest_targets = selection_df[selection_df['交易日期'] == latest_date].copy()
        
        scripts_codes = latest_targets['股票代码'].tolist()
        logging.info(f"最新选股日期: {latest_date}, 标的数量: {len(scripts_codes)}")

        # 4. 获取即时行情计算价格
        market_data = DataProvider.fetch_qmt_data(scripts_codes)
        if market_data.empty:
            logging.error("无法获取行情数据")
            return

        # 合并数据
        # latest_targets 有 '股票代码', market_data 有 'stock_code'
        # 注意: 选股结果里的代码格式可能不同？原代码做了处理吗?
        # 原代码：calculate_data 入参是 list(latest_data['股票代码'])
        # 然后 merged_df = pd.merge(original_data, latest_data, left_on='stock_code', right_on='股票代码')
        merged_df = pd.merge(market_data, latest_targets, left_on='stock_code', right_on='股票代码')
        
        # 5. 计算资金和股数
        # 获取账户可用资金 (这里需要 TraderClient 吗？原代码是直接 Config.xt_trader.query_stock_asset)
        # 此时可能是非交易时间，或者不需要连接QMT就可以生成？
        # 原Config是在最开始就连接了QMT。
        # 我们这里为了解耦，可以使用 Config 中的某种默认配置，或者建立连接。
        # 为了保证准确性，我们使用 TraderClient 获取一次资金。
        from ..core.trader_client import TraderClient
        client = TraderClient()
        try:
            client.start()
            asset = client.get_asset()
            if asset:
                total_cash = asset.cash
                logging.info(f"账户可用资金: {total_cash}")
            else:
                logging.warning("无法获取资金，使用默认 0")
                total_cash = 0
        except Exception as e:
            logging.warning(f"连接交易端失败，无法获取资金: {e}")
            total_cash = 0
        finally:
            client.stop()

        # 计算投入资金
        invest_amount = total_cash * multiplier
        per_stock_fund = invest_amount / len(merged_df) if len(merged_df) > 0 else 0
        
        prices = merged_df['预计买入最大价格'].tolist()
        quantities = PlanComponents.calculate_buy_quantities(prices, per_stock_fund)
        merged_df['预计买入股票数量'] = quantities
        
        # 6. 计算日期
        # 给定日期
        given_date_str = merged_df['交易日期'].iloc[0] # date string
        given_date = pd.to_datetime(given_date_str)
        
        buy_date = PlanComponents.get_first_trade_date_after(trading_days, given_date)
        sell_date = PlanComponents.calculate_sell_date(buy_date, trading_days.tolist(), self.config.HOLDING_PERIOD)
        
        if not buy_date:
            logging.error("无法计算买入日期")
            return

        logging.info(f"计划买入日期: {buy_date}, 计划卖出日期: {sell_date}")

        # 7. 格式化并保存
        
        # 格式化股票代码
        # merged_df['股票代码'] 可能是 sh000001
        # 我们需要转为 000001.SH (QMT格式)
        def format_code(x):
            if x.startswith('sh') or x.startswith('sz'):
                return f"{x[2:]}.{x[:2].upper()}"
            # 如果已经是数字开头，不知道后缀？
            return x

        merged_df['股票代码'] = merged_df['stock_code'].apply(format_code)
        
        merged_df['计划买入日期'] = buy_date
        merged_df['计划卖出日期'] = sell_date
        merged_df['选股日期'] = merged_df['交易日期']

        # 保存买入计划
        buy_cols = ['计划买入日期', '股票代码', '预计买入最大价格', '预计买入股票数量']
        buy_plan = merged_df[buy_cols]
        Storage.save_plan(buy_plan, "买入计划.csv")

        # 保存卖出计划
        sell_cols = ['计划卖出日期', '股票代码', '预计买入股票数量']
        sell_plan = merged_df[sell_cols].rename(columns={'预计买入股票数量': '预计卖出股票数量'})
        Storage.save_plan(sell_plan, "卖出计划.csv")

        # 8. 重置标记
        Storage.reset_execution_markers()
        
        logging.info("计划生成完成！")
