# -*- coding: utf-8 -*-
import pandas as pd
from xtquant import xtdata
import os
import time
import argparse
from datetime import datetime, timedelta

# 统一数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def parse_date_param(date_str):
    """
    解析日期参数，支持特殊值 today 和 yesterday
    
    参数:
    date_str: 日期字符串，可以是 'today', 'yesterday' 或 'YYYY-MM-DD' 格式
    
    返回:
    tuple: (实际日期字符串, 原始参数)
    """
    if date_str is None:
        return None, None
    
    date_str = date_str.lower().strip()
    
    if date_str == 'today':
        # 智能交易日映射：获取最近的交易日
        actual_date = get_latest_trading_date()
        return actual_date, 'today'
    elif date_str == 'yesterday':
        # 智能交易日映射：获取上一个交易日
        actual_date = get_previous_trading_date()
        return actual_date, 'yesterday'
    else:
        # 验证日期格式
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str, date_str
        except ValueError:
            raise ValueError(f"无效的日期格式: {date_str}，请使用 'today', 'yesterday' 或 'YYYY-MM-DD' 格式")

# 全局缓存，避免重复警告和重复调用
_trading_dates_cache = {}
_api_warning_shown = False

def get_trading_dates_from_xtdata(days_back=30):
    """
    使用xtdata官方API获取交易日列表（带缓存优化）
    
    参数:
    days_back: 向前获取多少天的交易日
    
    返回:
    list: 交易日列表，格式为['YYYY-MM-DD', ...]
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
            if not _api_warning_shown:
                print("⚠️ 无法从xtdata获取交易日列表，使用备用方案")
                _api_warning_shown = True
            result = get_fallback_trading_dates(days_back)
            _trading_dates_cache[cache_key] = result
            return result
            
    except Exception as e:
        if not _api_warning_shown:
            print(f"⚠️ 获取交易日列表失败: {e}")
            print("💡 使用备用交易日计算方案（仅提示一次）")
            _api_warning_shown = True
        result = get_fallback_trading_dates(days_back)
        _trading_dates_cache[cache_key] = result
        return result

def get_fallback_trading_dates(days_back=30):
    """
    备用方案：简单的交易日计算（仅排除周末，不考虑节假日）
    
    参数:
    days_back: 向前计算多少天
    
    返回:
    list: 交易日列表
    """
    from datetime import datetime, timedelta
    
    trading_dates = []
    current_date = datetime.now().date()
    
    for i in range(days_back + 5):  # 多算几天确保有足够数据
        check_date = current_date - timedelta(days=i)
        # 周一到周五为交易日
        if check_date.weekday() < 5:
            trading_dates.append(check_date.strftime('%Y-%m-%d'))
    
    return sorted(trading_dates)

def is_trading_time():
    """
    判断当前是否为交易时间
    
    返回:
    bool: True表示是交易时间
    """
    from datetime import datetime
    
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()
    
    # 周末肯定不是交易时间
    if weekday >= 5:  # 周六、周日
        return False
    
    # 工作日的交易时间段
    # 早盘：9:15-11:30（集合竞价从9:15开始）
    # 午盘：13:00-15:00
    morning_start = datetime.strptime("09:15:00", "%H:%M:%S").time()
    morning_end = datetime.strptime("11:30:00", "%H:%M:%S").time()
    afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
    afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()
    
    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)

def get_latest_trading_date():
    """
    获取最近的交易日
    智能判断：如果当前是交易时间，返回今日；否则返回上一个交易日
    
    返回:
    str: 最近交易日的字符串格式 'YYYY-MM-DD'
    """
    from datetime import datetime
    
    # 获取交易日列表
    trading_dates = get_trading_dates_from_xtdata()
    
    if not trading_dates:
        # 备用方案
        return datetime.now().strftime('%Y-%m-%d')
    
    current_date_str = datetime.now().strftime('%Y-%m-%d')
    
    # 检查今日是否为交易日
    if current_date_str in trading_dates:
        # 今日是交易日
        if is_trading_time():
            # 当前是交易时间，返回今日
            print(f"💡 当前是交易时间，'today' 映射到今日: {current_date_str}")
            return current_date_str
        else:
            # 当前不是交易时间，检查时间
            current_hour = datetime.now().hour
            if current_hour < 9:
                # 早上9点前，还未开始交易，返回上一个交易日
                # 避免循环依赖，直接在交易日列表中查找
                current_index = trading_dates.index(current_date_str)
                if current_index > 0:
                    previous_date = trading_dates[current_index - 1]
                    print(f"💡 当前时间早于交易时间（{datetime.now().strftime('%H:%M')}），'today' 映射到上一交易日: {previous_date}")
                    return previous_date
                else:
                    print(f"💡 当前时间早于交易时间，但无上一交易日，'today' 映射到今日: {current_date_str}")
                    return current_date_str
            else:
                # 交易时间之后，返回今日
                print(f"💡 今日交易已结束，'today' 映射到今日: {current_date_str}")
                return current_date_str
    else:
        # 今日不是交易日，返回最近的交易日
        for date_str in reversed(trading_dates):
            if date_str < current_date_str:
                print(f"💡 今日非交易日，'today' 映射到最近交易日: {date_str}")
                return date_str
        
        # 如果没找到，返回列表中最新的日期
        latest_date = trading_dates[-1] if trading_dates else current_date_str
        print(f"💡 'today' 映射到最新交易日: {latest_date}")
        return latest_date

def get_previous_trading_date():
    """
    获取上一个交易日（相对于最近交易日的前一个交易日）
    
    返回:
    str: 上一个交易日的字符串格式 'YYYY-MM-DD'
    """
    # 获取交易日列表
    trading_dates = get_trading_dates_from_xtdata()
    
    if len(trading_dates) < 2:
        # 数据不足，使用备用方案
        from datetime import datetime, timedelta
        return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 获取最近的交易日
    latest_trading_date = get_latest_trading_date()
    
    # 在交易日列表中找到上一个交易日
    try:
        current_index = trading_dates.index(latest_trading_date)
        if current_index > 0:
            previous_date = trading_dates[current_index - 1]
            print(f"💡 'yesterday' 映射到上一交易日: {previous_date}")
            return previous_date
        else:
            # 当前是列表中最早的日期，计算更早的日期
            print(f"💡 'yesterday' 映射到计算的上一日期")
            return trading_dates[0]  # 返回最早的交易日
    except ValueError:
        # 最近交易日不在列表中，返回列表中最新的日期
        previous_date = trading_dates[-2] if len(trading_dates) >= 2 else trading_dates[-1]
        print(f"💡 'yesterday' 映射到: {previous_date}")
        return previous_date

class KLineDataCollector:
    """
    K线数据收集器 - 支持获取多种级别的K线数据
    """
    
    def __init__(self, stock_code, dividend_type='none'):
        """
        初始化数据收集器
        
        参数:
        stock_code: 股票代码，如 "600689.SH"
        dividend_type: 复权类型 'none'(不复权), 'front'(前复权), 'back'(后复权)
        """
        self.stock_code = stock_code
        self.dividend_type = dividend_type
        self.results = {}
        
        # 支持的周期配置
        self.periods_config = {
            # 分钟级别
            "1m": {"name": "1分钟", "count": 500},
            "5m": {"name": "5分钟", "count": 500},
            "15m": {"name": "15分钟", "count": 300},
            "30m": {"name": "30分钟", "count": 200},
            "60m": {"name": "60分钟", "count": 100},
            
            # 日级别以上
            "1d": {"name": "日线", "count": -1},
            "1w": {"name": "周线", "count": -1},
            "1M": {"name": "月线", "count": -1}
        }
    
    def get_kline_data(self, period, start_date=None, end_date=None, save_to_file=True, output_format='csv', count_limit=None):
        """
        获取指定周期的K线数据
        
        参数:
        period: 时间周期
        start_date: 开始日期 (支持 'today', 'yesterday', 'YYYY-MM-DD')
        end_date: 结束日期 (支持 'today', 'yesterday', 'YYYY-MM-DD')
        save_to_file: 是否保存为文件
        output_format: 输出格式，'csv' 或 'json'，默认为 'csv'
        count_limit: K线数量限制，None表示不限制
        
        返回:
        DataFrame: K线数据
        """
        
        period_info = self.periods_config.get(period, {"name": period, "count": -1})
        period_name = period_info["name"]
        count = period_info["count"]
        
        # 处理特殊日期参数
        actual_start_date, original_start = parse_date_param(start_date)
        actual_end_date, original_end = parse_date_param(end_date)
        
        # 判断是否使用特殊日期标识（today/yesterday）
        use_special_date_filename = (original_start in ['today', 'yesterday'] or 
                                   original_end in ['today', 'yesterday'])
        
        # 判断是否为自定义时间范围 - 但排除特殊日期情况
        is_custom_range = (actual_start_date is not None or actual_end_date is not None) and not use_special_date_filename
        
        print(f"开始获取 {self.stock_code} 的{period_name}数据（{self.dividend_type}复权）...")
        if use_special_date_filename:
            date_desc = f"（{original_start or '开始'} 到 {original_end or '最新'}）"
            print(f"使用特殊日期: {date_desc}")
            print("💡 提示：特殊日期参数将使用最新数据获取方式，确保能获取到当日数据")
        elif is_custom_range:
            print(f"使用自定义时间范围: {actual_start_date or '开始'} 到 {actual_end_date or '最新'}")
        
        if count_limit:
            print(f"K线数量限制: {count_limit} 根（取最新数据）")
        
        # 对分钟级数据跨日期查询给出警告（但排除特殊日期）
        if period in ['1m', '5m', '15m', '30m', '60m'] and is_custom_range and actual_start_date and actual_end_date:
            from datetime import datetime
            try:
                start_dt = datetime.strptime(actual_start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(actual_end_date, '%Y-%m-%d')
                if (end_dt - start_dt).days > 0:
                    print("⚠️  警告：分钟级数据跨日期查询可能失败，建议单日查询")
                    print(f"   如查询今日数据：--start_date today")
                    print(f"   如查询昨日数据：--start_date yesterday --end_date yesterday")
            except:
                pass
        
        try:
            # 下载历史数据
            xtdata.download_history_data(self.stock_code, period=period, incrementally=True)
            
            # 获取市场数据 - 优化获取逻辑
            if use_special_date_filename:
                # 对于今日/昨日等特殊日期，使用count方式获取最新数据，避免时间范围查询问题
                print("使用最新数据获取方式...")
                data = xtdata.get_market_data_ex(
                    field_list=[], 
                    stock_list=[self.stock_code], 
                    period=period, 
                    count=count if count > 0 else 1000,  # 获取足够多的数据，后续再筛选
                    dividend_type=self.dividend_type
                )
            elif is_custom_range and actual_start_date and actual_end_date:
                # 只有真正的自定义时间范围才使用时间范围查询
                print(f"使用时间范围查询: {actual_start_date} 到 {actual_end_date}")
                data = xtdata.get_market_data_ex(
                    field_list=[], 
                    stock_list=[self.stock_code], 
                    period=period, 
                    start_time=actual_start_date, 
                    end_time=actual_end_date,
                    count=-1,
                    dividend_type=self.dividend_type
                )
            else:
                # 默认获取全量数据
                data = xtdata.get_market_data_ex(
                    field_list=[], 
                    stock_list=[self.stock_code], 
                    period=period, 
                    count=count,
                    dividend_type=self.dividend_type
                )
            
            if data is None or (hasattr(data, '__len__') and len(data) == 0) or self.stock_code not in data:
                print(f"未能获取到 {self.stock_code} 的{period_name}数据")
                return None
            
            stock_data = data[self.stock_code]
            
            # 检查数据是否为空或None（stock_data已经是DataFrame）
            if stock_data is None or (hasattr(stock_data, 'empty') and stock_data.empty):
                print(f"API返回的 {self.stock_code} 的{period_name}数据为空")
                print("可能原因：")
                print("1. 时间范围内没有交易数据（如跨越休市日期）")
                print("2. 股票代码不正确")
                print("3. 当前时间段暂无数据")
                if period in ['1m', '5m', '15m', '30m', '60m']:
                    print("💡 建议：分钟级数据可能需要在交易时间内获取")
                return None
            
            # stock_data已经是DataFrame，直接处理
            df = self._process_dataframe(stock_data, period)
            
            if df is not None and not df.empty:
                # 如果使用特殊日期，需要进一步筛选数据
                if use_special_date_filename and 'datetime' in df.columns:
                    df = self._filter_by_special_date(df, original_start, original_end)
                
                if df is None or df.empty:
                    print(f"根据特殊日期筛选后，{period_name}数据为空")
                    if original_start == 'today':
                        print("💡 提示：今日可能还没有交易数据，可尝试获取昨日数据：--start_date yesterday")
                    return None
                
                original_count = len(df)
                
                # 应用K线数量限制（取最新的N根K线）
                if count_limit and count_limit > 0:
                    df = df.tail(count_limit).copy()
                    print(f"原始数据: {original_count} 条，限制后: {len(df)} 条{period_name}数据")
                else:
                    print(f"成功获取 {len(df)} 条{period_name}数据")
                
                if 'datetime' in df.columns and not df.empty:
                    print(f"时间范围: {df['datetime'].min()} 到 {df['datetime'].max()}")
                
                # 保存为文件，传递是否为自定义范围和特殊日期信息
                if save_to_file:
                    self._save_data(df, period, period_name, is_custom_range, 
                                  use_special_date_filename, original_start, original_end, count_limit, output_format)
                
                # 存储到结果中
                self.results[period] = df
                
            return df
            
        except Exception as e:
            print(f"获取{period_name}数据时出错: {e}")
            
            # 提供更详细的错误信息和建议
            error_str = str(e)
            if "iterable" in error_str or "NoneType" in error_str:
                print("❌ 错误原因：API返回的数据格式异常")
                print("💡 可能的解决方案：")
                print("   1. 检查股票代码格式（如：600689.SH, 000001.SZ）")
                print("   2. 确认网络连接和xtquant服务状态")
                print("   3. 检查系统时间是否正确")
                if use_special_date_filename:
                    print("   4. 特殊日期可能暂无数据，可尝试其他日期")
                    if original_start == 'today':
                        print("   5. 如果是获取今日数据，可能需要在交易时间内尝试")
                        print("      或尝试获取昨日数据：--start_date yesterday")
                elif period in ['1m', '5m', '15m', '30m', '60m']:
                    print("   4. 分钟级数据建议使用：--start_date today（不指定end_date）")
            else:
                print(f"详细错误信息: {error_str}")
            
            return None

    def _filter_by_special_date(self, df, original_start, original_end):
        """
        根据特殊日期筛选数据 - 智能交易日映射
        today: 最近的交易日（有数据的最新交易日）
        yesterday: 上一个交易日（相对于today的上一个交易日）
        """
        if 'datetime' not in df.columns:
            return df
        
        from datetime import datetime, timedelta
        
        # 获取所有可用的交易日，按日期排序
        available_dates = sorted(df['datetime'].dt.date.unique())
        
        if len(available_dates) == 0:
            print("❌ 数据中没有可用的交易日")
            return df
        
        # 智能映射特殊日期到实际交易日
        today_trading_date = None
        yesterday_trading_date = None
        
        if len(available_dates) >= 1:
            today_trading_date = available_dates[-1]  # 最新交易日
            
        if len(available_dates) >= 2:
            yesterday_trading_date = available_dates[-2]  # 上一个交易日
        
        print(f"💡 智能交易日映射:")
        print(f"   数据包含 {len(available_dates)} 个交易日")
        print(f"   最新交易日: {today_trading_date}")
        if yesterday_trading_date:
            print(f"   上一交易日: {yesterday_trading_date}")
        else:
            print(f"   上一交易日: 无（数据不足）")
        
        current_system_date = datetime.now().date()
        print(f"   系统当前日期: {current_system_date}")
        
        # 检查系统时间是否合理
        if today_trading_date:
            days_diff = abs((current_system_date - today_trading_date).days)
            if days_diff > 7:  # 超过7天差异认为系统时间有问题
                print(f"⚠️  系统时间可能不正确（与最新交易日相差{days_diff}天）")
                print(f"   建议检查系统时间设置")
        
        filtered_df = df.copy()
        
        # 确定实际的开始和结束日期
        actual_start_date = None
        actual_end_date = None
        
        if original_start == 'today':
            if today_trading_date:
                actual_start_date = today_trading_date
                print(f"🔍 开始日期 'today' 映射到: {today_trading_date}")
            else:
                print("❌ 无法找到对应的交易日数据")
                return df.iloc[0:0].copy()  # 返回空DataFrame，保持列结构
                
        elif original_start == 'yesterday':
            if yesterday_trading_date:
                actual_start_date = yesterday_trading_date
                print(f"🔍 开始日期 'yesterday' 映射到: {yesterday_trading_date}")
            else:
                print("❌ 数据不足，无法找到上一个交易日")
                print("💡 提示：尝试使用 'today' 获取最新交易日数据")
                return df.iloc[0:0].copy()  # 返回空DataFrame，保持列结构
        
        if original_end == 'today':
            if today_trading_date:
                actual_end_date = today_trading_date
                print(f"🔍 结束日期 'today' 映射到: {today_trading_date}")
        elif original_end == 'yesterday':
            if yesterday_trading_date:
                actual_end_date = yesterday_trading_date
                print(f"🔍 结束日期 'yesterday' 映射到: {yesterday_trading_date}")
        
        # 根据实际日期范围筛选数据
        if actual_start_date is not None:
            filtered_df = filtered_df[filtered_df['datetime'].dt.date >= actual_start_date]
            print(f"📅 筛选开始日期 >= {actual_start_date}")
            
        if actual_end_date is not None:
            filtered_df = filtered_df[filtered_df['datetime'].dt.date <= actual_end_date]
            print(f"📅 筛选结束日期 <= {actual_end_date}")
        
        # 如果既有开始日期又有结束日期，显示最终的日期范围
        if actual_start_date and actual_end_date:
            print(f"📊 最终日期范围: {actual_start_date} 到 {actual_end_date}")
        elif actual_start_date:
            print(f"📊 最终日期范围: 从 {actual_start_date} 开始")
        elif actual_end_date:
            print(f"📊 最终日期范围: 到 {actual_end_date} 结束")
        
        return filtered_df

    def _process_dataframe(self, stock_data, period):
        """
        处理xtdata返回的DataFrame数据
        """
        if stock_data is None or not hasattr(stock_data, 'empty') or stock_data.empty:
            print(f"股票数据为空或格式错误: {type(stock_data)}")
            return None
            
        df = stock_data.copy()
        
        # 时间处理 - xtdata返回的DataFrame中时间列为'time'
        if 'time' in df.columns:
            # 修复时区问题：将UTC时间转换为中国时间（UTC+8）
            df['datetime'] = pd.to_datetime(df['time'], unit='ms', utc=True).dt.tz_convert('Asia/Shanghai')
            # 移除时区信息，保留本地时间
            df['datetime'] = df['datetime'].dt.tz_localize(None)
            df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
            
            # 根据周期添加不同的时间字段
            if period in ['1m', '5m', '15m', '30m', '60m']:
                df['time_str'] = df['datetime'].dt.strftime('%H:%M:%S')
            elif period == '1w':
                df['year'] = df['datetime'].dt.year
                df['week_number'] = df['datetime'].dt.isocalendar().week
                df['year_week'] = df['year'].astype(str) + '-W' + df['week_number'].astype(str).str.zfill(2)
            elif period == '1M':
                df['year'] = df['datetime'].dt.year
                df['month'] = df['datetime'].dt.month
                df['year_month'] = df['datetime'].dt.strftime('%Y-%m')
                df['quarter'] = df['datetime'].dt.quarter
                df['year_quarter'] = df['year'].astype(str) + '-Q' + df['quarter'].astype(str)
        
        # 检查是否有基础的价格数据
        if 'close' not in df.columns:
            print(f"未获取到有效的价格数据，数据列: {list(df.columns)}")
            return None
        
        # 计算技术指标
        if 'open' in df.columns and 'close' in df.columns:
            df['change'] = df['close'] - df['open']
            df['change_pct'] = (df['change'] / df['open'] * 100).round(2)
            
            if 'high' in df.columns and 'low' in df.columns:
                df['amplitude'] = ((df['high'] - df['low']) / df['open'] * 100).round(2)
        
        # 添加元数据
        df['stock_code'] = self.stock_code
        df['period'] = period
        df['dividend_type'] = self.dividend_type  # 添加复权类型标识
        
        return df
    
    def _save_data(self, df, period, period_name, is_custom_range, use_special_date_filename, original_start, original_end, count_limit, output_format='csv'):
        """
        保存数据为指定格式文件（支持CSV和JSON）
        
        参数:
        output_format: 输出格式，'csv' 或 'json'，默认为 'csv'
        """
        try:
            import json
            stock_name = self.stock_code.replace('.', '_')
            
            # 文件名period映射：避免Windows文件系统大小写不敏感导致的冲突
            filename_period_map = {
                "1M": "1month"  # 月线映射为1month，避免与1m（1分钟线）冲突
            }
            filename_period = filename_period_map.get(period, period)
            
            # 构建文件名
            filename_parts = [stock_name, filename_period, self.dividend_type]
            
            # 文件命名逻辑优先级：
            # 1. 如果使用特殊日期标识（today/yesterday），直接使用特殊标识
            # 2. 否则，如果是自定义时间范围，使用实际日期
            # 3. 否则，不添加时间范围（全量数据）
            # 4. 如果有K线数量限制，添加数量信息
            
            if use_special_date_filename:
                # 使用特殊日期标识，确保文件名固定
                if original_start and original_end:
                    if original_start == original_end:
                        filename_parts.append(original_start)
                    else:
                        filename_parts.append(f"{original_start}_{original_end}")
                elif original_start:
                    filename_parts.append(original_start)
                elif original_end:
                    filename_parts.append(original_end)
                    
            elif is_custom_range and 'datetime' in df.columns and not df.empty:
                # 自定义范围且非特殊日期，使用实际日期
                start_date = df['datetime'].min().strftime('%Y%m%d')
                end_date = df['datetime'].max().strftime('%Y%m%d')
                
                # 如果开始和结束日期相同，只显示一个日期
                if start_date == end_date:
                    filename_parts.append(start_date)
                else:
                    filename_parts.extend([start_date, end_date])
            
            # 添加K线数量信息（如果有限制）
            if count_limit and count_limit > 0:
                filename_parts.append(f"last{count_limit}")
            
            # 根据输出格式生成文件名和保存数据
            if output_format.lower() == 'json':
                filename = "_".join(filename_parts) + "_kline.json"
                # 保存到数据目录
                if not os.path.isabs(filename):
                    filename = os.path.join(DATA_DIR, filename)
                self._save_to_json(df, filename, period_name)
            else:
                # 默认保存为CSV
                filename = "_".join(filename_parts) + "_kline.csv"
                # 保存到数据目录
                if not os.path.isabs(filename):
                    filename = os.path.join(DATA_DIR, filename)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"{period_name}数据已保存到: {filename}")
            
        except Exception as e:
            print(f"保存{period_name}数据时出错: {e}")
    
    def _save_to_json(self, df, filename, period_name):
        """
        将DataFrame保存为JSON格式
        """
        try:
            import json
            from datetime import datetime
            
            # 准备JSON数据结构
            if df.empty:
                print(f"⚠️ {period_name}数据为空，无法保存JSON文件")
                return
            
            # 构建JSON数据结构
            json_data = {
                "metadata": {
                    "stock_code": self.stock_code,
                    "period": df['period'].iloc[0] if 'period' in df.columns else "unknown",
                    "dividend_type": self.dividend_type,
                    "data_count": len(df),
                    "export_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                "time_range": {},
                "kline_data": []
            }
            
            # 添加时间范围信息
            if 'datetime' in df.columns:
                json_data["time_range"] = {
                    "start_time": df['datetime'].min().strftime('%Y-%m-%d %H:%M:%S'),
                    "end_time": df['datetime'].max().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # 转换DataFrame数据为JSON友好格式
            for index, row in df.iterrows():
                kline_record = {}
                
                # 处理每一列数据
                for column in df.columns:
                    value = row[column]
                    
                    # 处理datetime类型
                    if pd.isna(value):
                        kline_record[column] = None
                    elif column == 'datetime' and hasattr(value, 'strftime'):
                        kline_record[column] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif column in ['time', 'date', 'time_str'] and isinstance(value, str):
                        kline_record[column] = value
                    elif isinstance(value, (int, float)):
                        # 保留数值精度，对价格相关字段保留2位小数
                        if column in ['open', 'high', 'low', 'close', 'change', 'change_pct', 'amplitude']:
                            kline_record[column] = round(float(value), 2) if not pd.isna(value) else None
                        else:
                            kline_record[column] = value
                    else:
                        kline_record[column] = str(value)
                
                json_data["kline_data"].append(kline_record)
            
            # 保存JSON文件
            # 确保保存到数据目录
            if not os.path.isabs(filename):
                filename = os.path.join(DATA_DIR, filename)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"{period_name}数据已保存到: {filename}")
            print(f"📊 JSON格式包含 {len(json_data['kline_data'])} 条K线记录")
            
        except Exception as e:
            print(f"保存{period_name}JSON数据时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def collect_all_data(self, periods=None, start_date=None, end_date=None, count_limit=None, output_format='csv'):
        """
        收集所有级别的K线数据
        
        参数:
        periods: 要收集的周期列表，None表示收集所有周期
        start_date: 开始日期 (支持 'today', 'yesterday', 'YYYY-MM-DD')
        end_date: 结束日期 (支持 'today', 'yesterday', 'YYYY-MM-DD')
        count_limit: K线数量限制，None表示不限制
        output_format: 输出格式，'csv' 或 'json'，默认为 'csv'
        """
        
        if periods is None:
            periods = list(self.periods_config.keys())
        
        # 处理特殊日期参数
        actual_start_date, original_start = parse_date_param(start_date)
        actual_end_date, original_end = parse_date_param(end_date)
        
        # 判断是否为自定义时间范围
        is_custom_range = actual_start_date is not None or actual_end_date is not None
        
        # 构建显示描述
        if original_start in ['today', 'yesterday'] or original_end in ['today', 'yesterday']:
            range_desc = f"（{original_start or '开始'} 到 {original_end or '最新'}）"
        elif is_custom_range:
            range_desc = f"（{actual_start_date or '开始'} 到 {actual_end_date or '最新'}）"
        else:
            range_desc = "（全量数据）"
        
        # 添加K线数量描述
        count_desc = f" - 限制最新 {count_limit} 根K线" if count_limit else ""
        
        # 添加格式描述
        format_desc = f" - 输出格式: {output_format.upper()}"
        
        print(f"开始收集 {self.stock_code} 的多级别K线数据（{self.dividend_type}复权）{range_desc}{count_desc}{format_desc}...")
        print(f"收集周期: {', '.join(periods)}")
        print("="*60)
        
        success_count = 0
        
        for i, period in enumerate(periods, 1):
            print(f"\n[{i}/{len(periods)}] 正在处理 {period} 数据...")
            
            # 使用原始参数（可能包含today/yesterday）
            df = self.get_kline_data(period, start_date, end_date, save_to_file=True, output_format=output_format, count_limit=count_limit)
            if df is not None and not df.empty:
                success_count += 1
            
            # 避免请求过于频繁
            if i < len(periods):
                time.sleep(1)
        
        print("\n" + "="*60)
        print(f"数据收集完成！成功: {success_count}/{len(periods)}")
        
        return self.results
    
    def get_summary(self):
        """
        获取数据摘要
        """
        if not self.results:
            print("暂无数据")
            return
        
        print(f"\n{self.stock_code} K线数据摘要（{self.dividend_type}复权）:")
        print("="*80)
        print(f"{'周期':<8} {'数据量':<8} {'开始时间':<20} {'结束时间':<20} {'最新价格':<10}")
        print("-"*80)
        
        for period, df in self.results.items():
            period_name = self.periods_config.get(period, {"name": period})["name"]
            count = len(df)
            
            if 'datetime' in df.columns:
                start_time = df['datetime'].min().strftime('%Y-%m-%d %H:%M:%S')
                end_time = df['datetime'].max().strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_time = "N/A"
                end_time = "N/A"
            
            latest_price = f"{df['close'].iloc[-1]:.2f}" if 'close' in df.columns else "N/A"
            
            print(f"{period_name:<8} {count:<8} {start_time:<20} {end_time:<20} {latest_price:<10}")

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='K线数据收集器')
    
    # 必需参数
    parser.add_argument('--stock_code', '-s', type=str, required=True,
                       help='股票代码，如: 600689.SH')
    
    # 可选参数
    parser.add_argument('--dividend_type', '-d', type=str, 
                       choices=['none', 'front', 'back'], default='none',
                       help='复权类型: none(不复权), front(前复权), back(后复权)')
    
    parser.add_argument('--periods', '-p', type=str, nargs='+',
                       choices=['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'],
                       help='要收集的周期，可多选，如: --periods 1d 1w 1M')
    
    parser.add_argument('--data_type', '-t', type=str, 
                       choices=['all', 'minute', 'daily', 'custom'], default='all',
                       help='数据类型: all(所有), minute(分钟级), daily(日/周/月级), custom(自定义)')
    
    parser.add_argument('--start_date', type=str,
                       help='开始日期，格式: YYYY-MM-DD 或使用 today/yesterday')
    
    parser.add_argument('--end_date', type=str,
                       help='结束日期，格式: YYYY-MM-DD 或使用 today/yesterday')
    
    parser.add_argument('--count', '-c', type=int,
                       help='K线数量限制，获取最新的N根K线（如: --count 20）')
    
    parser.add_argument('--output_format', '-f', type=str, 
                       choices=['csv', 'json'], default='csv',
                       help='输出格式: csv(CSV格式), json(JSON格式)，默认为csv')
    
    parser.add_argument('--no_save', action='store_true',
                       help='不保存文件')
    
    return parser.parse_args()

def main():
    """
    主函数：支持命令行参数和交互式两种模式
    """
    
    # 尝试解析命令行参数
    import sys
    if len(sys.argv) > 1:
        # 命令行模式
        args = parse_arguments()
        
        stock_code = args.stock_code
        dividend_type = args.dividend_type
        
        # 创建数据收集器
        collector = KLineDataCollector(stock_code, dividend_type)
        
        # 确定要收集的周期
        if args.data_type == 'all':
            periods = None
        elif args.data_type == 'minute':
            periods = ["1m", "5m", "15m", "30m", "60m"]
        elif args.data_type == 'daily':
            periods = ["1d", "1w", "1M"]
        elif args.data_type == 'custom' and args.periods:
            periods = args.periods
        else:
            periods = None
        
        # 收集数据
        save_file = not args.no_save
        if save_file:
            results = collector.collect_all_data(periods, args.start_date, args.end_date, args.count, args.output_format)
        else:
            # 如果不保存文件，使用get_kline_data获取数据但不保存
            results = {}
            for period in (periods or list(collector.periods_config.keys())):
                df = collector.get_kline_data(period, args.start_date, args.end_date, save_to_file=False, count_limit=args.count)
                if df is not None:
                    results[period] = df
        
        # 显示摘要
        collector.get_summary()
        
        print(f"\n使用命令行示例:")
        print(f"python {sys.argv[0]} --stock_code 600689.SH --dividend_type front --data_type all")
        print(f"python {sys.argv[0]} -s 600689.SH -d back -t minute --start_date 2024-01-01")
        print(f"python {sys.argv[0]} -s 600689.SH -d front -t minute --start_date today --count 20")
        print(f"python {sys.argv[0]} -s 600689.SH -f json -t all")
        print(f"python {sys.argv[0]} --stock_code 600689.SH --output_format json --start_date yesterday")
        
    else:
        # 交互式模式（原有逻辑）
        print("=" * 60)
        print("🚀 K线数据收集器 - 交互式模式")
        print("=" * 60)
        
        # 输入股票代码
        print("\n📊 请输入股票代码:")
        print("格式说明:")
        print("  上海证券交易所: 600689.SH")
        print("  深圳证券交易所: 000001.SZ")
        print("  默认: 600689.SH (上海三毛)")
        
        stock_code_input = input("\n请输入股票代码: ").strip()
        stock_code = stock_code_input if stock_code_input else "600689.SH"
        
        print(f"\n✅ 已选择股票: {stock_code}")
        
        try:
            # 选择复权类型
            print("\n💰 请选择复权类型:")
            print("1. 不复权 (none) - 原始价格数据")
            print("2. 前复权 (front) - 适合技术分析")
            print("3. 后复权 (back) - 适合投资分析")
            
            dividend_choice = input("请输入选择 (1-3, 默认为1): ").strip() or "1"
            dividend_map = {"1": "none", "2": "front", "3": "back"}
            dividend_type = dividend_map.get(dividend_choice, "none")
            
            print(f"✅ 已选择复权类型: {dividend_type}")
            
            # 创建数据收集器
            collector = KLineDataCollector(stock_code, dividend_type)
            
            # 选择要收集的数据类型
            print("\n📈 请选择要收集的数据类型:")
            print("1. 所有数据（推荐）")
            print("2. 仅分钟级数据")
            print("3. 仅日/周/月数据")
            print("4. 自定义选择")
            
            choice = input("请输入选择 (1-4, 默认为1): ").strip() or "1"
            
            if choice == "1":
                periods = None
            elif choice == "2":
                periods = ["1m", "5m", "15m", "30m", "60m"]
            elif choice == "3":
                periods = ["1d", "1w", "1M"]
            elif choice == "4":
                print("可选周期: 1m, 5m, 15m, 30m, 60m, 1d, 1w, 1M")
                periods_input = input("请输入周期（用逗号分隔）: ").strip()
                periods = [p.strip() for p in periods_input.split(",") if p.strip()]
            else:
                periods = None
            
            # 询问是否指定时间范围
            print("\n📅 是否指定时间范围？")
            print("1. 获取全量数据（推荐）")
            print("2. 指定时间范围")
            
            time_choice = input("请输入选择 (1-2, 默认为1): ").strip() or "1"
            
            start_date = None
            end_date = None
            
            if time_choice == "2":
                print("时间格式说明:")
                print("  标准格式: YYYY-MM-DD (如: 2024-01-01)")
                print("  特殊参数: today, yesterday")
                print("  注意: 使用 today/yesterday 时文件名固定，便于定期更新")
                
                start_date = input("请输入开始日期（可选）: ").strip() or None
                end_date = input("请输入结束日期（可选）: ").strip() or None
                
                if start_date or end_date:
                    print(f"✅ 时间范围: {start_date or '开始'} 到 {end_date or '最新'}")
                    if start_date in ['today', 'yesterday'] or end_date in ['today', 'yesterday']:
                        print("🔄 使用特殊日期参数，文件名将固定便于定期更新")
            
            # 询问是否限制K线数量
            print("\n📊 是否限制K线数量？")
            print("1. 获取全部数据（推荐）")
            print("2. 限制最新N根K线")
            
            count_choice = input("请输入选择 (1-2, 默认为1): ").strip() or "1"
            
            count_limit = None
            if count_choice == "2":
                while True:
                    try:
                        count_input = input("请输入K线数量（如: 20）: ").strip()
                        if count_input:
                            count_limit = int(count_input)
                            if count_limit > 0:
                                print(f"✅ 将获取最新 {count_limit} 根K线")
                                break
                            else:
                                print("❌ 请输入大于0的数字")
                        else:
                            break
                    except ValueError:
                        print("❌ 请输入有效的数字")
            
            # 选择输出格式
            print("\n💾 请选择输出格式:")
            print("1. CSV格式（推荐，适合Excel打开）")
            print("2. JSON格式（适合程序处理）")
            
            format_choice = input("请输入选择 (1-2, 默认为1): ").strip() or "1"
            output_format = "csv" if format_choice == "1" else "json"
            
            print(f"✅ 已选择输出格式: {output_format.upper()}")
            
            # 收集数据
            results = collector.collect_all_data(periods, start_date, end_date, count_limit, output_format)
            
            # 显示摘要
            collector.get_summary()
            
            # 显示部分数据预览
            if results:
                print(f"\n数据预览示例（最新数据）:")
                print("="*80)
                
                for period, df in list(results.items())[:3]:
                    period_name = collector.periods_config.get(period, {"name": period})["name"]
                    print(f"\n{period_name} 最新3条数据:")
                    
                    display_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                    available_cols = [col for col in display_cols if col in df.columns]
                    if available_cols:
                        print(df[available_cols].tail(3).to_string(index=False))
            
        except Exception as e:
            print(f"程序执行出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()