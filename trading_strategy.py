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

# 添加akshare源码目录到Python路径
sys.path.insert(0, os.path.abspath('./akshare'))
import akshare as ak

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
    
    def __init__(self, base_investment=1000, stop_loss_rate=0.10, 
                 profit_callback_rate=0.01, max_profit_rate=0.5,
                 min_gold_change=0.002, min_buy_amount=100,
                 transaction_cost_rate=0.001, max_hold_days=30):
        """
        初始化交易策略
        
        Args:
            base_investment: 每次投资的基准金额（每次买入金额 = 基础金额 × 金价涨幅）
            stop_loss_rate: 止损率（当亏损到总成本的（1-止损率）时卖出）
            profit_callback_rate: 盈利回调率（从最大盈利率回调到（最大盈利率-盈利回调率）时卖出）
            max_profit_rate: 最大盈利率（当盈利超过最大盈利率时卖出）
            min_gold_change: 最小金价涨幅阈值（0.2%，只有金价涨幅超过最小金价涨幅阈值时才买入）
            min_buy_amount: 最小买入金额（每次买入金额不能小于最小买入金额）
            transaction_cost_rate: 交易成本率（0.1%，每次买入和卖出时需要扣除交易成本）
            max_hold_days: 最大持仓天数（超过最大持仓天数时卖出）
        """
        self.base_investment = base_investment
        self.stop_loss_rate = stop_loss_rate
        self.profit_callback_rate = profit_callback_rate
        self.max_profit_rate = max_profit_rate
        self.min_gold_change = min_gold_change
        self.min_buy_amount = min_buy_amount
        self.transaction_cost_rate = transaction_cost_rate
        self.max_hold_days = max_hold_days
        
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
        
        # 持久化文件路径
        self.persistence_file = 'strategy_state.json'
        
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
    
    def load_state(self):
        """从文件加载策略状态"""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 恢复状态
                self.total_cost = data.get('total_cost', 0)
                self.total_shares = data.get('total_shares', 0)
                self.total_investment = data.get('total_investment', 0)
                self.history_max_profit = data.get('history_max_profit', 0)
                self.last_total_profit = data.get('last_total_profit', 0)
                
                # 恢复交易历史
                self.trade_history = data.get('trade_history', [])
                
                # 恢复最后交易日期
                if data.get('last_trade_date'):
                    self.last_trade_date = datetime.strptime(data['last_trade_date'], '%Y-%m-%d').date()
                
                print(f"[持久化] 成功加载历史状态:")
                print(f"  总成本: {self.total_cost:.2f}元")
                print(f"  总持股: {self.total_shares:.2f}股")
                print(f"  历史最大盈利: {self.history_max_profit:.2f}元")
                print(f"  交易历史: {len(self.trade_history)}条记录")
            else:
                print(f"[持久化] 未找到历史状态文件，使用默认值")
        except Exception as e:
            print(f"[持久化] 加载状态失败: {e}")
            print(f"[持久化] 使用默认值继续运行")
    
    def save_state(self):
        """保存策略状态到文件"""
        try:
            data = {
                'total_cost': self.total_cost,
                'total_shares': self.total_shares,
                'total_investment': self.total_investment,
                'history_max_profit': self.history_max_profit,
                'last_total_profit': self.last_total_profit,
                'trade_history': self.trade_history,
                'last_trade_date': self.last_trade_date.strftime('%Y-%m-%d') if self.last_trade_date else None,
                'save_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[持久化] 状态已保存到 {self.persistence_file}")
        except Exception as e:
            print(f"[持久化] 保存状态失败: {e}")
    
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
        if hasattr(self.current_position, 'buy_date'):
            days_held = (datetime.now() - self.current_position['buy_date']).days
            if days_held > self.max_hold_days:
                return True, f"长期持有：已持有{days_held}天"
        
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
                    'buy_price': current_stock_price,
                    'shares': shares,
                    'buy_amount': buy_amount,
                    'net_buy_amount': net_buy_amount,
                    'transaction_cost': transaction_cost,
                    'buy_date': datetime.now(),
                    'max_profit_rate': 0
                }
                
                self.last_trade_date = datetime.now().date()
                trade_result['action'] = 'BUY'
                trade_result['shares'] = shares
                trade_result['transaction_cost'] = transaction_cost
                trade_result['total_shares'] = self.total_shares
                trade_result['total_cost'] = self.total_cost
                
                print(f"[成功] 执行买入: {shares:.2f}股，金额: {buy_amount:.2f}元，手续费: {transaction_cost:.2f}元")
                print(f"更新后状态: 总成本={self.total_cost:.2f}元，总持股={self.total_shares:.2f}股")
                
                # 保存状态
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
                    'sell_date': datetime.now(),
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
                
                # 保存状态
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
    
    def get_strategy_status_improved(self):
        """获取改进的策略状态（基于全局状态）"""
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
    
    def get_strategy_summary_improved(self):
        """获取改进的策略摘要"""
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

def main():
    """主函数 - 测试改进版策略"""
    print("改进版黄金板块量化交易策略测试")
    print("=" * 60)
    
    # 创建改进版策略实例
    strategy = TradingStrategy(
        
    )
    
    # 执行策略
    result = strategy.execute_strategy_improved('002155')
    
    if 'error' in result:
        print(f"[错误] 策略执行失败: {result['error']}")
    else:
        print(f"[成功] 策略执行成功")
        print(f"金价: {result['gold_price']}美元")
        print(f"金价涨跌: {result['gold_change_rate']*100:.2f}%")
        print(f"股票价格: {result['stock_price']}元")
        
        if result.get('action') == 'BUY':
            print(f"买入: {result['shares']:.2f}股，金额: {result['buy_amount']:.2f}元")
            print(f"手续费: {result.get('transaction_cost', 0):.2f}元")
        elif result.get('action') == 'SELL':
            print(f"卖出: 净盈利{result['profit']:.2f}元 ({result['profit_rate']*100:.2f}%)")
            print(f"卖出原因: {result.get('sell_reason', '未知')}")
            print(f"手续费: {result.get('transaction_cost', 0):.2f}元")
        else:
            print("无交易操作")
    
    # 获取策略状态
    status = strategy.get_strategy_status_improved()
    if status['has_position']:
        print(f"\n[状态] 当前持仓状态:")
        print(f"当前价格: {status['current_price']}元")
        print(f"总持股: {status['total_shares']:.2f}股")
        print(f"总成本: {status['total_cost']:.2f}元")
        print(f"持仓市值: {status['current_market_value']:.2f}元")
        print(f"当前总盈利: {status['current_total_profit']:.2f}元")
        print(f"当前盈利率: {status['current_profit_rate']*100:.2f}%")
        print(f"历史最大盈利: {status['history_max_profit']:.2f}元")
    else:
        print(f"\n[状态] 当前无持仓")
        print(f"总成本: {status['total_cost']:.2f}元")
        print(f"总持股: {status['total_shares']:.2f}股")
        print(f"历史最大盈利: {status['history_max_profit']:.2f}元")
    
    # 获取策略摘要
    summary = strategy.get_strategy_summary_improved()
    print(f"\n[统计] 策略摘要:")
    print(f"总交易次数: {summary['total_trades']}")
    print(f"总净盈利: {summary['total_net_profit']:.2f}元")
    print(f"总交易成本: {summary['total_transaction_cost']:.2f}元")
    print(f"盈利交易: {summary['win_trades']}次")
    print(f"胜率: {summary['win_rate']:.2f}%")
    print(f"当前持仓: {'是' if summary['current_position'] else '否'}")
    print(f"总持股: {summary['total_shares']:.2f}股")
    print(f"总成本: {summary['total_cost']:.2f}元")
    print(f"历史最大盈利: {summary['history_max_profit']:.2f}元")
    print(f"最后交易日期: {summary['last_trade_date']}")

if __name__ == "__main__":
    main()
