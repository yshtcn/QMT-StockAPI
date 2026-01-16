# -*- coding: utf-8 -*-
import pandas as pd
from xtquant import xtdata
import os
import time
import argparse
from datetime import datetime, timedelta
import sys
import json

# 全局缓存，避免重复警告和重复调用
_trading_dates_cache = {}  # 清空缓存，让新的交易日逻辑生效
_api_warning_shown = False

# 统一数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

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
        
        # 计算查询的时间范围（包含未来几天以确保能获取下一个交易日）
        now = datetime.now()
        start_date = now - timedelta(days=days_back)
        end_date = now + timedelta(days=10)  # 向未来获取10天，确保能找到下一个交易日
        
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
    
    # 向前获取历史交易日
    for i in range(days_back):
        check_date = current_date - timedelta(days=i)
        # 周一到周五为交易日
        if check_date.weekday() < 5:
            trading_dates.append(check_date.strftime('%Y-%m-%d'))
    
    # 向后获取未来交易日（确保能找到下一个交易日）
    for i in range(1, 11):  # 未来10天
        check_date = current_date + timedelta(days=i)
        # 周一到周五为交易日
        if check_date.weekday() < 5:
            trading_dates.append(check_date.strftime('%Y-%m-%d'))
    
    return sorted(trading_dates)

def is_trading_day(date_obj):
    """
    判断指定日期是否为交易日
    
    参数:
    date_obj: datetime.date 对象或字符串
    
    返回:
    bool: True表示是交易日
    """
    try:
        # 获取交易日列表
        trading_dates = get_trading_dates_from_xtdata(10)  # 获取最近10天足够了
        
        if isinstance(date_obj, str):
            check_date = date_obj
        else:
            check_date = date_obj.strftime('%Y-%m-%d')
        
        return check_date in trading_dates
        
    except Exception as e:
        print(f"⚠️ 判断交易日失败: {e}，使用备用方案")
        # 备用方案：简单的周末检查
        if isinstance(date_obj, str):
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        return date_obj.weekday() < 5

def get_next_trading_date(from_date=None):
    """
    获取下一个交易日
    
    参数:
    from_date: 起始日期，默认为今日
    
    返回:
    datetime.date: 下一个交易日
    """
    try:
        if from_date is None:
            from_date = datetime.now().date()
        elif isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        
        # 获取交易日列表
        trading_dates = get_trading_dates_from_xtdata(30)  # 获取30天够用了
        
        # 转换为date对象列表并排序
        trading_date_objs = []
        for date_str in trading_dates:
            try:
                trading_date_objs.append(datetime.strptime(date_str, '%Y-%m-%d').date())
            except:
                continue
        
        trading_date_objs.sort()
        
        # 找到下一个交易日
        for trading_date in trading_date_objs:
            if trading_date > from_date:
                return trading_date
        
        # 如果没找到，计算一个大概的日期（备用方案）
        next_date = from_date + timedelta(days=1)
        while next_date.weekday() >= 5:  # 跳过周末
            next_date += timedelta(days=1)
        return next_date
        
    except Exception as e:
        print(f"⚠️ 获取下一交易日失败: {e}，使用备用方案")
        # 备用方案
        if from_date is None:
            from_date = datetime.now().date()
        
        next_date = from_date + timedelta(days=1)
        while next_date.weekday() >= 5:  # 跳过周末
            next_date += timedelta(days=1)
        return next_date

class RealTimePriceMonitor:
    """
    实时股价监控器
    """
    
    def __init__(self, stock_code="600689.SH"):
        """
        初始化实时股价监控器
        
        参数:
        stock_code: 股票代码，默认为600689.SH（上海三毛）
        """
        self.stock_code = stock_code
        self.stock_name = self._get_stock_name()
        
    def _get_stock_name(self):
        """
        根据股票代码获取股票名称
        """
        # 股票代码-名称映射（包含指数和个股）
        stock_names = {
            # 主要指数
            "000001.SH": "上证指数",
            "399001.SZ": "深证成指", 
            "399006.SZ": "创业板指",
            "000300.SH": "沪深300",
            "000016.SH": "上证50",
            "000905.SH": "中证500",
            
            # 热门个股 - 上海证券交易所
            "600689.SH": "上海三毛",
            "600000.SH": "浦发银行",
            "600036.SH": "招商银行", 
            "600519.SH": "贵州茅台",
            "600276.SH": "恒瑞医药",
            "600588.SH": "用友网络",
            
            # 热门个股 - 深圳证券交易所
            "000001.SZ": "平安银行", 
            "000002.SZ": "万科A",
            "000858.SZ": "五粮液",
            "000876.SZ": "新希望",
            "002415.SZ": "海康威视",
            "300014.SZ": "亿纬锂能",
            
            # ETF基金
            "510050.SH": "上证50ETF",
            "510300.SH": "沪深300ETF", 
            "159919.SZ": "沪深300ETF",
            "159915.SZ": "创业板ETF"
        }
        return stock_names.get(self.stock_code, "未知股票")
    
    def is_trading_time(self):
        """
        简化的活跃窗口判断：周一至周五 09:00-15:30。
        """
        now = datetime.now()
        if now.weekday() >= 5:  # 周六、周日
            return False
        current_time = now.time()
        window_start = datetime.strptime("09:00:00", "%H:%M:%S").time()
        window_end = datetime.strptime("15:30:00", "%H:%M:%S").time()
        return window_start <= current_time <= window_end
    
    def get_next_trading_time(self):
        """
        获取下次交易时间（使用官方交易日历）
        
        返回:
        datetime: 下次交易开始时间
        """
        now = datetime.now()
        current_time = now.time()
        current_date_str = now.strftime('%Y-%m-%d')
        
        # 今天的交易时间点
        morning_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
        afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()
        
        # 如果今天是交易日
        if is_trading_day(current_date_str):
            # 如果当前时间早于上午开盘
            if current_time < morning_start:
                next_trading = datetime.combine(now.date(), morning_start)
                return next_trading
            
            # 如果当前时间在上午休市到下午开盘之间
            elif current_time < afternoon_start:
                next_trading = datetime.combine(now.date(), afternoon_start)
                return next_trading
            
            # 如果当前时间在下午交易时间内，返回下一个交易日的开盘时间
            elif current_time <= afternoon_end:
                # 正在下午交易时间内，下次交易时间是下一个交易日的上午开盘
                try:
                    next_trading_date = get_next_trading_date(now.date())
                    next_trading = datetime.combine(next_trading_date, morning_start)
                    return next_trading
                except Exception as e:
                    print(f"⚠️ 计算下一交易时间失败: {e}，使用备用方案")
                    # 备用方案：从今天开始找下一个工作日
                    days_ahead = 1  # 这里下午交易中，下次确实是明天
                    while True:
                        next_day = now + timedelta(days=days_ahead)
                        if next_day.weekday() < 5:  # 工作日
                            next_trading = datetime.combine(next_day.date(), morning_start)
                            return next_trading
                        days_ahead += 1
        
        # 其他情况：找到下一个交易日的上午开盘时间
        try:
            next_trading_date = get_next_trading_date(now.date())
            next_trading = datetime.combine(next_trading_date, morning_start)
            return next_trading
        except Exception as e:
            print(f"⚠️ 计算下一交易时间失败: {e}，使用备用方案")
            # 备用方案：简单地找下一个工作日
            days_ahead = 1
            while True:
                next_day = now + timedelta(days=days_ahead)
                if next_day.weekday() < 5:  # 工作日
                    next_trading = datetime.combine(next_day.date(), morning_start)
                    return next_trading
                days_ahead += 1
    
    def get_trading_status_info(self):
        """
        获取交易状态信息
        
        返回:
        dict: 包含交易状态的信息
        """
        now = datetime.now()
        is_trading = self.is_trading_time()
        next_trading = self.get_next_trading_time()
        
        status_info = {
            'is_trading': is_trading,
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'next_trading_time': next_trading.strftime('%Y-%m-%d %H:%M:%S'),
            'weekday': now.weekday(),
            'weekday_name': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][now.weekday()]
        }
        
        return status_info
    
    def get_real_time_price(self):
        """
        获取实时股价数据
        
        返回:
        dict: 包含股价信息的字典，失败返回None
        """
        try:
            # 尝试多种方式获取数据
            print(f"🔍 正在获取 {self.stock_code} 的实时数据...")
            print(f"🔧 调试：股票代码 = {self.stock_code}, 股票名称 = {self.stock_name}")
            
            # 检查代码类型（仅用于信息提示）
            if self.stock_code in ["000001.SH", "399001.SZ", "399006.SZ"]:
                print(f"📊 检测到指数代码 {self.stock_code}，正在获取指数数据")
            
            # 方法1：获取实时tick数据
            print(f"🔄 方法1：尝试获取tick数据...")
            data = xtdata.get_full_tick([self.stock_code])
            
            if not data or self.stock_code not in data:
                print(f"⚠️  Tick数据获取失败，尝试其他方式...")
                
                # 方法2：尝试获取最新K线数据
                try:
                    print(f"🔄 方法2：尝试使用K线数据作为替代...")
                    return self._get_price_from_kline()
                        
                except Exception as e:
                    print(f"⚠️  K线数据获取也失败: {e}")
                
                print(f"❌ 未能获取到 {self.stock_code} 的任何数据")
                return None
            
            tick_data = data[self.stock_code]
            
            if tick_data is None or len(tick_data) == 0:
                print(f"❌ {self.stock_code} 的实时数据为空")
                return None
            
            print(f"🔧 调试信息：tick_data类型 = {type(tick_data)}")
            
            # xtquant的get_full_tick返回的可能是dict格式，需要特殊处理
            if isinstance(tick_data, dict):
                print(f"🔧 调试信息：tick数据为dict格式，键: {list(tick_data.keys())}")
                
                # 检查是否有有效的价格数据
                if 'lastPrice' in tick_data and tick_data['lastPrice'] is not None and tick_data['lastPrice'] > 0:
                    print(f"✅ 从tick数据获取价格: {tick_data['lastPrice']}")
                    
                    # 直接从tick dict构建价格信息
                    price_info = {
                        'stock_code': self.stock_code,
                        'stock_name': self.stock_name,
                        'current_price': float(tick_data.get('lastPrice', 0)),
                        'open_price': float(tick_data.get('open', 0)),
                        'high_price': float(tick_data.get('high', 0)),
                        'low_price': float(tick_data.get('low', 0)),
                        'pre_close': float(tick_data.get('lastClose', 0)),
                        'volume': int(tick_data.get('volume', 0)),
                        'amount': float(tick_data.get('amount', 0)),
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'system_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 计算涨跌幅
                    if price_info['pre_close'] and price_info['pre_close'] != 0:
                        change = price_info['current_price'] - price_info['pre_close']
                        change_pct = (change / price_info['pre_close']) * 100
                        price_info['change'] = round(change, 2)
                        price_info['change_pct'] = round(change_pct, 2)
                    else:
                        price_info['change'] = 0
                        price_info['change_pct'] = 0
                    
                    # 计算振幅
                    if price_info['pre_close'] and price_info['pre_close'] != 0:
                        amplitude = ((price_info['high_price'] - price_info['low_price']) / price_info['pre_close']) * 100
                        price_info['amplitude'] = round(amplitude, 2)
                    else:
                        price_info['amplitude'] = 0
                    
                    return price_info
                else:
                    # 如果tick数据无效，使用K线数据
                    print(f"💡 tick数据价格无效，尝试使用K线数据...")
                    return self._get_price_from_kline()
                
            else:
                # 如果是DataFrame格式
                latest_tick = tick_data.iloc[-1] if hasattr(tick_data, 'iloc') else tick_data
            
            # 检查数据是否有效
            current_price = getattr(latest_tick, 'lastPrice', 0)
            if current_price == 0:
                print(f"⚠️  获取到的价格为0，数据可能异常")
                print(f"🔧 调试信息：可用字段 = {list(latest_tick.index) if hasattr(latest_tick, 'index') else 'N/A'}")
                
                # 尝试其他价格字段
                for price_field in ['close', 'price', 'last_price', 'current']:
                    if hasattr(latest_tick, price_field):
                        alt_price = getattr(latest_tick, price_field)
                        if alt_price > 0:
                            print(f"💡 使用替代价格字段 '{price_field}': {alt_price}")
                            current_price = alt_price
                            break
                
                # 如果tick数据还是无效，使用K线数据
                if current_price == 0:
                    print(f"💡 tick数据价格为0，尝试使用K线数据...")
                    return self._get_price_from_kline()
            
            # 处理时间戳
            if hasattr(latest_tick, 'time'):
                timestamp = latest_tick.time
                if pd.notnull(timestamp):
                    # 转换时间戳
                    dt = pd.to_datetime(timestamp, unit='ms', utc=True).tz_convert('Asia/Shanghai')
                    update_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建股价信息字典（使用已检查的current_price）
            price_info = {
                'stock_code': self.stock_code,
                'stock_name': self.stock_name,
                'current_price': current_price,
                'open_price': getattr(latest_tick, 'open', 0),
                'high_price': getattr(latest_tick, 'high', 0),
                'low_price': getattr(latest_tick, 'low', 0),
                'pre_close': getattr(latest_tick, 'lastClose', 0),
                'volume': getattr(latest_tick, 'volume', 0),
                'amount': getattr(latest_tick, 'amount', 0),
                'update_time': update_time,
                'system_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 计算涨跌幅
            if price_info['pre_close'] and price_info['pre_close'] != 0:
                change = price_info['current_price'] - price_info['pre_close']
                change_pct = (change / price_info['pre_close']) * 100
                price_info['change'] = round(change, 2)
                price_info['change_pct'] = round(change_pct, 2)
            else:
                price_info['change'] = 0
                price_info['change_pct'] = 0
            
            # 计算振幅
            if price_info['pre_close'] and price_info['pre_close'] != 0:
                amplitude = ((price_info['high_price'] - price_info['low_price']) / price_info['pre_close']) * 100
                price_info['amplitude'] = round(amplitude, 2)
            else:
                price_info['amplitude'] = 0
                
            return price_info
            
        except Exception as e:
            print(f"❌ 获取实时数据时出错: {e}")
            print(f"🔧 详细错误信息: {str(e)}")
            print(f"💡 建议：")
            print(f"   1. 检查xtquant是否正常运行")
            print(f"   2. 确认股票代码格式正确")
            print(f"   3. 检查网络连接")
            return None
    
    def _get_price_from_kline(self):
        """
        当tick数据无效时，使用K线数据获取价格信息
        
        返回:
        dict: 股价信息字典
        """
        try:
            print(f"🔄 使用K线数据获取 {self.stock_code} 的价格信息...")
            
            # 获取最新的日K线数据
            kline_data = xtdata.get_market_data_ex(
                field_list=[], 
                stock_list=[self.stock_code], 
                period='1d', 
                count=2,  # 获取2天数据，用于计算涨跌幅
                dividend_type='none'
            )
            
            if not kline_data or self.stock_code not in kline_data:
                print(f"❌ 无法获取K线数据")
                return None
            
            df = kline_data[self.stock_code]
            if df.empty:
                print(f"❌ K线数据为空")
                return None
            
            # 获取最新数据
            latest = df.iloc[-1]
            
            # 获取昨日数据（如果有的话）
            pre_close = latest['preClose'] if 'preClose' in df.columns else (df.iloc[-2]['close'] if len(df) > 1 else latest['close'])
            
            price_info = {
                'stock_code': self.stock_code,
                'stock_name': self.stock_name,
                'current_price': latest['close'],
                'open_price': latest['open'],
                'high_price': latest['high'],
                'low_price': latest['low'],
                'pre_close': pre_close,
                'volume': latest['volume'],
                'amount': latest['amount'],
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'system_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 计算涨跌幅
            if pre_close and pre_close != 0:
                change = price_info['current_price'] - pre_close
                change_pct = (change / pre_close) * 100
                price_info['change'] = round(change, 2)
                price_info['change_pct'] = round(change_pct, 2)
            else:
                price_info['change'] = 0
                price_info['change_pct'] = 0
            
            # 计算振幅
            if pre_close and pre_close != 0:
                amplitude = ((price_info['high_price'] - price_info['low_price']) / pre_close) * 100
                price_info['amplitude'] = round(amplitude, 2)
            else:
                price_info['amplitude'] = 0
            
            print(f"✅ 成功从K线数据获取价格: {price_info['current_price']:.2f} 元")
            return price_info
            
        except Exception as e:
            print(f"❌ 从K线数据获取价格失败: {e}")
            return None
    
    def _process_kline_data(self, kline_data):
        """
        处理K线数据作为备选数据源
        
        参数:
        kline_data: K线数据
        
        返回:
        dict: 股价信息字典
        """
        try:
            # 从K线数据构建价格信息
            price_info = {
                'stock_code': self.stock_code,
                'stock_name': self.stock_name,
                'current_price': getattr(kline_data, 'close', 0),
                'open_price': getattr(kline_data, 'open', 0),
                'high_price': getattr(kline_data, 'high', 0),
                'low_price': getattr(kline_data, 'low', 0),
                'pre_close': getattr(kline_data, 'close', 0),  # K线数据中没有昨收，用收盘价代替
                'volume': getattr(kline_data, 'volume', 0),
                'amount': getattr(kline_data, 'amount', 0),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'system_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 计算涨跌幅（使用开盘价作为参考）
            if price_info['open_price'] and price_info['open_price'] != 0:
                change = price_info['current_price'] - price_info['open_price']
                change_pct = (change / price_info['open_price']) * 100
                price_info['change'] = round(change, 2)
                price_info['change_pct'] = round(change_pct, 2)
            else:
                price_info['change'] = 0
                price_info['change_pct'] = 0
            
            # 计算振幅
            if price_info['open_price'] and price_info['open_price'] != 0:
                amplitude = ((price_info['high_price'] - price_info['low_price']) / price_info['open_price']) * 100
                price_info['amplitude'] = round(amplitude, 2)
            else:
                price_info['amplitude'] = 0
                
            return price_info
            
        except Exception as e:
            print(f"❌ 处理K线数据时出错: {e}")
            return None
    
    def display_price_info(self, price_info, show_countdown=False):
        """
        在控制台显示股价信息
        
        参数:
        price_info: 股价信息字典
        show_countdown: 是否显示倒计时信息
        """
        if not price_info:
            return
        
        # 清屏（Windows）
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print(f"📈 实时股价监控 - {price_info['stock_name']} ({price_info['stock_code']})")
        print("=" * 80)
        
        # 检查数据有效性
        data_valid = (price_info['current_price'] > 0 or price_info['pre_close'] > 0)
        
        if not data_valid:
            print("⚠️  数据异常：所有价格为0，可能原因：")
            print("   1. 股票代码错误或不存在")
            print("   2. 该股票已退市或停牌")
            print("   3. xtquant数据源问题")
            print("   4. 网络连接问题")
            print("\n💡 建议：")
            print("   - 检查股票代码格式（如：600689.SH）")
            print("   - 尝试其他股票代码测试")
            print("   - 检查xtquant服务状态")
        
        # 价格信息
        print(f"💰 当前价格: {price_info['current_price']:.2f}")
        print(f"📊 昨收价格: {price_info['pre_close']:.2f}")
        
        # 涨跌信息（带颜色）
        change = price_info['change']
        change_pct = price_info['change_pct']
        
        if change > 0:
            change_color = "🔴"  # 上涨用红色
            change_str = f"+{change:.2f} (+{change_pct:.2f}%)"
        elif change < 0:
            change_color = "🟢"  # 下跌用绿色
            change_str = f"{change:.2f} ({change_pct:.2f}%)"
        else:
            change_color = "⚪"  # 平盘用白色
            change_str = f"{change:.2f} ({change_pct:.2f}%)"
        
        print(f"📈 涨跌幅度: {change_color} {change_str}")
        
        # 价格区间
        print(f"⬆️  今日最高: {price_info['high_price']:.2f}")
        print(f"⬇️  今日最低: {price_info['low_price']:.2f}")
        print(f"🌅 今日开盘: {price_info['open_price']:.2f}")
        print(f"📊 振幅: {price_info['amplitude']:.2f}%")
        
        # 成交信息
        volume_wan = price_info['volume'] / 10000  # 转换为万手
        amount_yi = price_info['amount'] / 100000000  # 转换为亿元
        
        print(f"📦 成交量: {volume_wan:.2f} 万手")
        print(f"💵 成交额: {amount_yi:.2f} 亿元")
        
        # 时间信息
        print("-" * 80)
        print(f"🕐 数据时间: {price_info['update_time']}")
        print(f"🖥️  系统时间: {price_info['system_time']}")
        
        # 交易状态和操作提示
        is_trading = self.is_trading_time()
        if is_trading:
            print("🟢 当前交易时间：数据实时更新")
            print("🔄 数据每几秒自动刷新...")
        else:
            print("🔴 非交易时间：显示最后收盘数据")
            
            # 在非交易时间显示倒计时信息
            if show_countdown:
                status_info = self.get_trading_status_info()
                print(f"📅 下次开盘时间: {status_info['next_trading_time']}")
                
                # 计算距离下次开盘的时间
                now = datetime.now()
                next_trading = datetime.strptime(status_info['next_trading_time'], '%Y-%m-%d %H:%M:%S')
                time_diff = next_trading - now
                
                if time_diff.total_seconds() > 0:
                    hours, remainder = divmod(time_diff.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    print(f"⏳ 距离下次开盘还有: {int(hours)}小时{int(minutes)}分钟")
                else:
                    print("⏳ 即将开盘...")
                
                print("🔄 将每30秒检查交易状态...")
            else:
                print("🔄 正在切换到等待模式...")
        
        print("💡 按 Ctrl+C 退出监控")
        print("=" * 80)
    
    def save_to_json(self, price_info, filename=None):
        """
        将股价信息保存到json文件
        
        参数:
        price_info: 股价信息字典
        filename: 文件名，默认根据股票代码生成
        """
        if not price_info:
            return
        
        if filename is None:
            stock_name_safe = price_info['stock_code'].replace('.', '_')
            filename = f"{stock_name_safe}_real_time_price.json"
        
        # 统一保存到数据目录（相对路径自动定位到./data）
        if not os.path.isabs(filename):
            filename = os.path.join(DATA_DIR, filename)
        
        try:
            # 构建JSON数据结构
            json_data = {
                "stock_info": {
                    "stock_code": price_info['stock_code'],
                    "stock_name": price_info['stock_name']
                },
                "price_data": {
                    "current_price": round(price_info['current_price'], 2),
                    "pre_close": round(price_info['pre_close'], 2),
                    "open_price": round(price_info['open_price'], 2),
                    "high_price": round(price_info['high_price'], 2),
                    "low_price": round(price_info['low_price'], 2),
                    "change": round(price_info['change'], 2),
                    "change_pct": round(price_info['change_pct'], 2),
                    "amplitude": round(price_info['amplitude'], 2)
                },
                "trading_data": {
                    "volume": price_info['volume'],
                    "volume_wan": round(price_info['volume'] / 10000, 2),
                    "amount": price_info['amount'],
                    "amount_yi": round(price_info['amount'] / 100000000, 2)
                },
                "time_info": {
                    "update_time": price_info['update_time'],
                    "system_time": price_info['system_time']
                },
                "trading_status": {
                    "is_trading_time": self.is_trading_time(),
                    "status_description": "交易时间内（数据实时）" if self.is_trading_time() else "非交易时间（最后收盘数据）"
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"📁 股价数据已保存到: {filename}")
            
        except Exception as e:
            print(f"❌ 保存文件时出错: {e}")
    
    def start_monitoring(self, interval=5, save_file=True):
        """
        开始实时监控（支持智能交易时间检查）
        
        参数:
        interval: 刷新间隔（秒），默认5秒
        save_file: 是否保存到文件，默认True
        """
        print(f"🚀 开始监控 {self.stock_name} ({self.stock_code}) 的实时股价...")
        print(f"⏰ 刷新间隔: {interval} 秒")
        print("💡 支持智能交易时间检查，非交易时间将保持显示最后价格")
        print("=" * 80)
        
        # 简化后的循环逻辑：
        # - 活跃窗口内：持续刷新
        # - 窗口外：更新一次后立即退出
        try:
            while True:
                is_trading = self.is_trading_time()
                
                # 获取一次数据
                price_info = self.get_real_time_price()
                if price_info:
                    self.display_price_info(price_info, show_countdown=False)
                    if save_file:
                        self.save_to_json(price_info)
                else:
                    print("❌ 获取数据失败，请检查环境、网络与代码参数")
                
                if is_trading:
                    time.sleep(interval)
                    continue
                else:
                    print("\n🔴 当前不在活跃窗口（周一至周五 09:00-15:30），已更新一次，程序将退出。")
                    break
                
        except KeyboardInterrupt:
            print("\n\n✅ 监控已停止，感谢使用！")
        except Exception as e:
            print(f"\n❌ 监控过程中出错: {e}")
    
    def _display_trading_status(self, status_info):
        """
        显示交易状态变化信息
        """
        print("\n" + "=" * 80)
        if status_info['is_trading']:
            print("🟢 进入交易时间，开始获取实时数据...")
        else:
            print("🔴 交易时间结束，进入等待模式...")
        print("=" * 80)
    
    def _display_price_with_countdown(self, price_info, status_info):
        """
        显示股价信息+等待倒计时的组合界面
        """
        # 清屏
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print(f"📈 实时股价监控 - {price_info['stock_name']} ({price_info['stock_code']})")
        print("=" * 80)
        
        # 价格信息
        print(f"💰 当前价格: {price_info['current_price']:.2f}")
        print(f"📊 昨收价格: {price_info['pre_close']:.2f}")
        
        # 涨跌信息
        change = price_info['change']
        change_pct = price_info['change_pct']
        
        if change > 0:
            change_color = "🔴"
            change_str = f"+{change:.2f} (+{change_pct:.2f}%)"
        elif change < 0:
            change_color = "🟢"
            change_str = f"{change:.2f} ({change_pct:.2f}%)"
        else:
            change_color = "⚪"
            change_str = f"{change:.2f} ({change_pct:.2f}%)"
        
        print(f"📈 涨跌幅度: {change_color} {change_str}")
        
        # 价格区间
        print(f"⬆️  今日最高: {price_info['high_price']:.2f}")
        print(f"⬇️  今日最低: {price_info['low_price']:.2f}")
        print(f"🌅 今日开盘: {price_info['open_price']:.2f}")
        print(f"📊 振幅: {price_info['amplitude']:.2f}%")
        
        # 成交信息
        volume_wan = price_info['volume'] / 10000
        amount_yi = price_info['amount'] / 100000000
        
        print(f"📦 成交量: {volume_wan:.2f} 万手")
        print(f"💵 成交额: {amount_yi:.2f} 亿元")
        
        # 分隔线
        print("-" * 80)
        
        # 交易状态和时间信息
        print(f"🔴 非交易时间：显示最后收盘数据")
        print(f"⏰ 当前时间: {status_info['current_time']}")
        print(f"📅 今天是: {status_info['weekday_name']}")
        
        if status_info['weekday'] >= 5:
            print("❌ 今天是周末，A股不开盘")
        else:
            print("❌ A股已收盘")
        
        print(f"📅 下次开盘时间: {status_info['next_trading_time']}")
        
        # 计算距离下次开盘的时间
        now = datetime.now()
        next_trading = datetime.strptime(status_info['next_trading_time'], '%Y-%m-%d %H:%M:%S')
        time_diff = next_trading - now
        
        if time_diff.total_seconds() > 0:
            hours, remainder = divmod(time_diff.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"⏳ 距离下次开盘还有: {int(hours)}小时{int(minutes)}分钟")
        else:
            print("⏳ 即将开盘...")
        
        print("🔄 将每30秒检查一次交易状态...")
        print("💡 按 Ctrl+C 退出监控")
        print("=" * 80)
    
    def _display_non_trading_info(self, status_info):
        """
        显示非交易时间的等待信息（当没有价格数据时使用）
        """
        # 清屏
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print(f"📈 实时股价监控 - {self.stock_name} ({self.stock_code})")
        print("=" * 80)
        print(f"⏰ 当前时间: {status_info['current_time']}")
        print(f"📅 今天是: {status_info['weekday_name']}")
        
        if status_info['weekday'] >= 5:
            print("❌ 今天是周末，A股不开盘")
        else:
            print("❌ 非交易时间，A股已收盘")
        
        print(f"📅 下次开盘时间: {status_info['next_trading_time']}")
        print("🔄 将每30秒检查一次交易状态...")
        print("💡 按 Ctrl+C 退出监控")
        print("=" * 80)
        
        # 计算距离下次开盘的时间
        now = datetime.now()
        next_trading = datetime.strptime(status_info['next_trading_time'], '%Y-%m-%d %H:%M:%S')
        time_diff = next_trading - now
        
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        if time_diff.total_seconds() > 0:
            print(f"⏳ 距离下次开盘还有: {int(hours)}小时{int(minutes)}分钟")
        else:
            print("⏳ 即将开盘...")
        
        print("=" * 80)

def parse_arguments():
    """
    解析命令行参数
    """
    parser = argparse.ArgumentParser(description='实时股价监控器')
    
    parser.add_argument('--stock_code', '-s', type=str, default='600689.SH',
                       help='股票代码，默认为600689.SH（上海三毛）')
    
    parser.add_argument('--interval', '-i', type=int, default=5,
                       help='刷新间隔（秒），默认5秒')
    
    parser.add_argument('--no_save', action='store_true',
                       help='不保存到文件')
    
    parser.add_argument('--once', action='store_true',
                       help='只获取一次数据，不循环监控')
    
    return parser.parse_args()

def main():
    """
    主函数
    """
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        args = parse_arguments()
        
        stock_code = args.stock_code
        interval = args.interval
        save_file = not args.no_save
        once_only = args.once
        
        # 创建监控器
        monitor = RealTimePriceMonitor(stock_code)
        
        if once_only:
            # 只获取一次数据
            print(f"🔍 获取 {monitor.stock_name} ({stock_code}) 的实时股价...")
            price_info = monitor.get_real_time_price()
            
            if price_info:
                monitor.display_price_info(price_info)
                if save_file:
                    monitor.save_to_json(price_info)
            else:
                print("❌ 获取数据失败")
        else:
            # 持续监控
            monitor.start_monitoring(interval, save_file)
        
    else:
        # 交互式模式
        print("=" * 60)
        print("📈 实时股价监控器")
        print("=" * 60)
        
        # 输入股票代码
        print("\n📊 请输入股票代码:")
        print("格式说明:")
        print("  上海证券交易所: 600689.SH")
        print("  深圳证券交易所: 000001.SZ")
        print("  默认: 600689.SH (上海三毛)")
        
        stock_code_input = input("\n请输入股票代码: ").strip()
        stock_code = stock_code_input if stock_code_input else "600689.SH"
        
        # 创建监控器
        monitor = RealTimePriceMonitor(stock_code)
        print(f"\n✅ 已选择股票: {monitor.stock_name} ({stock_code})")
        
        # 显示当前交易状态
        status_info = monitor.get_trading_status_info()
        print(f"📅 当前时间: {status_info['current_time']} ({status_info['weekday_name']})")
        if status_info['is_trading']:
            print("🟢 当前为交易时间，可获取实时数据")
        else:
            print("🔴 当前为非交易时间")
            print(f"📅 下次开盘: {status_info['next_trading_time']}")
        
        # 选择监控模式
        print("\n⏰ 请选择监控模式:")
        print("1. 持续监控（推荐）")
        print("2. 获取一次数据")
        
        mode_choice = input("请输入选择 (1-2, 默认为1): ").strip() or "1"
        
        if mode_choice == "2":
            # 只获取一次
            price_info = monitor.get_real_time_price()
            if price_info:
                monitor.display_price_info(price_info)
                monitor.save_to_json(price_info)
                input("\n按回车键退出...")
        else:
            # 持续监控
            print("\n⚙️  监控设置:")
            interval_input = input("刷新间隔（秒，默认5秒）: ").strip()
            interval = int(interval_input) if interval_input.isdigit() else 5
            
            monitor.start_monitoring(interval, True)

if __name__ == "__main__":
    main() 