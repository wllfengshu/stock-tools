#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
专业K线图黄金板块交易系统
使用专业的K线图库
"""

import sys
import os

# 添加akshare源码目录到Python路径
sys.path.insert(0, os.path.abspath('./akshare'))
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 配置参数
TARGET_STOCK_NAME = "湖南黄金"
BASE_INVESTMENT = 10000  # 基础投资金额
STOP_LOSS_RATE = 0.10    # 止损率 10%
PROFIT_TAKE_RATE = 0.15  # 止盈率 15%

# 新增策略参数
GOLD_PRICE_CHECK_TIME = "08:00"  # 金价检查时间
STOCK_BUY_TIME = "09:30"        # 股票买入时间
PROFIT_CALLBACK_RATE = 0.01     # 盈利回调率 1% (从5%回调到4%)
MAX_PROFIT_RATE = 0.05           # 最大盈利率 5%

class TradingStrategy:
    """
    黄金板块量化交易策略
    """
    
    def __init__(self, base_investment=10000, stop_loss_rate=0.10, 
                 profit_callback_rate=0.01, max_profit_rate=0.05):
        """
        初始化交易策略
        
        Args:
            base_investment: 基础投资金额
            stop_loss_rate: 止损率
            profit_callback_rate: 盈利回调率
            max_profit_rate: 最大盈利率
        """
        self.base_investment = base_investment
        self.stop_loss_rate = stop_loss_rate
        self.profit_callback_rate = profit_callback_rate
        self.max_profit_rate = max_profit_rate
        self.positions = []
        self.trade_history = []
        
    def should_buy(self, gold_change_rate):
        """
        判断是否应该买入
        
        Args:
            gold_change_rate: 金价涨跌幅
            
        Returns:
            tuple: (是否买入, 买入金额)
        """
        if gold_change_rate > 0:  # 金价上涨
            buy_amount = self.base_investment * gold_change_rate
            return True, buy_amount
        return False, 0
    
    def should_sell(self, current_price, buy_price, max_profit_rate):
        """
        判断是否应该卖出
        
        Args:
            current_price: 当前价格
            buy_price: 买入价格
            max_profit_rate: 历史最大盈利率
            
        Returns:
            bool: 是否卖出
        """
        if max_profit_rate >= self.max_profit_rate:
            # 如果曾经达到过5%盈利，现在回调到4%就卖出
            current_profit_rate = (current_price - buy_price) / buy_price
            if current_profit_rate <= self.max_profit_rate - self.profit_callback_rate:
                return True
        
        # 止损检查
        if current_price <= buy_price * (1 - self.stop_loss_rate):
            return True
            
        return False
    
    def calculate_position_value(self, shares, current_price):
        """计算持仓价值"""
        return shares * current_price
    
    def calculate_profit_rate(self, current_price, buy_price):
        """计算盈利率"""
        return (current_price - buy_price) / buy_price

class ProfessionalInteractiveSystem:
    """
    专业K线图黄金板块交易系统
    """
    
    def __init__(self):
        """初始化专业系统"""
        self.positions = []
        self.trade_history = []
        self.current_position = None
        self.data = None
        self.gold_data = None
        self.strategy = TradingStrategy(
            base_investment=BASE_INVESTMENT,
            stop_loss_rate=STOP_LOSS_RATE,
            profit_callback_rate=PROFIT_CALLBACK_RATE,
            max_profit_rate=MAX_PROFIT_RATE
        )
        
    def get_stock_data(self, months=6, stock_code='002155'):
        """获取股票数据"""
        print(f"正在获取股票{stock_code}近{months}个月的历史数据...")
        
        # 获取最近6个月的数据，不限制结束日期
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=months*30)).strftime('%Y%m%d')
        
        try:
            stock_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if stock_data.empty:
                print(f"❌ 未获取到股票{stock_code}的数据")
                raise Exception(f"无法获取股票{stock_code}的历史数据")
            
            # 确保索引是datetime类型
            if not isinstance(stock_data.index, pd.DatetimeIndex):
                print(f" 警告: 股票{stock_code}索引不是DatetimeIndex，尝试转换...")
                stock_data.index = pd.to_datetime(stock_data.index)
            
            print(f"✅ 成功获取股票{stock_code}的 {len(stock_data)} 条数据")
            return stock_data
            
        except Exception as e:
            print(f"❌ 获取股票{stock_code}数据出错: {e}")
            raise Exception(f"获取股票{stock_code}数据失败: {str(e)}")
    
    # 已移除模拟数据生成函数，现在只使用真实数据
    
    def get_gold_historical_data(self, months=6):
        """获取伦敦金历史数据"""
        print(f"正在获取伦敦金近{months}个月的历史数据...")
        
        try:
            # 使用akshare获取伦敦金历史数据
            print(" 调用 ak.futures_foreign_hist(symbol='XAU')...")
            gold_data = ak.futures_foreign_hist(symbol="XAU")
            
            print(f" 原始伦敦金数据形状: {gold_data.shape}")
            print(f" 原始伦敦金数据列名: {gold_data.columns.tolist()}")
            
            if gold_data.empty:
                print(" 未获取到伦敦金历史数据，使用模拟数据...")
                return self.create_gold_mock_data(months)
            
            # 显示原始数据的前几行和后几行
            print(" 原始数据前5行:")
            print(gold_data.head())
            print(" 原始数据后5行:")
            print(gold_data.tail())
            
            # 处理数据格式
            print(" 处理数据格式...")
            gold_data['date'] = pd.to_datetime(gold_data['date'])
            gold_data = gold_data.set_index('date')
            gold_data = gold_data.sort_index()
            
            # 确保索引是datetime类型
            if not isinstance(gold_data.index, pd.DatetimeIndex):
                print(" 警告: 索引不是DatetimeIndex，尝试转换...")
                gold_data.index = pd.to_datetime(gold_data.index)
            
            # 获取最新数据日期
            latest_date = gold_data.index.max()
            earliest_date = gold_data.index.min()
            print(f" 伦敦金数据日期范围: {earliest_date.strftime('%Y-%m-%d')} 到 {latest_date.strftime('%Y-%m-%d')}")
            print(f" 伦敦金数据总条数: {len(gold_data)}")
            
            # 显示最近10天的数据
            print(" 最近10天数据:")
            print(gold_data.tail(10))
            
            # 筛选最近几个月的数据，但不过滤到当前日期
            # 因为伦敦金是24小时交易的，应该能获取到最新数据
            end_date = latest_date
            start_date = end_date - timedelta(days=months*30)
            print(f" 筛选数据范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
            
            original_count = len(gold_data)
            gold_data = gold_data[(gold_data.index >= start_date) & (gold_data.index <= end_date)]
            filtered_count = len(gold_data)
            
            print(f" 筛选前数据条数: {original_count}")
            print(f" 筛选后数据条数: {filtered_count}")
            
            if filtered_count == 0:
                print(" 筛选后没有数据，使用全部数据")
                gold_data = ak.futures_foreign_hist(symbol="XAU")
                gold_data['date'] = pd.to_datetime(gold_data['date'])
                gold_data = gold_data.set_index('date')
                gold_data = gold_data.sort_index()
                # 只取最近的数据
                gold_data = gold_data.tail(months*30)
            
            # 重命名列以匹配股票数据格式
            gold_data = gold_data.rename(columns={
                'open': '开盘',
                'high': '最高', 
                'low': '最低',
                'close': '收盘',
                'volume': '成交量'
            })
            
            print(f"成功获取伦敦金 {len(gold_data)} 条数据")
            return gold_data
            
        except Exception as e:
            print(f"获取伦敦金历史数据出错: {e}")
            print("使用伦敦金模拟数据...")
            return self.create_gold_mock_data(months)
    
    def create_gold_mock_data(self, months=6):
        """创建伦敦金模拟数据"""
        print("创建伦敦金模拟数据...")
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=months*30), 
                             end=datetime.now(), freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        # 生成伦敦金价格数据
        np.random.seed(42)
        base_price = 2000.0
        prices = []
        
        # 生成趋势和波动
        trend = np.linspace(0, 0.2, len(dates))
        noise = np.random.normal(0, 0.02, len(dates))
        price_changes = trend + noise
        
        for i, date in enumerate(dates):
            if i == 0:
                current_price = base_price
            else:
                current_price = prices[i-1]['收盘'] * (1 + price_changes[i])
                current_price = max(1500.0, min(2500.0, current_price))
            
            # 生成OHLC数据
            daily_volatility = np.random.uniform(0.01, 0.03)
            gap = np.random.normal(0, 0.005)
            open_price = current_price * (1 + gap)
            
            high_low_range = current_price * daily_volatility
            high_price = max(open_price, current_price) + np.random.uniform(0, high_low_range)
            low_price = min(open_price, current_price) - np.random.uniform(0, high_low_range)
            close_price = open_price * (1 + price_changes[i])
            
            high_price = max(open_price, high_price, close_price)
            low_price = min(open_price, low_price, close_price)
            
            volume = int(np.random.uniform(1000, 5000))
            
            prices.append({
                '开盘': round(open_price, 2),
                '最高': round(high_price, 2),
                '最低': round(low_price, 2),
                '收盘': round(close_price, 2),
                '成交量': volume
            })
        
        gold_data = pd.DataFrame(prices, index=dates)
        return gold_data
    
    def get_international_gold_price(self):
        """获取国际金价数据"""
        try:
            # 使用akshare获取真实的伦敦金价格
            gold_data = ak.futures_foreign_commodity_realtime(symbol=['XAU'])
            
            if not gold_data.empty:
                # 获取当前价格（第二列是当前价格）
                current_price = float(gold_data.iloc[0, 1])
                # 获取昨收价格（第9列是昨收价格）
                previous_price = float(gold_data.iloc[0, 8])
                # 手动计算涨跌幅，确保准确性
                price_change_rate = (current_price - previous_price) / previous_price
                
                print(f"获取到真实金价数据: 当前价格=${current_price:.2f}, 昨收=${previous_price:.2f}, 涨跌幅={price_change_rate*100:.2f}%")
                return current_price, previous_price, price_change_rate
            else:
                print("未获取到金价数据，使用默认值")
                return 2000.0, 1980.0, 0.01
                
        except Exception as e:
            print(f"获取真实金价数据失败: {e}")
            print("回退到模拟数据")
            # 回退到模拟数据
            base_price = 2000.0
            np.random.seed(int(datetime.now().timestamp()) % 1000)
            change_percent = np.random.normal(0, 0.02)
            current_price = base_price * (1 + change_percent)
            previous_price = base_price * (1 + np.random.normal(0, 0.01))
            
            price_change_rate = (current_price - previous_price) / previous_price
            return current_price, previous_price, price_change_rate
    
    def prepare_data(self, months=6, stock_code='002155'):
        """准备数据 - 只负责数据处理，不涉及图表"""
        print(f"正在准备股票{stock_code}数据...")
        
        try:
            # 获取股票数据
            self.data = self.get_stock_data(months, stock_code)
            
            if self.data.empty:
                print(f"❌ 股票{stock_code}数据为空")
                return False
                
        except Exception as e:
            print(f"❌ 准备股票{stock_code}数据失败: {e}")
            return False
        
        # 准备股票数据
        self.data['日期'] = pd.to_datetime(self.data['日期'])
        self.data = self.data.set_index('日期')
        self.data = self.data.sort_index()
        
        # 确保OHLC数据为数值类型
        self.data['开盘'] = pd.to_numeric(self.data['开盘'], errors='coerce')
        self.data['最高'] = pd.to_numeric(self.data['最高'], errors='coerce')
        self.data['最低'] = pd.to_numeric(self.data['最低'], errors='coerce')
        self.data['收盘'] = pd.to_numeric(self.data['收盘'], errors='coerce')
        self.data['成交量'] = pd.to_numeric(self.data['成交量'], errors='coerce')
        
        # 删除包含NaN的行
        self.data = self.data.dropna()
        
        print(f"股票数据准备完成，形状: {self.data.shape}")
        print(f"股票价格范围: {self.data['收盘'].min():.2f} - {self.data['收盘'].max():.2f}")
        
        # 获取伦敦金数据
        print(f"正在准备伦敦金数据...")
        self.gold_data = self.get_gold_historical_data(months)
        
        if not self.gold_data.empty:
            # 确保OHLC数据为数值类型
            self.gold_data['开盘'] = pd.to_numeric(self.gold_data['开盘'], errors='coerce')
            self.gold_data['最高'] = pd.to_numeric(self.gold_data['最高'], errors='coerce')
            self.gold_data['最低'] = pd.to_numeric(self.gold_data['最低'], errors='coerce')
            self.gold_data['收盘'] = pd.to_numeric(self.gold_data['收盘'], errors='coerce')
            self.gold_data['成交量'] = pd.to_numeric(self.gold_data['成交量'], errors='coerce')
            
            # 删除包含NaN的行
            self.gold_data = self.gold_data.dropna()
            
            print(f"伦敦金数据准备完成，形状: {self.gold_data.shape}")
            print(f"伦敦金价格范围: ${self.gold_data['收盘'].min():.2f} - ${self.gold_data['收盘'].max():.2f}")
            
            # 数据日期对齐 - 使用日期并集和空缺处理
            if not self.data.empty and not self.gold_data.empty:
                print("开始数据对齐处理...")
                
                # 获取两个数据集的日期范围
                stock_start = self.data.index.min()
                stock_end = self.data.index.max()
                gold_start = self.gold_data.index.min()
                gold_end = self.gold_data.index.max()
                
                print(f"股票数据日期范围: {stock_start.strftime('%Y-%m-%d')} 到 {stock_end.strftime('%Y-%m-%d')}")
                print(f"伦敦金数据日期范围: {gold_start.strftime('%Y-%m-%d')} 到 {gold_end.strftime('%Y-%m-%d')}")
                
                # 创建日期并集
                stock_dates = set(self.data.index.date)
                gold_dates = set(self.gold_data.index.date)
                union_dates = sorted(stock_dates.union(gold_dates))
                
                print(f"日期并集总数: {len(union_dates)}")
                print(f"并集日期范围: {union_dates[0]} 到 {union_dates[-1]}")
                
                # 显示最近20个日期
                print("并集日期列表（最近20个）:")
                for i, date in enumerate(union_dates[-20:]):
                    print(f"  {i+1}. {date}")
                
                # 重新构建对齐后的数据
                print("重新构建对齐数据...")
                
                # 创建新的DataFrame，使用并集日期作为索引
                aligned_stock_data = pd.DataFrame(index=union_dates)
                aligned_gold_data = pd.DataFrame(index=union_dates)
                
                # 填充股票数据
                for date in union_dates:
                    if date in stock_dates:
                        # 找到对应的股票数据
                        stock_row = self.data[self.data.index.date == date]
                        if not stock_row.empty:
                            # 复制所有列的数据
                            for col in stock_row.columns:
                                aligned_stock_data.loc[date, col] = stock_row.iloc[0][col]
                    # 如果日期不在股票数据中，保持NaN（空缺处理）
                
                # 填充伦敦金数据
                for date in union_dates:
                    if date in gold_dates:
                        # 找到对应的伦敦金数据
                        gold_row = self.gold_data[self.gold_data.index.date == date]
                        if not gold_row.empty:
                            # 复制所有列的数据
                            for col in gold_row.columns:
                                aligned_gold_data.loc[date, col] = gold_row.iloc[0][col]
                    # 如果日期不在伦敦金数据中，保持NaN（空缺处理）
                
                # 更新数据
                self.data = aligned_stock_data
                self.gold_data = aligned_gold_data
                
                # 重新设置索引为datetime对象，确保strftime方法可用
                self.data.index = pd.to_datetime(self.data.index)
                self.gold_data.index = pd.to_datetime(self.gold_data.index)
                
                print(f"对齐后股票数据形状: {self.data.shape}")
                print(f"对齐后伦敦金数据形状: {self.gold_data.shape}")
                
                # 显示对齐后的数据统计
                stock_valid_count = self.data.dropna().shape[0]
                gold_valid_count = self.gold_data.dropna().shape[0]
                
                print(f"对齐后股票有效数据: {stock_valid_count}条")
                print(f"对齐后伦敦金有效数据: {gold_valid_count}条")
                
                # 显示最近10个日期的数据情况
                print("最近10个日期的数据情况:")
                recent_dates = union_dates[-10:]
                for date in recent_dates:
                    stock_has_data = date in stock_dates
                    gold_has_data = date in gold_dates
                    stock_status = "有" if stock_has_data else "无"
                    gold_status = "有" if gold_has_data else "无"
                    print(f"  {date}: 股票{stock_status} 伦敦金{gold_status}")
                
                print("数据对齐完成！")
        else:
            print("无法获取伦敦金数据")
        
        return True
    
    def get_strategy_status(self):
        """获取策略状态 - 只返回数据，不涉及图表"""
        print(f"🔍 get_strategy_status: data is None={self.data is None}, empty={self.data.empty if self.data is not None else 'N/A'}")
        
        if self.data is None or self.data.empty:
            print("⚠️ 数据为空，返回None")
            return None
        
        # 清理NaN值的辅助函数
        def clean_nan(value, default=0.0):
            import math
            if isinstance(value, float) and math.isnan(value):
                return default
            return value
        
        # 调试数据
        print(f"📊 数据形状: {self.data.shape}")
        print(f"📊 收盘价列: {self.data['收盘'].iloc[-5:].tolist()}")
        print(f"📊 最新收盘价: {self.data['收盘'].iloc[-1]}")
        
        current_price = clean_nan(self.data['收盘'].iloc[-1])
        print(f"📊 清理后的当前价格: {current_price}")
        
        current_gold_price, _, gold_change_rate = self.get_international_gold_price()
        
        # 清理金价数据
        current_gold_price = clean_nan(current_gold_price, 2000.0)
        gold_change_rate = clean_nan(gold_change_rate, 0.0)
        
        # 计算股价涨跌
        stock_change_rate = 0.0
        if len(self.data) >= 2:
            previous_stock_price = clean_nan(self.data['收盘'].iloc[-2])
            if previous_stock_price != 0:
                stock_change_rate = clean_nan((current_price - previous_stock_price) / previous_stock_price)
        
        return {
            'current_price': current_price,
            'stock_change_rate': stock_change_rate,
            'gold_price': current_gold_price,
            'gold_change_rate': gold_change_rate,
            'has_position': self.current_position is not None,
            'trade_count': len(self.trade_history),
            'base_investment': BASE_INVESTMENT,
            'stop_loss_rate': STOP_LOSS_RATE,
            'profit_take_rate': PROFIT_TAKE_RATE
        }
    
    def get_stock_name(self, stock_code):
        """根据股票代码获取股票名称"""
        stock_names = {
            '002155': '湖南黄金',
            '600547': '山东黄金', 
            '000975': '银泰黄金',
            '600489': '中金黄金',
            '002237': '恒邦股份',
            '600988': '赤峰黄金'
        }
        return stock_names.get(stock_code, f'股票{stock_code}')

def main(months=6, stock_code=None, web_mode=False):
    """主程序入口 - 只负责业务逻辑"""
    print("专业黄金板块交易系统启动")
    print("=" * 60)
    
    # 创建系统实例
    system = ProfessionalInteractiveSystem()
    
    print(f"时间范围: {months}个月")
    print(f"目标股票: {stock_code or TARGET_STOCK_NAME}")
    
    # 准备数据
    if system.prepare_data(months):
        print("数据准备完成！")
        
        # 获取策略状态
        status = system.get_strategy_status()
        if status:
            print(f"当前股价: {status['current_price']:.2f}元")
            print(f"国际金价: ${status['gold_price']:.2f}")
            print(f"金价涨跌: {status['gold_change_rate']*100:.2f}%")
            print(f"交易次数: {status['trade_count']}")
        
        print("\n系统特点:")
        print("1. 专业的数据处理")
        print("2. 准确的策略计算")
        print("3. 完整的交易记录")
        print("4. 真实的市场数据")
        print("5. 清晰的业务逻辑")
    else:
        print("数据准备失败")
    
    return system

# 在类外部添加方法到ProfessionalInteractiveSystem类
def add_strategy_methods_to_class():
    """为ProfessionalInteractiveSystem类添加策略方法"""
    
    def execute_strategy(self, stock_code='002155'):
        """
        执行量化交易策略
        
        Args:
            stock_code: 股票代码
            
        Returns:
            dict: 策略执行结果
        """
        try:
            # 1. 获取国际金价
            gold_data = self.get_international_gold_price()
            if gold_data is None or gold_data.empty:
                return {'error': '无法获取国际金价数据'}
            
            current_gold_price = gold_data.iloc[0, 1]
            previous_gold_price = gold_data.iloc[0, 8]
            gold_change_rate = (current_gold_price - previous_gold_price) / previous_gold_price
            
            # 2. 获取股票当前价格
            stock_data = self.get_stock_data()
            if stock_data is None or stock_data.empty:
                return {'error': '无法获取股票数据'}
            
            current_stock_price = stock_data.iloc[-1]['收盘']
            
            # 3. 执行买入逻辑
            should_buy, buy_amount = self.strategy.should_buy(gold_change_rate)
            
            # 4. 检查卖出条件（如果有持仓）
            should_sell = False
            if self.current_position:
                should_sell = self.strategy.should_sell(
                    current_stock_price, 
                    self.current_position['buy_price'],
                    self.current_position.get('max_profit_rate', 0)
                )
            
            # 5. 执行交易
            trade_result = {
                'gold_price': current_gold_price,
                'gold_change_rate': gold_change_rate,
                'stock_price': current_stock_price,
                'should_buy': should_buy,
                'buy_amount': buy_amount,
                'should_sell': should_sell,
                'current_position': self.current_position
            }
            
            if should_buy and not self.current_position:
                # 执行买入
                shares = buy_amount / current_stock_price
                self.current_position = {
                    'buy_price': current_stock_price,
                    'shares': shares,
                    'buy_amount': buy_amount,
                    'buy_date': datetime.now(),
                    'max_profit_rate': 0
                }
                trade_result['action'] = 'BUY'
                trade_result['shares'] = shares
                
            elif should_sell and self.current_position:
                # 执行卖出
                sell_amount = self.current_position['shares'] * current_stock_price
                profit = sell_amount - self.current_position['buy_amount']
                profit_rate = profit / self.current_position['buy_amount']
                
                self.trade_history.append({
                    'buy_price': self.current_position['buy_price'],
                    'sell_price': current_stock_price,
                    'shares': self.current_position['shares'],
                    'profit': profit,
                    'profit_rate': profit_rate,
                    'buy_date': self.current_position['buy_date'],
                    'sell_date': datetime.now()
                })
                
                trade_result['action'] = 'SELL'
                trade_result['profit'] = profit
                trade_result['profit_rate'] = profit_rate
                
                self.current_position = None
            
            # 6. 更新持仓最大盈利率
            if self.current_position:
                current_profit_rate = self.strategy.calculate_profit_rate(
                    current_stock_price, self.current_position['buy_price']
                )
                self.current_position['max_profit_rate'] = max(
                    self.current_position['max_profit_rate'], 
                    current_profit_rate
                )
                trade_result['current_profit_rate'] = current_profit_rate
                trade_result['max_profit_rate'] = self.current_position['max_profit_rate']
            
            return trade_result
            
        except Exception as e:
            return {'error': f'策略执行失败: {str(e)}'}
    
    def get_strategy_status(self):
        """获取策略状态"""
        if not self.current_position:
            return {
                'has_position': False,
                'message': '当前无持仓'
            }
        
        # 获取当前股票价格
        try:
            stock_data = self.get_stock_data()
            current_price = stock_data.iloc[-1]['收盘']
            
            current_profit_rate = self.strategy.calculate_profit_rate(
                current_price, self.current_position['buy_price']
            )
            
            position_value = self.strategy.calculate_position_value(
                self.current_position['shares'], current_price
            )
            
            return {
                'has_position': True,
                'buy_price': self.current_position['buy_price'],
                'current_price': current_price,
                'shares': self.current_position['shares'],
                'position_value': position_value,
                'profit_rate': current_profit_rate,
                'max_profit_rate': self.current_position['max_profit_rate'],
                'buy_date': self.current_position['buy_date'].strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {
                'has_position': True,
                'error': f'获取持仓状态失败: {str(e)}'
            }

if __name__ == "__main__":
    main()
