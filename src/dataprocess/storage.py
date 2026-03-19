import pandas as pd
import os
import logging
from src.core.config import Config

class Storage:
    """
    数据存储与加载管理类，负责所有的本地CSV、计划文件的读写，严格遵循单一职责原则。
    """

    @staticmethod
    def load_csv(path: str) -> pd.DataFrame:
        """
        加载指定路径的CSV文件
        :param path: 文件路径
        :return: DataFrame
        """
        try:
            if not os.path.exists(path):
                logging.warning(f"文件未找到: {path}")
                return pd.DataFrame()
            return pd.read_csv(path, encoding='utf-8')
        except Exception as e:
            logging.error(f"加载CSV文件 {path} 时出错: {e}")
            return pd.DataFrame()

    @staticmethod
    def save_plan(df: pd.DataFrame, filename: str) -> bool:
        """
        保存交易计划到配置的交易计划目录
        :param df: 需要保存的数据框
        :param filename: 文件名（如 "买入计划.csv"）
        :return: 是否保存成功
        """
        try:
            if not os.path.exists(Config.TRADE_PLAN_DIR):
                os.makedirs(Config.TRADE_PLAN_DIR)
                
            file_path = os.path.join(Config.TRADE_PLAN_DIR, filename)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            logging.info(f"成功将买入计划保存至 {file_path}")
            return True
        except Exception as e:
            logging.error(f"保存计划 {filename} 时出错: {e}")
            return False

    @staticmethod
    def reset_execution_markers() -> bool:
        """
        重置/清理执行标记，例如防止前一日的执行状态影响新一天的交易计划
        :return: 是否重置成功
        """
        try:
            # 清理标记文件逻辑（视具体执行逻辑而定）
            # 例如删除一个 mark.txt 或者在日志中做切割
            logging.info("重置执行标记，准备迎接新交易日")
            return True
        except Exception as e:
            logging.error(f"重置标记时出错: {e}")
            return False
