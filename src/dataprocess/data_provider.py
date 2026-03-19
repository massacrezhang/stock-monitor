import pandas as pd
from typing import List
import logging
from xtquant import xtdata
import akshare as ak

class DataProvider:
    """
    Data Provider for fetching market data and trading calendars using QMT (xtquant).
    """

    @staticmethod
    def get_trade_calendar(start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch the trading calendar between start_date and end_date using akshare.
        
        :param start_date: str, format 'YYYY-MM-DD'
        :param end_date: str, format 'YYYY-MM-DD'
        :return: pd.DataFrame with columns ['date', 'is_trade']
        """
        try:
            # 使用 akshare 获取新浪A股历史交易日历数据
            trade_dates_df = ak.tool_trade_date_hist_sina()
            
            # 过滤出所需范围内的日期，akshare 默认格式为 datetime.date 或 str
            trade_dates_df['trade_date'] = pd.to_datetime(trade_dates_df['trade_date'])
            
            # 设定过滤区间
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            mask = (trade_dates_df['trade_date'] >= start) & (trade_dates_df['trade_date'] <= end)
            filtered_dates = trade_dates_df.loc[mask, 'trade_date'].dt.strftime('%Y-%m-%d').tolist()
            
            # 构建标准的格式返回
            df = pd.DataFrame({
                'date': filtered_dates,
                'is_trade': 1
            })
            return df
            
        except Exception as e:
            # 极端回退策略：如果你没装 akshare 或断网时，退避至工作日
            logging.warning(f"使用 akshare 获取交易日历失败: {e}，回退至普通工作日。可能导致节假日计算误差。")
            dates = pd.date_range(start=start_date, end=end_date, freq='B')
            return pd.DataFrame({
                'date': dates.strftime('%Y-%m-%d'),
                'is_trade': 1
            })

    @staticmethod
    def fetch_qmt_data(scripts_codes: List[str]) -> pd.DataFrame:
        """
        从 QMT 获取股票行情并计算预计买入最大价格。
        由于策略需要使用，暂时保持原函数名称(fetch_qmt_data)以便 plan_generator 能够平滑过渡调用。
        
        :param scripts_codes: List of stock codes (e.g., ['sh600000', 'sz000001'])
        :return: pd.DataFrame containing 'stock_code' and calculated prices
        """
        # 1. 转换股票代码格式 (选股可能是 sh600000，QMT 需要 600000.SH)
        qmt_codes = []
        code_mapping = {}
        for code in scripts_codes:
            code_lower = code.lower()
            if code_lower.startswith('sh'):
                qmt_code = f"{code[2:]}.SH"
            elif code_lower.startswith('sz'):
                qmt_code = f"{code[2:]}.SZ"
            else:
                qmt_code = code # 如果已经是正确格式或未知格式
            
            qmt_codes.append(qmt_code)
            code_mapping[qmt_code] = code

        # 3. 获取全推快照数据（包含昨收、买卖一档等）
        tick_data = xtdata.get_full_tick(qmt_codes)
        
        data = []
        for qmt_code in qmt_codes:
            original_code = code_mapping.get(qmt_code, qmt_code)
            tick = tick_data.get(qmt_code, {})
            
            if not tick:
                logging.warning(f"未能获取到标的 {original_code} ({qmt_code}) 的行情数据")
                continue
            
            # 4. 从 full_tick 取昨收 (lastClose)
            last_close = tick.get('lastClose', 0.0)
            
            # 卖一价数组
            askPrice_arr = tick.get('askPrice', [0.0])
            sell1 = askPrice_arr[0] if len(askPrice_arr) > 0 else 0.0
            
            # 盘前未竞价时或者一字涨停没有卖单时可能无卖一价，做兜底处理使用昨收价
            if sell1 <= 0.0 or sell1 >= 900000:
                sell1 = last_close
                
            # 5. 根据要求计算 预计买入最大价格: 卖一单价的 1.1 倍 (即涨停价，四舍五入保留2位小数)
            # 如果是停牌彻底没日期的票做兜底0.0
            max_buy_price = round(sell1 * 1.1, 2) if sell1 > 0 else 0.0
            
            data.append({
                'stock_code': original_code,
                'last_close': last_close,
                'sell1': sell1,
                'current_price': tick.get('lastPrice', last_close),
                'open': tick.get('open', 0.0),
                'high': tick.get('high', 0.0),
                'low': tick.get('low', 0.0),
                'volume': tick.get('volume', 0),
                '预计买入最大价格': max_buy_price
            })
            
        return pd.DataFrame(data)
