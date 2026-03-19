import sys
import argparse
import logging
from src.core import Config, TraderClient
from src.utils import LoggerSetup, WeChatNotifier
from src.strategy import PlanGenerator
from src.execution import Executor, Monitor

def _setup_system(mode: str):
    """
    初始化系统组件
    :param mode: 运行模式 (plan/trade/monitor)
    :return: (logger, notifier, client)
    """
    # 1. 初始化推送服务
    notifier = WeChatNotifier(
        keys=Config.WECHAT_KEYS,
        enabled=Config.ENABLE_WECHAT
    )
    
    # 2. 初始化日志
    log_file = f"{mode}.log"
    logger = LoggerSetup.setup_logging(log_filename=log_file, notifier=notifier)
    
    # 3. 初始化交易客户端 (懒连接)
    client = TraderClient()
    
    return logger, notifier, client

def run_plan(args):
    """执行 STEP1: 生成计划"""
    logger, notifier, client = _setup_system("plan")
    
    try:
        logging.info(">>> 启动交易计划生成模块 <<<")
        generator = PlanGenerator() # PlanGenerator 内部会处理资金查询
        generator.run()
        logging.info("交易计划生成任务结束")
    except Exception as e:
        logging.error(f"计划生成失败: {e}", exc_info=True)
        sys.exit(1)

def run_trade(args):
    """执行 STEP2: 每日交易 (早盘)"""
    logger, notifier, client = _setup_system("trade")
    
    try:
        logging.info(">>> 启动每日交易执行模块 <<<")
        executor = Executor(client)
        
        # 依次执行买入和卖出
        logging.info("--- 检查买入计划 ---")
        executor.run_buy()
        
        logging.info("--- 检查卖出计划 ---")
        executor.run_sell()
        
        logging.info("每日交易任务检查结束")
        client.stop()
        
    except Exception as e:
        logging.error(f"交易执行失败: {e}", exc_info=True)
        client.stop() # 确保断开
        sys.exit(1)

def run_monitor(args):
    """执行 STEP3: 盘中监控"""
    logger, notifier, client = _setup_system("monitor")
    
    try:
        logging.info(">>> 启动盘中监控模块 <<<")
        monitor = Monitor(client)
        monitor.run_loop() # 这是一个无限循环，直到收盘或异常
        
        client.stop()
        logging.info("监控模块已停止")
        
    except KeyboardInterrupt:
        logging.info("监控被用户手动停止")
        client.stop()
    except Exception as e:
        logging.error(f"监控运行失败: {e}", exc_info=True)
        client.stop()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="策略实盘系统主入口")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 命令 1: 生成计划 (STEP1)
    plan_parser = subparsers.add_parser("plan", help="生成新的交易计划 (STEP1)")
    
    # 命令 2: 执行交易 (STEP2)
    trade_parser = subparsers.add_parser("trade", help="执行每日交易买卖 (STEP2)")
    
    # 命令 3: 盘中监控 (STEP3)
    monitor_parser = subparsers.add_parser("monitor", help="启动盘中监控与止损 (STEP3)")
    
    args = parser.parse_args()
    
    if args.command == "plan":
        run_plan(args)
    elif args.command == "trade":
        run_trade(args)
    elif args.command == "monitor":
        run_monitor(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
