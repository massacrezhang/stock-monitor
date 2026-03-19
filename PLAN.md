# Refactoring Plan: Object-Oriented Python Trading System

## Phase 1: Core Infrastructure

- [ ] **Configuration Management**: Encapsulate settings from `Config.py` into a `Config` class in `src/core/config.py`.
- [ ] **Notification Service**: Refactor `Bot_connection.py` into `src/utils/notifier.py` as a `NotificationService` class.
- [ ] **Logging Service**: Standardize logging setup in `src/utils/logger.py`.
- [ ] **Trader Client**: Encapsulate `XtQuantTrader` connection and session management in `src/core/trader_client.py`.

## Phase 2: Data & Strategy (STEP 1)

- [ ] **Data Manager**: Refactor data fetching (Sina API, local CSVs) from `Function.py` into `src/data/data_manager.py`.
- [ ] **Strategy Engine**: Refactor "STEP1\_生成计划" logic into `src/strategy/generator.py`.
- [ ] **Plan Manager**: Handle reading/writing execution plans (CSVs) in `src/data/plan_manager.py`.

## Phase 3: Execution & Monitoring (STEP 2 & 3)

- [ ] **Execution Engine**: Refactor "STEP2\_选股下单" into `src/execution/executor.py`.
- [ ] **Monitor Engine**: Refactor "STEP3\_循环监视" into `src/execution/monitor.py`.
- [ ] **Data Fetching (QMT)**: Move QMT specific data fetching to `src/data/qmt_source.py`.

## Phase 4: Entry Points & Cleanup

- [ ] Create `main.py` as the CLI entry point.
- [ ] Create `run_step1.py`, `run_step2.py`, `run_step3.py` wrappers if needed for compatibility.
- [ ] Remove old files (`Config.py`, `Function.py`, etc.) after verification.
