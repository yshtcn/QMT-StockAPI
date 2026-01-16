# -*- coding: utf-8 -*-
"""
时间窗口检查工具（简化逻辑）
供批处理文件调用，返回退出码：
- 0: 当前处于活跃窗口（周一至周五 09:00-15:30）
- 1: 当前不在活跃窗口

说明：
- 采用简化规则，不依赖交易日历与节假日数据，仅按周一至周五与时间段判断。
- 兼容旧参数 --extend-minutes / --extend-time，但已不再生效。
"""

import sys
import argparse
from datetime import datetime, time
from xtquant import xtdata

# 全局缓存，避免重复警告和重复调用
_trading_dates_cache = {}
_api_warning_shown = False

def get_trading_dates_from_xtdata(days_back=10):
    """
    使用xtdata官方API获取交易日列表（带缓存优化）
    """
    global _trading_dates_cache, _api_warning_shown
    
    # 检查缓存
    cache_key = f"trading_dates_{days_back}"
    if cache_key in _trading_dates_cache:
        return _trading_dates_cache[cache_key]
    
    try:
        from datetime import datetime, timedelta
        
        # 先下载节假日数据（确保数据最新）
        xtdata.download_holiday_data()
        
        # 计算查询的时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # 获取交易日列表
        trading_dates = xtdata.get_trading_dates(
            market='XSHG',  # 上海证券交易所
            start_time=start_date.strftime('%Y%m%d'),
            end_time=end_date.strftime('%Y%m%d')
        )
        
        if trading_dates and len(trading_dates) > 0:
            # 转换格式：从 '20250725' 转为 '2025-07-25'
            formatted_dates = []
            for date_str in trading_dates:
                if len(date_str) == 8:  # YYYYMMDD格式
                    formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    formatted_dates.append(formatted)
            
            result = sorted(formatted_dates)
            _trading_dates_cache[cache_key] = result
            return result
        else:
            result = get_fallback_trading_dates(days_back)
            _trading_dates_cache[cache_key] = result
            return result
            
    except Exception as e:
        result = get_fallback_trading_dates(days_back)
        _trading_dates_cache[cache_key] = result
        return result

def get_fallback_trading_dates(days_back=10):
    """
    备用方案：简单的交易日计算（仅排除周末）
    """
    from datetime import datetime, timedelta
    
    trading_dates = []
    current_date = datetime.now().date()
    
    for i in range(days_back + 5):
        check_date = current_date - timedelta(days=i)
        # 周一到周五为交易日
        if check_date.weekday() < 5:
            trading_dates.append(check_date.strftime('%Y-%m-%d'))
    
    return sorted(trading_dates)

def is_trading_day(date_str):
    """
    判断指定日期是否为交易日（兼容保留，当前未使用交易日历）。
    现逻辑：仅用于向后兼容，简单以周一至周五作为交易日。
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        return date_obj.weekday() < 5
    except Exception:
        return False

def is_active_window():
    """
    简化后的活跃窗口判断：周一至周五 09:00-15:30。
    """
    now = datetime.now()
    # 周一(0)至周五(4)
    if now.weekday() >= 5:
        return False
    current_time = now.time()
    window_start = time(9, 0, 0)    # 09:00:00
    window_end = time(15, 30, 0)    # 15:30:00
    return window_start <= current_time <= window_end

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='活跃时间窗口检查工具（周一至周五 09:00-15:30）')
    # 兼容旧参数但不生效
    parser.add_argument('--extend-minutes', type=int, default=0, help='已废弃，无效参数')
    parser.add_argument('--extend-time', type=str, help='已废弃，无效参数')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    return parser.parse_args()

def main():
    """
    主函数
    """
    try:
        args = parse_arguments()
        
        # 调用活跃窗口检查
        is_trading = is_active_window()
        
        # 如果需要显示详细信息
        if args.verbose:
            now = datetime.now()
            date_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            if is_trading:
                print(f"✅ {date_str} - 当前处于活跃窗口（周一至周五 09:00-15:30）")
            else:
                print(f"❌ {date_str} - 当前不在活跃窗口（周一至周五 09:00-15:30）")
        
        if is_trading:
            # 当前是交易时间，返回退出码 0
            sys.exit(0)
        else:
            # 当前不是交易时间，返回退出码 1
            sys.exit(1)
            
    except Exception as e:
        if '--verbose' in sys.argv or '-v' in sys.argv:
            print(f"❌ 检查交易时间时出错: {e}")
        # 出错时，默认返回非交易时间（退出码 1）
        sys.exit(1)

if __name__ == "__main__":
    main() 