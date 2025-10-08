#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
改进版黄金板块量化交易策略
基于国际金价涨跌的A股黄金板块交易策略
"""

import sys
import os
import json
from datetime import datetime, timedelta
import time
import pandas as pd
import akshare as ak

# 添加数据库模块
sys.path.insert(0, os.path.abspath('./database'))
from database.strategy_dao import StrategyDAO
from database.table_entity import ToolStockToolsGold

class TradingStrategy:
    """
    策略逻辑：
    1. 每天早上8点获取国际金价
    2. 计算金价涨跌幅
    3. 如果金价上涨，则买入黄金股（买入金额 = 基础金额 × 金价涨幅）
    4. 如果金价下跌，则不买入
    5. 卖出规则：盈利回调时卖出（从5%回调到4%）
    6. 止损：亏损10%时卖出
    """
    
    def __init__(self):
        """
        初始化交易策略 - 使用默认参数，支持后续动态更新
        """
        # 默认用户标识
        self.user_id = 100001
        self.auth = 'default_user'
        
        # 默认策略参数
        self.base_investment = 1000
        self.stop_loss_rate = 0.10
        self.profit_callback_rate = 0.01
        self.max_profit_rate = 0.5
        self.min_gold_change = 0.002
        self.min_buy_amount = 100
        self.transaction_cost_rate = 0.001
        self.max_hold_days = 30
        
        # 交易记录
        self.trade_history = []
        # 当前持仓
        self.current_position = None
        # 最后交易日期
        self.last_trade_date = None
        
        # 全局状态管理（持久化存储）
        self.total_cost = 0  # 总成本（初始资金+每次买入的资金）
        self.total_shares = 0  # 总持股数量
        self.total_investment = 0  # 总投资金额
        self.history_max_profit = 0  # 历史最大盈利金额
        self.last_total_profit = 0  # 上一次的总盈利
        
        # 数据库DAO
        self.dao = StrategyDAO()
        
        # 加载历史状态
        self.load_state()
        
        print(f"改进版策略初始化完成:")
        print(f"  基础投资金额: {self.base_investment}元")
        print(f"  止损率: {self.stop_loss_rate*100}%")
        print(f"  盈利回调率: {self.profit_callback_rate*100}%")
        print(f"  最大盈利率: {self.max_profit_rate*100}%")
        print(f"  最小金价涨幅阈值: {self.min_gold_change*100}%")
        print(f"  最小买入金额: {self.min_buy_amount}元")
        print(f"  交易成本率: {self.transaction_cost_rate*100}%")
        print(f"  最大持仓天数: {self.max_hold_days}天")
        print(f"  历史最大盈利: {self.history_max_profit:.2f}元")
        print(f"  总成本: {self.total_cost:.2f}元")
        print(f"  总持股: {self.total_shares:.2f}股")
    
    def update_strategy_params(self, user_id=None, auth=None, base_investment=None, 
                              stop_loss_rate=None, profit_callback_rate=None, 
                              max_profit_rate=None, min_gold_change=None, 
                              min_buy_amount=None, transaction_cost_rate=None, 
                              max_hold_days=None):
        """
        动态更新策略参数
        
        Args:
            user_id: 用户ID，对应数据库中的tool_stock_tools_gold_id
            auth: 用户认证标识，用于数据库查询
            base_investment: 每次投资的基准金额
            stop_loss_rate: 止损率
            profit_callback_rate: 盈利回调率
            max_profit_rate: 最大盈利率
            min_gold_change: 最小金价涨幅阈值
            min_buy_amount: 最小买入金额
            transaction_cost_rate: 交易成本率
            max_hold_days: 最大持仓天数
        """
        # 更新用户标识
        if user_id is not None:
            self.user_id = user_id
        if auth is not None:
            self.auth = auth
        
        # 更新策略参数
        if base_investment is not None:
            self.base_investment = base_investment
        if stop_loss_rate is not None:
            self.stop_loss_rate = stop_loss_rate
        if profit_callback_rate is not None:
            self.profit_callback_rate = profit_callback_rate
        if max_profit_rate is not None:
            self.max_profit_rate = max_profit_rate
        if min_gold_change is not None:
            self.min_gold_change = min_gold_change
        if min_buy_amount is not None:
            self.min_buy_amount = min_buy_amount
        if transaction_cost_rate is not None:
            self.transaction_cost_rate = transaction_cost_rate
        if max_hold_days is not None:
            self.max_hold_days = max_hold_days
        
        print(f"策略参数已更新:")
        print(f"  用户ID: {self.user_id}")
        print(f"  用户认证: {self.auth}")
        print(f"  基础投资金额: {self.base_investment}元")
        print(f"  止损率: {self.stop_loss_rate*100}%")
        print(f"  盈利回调率: {self.profit_callback_rate*100}%")
        print(f"  最大盈利率: {self.max_profit_rate*100}%")
        print(f"  最小金价涨幅阈值: {self.min_gold_change*100}%")
        print(f"  最小买入金额: {self.min_buy_amount}元")
        print(f"  交易成本率: {self.transaction_cost_rate*100}%")
        print(f"  最大持仓天数: {self.max_hold_days}天")
        
        # 重新加载状态（因为用户可能改变了）
        self.load_state()
    
    def load_state(self):
        """从数据库加载策略状态"""
        try:
            # 从数据库加载用户信息
            user_data = self.dao.load_user_info_by_auth(self.auth)
                
            if user_data:
                # 恢复状态
                self.total_cost = user_data.total_cost
                self.total_shares = user_data.total_shares
                self.history_max_profit = user_data.history_max_profit
                self.last_total_profit = user_data.last_total_profit
                
                # 恢复交易历史
                self.trade_history = user_data.get_trade_history_list()
                
                # 恢复最后交易日期
                if user_data.last_trade_date:
                    if isinstance(user_data.last_trade_date, str):
                        self.last_trade_date = datetime.strptime(user_data.last_trade_date, '%Y-%m-%d').date()
                    else:
                        self.last_trade_date = user_data.last_trade_date.date()
                
                # 恢复持仓信息
                position_dict = user_data.get_position_dict()
                if position_dict.get('has_position', False):
                    self.current_position = position_dict
                
                print(f"[数据库] 成功加载历史状态:")
                print(f"  用户ID: {user_data.tool_stock_tools_gold_id}")
                print(f"  总成本: {self.total_cost:.2f}元")
                print(f"  总持股: {self.total_shares:.2f}股")
                print(f"  历史最大盈利: {self.history_max_profit:.2f}元")
                print(f"  交易历史: {len(self.trade_history)}条记录")
                print(f"  最后交易日期: {self.last_trade_date}")
            else:
                print(f"[数据库] 未找到用户数据，使用默认值")
                print(f"[数据库] 用户认证: {self.auth}")
        except Exception as e:
            print(f"[数据库] 加载状态失败: {e}")
            print(f"[数据库] 使用默认值继续运行")
            import traceback
            traceback.print_exc()
    
    def save_state(self):
        """保存策略状态到数据库"""
        try:
            # 创建用户数据对象
            user_data = ToolStockToolsGold(
                tool_stock_tools_gold_id=self.user_id,
                auth=self.auth,
                total_cost=self.total_cost,
                total_shares=self.total_shares,
                history_max_profit=self.history_max_profit,
                last_total_profit=self.last_total_profit,
                last_trade_date=self.last_trade_date
            )
            
            # 设置持仓信息
            if self.current_position:
                user_data.set_position_dict(self.current_position)
            else:
                user_data.set_position_dict({
                    'has_position': self.total_shares > 0,
                    'buy_price': 0,
                    'shares': self.total_shares,
                    'amount': self.total_shares * 0,  # 需要当前价格计算
                    'current_profit_rate': 0,
                    'max_profit_rate': 0
                })
            
            # 设置交易历史
            user_data.set_trade_history_list(self.trade_history)
            
            # 保存到数据库
            success = self.dao.save_user_info(user_data)
            
            if success:
                print(f"[数据库] 状态已保存到数据库")
                print(f"  用户ID: {self.user_id}")
                print(f"  总成本: {self.total_cost:.2f}元")
                print(f"  总持股: {self.total_shares:.2f}股")
                print(f"  历史最大盈利: {self.history_max_profit:.2f}元")
            else:
                print(f"[数据库] 保存状态失败")
        except Exception as e:
            print(f"[数据库] 保存状态失败: {e}")
            import traceback
            traceback.print_exc()
    
    def get_gold_price_with_validation(self):
        """获取并验证金价数据"""
        try:
            print("正在获取国际金价数据...")
            
            # 尝试多种方式获取金价数据
            gold_data = None
            
            # 方法1: 实时数据
            try:
                print("尝试获取实时金价数据...")
                gold_data = ak.futures_foreign_commodity_realtime(symbol=['XAU'])
                if gold_data is not None and not gold_data.empty:
                    print("[成功] 实时金价数据获取成功")
                    print(f"实时数据形状: {gold_data.shape}")
                    print(f"实时数据列名: {gold_data.columns.tolist()}")
                    print(f"实时数据前几行:\n{gold_data.head()}")
            except Exception as e:
                print(f"实时金价数据获取失败: {e}")
            
            # 方法2: 历史数据作为备选
            if gold_data is None or gold_data.empty or len(gold_data) < 2:
                try:
                    print("尝试获取历史金价数据...")
                    # 获取更多历史数据，确保有足够的数据计算涨跌幅
                    # 使用正确的akshare函数获取历史数据
                    gold_data = ak.futures_foreign_hist(symbol='XAU')
                    if gold_data is not None and not gold_data.empty:
                        print("[成功] 历史金价数据获取成功")
                        print(f"历史数据形状: {gold_data.shape}")
                        print(f"历史数据列名: {gold_data.columns.tolist()}")
                except Exception as e:
                    print(f"历史金价数据获取失败: {e}")
            
            # 方法3: 使用其他金价数据源
            if gold_data is None or gold_data.empty or len(gold_data) < 2:
                try:
                    print("尝试获取其他金价数据源...")
                    # 尝试获取伦敦金数据
                    gold_data = ak.futures_foreign_hist(symbol='XAUUSD')
                    if gold_data is not None and not gold_data.empty:
                        print("[成功] 伦敦金数据获取成功")
                except Exception as e:
                    print(f"伦敦金数据获取失败: {e}")
            
            if gold_data is None or gold_data.empty:
                print("[错误] 所有金价数据获取方式都失败")
                return None, None
            
            print(f"最终获取的金价数据形状: {gold_data.shape}")
            print(f"数据列名: {gold_data.columns.tolist()}")
            print(f"数据前几行:\n{gold_data.head()}")
            
            # 数据验证和处理
            if len(gold_data) >= 2:
                # 有足够的历史数据
                try:
                    # 尝试不同的列名
                    price_columns = ['收盘', 'close', 'Close', 'CLOSE', '价格', 'price']
                    current_price = None
                    previous_price = None
                    
                    for col in price_columns:
                        if col in gold_data.columns:
                            current_price = float(gold_data.iloc[-1][col])
                            previous_price = float(gold_data.iloc[-2][col])
                            print(f"使用列名 '{col}' 获取价格数据")
                            break
                    
                    # 如果列名匹配失败，尝试使用索引
                    if current_price is None:
                        print("尝试使用索引获取价格数据...")
                        # 假设价格在第二列（索引1）
                        current_price = float(gold_data.iloc[-1, 1])
                        previous_price = float(gold_data.iloc[-2, 1])
                        print("使用索引1获取价格数据")
                    
                    if current_price is not None and previous_price is not None:
                        print(f"当前金价: {current_price}美元")
                        print(f"前一日金价: {previous_price}美元")
                        return current_price, previous_price
                    else:
                        print("[错误] 无法从数据中提取价格信息")
                        return None, None
                        
                except Exception as e:
                    print(f"[错误] 处理金价数据时出错: {e}")
                    print(f"数据内容: {gold_data.iloc[-2:].to_dict()}")
                    return None, None
            else:
                print(f"[错误] 金价数据不足，只有{len(gold_data)}条记录，需要至少2条")
                return None, None
                
        except Exception as e:
            print(f"[错误] 获取金价数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def get_stock_price_with_retry(self, stock_code='002155', max_retries=3):
        """获取股票价格，带重试机制"""
        for attempt in range(max_retries):
            try:
                print(f"正在获取股票{stock_code}价格 (尝试 {attempt + 1}/{max_retries})...")
                
                stock_data = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=(datetime.now() - timedelta(days=10)).strftime('%Y%m%d'),
                    end_date=datetime.now().strftime('%Y%m%d')
                )
                
                if stock_data is not None and not stock_data.empty:
                    current_price = float(stock_data.iloc[-1]['收盘'])
                    print(f"[成功] 股票当前价格: {current_price}元")
                    return current_price
                else:
                    print(f"股票数据为空 (尝试 {attempt + 1}/{max_retries})")
                    
            except Exception as e:
                print(f"获取股票价格失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                print("等待2秒后重试...")
                time.sleep(2)
        
        print("[错误] 所有重试都失败")
        return None
    
    def should_buy_improved(self, gold_change_rate):
        """
        买入判断逻辑
        
        Args:
            gold_change_rate: 金价涨跌幅
            
        Returns:
            tuple: (是否买入, 买入金额)
        """
        # 检查金价涨幅是否达到最小阈值
        if gold_change_rate < self.min_gold_change:
            print(f"金价涨幅{gold_change_rate*100:.2f}%未达到最小阈值{self.min_gold_change*100:.2f}%，不买入")
            return False, 0
        
        # 计算买入金额，但设置合理的上限和下限
        buy_amount = self.base_investment * gold_change_rate
        
        # 确保买入金额不小于最小值
        if buy_amount < self.min_buy_amount:
            buy_amount = self.min_buy_amount
            print(f"买入金额调整为最小金额: {buy_amount}元")
        
        # 设置买入金额上限（不超过基础投资金额）
        max_buy_amount = self.base_investment * 1
        if buy_amount > max_buy_amount:
            buy_amount = max_buy_amount
            print(f"买入金额调整为上限: {buy_amount}元")
        
        print(f"金价上涨{gold_change_rate*100:.2f}%，建议买入金额: {buy_amount:.2f}元")
        return True, buy_amount
    
    def should_sell_improved(self, current_price):
        """
        卖出判断逻辑（基于全局状态）
        
        Args:
            current_price: 当前价格
            
        Returns:
            tuple: (是否卖出, 卖出原因)
        """
        # 计算当前持仓市值
        current_market_value = self.total_shares * current_price
        
        # 计算当前总盈利
        current_total_profit = current_market_value - self.total_cost
        
        # 计算当前盈利率
        current_profit_rate = current_total_profit / self.total_cost if self.total_cost > 0 else 0
        
        print(f"当前状态检查:")
        print(f"  总成本: {self.total_cost:.2f}元")
        print(f"  总持股: {self.total_shares:.2f}股")
        print(f"  当前持仓市值: {current_market_value:.2f}元")
        print(f"  当前总盈利: {current_total_profit:.2f}元")
        print(f"  当前盈利率: {current_profit_rate*100:.2f}%")
        print(f"  历史最大盈利: {self.history_max_profit:.2f}元")
        print(f"  上一次总盈利: {self.last_total_profit:.2f}元")
        
        # 1. 止损检查
        if current_profit_rate <= -self.stop_loss_rate:
            return True, f"止损：当前亏损{abs(current_profit_rate)*100:.2f}%"
        
        # 2. 盈利回调检查（修复版）
        if self.history_max_profit > 0:  # 只有当历史最大盈利大于0时才检查回调
            # 计算盈利缩小的金额
            profit_decrease = self.history_max_profit - current_total_profit
            # 计算盈利缩小的比例
            profit_decrease_rate = profit_decrease / self.history_max_profit if self.history_max_profit > 0 else 0
            
            print(f"盈利回调检查:")
            print(f"  盈利缩小金额: {profit_decrease:.2f}元")
            print(f"  盈利缩小比例: {profit_decrease_rate*100:.2f}%")
            print(f"  盈利回调阈值: {self.profit_callback_rate*100:.2f}%")
            
            if profit_decrease_rate >= self.profit_callback_rate:
                return True, f"盈利回调：从{self.history_max_profit:.2f}元回调到{current_total_profit:.2f}元，缩小{profit_decrease_rate*100:.2f}%"
        
        # 3. 长期持有检查（超过max_hold_days天强制卖出）
        if self.current_position and 'buy_date' in self.current_position:
            try:
                if isinstance(self.current_position['buy_date'], str):
                    buy_date = datetime.strptime(self.current_position['buy_date'], '%Y-%m-%d %H:%M:%S')
                else:
                    buy_date = self.current_position['buy_date']
                days_held = (datetime.now() - buy_date).days
                if days_held > self.max_hold_days:
                    return True, f"长期持有：已持有{days_held}天"
            except Exception as e:
                print(f"计算持仓天数时出错: {e}")
        
        # 4. 大幅盈利检查（盈利超过max_profit_rate%时考虑卖出）
        if current_profit_rate > self.max_profit_rate:
            return True, f"大幅盈利：当前盈利{current_profit_rate*100:.2f}%"
        
        return False, "继续持有"
    
    def can_trade_today(self):
        """检查今天是否可以交易（防止频繁交易）"""
        today = datetime.now().date()
        
        if self.last_trade_date is None:
            return True
        
        if self.last_trade_date == today:
            print("今天已经交易过，避免频繁交易")
            return False
        
        return True
    
    def calculate_transaction_cost(self, amount):
        """计算交易成本"""
        return amount * self.transaction_cost_rate
    
    def execute_strategy_improved(self, stock_code='002155'):
        """
        执行改进版量化交易策略
        """
        print(f"\n{'='*60}")
        print(f"执行改进版量化交易策略 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # 1. 检查交易频率
            if not self.can_trade_today():
                return {'error': '今天已经交易过，避免频繁交易'}
            
            # 2. 获取并验证金价数据
            current_gold_price, previous_gold_price = self.get_gold_price_with_validation()
            if current_gold_price is None or previous_gold_price is None:
                return {'error': '无法获取有效的金价数据'}
            
            gold_change_rate = (current_gold_price - previous_gold_price) / previous_gold_price
            print(f"金价涨跌幅: {gold_change_rate*100:.2f}%")
            
            # 3. 获取股票价格
            current_stock_price = self.get_stock_price_with_retry(stock_code)
            if current_stock_price is None:
                return {'error': '无法获取股票数据'}
            
            # 4. 执行改进的买入逻辑
            should_buy, buy_amount = self.should_buy_improved(gold_change_rate)
            
            # 5. 检查卖出条件（如果有持仓）
            should_sell = False
            sell_reason = ""
            if self.total_shares > 0:  # 如果有持股就检查卖出
                should_sell, sell_reason = self.should_sell_improved(current_stock_price)
                print(f"卖出检查: {sell_reason}")
            
            # 6. 执行交易
            trade_result = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'gold_price': current_gold_price,
                'gold_change_rate': gold_change_rate,
                'stock_price': current_stock_price,
                'should_buy': should_buy,
                'buy_amount': buy_amount,
                'should_sell': should_sell,
                'sell_reason': sell_reason,
                'current_position': self.current_position
            }
            
            if should_buy:
                # 执行买入
                transaction_cost = self.calculate_transaction_cost(buy_amount)
                net_buy_amount = buy_amount - transaction_cost
                shares = net_buy_amount / current_stock_price
                
                # 更新全局状态
                self.total_cost += buy_amount  # 增加总成本
                self.total_shares += shares   # 增加总持股
                self.total_investment += buy_amount  # 增加总投资
                
                # 记录当前持仓信息（用于显示）
                self.current_position = {
                    'has_position': True,
                    'buy_price': current_stock_price,
                    'shares': shares,
                    'buy_amount': buy_amount,
                    'net_buy_amount': net_buy_amount,
                    'transaction_cost': transaction_cost,
                    'buy_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'max_profit_rate': 0,
                    'current_profit_rate': 0
                }
                
                self.last_trade_date = datetime.now().date()
                trade_result['action'] = 'BUY'
                trade_result['shares'] = shares
                trade_result['transaction_cost'] = transaction_cost
                trade_result['total_shares'] = self.total_shares
                trade_result['total_cost'] = self.total_cost
                
                print(f"[成功] 执行买入: {shares:.2f}股，金额: {buy_amount:.2f}元，手续费: {transaction_cost:.2f}元")
                print(f"更新后状态: 总成本={self.total_cost:.2f}元，总持股={self.total_shares:.2f}股")
                
                # 保存状态到数据库
                self.save_state()
                
            elif should_sell and self.total_shares > 0:
                # 执行卖出（全部卖出）
                sell_amount = self.total_shares * current_stock_price
                transaction_cost = self.calculate_transaction_cost(sell_amount)
                net_sell_amount = sell_amount - transaction_cost
                
                # 计算总盈利
                total_profit = net_sell_amount - self.total_cost
                total_profit_rate = total_profit / self.total_cost if self.total_cost > 0 else 0
                
                # 记录交易历史
                self.trade_history.append({
                    'sell_price': current_stock_price,
                    'shares': self.total_shares,
                    'sell_amount': sell_amount,
                    'net_sell_amount': net_sell_amount,
                    'total_cost': self.total_cost,
                    'total_profit': total_profit,
                    'total_profit_rate': total_profit_rate,
                    'sell_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'sell_reason': sell_reason,
                    'transaction_cost': transaction_cost
                })
                
                # 更新历史最大盈利
                if total_profit > self.history_max_profit:
                    self.history_max_profit = total_profit
                
                # 更新上一次总盈利
                self.last_total_profit = total_profit
                
                self.last_trade_date = datetime.now().date()
                trade_result['action'] = 'SELL'
                trade_result['total_profit'] = total_profit
                trade_result['total_profit_rate'] = total_profit_rate
                trade_result['sell_reason'] = sell_reason
                trade_result['transaction_cost'] = transaction_cost
                trade_result['total_shares'] = self.total_shares
                trade_result['total_cost'] = self.total_cost
                
                print(f"[成功] 执行卖出: {self.total_shares:.2f}股，总盈利: {total_profit:.2f}元 ({total_profit_rate*100:.2f}%)")
                print(f"卖出原因: {sell_reason}")
                
                # 清空持仓
                self.total_shares = 0
                self.total_cost = 0
                self.current_position = None
                
                # 保存状态到数据库
                self.save_state()
            
            # 7. 更新持仓状态和盈利信息
            if self.total_shares > 0:
                current_market_value = self.total_shares * current_stock_price
                current_total_profit = current_market_value - self.total_cost
                current_profit_rate = current_total_profit / self.total_cost if self.total_cost > 0 else 0
                
                # 更新历史最大盈利
                if current_total_profit > self.history_max_profit:
                    self.history_max_profit = current_total_profit
                
                trade_result['current_market_value'] = current_market_value
                trade_result['current_total_profit'] = current_total_profit
                trade_result['current_profit_rate'] = current_profit_rate
                trade_result['history_max_profit'] = self.history_max_profit
                trade_result['total_shares'] = self.total_shares
                trade_result['total_cost'] = self.total_cost
                
                print(f"当前持仓状态:")
                print(f"  持仓市值: {current_market_value:.2f}元")
                print(f"  当前总盈利: {current_total_profit:.2f}元")
                print(f"  当前盈利率: {current_profit_rate*100:.2f}%")
                print(f"  历史最大盈利: {self.history_max_profit:.2f}元")
            
            return trade_result
            
        except Exception as e:
            error_msg = f'策略执行失败: {str(e)}'
            print(f"[错误] {error_msg}")
            import traceback
            traceback.print_exc()
            return {'error': error_msg}
    
    def get_strategy_status_improved(self, refresh_from_db=False):
        """获取改进的策略状态（基于全局状态）
        
        Args:
            refresh_from_db: 是否从数据库重新加载最新状态
        """
        # 如果需要从数据库刷新状态
        if refresh_from_db:
            self.load_state()
        
        if self.total_shares <= 0:
            return {
                'has_position': False,
                'message': '当前无持仓',
                'total_cost': self.total_cost,
                'total_shares': self.total_shares,
                'history_max_profit': self.history_max_profit
            }
        
        try:
            current_price = self.get_stock_price_with_retry()
            if current_price is None:
                return {
                    'has_position': True,
                    'error': '无法获取当前股票价格',
                    'total_cost': self.total_cost,
                    'total_shares': self.total_shares
                }
            
            # 计算当前状态
            current_market_value = self.total_shares * current_price
            current_total_profit = current_market_value - self.total_cost
            current_profit_rate = current_total_profit / self.total_cost if self.total_cost > 0 else 0
            
            return {
                'has_position': True,
                'current_price': current_price,
                'total_shares': self.total_shares,
                'total_cost': self.total_cost,
                'current_market_value': current_market_value,
                'current_total_profit': current_total_profit,
                'current_profit_rate': current_profit_rate,
                'history_max_profit': self.history_max_profit,
                'last_total_profit': self.last_total_profit
            }
        except Exception as e:
            return {
                'has_position': True,
                'error': f'获取持仓状态失败: {str(e)}',
                'total_cost': self.total_cost,
                'total_shares': self.total_shares
            }
    
    def get_strategy_summary_improved(self, refresh_from_db=False):
        """获取改进的策略摘要
        
        Args:
            refresh_from_db: 是否从数据库重新加载最新状态
        """
        # 如果需要从数据库刷新状态
        if refresh_from_db:
            self.load_state()
        
        total_trades = len(self.trade_history)
        total_net_profit = sum([trade.get('total_profit', 0) for trade in self.trade_history])
        total_transaction_cost = sum([trade.get('transaction_cost', 0) for trade in self.trade_history])
        win_trades = len([trade for trade in self.trade_history if trade.get('total_profit', 0) > 0])
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'total_net_profit': total_net_profit,
            'total_transaction_cost': total_transaction_cost,
            'win_trades': win_trades,
            'win_rate': win_rate,
            'current_position': self.total_shares > 0,
            'total_shares': self.total_shares,
            'total_cost': self.total_cost,
            'history_max_profit': self.history_max_profit,
            'last_trade_date': self.last_trade_date.strftime('%Y-%m-%d') if self.last_trade_date else None
        }

    def run_backtest(self, stock_code='002155', months=6, start_date=None, end_date=None):
        """
        运行历史回测
        
        Args:
            stock_code: 股票代码
            months: 回测月数
            start_date: 开始日期 (YYYY-MM-DD格式)
            end_date: 结束日期 (YYYY-MM-DD格式)
            
        Returns:
            dict: 回测结果，包含交易记录和收益曲线数据
        """
        print(f"\n{'='*60}")
        print(f"开始历史回测 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"股票代码: {stock_code}")
        print(f"回测月数: {months}")
        print(f"{'='*60}")
        
        try:
            # 计算回测日期范围
            if start_date and end_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=months * 30)
            
            print(f"回测时间范围: {start_dt.strftime('%Y-%m-%d')} 到 {end_dt.strftime('%Y-%m-%d')}")
            
            # 获取历史数据
            print("正在获取历史股票数据...")
            stock_data = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_dt.strftime('%Y%m%d'),
                end_date=end_dt.strftime('%Y%m%d')
            )
            
            if stock_data is None or stock_data.empty:
                return {'error': '无法获取股票历史数据'}
            
            print(f"获取到股票数据: {len(stock_data)}条记录")
            
            # 获取历史金价数据
            print("正在获取历史金价数据...")
            gold_data = ak.futures_foreign_hist(symbol='XAU')
            
            if gold_data is None or gold_data.empty:
                return {'error': '无法获取金价历史数据'}
            
            print(f"获取到金价数据: {len(gold_data)}条记录")
            
            # 初始化回测状态
            backtest_state = {
                'total_cost': 0,
                'total_shares': 0,
                'total_investment': 0,
                'history_max_profit': 0,
                'last_total_profit': 0,
                'current_position': None,
                'trade_history': [],
                'last_trade_date': None
            }
            
            # 收益曲线数据
            profit_curve = []
            daily_returns = []
            
            # 按日期遍历进行回测
            for i, (date, row) in enumerate(stock_data.iterrows()):
                current_date = date.date()
                current_stock_price = float(row['收盘'])
                
                # 获取对应日期的金价数据
                gold_price_data = self._get_gold_price_for_date(gold_data, current_date)
                if gold_price_data is None:
                    continue
                
                current_gold_price = gold_price_data['current']
                previous_gold_price = gold_price_data['previous']
                
                if previous_gold_price is None or previous_gold_price == 0:
                    continue
                
                # 计算金价涨跌幅
                gold_change_rate = (current_gold_price - previous_gold_price) / previous_gold_price
                
                # 执行交易逻辑
                trade_result = self._execute_backtest_trade(
                    backtest_state, current_date, current_stock_price, 
                    gold_change_rate, current_gold_price
                )
                
                # 计算当前总资产和收益
                current_market_value = backtest_state['total_shares'] * current_stock_price
                current_total_profit = current_market_value - backtest_state['total_cost']
                current_profit_rate = current_total_profit / backtest_state['total_cost'] if backtest_state['total_cost'] > 0 else 0
                
                # 更新历史最大盈利
                if current_total_profit > backtest_state['history_max_profit']:
                    backtest_state['history_max_profit'] = current_total_profit
                
                # 记录收益曲线数据
                profit_curve.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'total_cost': backtest_state['total_cost'],
                    'market_value': current_market_value,
                    'total_profit': current_total_profit,
                    'profit_rate': current_profit_rate,
                    'stock_price': current_stock_price,
                    'gold_price': current_gold_price,
                    'gold_change_rate': gold_change_rate,
                    'has_position': backtest_state['total_shares'] > 0,
                    'trade_action': trade_result.get('action', 'HOLD')
                })
                
                # 记录日收益率
                if i > 0:
                    daily_return = (current_stock_price - stock_data.iloc[i-1]['收盘']) / stock_data.iloc[i-1]['收盘']
                    daily_returns.append(daily_return)
            
            # 计算回测统计
            total_trades = len(backtest_state['trade_history'])
            total_net_profit = sum([trade.get('total_profit', 0) for trade in backtest_state['trade_history']])
            win_trades = len([trade for trade in backtest_state['trade_history'] if trade.get('total_profit', 0) > 0])
            win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 计算年化收益率
            days = (end_dt - start_dt).days
            annual_return = (total_net_profit / backtest_state['total_cost'] * 365 / days * 100) if backtest_state['total_cost'] > 0 and days > 0 else 0
            
            # 计算最大回撤
            max_drawdown = self._calculate_max_drawdown(profit_curve)
            
            print(f"\n回测完成:")
            print(f"  总交易次数: {total_trades}")
            print(f"  总盈利: {total_net_profit:.2f}元")
            print(f"  胜率: {win_rate:.2f}%")
            print(f"  年化收益率: {annual_return:.2f}%")
            print(f"  最大回撤: {max_drawdown:.2f}%")
            
            return {
                'success': True,
                'backtest_period': {
                    'start_date': start_dt.strftime('%Y-%m-%d'),
                    'end_date': end_dt.strftime('%Y-%m-%d'),
                    'days': days
                },
                'statistics': {
                    'total_trades': total_trades,
                    'total_net_profit': total_net_profit,
                    'win_trades': win_trades,
                    'win_rate': win_rate,
                    'annual_return': annual_return,
                    'max_drawdown': max_drawdown,
                    'final_market_value': profit_curve[-1]['market_value'] if profit_curve else 0,
                    'final_profit_rate': profit_curve[-1]['profit_rate'] if profit_curve else 0
                },
                'profit_curve': profit_curve,
                'trade_history': backtest_state['trade_history'],
                'daily_returns': daily_returns
            }
            
        except Exception as e:
            error_msg = f'回测失败: {str(e)}'
            print(f"[错误] {error_msg}")
            import traceback
            traceback.print_exc()
            return {'error': error_msg}
    
    def _get_gold_price_for_date(self, gold_data, target_date):
        """获取指定日期的金价数据"""
        try:
            # 找到最接近目标日期的金价数据
            gold_data['date'] = pd.to_datetime(gold_data.index).date
            
            # 查找目标日期或之前最近的数据
            available_dates = gold_data[gold_data['date'] <= target_date]
            if available_dates.empty:
                return None
            
            # 获取当前日期和前一天的数据
            current_data = available_dates.iloc[-1]
            previous_data = available_dates.iloc[-2] if len(available_dates) > 1 else None
            
            # 尝试不同的价格列名
            price_columns = ['收盘', 'close', 'Close', 'CLOSE', '价格', 'price']
            current_price = None
            previous_price = None
            
            for col in price_columns:
                if col in current_data:
                    current_price = float(current_data[col])
                    if previous_data is not None and col in previous_data:
                        previous_price = float(previous_data[col])
                    break
            
            if current_price is None:
                # 如果列名匹配失败，使用第二列（通常是价格）
                current_price = float(current_data.iloc[1])
                if previous_data is not None:
                    previous_price = float(previous_data.iloc[1])
            
            return {
                'current': current_price,
                'previous': previous_price
            }
            
        except Exception as e:
            print(f"获取金价数据失败: {e}")
            return None
    
    def _execute_backtest_trade(self, backtest_state, current_date, current_stock_price, gold_change_rate, current_gold_price):
        """执行回测交易逻辑"""
        trade_result = {'action': 'HOLD'}
        
        # 检查买入条件
        should_buy, buy_amount = self.should_buy_improved(gold_change_rate)
        
        # 检查卖出条件（如果有持仓）
        should_sell = False
        sell_reason = ""
        if backtest_state['total_shares'] > 0:
            should_sell, sell_reason = self._should_sell_backtest(backtest_state, current_stock_price)
        
        if should_buy:
            # 执行买入
            transaction_cost = self.calculate_transaction_cost(buy_amount)
            net_buy_amount = buy_amount - transaction_cost
            shares = net_buy_amount / current_stock_price
            
            # 更新回测状态
            backtest_state['total_cost'] += buy_amount
            backtest_state['total_shares'] += shares
            backtest_state['total_investment'] += buy_amount
            
            # 记录当前持仓信息
            backtest_state['current_position'] = {
                'has_position': True,
                'buy_price': current_stock_price,
                'shares': shares,
                'buy_amount': buy_amount,
                'net_buy_amount': net_buy_amount,
                'transaction_cost': transaction_cost,
                'buy_date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                'max_profit_rate': 0,
                'current_profit_rate': 0
            }
            
            backtest_state['last_trade_date'] = current_date
            trade_result['action'] = 'BUY'
            trade_result['shares'] = shares
            trade_result['amount'] = buy_amount
            
        elif should_sell and backtest_state['total_shares'] > 0:
            # 执行卖出
            sell_amount = backtest_state['total_shares'] * current_stock_price
            transaction_cost = self.calculate_transaction_cost(sell_amount)
            net_sell_amount = sell_amount - transaction_cost
            
            # 计算总盈利
            total_profit = net_sell_amount - backtest_state['total_cost']
            total_profit_rate = total_profit / backtest_state['total_cost'] if backtest_state['total_cost'] > 0 else 0
            
            # 记录交易历史
            backtest_state['trade_history'].append({
                'sell_price': current_stock_price,
                'shares': backtest_state['total_shares'],
                'sell_amount': sell_amount,
                'net_sell_amount': net_sell_amount,
                'total_cost': backtest_state['total_cost'],
                'total_profit': total_profit,
                'total_profit_rate': total_profit_rate,
                'sell_date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                'sell_reason': sell_reason,
                'transaction_cost': transaction_cost
            })
            
            # 更新历史最大盈利
            if total_profit > backtest_state['history_max_profit']:
                backtest_state['history_max_profit'] = total_profit
            
            backtest_state['last_trade_date'] = current_date
            trade_result['action'] = 'SELL'
            trade_result['total_profit'] = total_profit
            trade_result['total_profit_rate'] = total_profit_rate
            
            # 清空持仓
            backtest_state['total_shares'] = 0
            backtest_state['total_cost'] = 0
            backtest_state['current_position'] = None
        
        return trade_result
    
    def _should_sell_backtest(self, backtest_state, current_price):
        """回测中的卖出判断逻辑"""
        # 计算当前持仓市值
        current_market_value = backtest_state['total_shares'] * current_price
        
        # 计算当前总盈利
        current_total_profit = current_market_value - backtest_state['total_cost']
        
        # 计算当前盈利率
        current_profit_rate = current_total_profit / backtest_state['total_cost'] if backtest_state['total_cost'] > 0 else 0
        
        # 1. 止损检查
        if current_profit_rate <= -self.stop_loss_rate:
            return True, f"止损：当前亏损{abs(current_profit_rate)*100:.2f}%"
        
        # 2. 盈利回调检查
        if backtest_state['history_max_profit'] > 0:
            profit_decrease = backtest_state['history_max_profit'] - current_total_profit
            profit_decrease_rate = profit_decrease / backtest_state['history_max_profit'] if backtest_state['history_max_profit'] > 0 else 0
            
            if profit_decrease_rate >= self.profit_callback_rate:
                return True, f"盈利回调：从{backtest_state['history_max_profit']:.2f}元回调到{current_total_profit:.2f}元，缩小{profit_decrease_rate*100:.2f}%"
        
        # 3. 长期持有检查
        if backtest_state['current_position'] and 'buy_date' in backtest_state['current_position']:
            try:
                buy_date = datetime.strptime(backtest_state['current_position']['buy_date'], '%Y-%m-%d %H:%M:%S')
                days_held = (datetime.now() - buy_date).days
                if days_held > self.max_hold_days:
                    return True, f"长期持有：已持有{days_held}天"
            except Exception as e:
                print(f"计算持仓天数时出错: {e}")
        
        # 4. 大幅盈利检查
        if current_profit_rate > self.max_profit_rate:
            return True, f"大幅盈利：当前盈利{current_profit_rate*100:.2f}%"
        
        return False, "继续持有"
    
    def _calculate_max_drawdown(self, profit_curve):
        """计算最大回撤"""
        if not profit_curve:
            return 0
        
        max_drawdown = 0
        peak_value = profit_curve[0]['market_value']
        
        for point in profit_curve:
            market_value = point['market_value']
            if market_value > peak_value:
                peak_value = market_value
            
            drawdown = (peak_value - market_value) / peak_value if peak_value > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown * 100  # 转换为百分比

