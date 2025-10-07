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
import json

# 添加akshare源码目录到Python路径
sys.path.insert(0, os.path.abspath('./akshare'))
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入数据库操作类
from database.strategy_dao import StrategyDAO
from database.table_entity import ToolStockToolsGold

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
        # 初始化数据库连接
        self.strategy_dao = StrategyDAO()
        # 确保数据库表存在
        # self.strategy_dao.create_table_if_not_exists()
        # 默认用户认证
        self.default_auth = 'abcdefaddd'
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
            
            # 确保数据按时间正序排列
            stock_data = stock_data.sort_index(ascending=True)
            
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
            # 使用伦敦金数据源
            print("使用伦敦金数据源 (XAU)...")
            gold_data = ak.futures_foreign_hist(symbol="XAU")
            
            if gold_data.empty:
                print("❌ 未获取到伦敦金数据")
                return pd.DataFrame()
            
            print(f"🔍 原始伦敦金数据列名: {gold_data.columns.tolist()}")
            print(f"🔍 原始伦敦金数据形状: {gold_data.shape}")
            print(f"🔍 原始伦敦金数据示例:")
            print(gold_data.head(3))
            
            # 数据预处理 - 适配futures_foreign_hist的数据格式
            # 该接口返回的是日度数据，需要转换为标准OHLCV格式
            if '日期' in gold_data.columns:
                # 将日期转换为日期索引
                gold_data['日期'] = pd.to_datetime(gold_data['日期'])
                gold_data = gold_data.set_index('日期')
            elif 'date' in gold_data.columns:
                gold_data['date'] = pd.to_datetime(gold_data['date'])
                gold_data = gold_data.set_index('date')
            else:
                # 如果没有日期列，使用索引
                gold_data.index = pd.to_datetime(gold_data.index)
            
            gold_data = gold_data.sort_index(ascending=True)  # 确保按时间正序排列
            
            # 获取最近N个月的数据
            cutoff_date = datetime.now() - timedelta(days=months*30)
            gold_data = gold_data[gold_data.index >= cutoff_date]
            
            # 检查并映射列名到标准OHLCV格式
            column_mapping = {
                'open': '开盘',
                'high': '最高',
                'low': '最低', 
                'close': '收盘',
                'volume': '成交量'
            }
            
            # 应用列名映射
            for eng_col, chn_col in column_mapping.items():
                if eng_col in gold_data.columns and chn_col not in gold_data.columns:
                    gold_data[chn_col] = gold_data[eng_col]
                    print(f"✅ 映射列 {eng_col} -> {chn_col}")
            
            # 确保数据包含OHLCV列
            required_columns = ['开盘', '最高', '最低', '收盘', '成交量']
            missing_columns = [col for col in required_columns if col not in gold_data.columns]
            
            if missing_columns:
                print(f"⚠️ 伦敦金数据缺少列: {missing_columns}")
                print(f"🔍 可用列: {gold_data.columns.tolist()}")
                # 如果缺少关键列，尝试从其他可能的列名获取
                alternative_mappings = {
                    'Open': '开盘',
                    'High': '最高',
                    'Low': '最低',
                    'Close': '收盘',
                    'Volume': '成交量'
                }
                
                for alt_col, chn_col in alternative_mappings.items():
                    if alt_col in gold_data.columns and chn_col not in gold_data.columns:
                        gold_data[chn_col] = gold_data[alt_col]
                        print(f"✅ 备用映射列 {alt_col} -> {chn_col}")
            
            print(f"✅ 成功获取伦敦金 {len(gold_data)} 条数据")
            if not gold_data.empty:
                print(f"📈 数据时间范围: {gold_data.index.min()} 到 {gold_data.index.max()}")
                print(f"📊 最终列名: {gold_data.columns.tolist()}")
                print(f"📊 最新收盘价: {gold_data['收盘'].iloc[-1] if '收盘' in gold_data.columns else 'N/A'}")
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
            print(f"📊 金价数据形状: {self.gold_data.shape}")
            print(f"📊 最新金价: {gold_price}")
            print(f"📊 金价数据索引: {self.gold_data.index[-3:].tolist()}")
            print(f"📊 金价收盘价: {self.gold_data['收盘'].iloc[-3:].tolist()}")
            
            # 详细显示最近几天的数据
            print(f"📊 最近5天金价数据详情:")
            recent_data = self.gold_data.tail(5)
            for i, (date, row) in enumerate(recent_data.iterrows()):
                close_price = row.get('收盘', 'N/A')
                print(f"  {i+1}. {date.strftime('%Y-%m-%d')}: 收盘价={close_price}")
            
            if len(self.gold_data) > 1:
                prev_gold_price = clean_nan(self.gold_data['收盘'].iloc[-2])
                prev_date = self.gold_data.index[-2]
                current_date = self.gold_data.index[-1]
                
                gold_change_rate = (gold_price - prev_gold_price) / prev_gold_price if prev_gold_price != 0 else 0
                
                print(f"📊 金价涨跌幅详细计算:")
                print(f"  当前日期: {current_date.strftime('%Y-%m-%d')}")
                print(f"  当前金价: {gold_price}")
                print(f"  前一日日期: {prev_date.strftime('%Y-%m-%d')}")
                print(f"  前一日金价: {prev_gold_price}")
                print(f"  涨跌金额: {gold_price - prev_gold_price}")
                print(f"  涨跌幅计算: ({gold_price} - {prev_gold_price}) / {prev_gold_price} = {gold_change_rate:.6f} = {gold_change_rate*100:.4f}%")
                
                # 检查数据合理性
                if abs(gold_change_rate) > 0.1:  # 涨跌幅超过10%
                    print(f"⚠️ 警告: 金价涨跌幅异常大 ({gold_change_rate*100:.2f}%)")
                if prev_gold_price == gold_price:
                    print(f"⚠️ 警告: 前一日金价与当前金价相同，可能数据有问题")
                    
            else:
                print("⚠️ 金价数据不足，无法计算涨跌幅")
        else:
            print("⚠️ 金价数据为空，使用默认值")
        
        # 从数据库加载持久化数据
        persistent_data = self.load_state_from_database()
        print(f"📊 从数据库加载的持久化数据: {persistent_data}")
        
        # 计算总资产和投资成本 - 确保数据类型一致
        total_shares = float(persistent_data.get('total_shares', 0))
        total_cost = float(persistent_data.get('total_cost', 0))
        # 总资产 = 当前市值（可卖出的价值）
        total_assets = current_price * total_shares  # 当前市值
        current_market_value = current_price * total_shares  # 当前市值（与total_assets相同）
        
        # 计算收益率
        if total_cost > 0:
            cumulative_return = (total_assets - total_cost) / total_cost  # 累计收益率
        else:
            cumulative_return = 0
        
        # 计算年化收益率
        # 从JSON文件获取投资开始日期，如果没有则使用默认值
        last_trade_date = persistent_data.get('last_trade_date', '2025-01-01')
        try:
            from datetime import datetime
            trade_date = datetime.strptime(last_trade_date, '%Y-%m-%d')
            current_date = datetime.now()
            investment_days = (current_date - trade_date).days
            if investment_days <= 0:
                investment_days = 1  # 避免除零错误
        except:
            investment_days = 365  # 默认一年
        
        if total_cost > 0 and investment_days > 0:
            annual_return = (cumulative_return / investment_days) * 365
        else:
            annual_return = 0
            
        print(f"📊 计算数据: total_shares={total_shares}, total_cost={total_cost}, total_assets={total_assets}")
        print(f"📊 投资天数: {investment_days}天")
        print(f"📊 收益率计算: cumulative_return={cumulative_return:.4f}, annual_return={annual_return:.4f}")
        
        # 构建状态信息
        status = {
            # 实时数据（不持久化）
            'current_price': current_price,
            'stock_change_rate': stock_change_rate,
            'gold_price': gold_price,
            'gold_change_rate': gold_change_rate,
            'total_assets': total_assets,  # 当前市值
            
            # 系统信息
            'data_points': len(self.stock_data),
            'date_range': {
                'start': self.stock_data.index.min().strftime('%Y-%m-%d'),
                'end': self.stock_data.index.max().strftime('%Y-%m-%d')
            },
            
            # 持久化数据
            'total_cost': persistent_data.get('total_cost', 0),
            'total_shares': total_shares,
            'cumulative_return': cumulative_return,  # 使用计算出的收益率
            'annual_return': annual_return,  # 使用计算出的年化收益率
            'position': persistent_data.get('position', {
                'has_position': False,
                'buy_price': 0,
                'shares': 0,
                'amount': 0,
                'current_profit_rate': 0,
                'max_profit_rate': 0
            })
        }
        
        print(f"📊 基础数据状态计算完成: 股价={current_price:.2f}, 涨跌={stock_change_rate:.4f}")
        
        # 保存状态到数据库
        self.save_state_to_database(status)
        
        return status
    
    def load_state_from_database(self):
        """
        从数据库加载策略状态
        
        Returns:
            dict: 策略状态数据
        """
        try:
            strategy = self.strategy_dao.load_user_info_by_auth(self.default_auth)
            if strategy:
                data = {
                    'total_cost': float(strategy.total_cost),
                    'total_shares': float(strategy.total_shares),
                    'history_max_profit': float(strategy.history_max_profit),
                    'last_total_profit': float(strategy.last_total_profit),
                    'position': strategy.get_position_dict(),
                    'trade_history': strategy.get_trade_history_list(),
                    'last_trade_date': strategy.last_trade_date.strftime('%Y-%m-%d') if strategy.last_trade_date else '',
                    'save_time': strategy.update_time.strftime('%Y-%m-%d %H:%M:%S') if strategy.update_time else ''
                }
                print(f"📂 从数据库加载状态: {data}")
                return data
            else:
                print("⚠️ 数据库中没有策略数据，使用默认值")
                return {}
        except Exception as e:
            print(f"❌ 从数据库加载状态失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def save_state_to_database(self, status):
        """
        保存策略状态到数据库
        
        Args:
            status (dict): 策略状态数据
        """
        try:
            # 创建策略对象
            strategy = ToolStockToolsGold()
            strategy.auth = self.default_auth
            strategy.total_cost = status.get('total_cost', 0)
            strategy.total_shares = status.get('total_shares', 0)
            strategy.history_max_profit = status.get('history_max_profit', 0)
            strategy.last_total_profit = status.get('last_total_profit', 0)
            strategy.set_position_dict(status.get('position', {}))
            strategy.set_trade_history_list(status.get('trade_history', []))
            
            # 处理日期字段
            last_trade_date = status.get('last_trade_date', '')
            if last_trade_date:
                try:
                    strategy.last_trade_date = datetime.strptime(last_trade_date, '%Y-%m-%d')
                except:
                    strategy.last_trade_date = None
            else:
                strategy.last_trade_date = None
            
            strategy.updater = 'system'
            strategy.creator = 'system'
            
            # 保存到数据库
            success = self.strategy_dao.save_user_info(strategy)
            if success:
                print(f"💾 状态已保存到数据库: 投资成本={strategy.total_cost}, 持股数={strategy.total_shares}")
            else:
                print("❌ 保存到数据库失败")
        except Exception as e:
            print(f"❌ 保存到数据库失败: {e}")
            import traceback
            traceback.print_exc()
    
    def calculate_cumulative_return(self, existing_state, current_status):
        """
        计算累计收益率
        
        Args:
            existing_state (dict): 现有状态
            current_status (dict): 当前状态
            
        Returns:
            float: 累计收益率
        """
        try:
            total_cost = existing_state.get('total_cost', 0)
            total_assets = current_status.get('current_price', 0) * current_status.get('position', {}).get('shares', 0)
            
            if total_cost > 0:
                return (total_assets - total_cost) / total_cost
            return 0
        except Exception as e:
            print(f"❌ 计算累计收益率失败: {e}")
            return 0
    
    def calculate_annual_return(self, existing_state, current_status):
        """
        计算年化收益率
        
        Args:
            existing_state (dict): 现有状态
            current_status (dict): 当前状态
            
        Returns:
            float: 年化收益率
        """
        try:
            cumulative_return = self.calculate_cumulative_return(existing_state, current_status)
            # 简化计算，假设6个月数据
            return cumulative_return * 2
        except Exception as e:
            print(f"❌ 计算年化收益率失败: {e}")
            return 0

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
