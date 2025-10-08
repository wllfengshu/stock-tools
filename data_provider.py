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

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入图表相关库
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 导入数据库操作类
sys.path.insert(0, os.path.abspath('./database'))
from database.strategy_dao import StrategyDAO
from database.table_entity import ToolStockToolsGold
from common_util import CommonUtil
strategy_dao = StrategyDAO()
common_util = CommonUtil()

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
        self.default_auth = 'abcdefaddd'
        # 懒加载数据容器
        self.stock_data = None
        self.gold_data = None
        print("✅ 数据提供者初始化完成")
    
    def get_current_status(self, stock_code='002155', months=6):
        """
        获取当前数据状态信息 - 基础信息模块的核心方法
        
        计算并返回：
        1. 当前股价和涨跌幅
        2. 金价和涨跌幅
        3. 数据统计信息
        
        Returns:
            dict: 数据状态信息，包含所有关键指标
        """
        # 懒加载数据
        if self.stock_data is None or getattr(self.stock_data, 'empty', True):
            try:
                self.stock_data = common_util.get_stock_data(months=months, stock_code=stock_code)
            except Exception as e:
                print(f"❌ 加载股票数据失败: {e}")
        if self.gold_data is None or getattr(self.gold_data, 'empty', True):
            try:
                self.gold_data = common_util.get_gold_data(months=months)
            except Exception as e:
                print(f"❌ 加载金价数据失败: {e}")

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
        gold_price = 0.0  # 默认金价
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
                'start': (self.stock_data.index.min().strftime('%Y-%m-%d')
                          if isinstance(self.stock_data.index.min(), pd.Timestamp) else str(self.stock_data.index.min())),
                'end': (self.stock_data.index.max().strftime('%Y-%m-%d')
                        if isinstance(self.stock_data.index.max(), pd.Timestamp) else str(self.stock_data.index.max()))
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
            strategy = strategy_dao.load_user_info_by_auth(self.default_auth)
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
            success = strategy_dao.save_user_info(strategy)
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
            return 0
    
    def create_chart_data(self, data, stock_name, gold_data=None, trade_points=None):
        """创建专业图表数据 - 支持双K线图显示"""
        
        # 创建子图 - 如果有伦敦金数据，增加一个子图，增加图表间距
        if gold_data is not None and not gold_data.empty:
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.12,  # 增加图表间距
                subplot_titles=(f'{stock_name} K线图', '伦敦金K线图', '成交量'),
                row_heights=[0.4, 0.3, 0.3]
            )
        else:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,  # 增加图表间距
                subplot_titles=(f'{stock_name} K线图', '成交量'),
                row_heights=[0.7, 0.3]
            )
        
        # 添加K线图 - 按照标准示例格式
        # 将pandas数据转换为标准格式
        kline_data = {
            'date': data.index.strftime('%Y-%m-%d').tolist(),
            'open': data['开盘'].tolist(),
            'high': data['最高'].tolist(),
            'low': data['最低'].tolist(),
            'close': data['收盘'].tolist()
        }
        
        # 添加K线图 - 使用标准格式，隐藏底部缩略图
        fig.add_trace(go.Candlestick(
            x=kline_data['date'],        # 时间序列
            open=kline_data['open'],     # 开盘价
            high=kline_data['high'],     # 最高价
            low=kline_data['low'],       # 最低价
            close=kline_data['close'],   # 收盘价
            name='股票K线'
        ))
        
        # 添加移动平均线 - 使用标准格式
        if len(data) >= 5:
            ma5 = data['收盘'].rolling(window=5).mean()
            ma5_data = {
                'date': data.index.strftime('%Y-%m-%d').tolist(),
                'ma5': ma5.tolist()
            }
            fig.add_trace(
                go.Scatter(
                    x=ma5_data['date'],
                    y=ma5_data['ma5'],
                    mode='lines',
                    name='MA5',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )
        
        if len(data) >= 20:
            ma20 = data['收盘'].rolling(window=20).mean()
            ma20_data = {
                'date': data.index.strftime('%Y-%m-%d').tolist(),
                'ma20': ma20.tolist()
            }
            fig.add_trace(
                go.Scatter(
                    x=ma20_data['date'],
                    y=ma20_data['ma20'],
                    mode='lines',
                    name='MA20',
                    line=dict(color='orange', width=2)
                ),
                row=1, col=1
            )
        
        # 添加伦敦金K线图
        if gold_data is not None and not gold_data.empty:
            # 检查必要的列是否存在
            required_columns = ['开盘', '最高', '最低', '收盘']
            missing_columns = [col for col in required_columns if col not in gold_data.columns]
            
            if not missing_columns:
                # 将伦敦金数据转换为标准格式
                gold_kline_data = {
                    'date': gold_data.index.strftime('%Y-%m-%d').tolist(),
                    'open': gold_data['开盘'].tolist(),
                    'high': gold_data['最高'].tolist(),
                    'low': gold_data['最低'].tolist(),
                    'close': gold_data['收盘'].tolist()
                }
                
                # 添加伦敦金K线图
                fig.add_trace(go.Candlestick(
                    x=gold_kline_data['date'],
                    open=gold_kline_data['open'],
                    high=gold_kline_data['high'],
                    low=gold_kline_data['low'],
                    close=gold_kline_data['close'],
                    name='伦敦金',
                    increasing_line_color='red',
                    decreasing_line_color='green',
                    hoverinfo='x+y',
                    hovertext=[f'日期: {date}<br>开盘: ${open:.2f}<br>最高: ${high:.2f}<br>最低: ${low:.2f}<br>收盘: ${close:.2f}' 
                              for date, open, high, low, close in zip(
                                  gold_kline_data['date'],
                                  gold_kline_data['open'],
                                  gold_kline_data['high'],
                                  gold_kline_data['low'],
                                  gold_kline_data['close']
                              )]
                ), row=2, col=1)
                
                # 添加伦敦金移动平均线 - MA5
                if len(gold_data) >= 5:
                    gold_ma5 = gold_data['收盘'].rolling(window=5).mean()
                    gold_ma5_data = {
                        'date': gold_data.index.strftime('%Y-%m-%d').tolist(),
                        'ma5': gold_ma5.tolist()
                    }
                    fig.add_trace(
                        go.Scatter(
                            x=gold_ma5_data['date'],
                            y=gold_ma5_data['ma5'],
                            mode='lines',
                            name='伦敦金MA5',
                            line=dict(color='blue', width=2),
                            hovertemplate='<b>伦敦金MA5</b><br>日期: %{x}<br>价格: $%{y:.2f}<extra></extra>'
                        ),
                        row=2, col=1
                    )
                
                # 添加伦敦金移动平均线 - MA20
                if len(gold_data) >= 20:
                    gold_ma20 = gold_data['收盘'].rolling(window=20).mean()
                    gold_ma20_data = {
                        'date': gold_data.index.strftime('%Y-%m-%d').tolist(),
                        'ma20': gold_ma20.tolist()
                    }
                    fig.add_trace(
                        go.Scatter(
                            x=gold_ma20_data['date'],
                            y=gold_ma20_data['ma20'],
                            mode='lines',
                            name='伦敦金MA20',
                            line=dict(color='orange', width=2),
                            hovertemplate='<b>伦敦金MA20</b><br>日期: %{x}<br>价格: $%{y:.2f}<extra></extra>'
                        ),
                        row=2, col=1
                    )
        
        # 添加交易点标识
        if trade_points and len(trade_points) > 0:
            # 买入点
            buy_points = [point for point in trade_points if point.get('action') == 'BUY']
            if buy_points:
                buy_dates = [point['date'] for point in buy_points]
                buy_prices = [point['price'] for point in buy_points]
                
                fig.add_trace(go.Scatter(
                    x=buy_dates,
                    y=buy_prices,
                    mode='markers',
                    name='买入点',
                    marker=dict(
                        symbol='triangle-up',
                        size=15,
                        color='red',
                        line=dict(width=2, color='darkred')
                    ),
                    hovertemplate='<b>买入点</b><br>日期: %{x}<br>价格: %{y:.2f}元<extra></extra>'
                ), row=1, col=1)
            
            # 卖出点
            sell_points = [point for point in trade_points if point.get('action') == 'SELL']
            if sell_points:
                sell_dates = [point['date'] for point in sell_points]
                sell_prices = [point['price'] for point in sell_points]
                
                fig.add_trace(go.Scatter(
                    x=sell_dates,
                    y=sell_prices,
                    mode='markers',
                    name='卖出点',
                    marker=dict(
                        symbol='triangle-down',
                        size=15,
                        color='green',
                        line=dict(width=2, color='darkgreen')
                    ),
                    hovertemplate='<b>卖出点</b><br>日期: %{x}<br>价格: %{y:.2f}元<extra></extra>'
                ), row=1, col=1)
        
        # 添加成交量 - 使用标准格式（上涨红色，下跌绿色）
        colors = ['red' if close >= open_price else 'green' 
                 for close, open_price in zip(data['收盘'], data['开盘'])]
        
        volume_data = {
            'date': data.index.strftime('%Y-%m-%d').tolist(),
            'volume': data['成交量'].tolist(),
            'colors': colors
        }
        
        # 确定成交量的行号
        volume_row = 3 if (gold_data is not None and not gold_data.empty) else 2
        
        fig.add_trace(
            go.Bar(
                x=volume_data['date'],
                y=volume_data['volume'],
                name='成交量',
                marker=dict(color=volume_data['colors'], opacity=0.7)
            ),
            row=volume_row, col=1
        )
        
        # 更新布局 - 隐藏底部缩略图，增加图表间距
        if gold_data is not None and not gold_data.empty:
            # 三子图布局
            fig.update_layout(
                title=f'{stock_name} & 伦敦金 K线图交易系统',
                yaxis_title='股票价格 (元)',
                yaxis2_title='伦敦金价格 (美元)',
                yaxis3_title='成交量',
                height=1000,
                width=None,
                showlegend=True,
                template='plotly_white',
                autosize=True,
                margin=dict(l=50, r=50, t=80, b=50),
                # 隐藏底部缩略图
                xaxis=dict(
                    type='category',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='lightgray',
                    matches=None,
                    tickformat='%Y-%m-%d',
                    rangeslider=dict(visible=False)  # 隐藏股票K线图底部缩略图
                ),
                xaxis2=dict(
                    type='category',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='lightgray',
                    matches=None,
                    tickformat='%Y-%m-%d',
                    rangeslider=dict(visible=False)  # 隐藏伦敦金K线图底部缩略图
                ),
                yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
                yaxis2=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
                yaxis3=dict(showgrid=True, gridwidth=1, gridcolor='lightgray')
            )
        else:
            # 二子图布局
            fig.update_layout(
                title=f'{stock_name} K线图交易系统',
                yaxis_title='价格 (元)',
                yaxis2_title='成交量',
                height=800,
                width=None,
                showlegend=True,
                template='plotly_white',
                autosize=True,
                margin=dict(l=50, r=50, t=80, b=50),
                # 隐藏底部缩略图
                xaxis=dict(
                    type='category',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='lightgray',
                    matches=None,
                    tickformat='%Y-%m-%d',
                    rangeslider=dict(visible=False)  # 隐藏底部缩略图
                ),
                yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
                yaxis2=dict(showgrid=True, gridwidth=1, gridcolor='lightgray')
            )
        
        # 转换为JSON格式
        return fig.to_json()
