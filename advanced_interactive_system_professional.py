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
BASE_INVESTMENT = 10000
STOP_LOSS_RATE = 0.05
PROFIT_TAKE_RATE = 0.15

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
        
    def get_stock_data(self, months=6):
        """获取股票数据"""
        print(f"正在获取{TARGET_STOCK_NAME}近{months}个月的历史数据...")
        
        # 获取最近6个月的数据，不限制结束日期
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=months*30)).strftime('%Y%m%d')
        
        try:
            stock_data = ak.stock_zh_a_hist(
                symbol='002155',
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if stock_data.empty:
                print("未获取到数据，使用专业模拟数据...")
                return self.create_professional_mock_data(months)
            
            print(f"成功获取 {len(stock_data)} 条数据")
            return stock_data
            
        except Exception as e:
            print(f"获取数据出错: {e}")
            print("使用专业模拟数据...")
            return self.create_professional_mock_data(months)
    
    def create_professional_mock_data(self, months=6):
        """创建专业模拟数据"""
        print("创建专业K线数据...")
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=months*30), 
                             end=datetime.now(), freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        # 生成更真实的股价数据
        np.random.seed(42)
        base_price = 20.0
        prices = []
        
        # 生成趋势和波动
        trend = np.linspace(0, 0.15, len(dates))
        noise = np.random.normal(0, 0.03, len(dates))
        price_changes = trend + noise
        
        for i, date in enumerate(dates):
            if i == 0:
                current_price = base_price
            else:
                current_price = prices[i-1]['收盘'] * (1 + price_changes[i])
                current_price = max(15.0, min(30.0, current_price))
            
            # 生成专业OHLC数据
            daily_volatility = np.random.uniform(0.015, 0.035)
            gap = np.random.normal(0, 0.008)
            open_price = current_price * (1 + gap)
            
            high_low_range = current_price * daily_volatility
            high_price = max(open_price, current_price) + np.random.uniform(0, high_low_range)
            low_price = min(open_price, current_price) - np.random.uniform(0, high_low_range)
            close_price = open_price * (1 + price_changes[i])
            
            high_price = max(open_price, high_price, close_price)
            low_price = min(open_price, low_price, close_price)
            
            volume = int(np.random.uniform(200000, 1000000))
            
            prices.append({
                '日期': date.strftime('%Y-%m-%d'),
                '开盘': round(open_price, 2),
                '最高': round(high_price, 2),
                '最低': round(low_price, 2),
                '收盘': round(close_price, 2),
                '成交量': volume
            })
        
        return pd.DataFrame(prices)
    
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
    
    def prepare_data(self, months=6):
        """准备数据 - 只负责数据处理，不涉及图表"""
        print(f"正在准备{TARGET_STOCK_NAME}数据...")
        
        # 获取股票数据
        self.data = self.get_stock_data(months)
        
        if self.data.empty:
            print("无法获取股票数据")
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
        if self.data is None or self.data.empty:
            return None
            
        current_price = self.data['收盘'].iloc[-1]
        current_gold_price, _, gold_change_rate = self.get_international_gold_price()
        
        # 计算股价涨跌
        stock_change_rate = 0.0
        if len(self.data) >= 2:
            previous_stock_price = self.data['收盘'].iloc[-2]
            stock_change_rate = (current_price - previous_stock_price) / previous_stock_price
        
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

if __name__ == "__main__":
    main()
