#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
数据提供者模块
专门负责获取和处理股票、金价等基础数据

主要功能：
1. 获取股票历史数据
2. 获取金价历史数据  
3. 数据清洗和格式化
4. 提供数据接口

作者：AI Assistant
创建时间：2024年12月
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

class DataProvider:
    """
    数据提供者类
    
    专门负责获取和处理基础数据，不涉及交易策略
    提供股票、金价等金融数据的获取和预处理功能
    """
    
    def __init__(self):
        """
        初始化数据提供者
        """
        print("✅ 数据提供者初始化完成")
    
    def get_stock_data(self, months=6, stock_code='002155'):
        """
        获取股票历史数据
        
        Args:
            months (int): 获取数据的月数，默认6个月
            stock_code (str): 股票代码，默认002155（湖南黄金）
            
        Returns:
            pd.DataFrame: 股票历史数据，包含OHLCV数据
        """
        print(f"📊 正在获取股票{stock_code}近{months}个月的历史数据...")
        
        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=months*30)).strftime('%Y%m%d')
        
        try:
            # 使用akshare获取股票数据
            stock_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if stock_data.empty:
                print(f"❌ 未获取到股票{stock_code}的数据")
                raise Exception(f"无法获取股票{stock_code}的历史数据")
            
            # 确保索引是datetime类型
            if not isinstance(stock_data.index, pd.DatetimeIndex):
                print(f"⚠️ 股票{stock_code}索引不是DatetimeIndex，尝试转换...")
                stock_data.index = pd.to_datetime(stock_data.index)
            
            print(f"✅ 成功获取股票{stock_code}的 {len(stock_data)} 条数据")
            print(f"📈 数据时间范围: {stock_data['日期'].min()} 到 {stock_data['日期'].max()}")
            return stock_data
            
        except Exception as e:
            print(f"❌ 获取股票{stock_code}数据出错: {e}")
            raise e
    
    def get_gold_data(self, months=6):
        """
        获取伦敦金历史数据
        
        Args:
            months (int): 获取数据的月数，默认6个月
            
        Returns:
            pd.DataFrame: 伦敦金历史数据，包含OHLCV格式
        """
        print(f"🥇 正在获取伦敦金近{months}个月的历史数据...")
        
        try:
            # 使用akshare获取伦敦金数据
            gold_data = ak.futures_london_gold_daily()
            
            if gold_data.empty:
                print("❌ 未获取到伦敦金数据")
                return pd.DataFrame()
            
            print(f"🔍 原始伦敦金数据列名: {gold_data.columns.tolist()}")
            print(f"🔍 原始伦敦金数据形状: {gold_data.shape}")
            
            # 数据预处理 - 确保列名正确
            if '日期' in gold_data.columns:
                gold_data['日期'] = pd.to_datetime(gold_data['日期'])
                gold_data = gold_data.set_index('日期')
            elif 'date' in gold_data.columns:
                gold_data['date'] = pd.to_datetime(gold_data['date'])
                gold_data = gold_data.set_index('date')
            else:
                # 如果没有日期列，使用索引
                gold_data.index = pd.to_datetime(gold_data.index)
            
            gold_data = gold_data.sort_index()
            
            # 获取最近N个月的数据
            cutoff_date = datetime.now() - timedelta(days=months*30)
            gold_data = gold_data[gold_data.index >= cutoff_date]
            
            # 确保数据包含OHLCV列
            required_columns = ['开盘', '最高', '最低', '收盘', '成交量']
            missing_columns = [col for col in required_columns if col not in gold_data.columns]
            
            if missing_columns:
                print(f"⚠️ 伦敦金数据缺少列: {missing_columns}")
                print(f"🔍 可用列: {gold_data.columns.tolist()}")
                
                # 尝试使用英文列名
                column_mapping = {
                    'open': '开盘',
                    'high': '最高', 
                    'low': '最低',
                    'close': '收盘',
                    'volume': '成交量'
                }
                
                for eng_col, chn_col in column_mapping.items():
                    if eng_col in gold_data.columns and chn_col not in gold_data.columns:
                        gold_data[chn_col] = gold_data[eng_col]
                        print(f"✅ 映射列 {eng_col} -> {chn_col}")
            
            print(f"✅ 成功获取伦敦金 {len(gold_data)} 条数据")
            if not gold_data.empty:
                print(f"📈 数据时间范围: {gold_data.index.min()} 到 {gold_data.index.max()}")
                print(f"📊 最终列名: {gold_data.columns.tolist()}")
            return gold_data
            
        except Exception as e:
            print(f"❌ 获取伦敦金数据出错: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_stock_name(self, stock_code):
        """
        根据股票代码获取股票名称
        
        Args:
            stock_code (str): 股票代码
            
        Returns:
            str: 股票名称
        """
        stock_names = {
            '002155': '湖南黄金',
            '600547': '山东黄金',
            '000975': '银泰黄金',
            '600489': '中金黄金',
            '002237': '恒邦股份',
            '600988': '赤峰黄金'
        }
        return stock_names.get(stock_code, f'股票{stock_code}')
    
    def prepare_data(self, months=6, stock_code='002155'):
        """
        准备数据 - 基础信息模块的数据准备方法
        
        Args:
            months (int): 获取数据的月数
            stock_code (str): 股票代码
            
        Returns:
            bool: 数据准备是否成功
        """
        print(f"🔄 基础信息模块：准备股票{stock_code}的{months}个月数据...")
        
        try:
            # 获取股票数据
            self.stock_data = self.get_stock_data(months, stock_code)
            if self.stock_data is None or self.stock_data.empty:
                print("❌ 股票数据获取失败")
                return False
            
            # 获取金价数据
            self.gold_data = self.get_gold_data(months)
            if self.gold_data is None or self.gold_data.empty:
                print("⚠️ 金价数据获取失败，使用默认值")
                # 金价数据失败不影响基础信息显示
            
            print(f"✅ 基础信息模块数据准备完成")
            print(f"📊 股票数据: {self.stock_data.shape}")
            print(f"📊 金价数据: {self.gold_data.shape if self.gold_data is not None else 'None'}")
            return True
            
        except Exception as e:
            print(f"❌ 基础信息模块数据准备失败: {e}")
            return False
    
    def get_current_status(self):
        """
        获取当前数据状态信息 - 基础信息模块的核心方法
        
        计算并返回：
        1. 当前股价和涨跌幅
        2. 金价和涨跌幅
        3. 数据统计信息
        
        Returns:
            dict: 数据状态信息，包含所有关键指标
        """
        print(f"🔍 获取基础数据状态: stock_data is None={self.stock_data is None}")
        
        if self.stock_data is None or self.stock_data.empty:
            print("⚠️ 股票数据为空，返回None")
            return None
        
        # 清理NaN值的辅助函数
        def clean_nan(value, default=0.0):
            """清理NaN值，替换为默认值"""
            import math
            if isinstance(value, float) and math.isnan(value):
                return default
            return value
        
        # 调试数据
        print(f"📊 股票数据形状: {self.stock_data.shape}")
        print(f"📊 最新收盘价: {self.stock_data['收盘'].iloc[-1]}")
        
        # 获取当前股价
        current_price = clean_nan(self.stock_data['收盘'].iloc[-1])
        
        # 计算股价涨跌幅
        if len(self.stock_data) > 1:
            prev_price = clean_nan(self.stock_data['收盘'].iloc[-2])
            stock_change_rate = (current_price - prev_price) / prev_price if prev_price != 0 else 0
        else:
            stock_change_rate = 0
        
        # 获取金价信息
        gold_price = 2000.0  # 默认金价
        gold_change_rate = 0.0  # 默认金价涨跌幅
        
        if self.gold_data is not None and not self.gold_data.empty:
            gold_price = clean_nan(self.gold_data['收盘'].iloc[-1])
            if len(self.gold_data) > 1:
                prev_gold_price = clean_nan(self.gold_data['收盘'].iloc[-2])
                gold_change_rate = (gold_price - prev_gold_price) / prev_gold_price if prev_gold_price != 0 else 0
        
        # 构建状态信息
        status = {
            'current_price': current_price,
            'stock_change_rate': stock_change_rate,
            'gold_price': gold_price,
            'gold_change_rate': gold_change_rate,
            'data_points': len(self.stock_data),
            'date_range': {
                'start': self.stock_data.index.min().strftime('%Y-%m-%d'),
                'end': self.stock_data.index.max().strftime('%Y-%m-%d')
            },
            'position': {
                'has_position': False,
                'buy_price': 0,
                'shares': 0,
                'amount': 0,
                'current_profit_rate': 0,
                'max_profit_rate': 0
            }
        }
        
        print(f"📊 基础数据状态计算完成: 股价={current_price:.2f}, 涨跌={stock_change_rate:.4f}")
        return status

# ==================== 使用示例 ====================
if __name__ == "__main__":
    """
    数据提供者使用示例
    """
    print("🚀 启动数据提供者...")
    
    # 创建数据提供者实例
    provider = DataProvider()
    
    # 准备数据
    if provider.prepare_data(months=6, stock_code='002155'):
        print("✅ 数据准备成功")
        
        # 获取数据状态
        status = provider.get_current_status()
        if status:
            print("📊 数据状态:")
            print(f"  当前股价: ¥{status['current_price']:.2f}")
            print(f"  股价涨跌: {status['stock_change_rate']*100:.2f}%")
            print(f"  金价: ${status['gold_price']:.2f}")
            print(f"  金价涨跌: {status['gold_change_rate']*100:.2f}%")
            print(f"  数据点数: {status['data_points']}")
        else:
            print("❌ 无法获取数据状态")
    else:
        print("❌ 数据准备失败")
    
    print("🎉 数据提供者运行完成")
