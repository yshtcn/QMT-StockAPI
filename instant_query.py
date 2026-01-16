# -*- coding: utf-8 -*-
"""
即时查询服务模块

功能：
- 按股票代码触发一次性数据更新：K线（多周期）+ 实时价格
- 自动保存到 ./data 目录（文件命名与现有规则一致）
- 并发控制：同一股票代码串行化，避免重复重负载
- 返回实时价格 + K线文件列表 + 预览摘要

尽量复用现有模块，避免改动原有代码：
- K线：AllKLineData.KLineDataCollector
- 实时：RealTimePrice.RealTimePriceMonitor
"""

import os
import re
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import pandas as pd

from AllKLineData import KLineDataCollector
from RealTimePrice import RealTimePriceMonitor


logger = logging.getLogger(__name__)

# 统一数据目录
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(BASE_DIR, exist_ok=True)

# 每只股票一个锁，避免同一股票并发更新
_STOCK_LOCKS: Dict[str, threading.Lock] = {}
_GLOBAL_LOCK = threading.Lock()


def _get_stock_lock(stock_code: str) -> threading.Lock:
    normalized = stock_code.upper()
    with _GLOBAL_LOCK:
        if normalized not in _STOCK_LOCKS:
            _STOCK_LOCKS[normalized] = threading.Lock()
        return _STOCK_LOCKS[normalized]


def normalize_stock_code(code: str) -> str:
    """
    规范化股票代码：
    - 支持 600689.SH / 600689SH / SH600689 / 600689_sh / 600689-sh
    - 返回标准格式：NNNNNN.EX (如 600689.SH)
    """
    if not code:
        raise ValueError("股票代码不能为空")

    code = code.strip().upper()

    # 已是标准格式
    if re.match(r"^\d{6}\.(SH|SZ)$", code):
        return code

    # 600689SH / 000001SZ / 600689-SH / 600689_SH
    m = re.match(r"^(\d{6})[._-]?(SH|SZ)$", code)
    if m:
        return f"{m.group(1)}.{m.group(2)}"

    # SH600689 / SZ000001
    m = re.match(r"^(SH|SZ)[._-]?(\d{6})$", code)
    if m:
        return f"{m.group(2)}.{m.group(1)}"

    # 仅6位数字，不猜交易所，提示错误
    if re.match(r"^\d{6}$", code):
        raise ValueError("股票代码缺少交易所后缀，请使用 600689.SH / 000001.SZ 格式")

    raise ValueError("无效的股票代码格式，请使用 600689.SH / 000001.SZ 格式")


def _expected_kline_filename(stock_code: str, period: str, dividend_type: str) -> str:
    """根据现有命名规则推导保存的CSV文件名。"""
    stock_name = stock_code.replace('.', '_')
    period_map = {"1M": "1month"}
    filename_period = period_map.get(period, period)
    return f"{stock_name}_{filename_period}_{dividend_type}_kline.csv"


def _load_preview_rows(filepath: str, limit: int = 5) -> List[Dict]:
    if not os.path.exists(filepath):
        return []
    try:
        df = pd.read_csv(filepath, encoding='utf-8')
        # 统一时间格式，截取最后几条
        if 'datetime' in df.columns:
            try:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df['datetime'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
        tail_df = df.tail(limit)
        return tail_df.to_dict('records')
    except Exception as e:
        logger.error(f"预览读取失败: {filepath}, 错误: {e}")
        return []


def perform_instant_update(
    stock_code: str,
    dividend_type: str = 'front',
    include_periods: Optional[List[str]] = None,
    include_realtime: bool = True,
    preview_limit: int = 5,
) -> Dict:
    """
    执行一次即时更新：K线（多周期）+ 实时价格。

    返回结构：
    {
      'success': True/False,
      'stock_code': '600689.SH',
      'kline_files': { '1m': 'xxx.csv', ... },
      'kline_preview': { '1m': [ {row}, ... ], ... },
      'realtime_file': 'xxx.json',
      'realtime_data': {...},
      'message': '...'
    }
    """
    normalized_code = normalize_stock_code(stock_code)
    lock = _get_stock_lock(normalized_code)

    # 默认包含全部周期，与现有保存规则保持一致
    default_periods = ['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M']
    # include_periods=None 表示使用默认全部周期；[] 表示不拉取任何K线（仅实时）
    periods = default_periods if include_periods is None else include_periods

    result: Dict = {
        'success': False,
        'stock_code': normalized_code,
        'kline_files': {},
        'kline_preview': {},
        'realtime_file': None,
        'realtime_data': None,
        'message': ''
    }

    # 生成期望文件名映射
    for p in periods:
        result['kline_files'][p] = _expected_kline_filename(normalized_code, p, dividend_type)

    # 执行任务（同一股票加锁，避免并发重复更新）
    with lock:
        try:
            tasks = []
            with ThreadPoolExecutor(max_workers=2) as executor:
                # 任务1：K线（按所需周期统一调用收集器，内部保存为文件）
                if periods:
                    def _collect_kline():
                        collector = KLineDataCollector(normalized_code, dividend_type)
                        # 仅收集指定周期，输出CSV，文件命名与既有规则一致
                        collector.collect_all_data(periods=periods, start_date=None, end_date=None, count_limit=None, output_format='csv')
                        return True

                    tasks.append(executor.submit(_collect_kline))

                # 任务2：实时价格
                if include_realtime:
                    def _collect_realtime():
                        monitor = RealTimePriceMonitor(normalized_code)
                        price = monitor.get_real_time_price()
                        if price:
                            monitor.save_to_json(price)
                        return price

                    tasks.append(executor.submit(_collect_realtime))

                # 汇总结果
                realtime_data = None
                for fut in as_completed(tasks):
                    value = fut.result()
                    # 可能是实时数据
                    if isinstance(value, dict) and 'current_price' in value:
                        realtime_data = value

                # 填充实时结果
                if include_realtime:
                    result['realtime_file'] = normalized_code.replace('.', '_') + '_real_time_price.json'
                    result['realtime_data'] = realtime_data

            # 读取预览
            for p, fname in result['kline_files'].items():
                filepath = os.path.join(BASE_DIR, fname)
                result['kline_preview'][p] = _load_preview_rows(filepath, limit=preview_limit)

            result['success'] = True
            result['message'] = '即时更新完成'
            return result

        except Exception as e:
            logger.exception(f"即时更新失败: {normalized_code}, 错误: {e}")
            result['success'] = False
            result['message'] = f"即时更新失败: {e}"
            return result


# 便于直接脚本调用简单测试
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='即时查询服务（命令行）')
    parser.add_argument('--stock_code', '-s', required=True, help='股票代码，如 600689.SH')
    parser.add_argument('--dividend_type', '-d', default='front', choices=['none', 'front', 'back'])
    args = parser.parse_args()

    out = perform_instant_update(args.stock_code, dividend_type=args.dividend_type)
    print(out)


