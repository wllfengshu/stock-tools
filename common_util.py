#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
通用工具: 认证校验
"""

import sys
import os

import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import akshare as ak
import pandas as pd
from typing import Tuple, Optional

sys.path.insert(0, os.path.abspath('./database'))
from database.strategy_dao import StrategyDAO
strategy_dao = StrategyDAO()

class CommonUtil:
    """工具类"""

    def __init__(self):
        print("✅ 通用工具初始化完成")

    def auth_is_valid(self, auth: str) -> Tuple[bool, str]:
        """校验 auth 是否有效"""
        if not auth or not isinstance(auth, str) or not auth.strip():
            return False, 'auth参数缺失或无效'

        token = auth.strip()

        # 1) 从数据库校验
        try:
            record = strategy_dao.load_user_info_by_auth(token)
        except Exception as e:
            return False, f'数据库访问失败: {e}'

        if record is None:
            return False, 'auth不存在或未注册'

        # 2) 业务字段校验（若字段存在则校验）
        # 删除标记
        deleted = getattr(record, 'deleted', None)
        if isinstance(deleted, str) and deleted.upper() in ('T', 'Y', 'TRUE', 'ON', '1'):
            return False, 'auth已被禁用'

        # 开关标记（如有）
        switched = getattr(record, 'switched', None)
        if isinstance(switched, str) and switched.upper() in ('OFF', 'DISABLED'):
            return False, 'auth已关闭'

        # 有效期校验（优先使用 expire_time/end_time，如有）
        now = datetime.now()
        expire_time = getattr(record, 'expire_time', None)
        end_time = getattr(record, 'end_time', None)

        try:
            if expire_time and isinstance(expire_time, datetime) and expire_time < now:
                return False, 'auth已过期'
        except Exception:
            pass

        try:
            if end_time and isinstance(end_time, datetime) and end_time < now:
                return False, 'auth已过期'
        except Exception:
            pass

        # 若存在开始时间，且未来生效
        start_time = getattr(record, 'start_time', None)
        try:
            if start_time and isinstance(start_time, datetime) and start_time > now:
                return False, 'auth尚未生效'
        except Exception:
            pass

        return True, 'auth校验通过'

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
            
            # 统一索引为日期，同时保留原'日期'列用于展示
            if '日期' in stock_data.columns:
                stock_data['日期'] = pd.to_datetime(stock_data['日期'])
                stock_data = stock_data.set_index('日期', drop=False)
            elif not isinstance(stock_data.index, pd.DatetimeIndex):
                print(f"⚠️ 股票{stock_code}索引不是DatetimeIndex，尝试转换...")
                stock_data.index = pd.to_datetime(stock_data.index, errors='coerce')
            
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



