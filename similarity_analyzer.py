#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
K线图走势相似度分析器
基于多维度综合分析的股票与金价走势相似度算法

算法说明：
1. 价格变化相关性分析 - 计算日涨跌幅的皮尔逊相关系数
2. 趋势方向一致性分析 - 比较移动平均线的斜率方向
3. 波动性相似度分析 - 比较价格波动幅度和频率
4. 价格模式匹配分析 - 使用DTW算法计算价格序列相似度
5. 成交量与价格关系分析 - 分析成交量与价格变化的关系相似度

最终输出：0-100的相似度分数，以及详细的可视化数据
"""

import sys
import os
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加akshare源码目录到Python路径
sys.path.insert(0, os.path.abspath('./akshare'))
import akshare as ak

# 使用tslearn库进行DTW计算 - 专业的时间序列分析库
from tslearn.metrics import dtw

class SimilarityAnalyzer:
    """
    K线图走势相似度分析器
    
    基于多维度综合分析，计算两条K线图的走势相似度
    适用于股票价格与金价走势的对比分析
    """
    
    def __init__(self):
        """
        初始化相似度分析器
        
        权重配置：
        - correlation: 价格变化相关性 (30%)
        - trend: 趋势方向一致性 (25%) 
        - volatility: 波动性相似度 (20%)
        - pattern: 价格模式匹配 (15%)
        - volume: 成交量关系 (10%)
        """
        self.weights = {
            'correlation': 0.30,      # 价格变化相关性
            'trend': 0.25,            # 趋势方向一致性  
            'volatility': 0.20,       # 波动性相似度
            'pattern': 0.15,          # 价格模式匹配
            'volume': 0.10           # 成交量关系
        }
        
        # 数据存储
        self.stock_data = None
        self.gold_data = None
        
        print("K线图走势相似度分析器初始化完成")
        print(f"权重配置: {self.weights}")
    
    def prepare_data(self, months=6, stock_code='002155'):
        """
        准备K线图分析数据
        
        功能：
        1. 获取股票历史数据
        2. 获取金价历史数据
        3. 数据清洗和格式化
        4. 数据类型转换
        
        Args:
            months (int): 数据月数
            stock_code (str): 股票代码
            
        Returns:
            bool: 数据准备是否成功
        """
        print(f"🔄 正在准备K线图分析数据...")
        
        try:
            # 获取股票数据
            self.stock_data = self.get_stock_data(months, stock_code)
            
            if self.stock_data.empty:
                print(f"❌ 股票{stock_code}数据为空")
                return False
                
        except Exception as e:
            print(f"❌ 准备股票{stock_code}数据失败: {e}")
            return False
        
        # 股票数据预处理
        print("🔧 正在处理股票数据...")
        self.stock_data['日期'] = pd.to_datetime(self.stock_data['日期'])
        self.stock_data = self.stock_data.set_index('日期')
        self.stock_data = self.stock_data.sort_index()
        
        # 确保OHLC数据为数值类型
        numeric_columns = ['开盘', '最高', '最低', '收盘', '成交量']
        for col in numeric_columns:
            if col in self.stock_data.columns:
                self.stock_data[col] = pd.to_numeric(self.stock_data[col], errors='coerce')
        
        # 删除包含NaN的行
        self.stock_data = self.stock_data.dropna()
        
        print(f"✅ 股票数据准备完成，形状: {self.stock_data.shape}")
        print(f"📊 股票价格范围: {self.stock_data['收盘'].min():.2f} - {self.stock_data['收盘'].max():.2f}")
        
        # 获取伦敦金数据
        print(f"🥇 正在准备伦敦金数据...")
        self.gold_data = self.get_gold_data(months)
        
        if not self.gold_data.empty:
            # 伦敦金数据预处理
            print("🔧 正在处理伦敦金数据...")
            
            # 确保OHLC数据为数值类型
            numeric_columns = ['开盘', '最高', '最低', '收盘', '成交量']
            for col in numeric_columns:
                if col in self.gold_data.columns:
                    self.gold_data[col] = pd.to_numeric(self.gold_data[col], errors='coerce')
            
            # 删除包含NaN的行
            self.gold_data = self.gold_data.dropna()
            
            print(f"✅ 伦敦金数据准备完成，形状: {self.gold_data.shape}")
            print(f"📊 伦敦金价格范围: ${self.gold_data['收盘'].min():.2f} - ${self.gold_data['收盘'].max():.2f}")
        else:
            print("⚠️ 伦敦金数据为空，将使用空数据")
        
        return True
    
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
            # 使用akshare获取伦敦金数据 - 使用XAU黄金期货数据
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
            
            gold_data = gold_data.sort_index()
            
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
            
            # 如果列名是英文，映射为中文
            for eng_col, chn_col in column_mapping.items():
                if eng_col in gold_data.columns and chn_col not in gold_data.columns:
                    gold_data[chn_col] = gold_data[eng_col]
                    print(f"✅ 映射列 {eng_col} -> {chn_col}")
            
            # 检查必要的列是否存在
            required_columns = ['开盘', '最高', '最低', '收盘', '成交量']
            missing_columns = [col for col in required_columns if col not in gold_data.columns]
            
            if missing_columns:
                print(f"⚠️ 伦敦金数据缺少列: {missing_columns}")
                print(f"🔍 可用列: {gold_data.columns.tolist()}")
                
                # 如果缺少成交量，生成模拟数据
                if '成交量' not in gold_data.columns:
                    import numpy as np
                    gold_data['成交量'] = np.random.randint(1000, 10000, len(gold_data))
                    print(f"✅ 已生成模拟成交量数据")
                
                # 如果缺少其他OHLC列，使用收盘价生成
                for col in ['开盘', '最高', '最低']:
                    if col not in gold_data.columns and '收盘' in gold_data.columns:
                        if col == '开盘':
                            gold_data[col] = gold_data['收盘'] * (0.98 + 0.04 * np.random.random(len(gold_data)))
                        elif col == '最高':
                            gold_data[col] = gold_data['收盘'] * (1 + 0.02 * np.random.random(len(gold_data)))
                        elif col == '最低':
                            gold_data[col] = gold_data['收盘'] * (1 - 0.02 * np.random.random(len(gold_data)))
                        print(f"✅ 已生成模拟{col}数据")
            
            print(f"✅ 伦敦金数据处理完成")
            print(f"📊 最终列名: {gold_data.columns.tolist()}")
            print(f"📊 数据示例:")
            print(gold_data[['开盘', '最高', '最低', '收盘', '成交量']].head(3))
            
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
    
    def preprocess_data(self, stock_data, gold_data):
        """
        数据预处理和标准化
        
        Args:
            stock_data: 股票数据 (DataFrame)
            gold_data: 金价数据 (DataFrame)
            
        Returns:
            tuple: (处理后的股票数据, 处理后的金价数据, 是否有成交量数据)
        """
        print("开始数据预处理...")
        
        # 检查成交量数据可用性
        has_stock_volume = '成交量' in stock_data.columns and not stock_data['成交量'].isna().all()
        has_gold_volume = '成交量' in gold_data.columns and not gold_data['成交量'].isna().all()
        
        print(f"成交量数据状态: 股票={has_stock_volume}, 金价={has_gold_volume}")
        
        # 如果没有成交量数据，不添加默认值
        if not has_stock_volume:
            print("股票数据无成交量，将跳过成交量相关计算")
        if not has_gold_volume:
            print("金价数据无成交量，将跳过成交量相关计算")
        
        # 计算日涨跌幅
        stock_data['涨跌幅'] = stock_data['收盘'].pct_change()
        gold_data['涨跌幅'] = gold_data['收盘'].pct_change()
        
        # 计算移动平均线
        for window in [5, 10, 20]:
            stock_data[f'MA{window}'] = stock_data['收盘'].rolling(window=window).mean()
            gold_data[f'MA{window}'] = gold_data['收盘'].rolling(window=window).mean()
        
        # 计算波动率
        stock_data['波动率'] = stock_data['涨跌幅'].rolling(window=5).std()
        gold_data['波动率'] = gold_data['涨跌幅'].rolling(window=5).std()
        
        # 只删除必要的NaN值，保留更多数据
        # 删除前几行的NaN（由于移动平均线计算）
        stock_data = stock_data.dropna(subset=['MA20'])  # 只删除MA20为NaN的行
        gold_data = gold_data.dropna(subset=['MA20'])
        
        # 确保索引是日期类型
        if not isinstance(stock_data.index, pd.DatetimeIndex):
            try:
                stock_data.index = pd.to_datetime(stock_data.index)
            except:
                pass
        
        if not isinstance(gold_data.index, pd.DatetimeIndex):
            try:
                gold_data.index = pd.to_datetime(gold_data.index)
            except:
                pass
        
        print(f"数据预处理完成")
        print(f"   股票数据: {len(stock_data)} 条记录")
        print(f"   金价数据: {len(gold_data)} 条记录")
        print(f"   股票数据索引类型: {type(stock_data.index)}")
        print(f"   金价数据索引类型: {type(gold_data.index)}")
        if len(stock_data) > 0:
            print(f"   股票数据索引示例: {stock_data.index[0]}")
        if len(gold_data) > 0:
            print(f"   金价数据索引示例: {gold_data.index[0]}")
        
        return stock_data, gold_data, (has_stock_volume, has_gold_volume)
    
    def calculate_correlation_similarity(self, stock_data, gold_data):
        """
        计算价格变化相关性相似度
        
        算法说明：
        1. 计算两条K线的日涨跌幅
        2. 计算皮尔逊相关系数
        3. 将相关系数(-1到1)转换为相似度分数(0到100)
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            
        Returns:
            float: 相关性相似度分数 (0-100)
        """
        print("计算价格变化相关性...")
        
        # 获取涨跌幅数据
        stock_changes = stock_data['涨跌幅'].dropna()
        gold_changes = gold_data['涨跌幅'].dropna()
        
        # 确保数据长度一致
        min_length = min(len(stock_changes), len(gold_changes))
        if min_length < 2:
            return 0.0
            
        stock_changes = stock_changes.iloc[-min_length:]
        gold_changes = gold_changes.iloc[-min_length:]
        
        # 计算皮尔逊相关系数
        try:
            correlation, p_value = stats.pearsonr(stock_changes, gold_changes)
            
            # 将相关系数转换为相似度分数
            # 相关系数范围: -1 到 1
            # 相似度分数范围: 0 到 100
            similarity_score = max(0, (correlation + 1) * 50)
            
            print(f"   相关系数: {correlation:.4f}")
            print(f"   相关性相似度: {similarity_score:.2f}")
            
            return similarity_score
            
        except Exception as e:
            print(f"   相关性计算失败: {e}")
            return 0.0
    
    def calculate_trend_similarity(self, stock_data, gold_data):
        """
        计算趋势方向一致性相似度
        
        算法说明：
        1. 计算移动平均线的斜率
        2. 比较趋势方向的一致性
        3. 计算趋势强度的相似度
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            
        Returns:
            float: 趋势相似度分数 (0-100)
        """
        print("计算趋势方向一致性...")
        
        try:
            # 计算MA5和MA20的斜率
            stock_ma5_slope = self._calculate_slope(stock_data['MA5'].dropna())
            stock_ma20_slope = self._calculate_slope(stock_data['MA20'].dropna())
            gold_ma5_slope = self._calculate_slope(gold_data['MA5'].dropna())
            gold_ma20_slope = self._calculate_slope(gold_data['MA20'].dropna())
            
            # 计算趋势方向一致性
            ma5_direction_similarity = self._direction_similarity(stock_ma5_slope, gold_ma5_slope)
            ma20_direction_similarity = self._direction_similarity(stock_ma20_slope, gold_ma20_slope)
            
            # 计算趋势强度相似度
            ma5_strength_similarity = self._strength_similarity(stock_ma5_slope, gold_ma5_slope)
            ma20_strength_similarity = self._strength_similarity(stock_ma20_slope, gold_ma20_slope)
            
            # 综合计算趋势相似度
            trend_similarity = (ma5_direction_similarity * 0.6 + ma20_direction_similarity * 0.4) * 0.7 + \
                             (ma5_strength_similarity * 0.6 + ma20_strength_similarity * 0.4) * 0.3
            
            print(f"   MA5方向相似度: {ma5_direction_similarity:.2f}")
            print(f"   MA20方向相似度: {ma20_direction_similarity:.2f}")
            print(f"   趋势相似度: {trend_similarity:.2f}")
            
            return trend_similarity
            
        except Exception as e:
            print(f"   趋势计算失败: {e}")
            return 0.0
    
    def calculate_volatility_similarity(self, stock_data, gold_data):
        """
        计算波动性相似度
        
        算法说明：
        1. 计算价格波动幅度和频率
        2. 比较变异系数
        3. 分析波动模式的相似性
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            
        Returns:
            float: 波动性相似度分数 (0-100)
        """
        print("计算波动性相似度...")
        
        try:
            # 计算变异系数 (标准差/均值)
            stock_cv = stock_data['涨跌幅'].std() / abs(stock_data['涨跌幅'].mean())
            gold_cv = gold_data['涨跌幅'].std() / abs(gold_data['涨跌幅'].mean())
            
            # 计算变异系数相似度
            cv_similarity = 100 - abs(stock_cv - gold_cv) / max(stock_cv, gold_cv) * 100
            cv_similarity = max(0, cv_similarity)
            
            # 计算波动率相似度
            stock_volatility = stock_data['波动率'].mean()
            gold_volatility = gold_data['波动率'].mean()
            
            volatility_similarity = 100 - abs(stock_volatility - gold_volatility) / max(stock_volatility, gold_volatility) * 100
            volatility_similarity = max(0, volatility_similarity)
            
            # 综合波动性相似度
            volatility_similarity = (cv_similarity * 0.6 + volatility_similarity * 0.4)
            
            print(f"   变异系数相似度: {cv_similarity:.2f}")
            print(f"   波动率相似度: {volatility_similarity:.2f}")
            print(f"   波动性相似度: {volatility_similarity:.2f}")
            
            return volatility_similarity
            
        except Exception as e:
            print(f"   波动性计算失败: {e}")
            return 0.0
    
    def calculate_pattern_similarity(self, stock_data, gold_data):
        """
        计算价格模式匹配相似度
        
        算法说明：
        1. 标准化价格数据
        2. 使用DTW(动态时间规整)算法
        3. 计算价格序列的相似度
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            
        Returns:
            float: 模式相似度分数 (0-100)
        """
        print("计算价格模式匹配...")
        
        try:
            # 标准化价格数据
            stock_prices = stock_data['收盘'].values
            gold_prices = gold_data['收盘'].values
            
            # 标准化到0-1范围
            stock_normalized = (stock_prices - stock_prices.min()) / (stock_prices.max() - stock_prices.min())
            gold_normalized = (gold_prices - gold_prices.min()) / (gold_prices.max() - gold_prices.min())
            
            # 确保长度一致
            min_length = min(len(stock_normalized), len(gold_normalized))
            stock_normalized = stock_normalized[:min_length]
            gold_normalized = gold_normalized[:min_length]
            
            # 计算DTW距离 - 使用tslearn专业库
            dtw_distance = dtw(stock_normalized, gold_normalized)
            
            # 将DTW距离转换为相似度分数
            # DTW距离越小，相似度越高
            max_distance = np.sqrt(2 * min_length)  # 理论最大距离
            pattern_similarity = max(0, 100 - (dtw_distance / max_distance) * 100)
            
            print(f"   DTW距离: {dtw_distance:.4f}")
            print(f"   模式相似度: {pattern_similarity:.2f}")
            
            return pattern_similarity
            
        except Exception as e:
            print(f"   模式计算失败: {e}")
            return 0.0
    
    def calculate_volume_similarity(self, stock_data, gold_data, has_volume_data):
        """
        计算成交量与价格关系相似度
        
        算法说明：
        1. 分析成交量与价格变化的关系
        2. 计算成交量与涨跌幅的相关性
        3. 比较成交量模式
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            has_volume_data: (has_stock_volume, has_gold_volume) 成交量数据可用性
            
        Returns:
            float: 成交量相似度分数 (0-100)
        """
        has_stock_volume, has_gold_volume = has_volume_data
        
        # 如果任一数据源没有成交量，返回中性分数
        if not has_stock_volume or not has_gold_volume:
            print("成交量数据不完整，跳过成交量相似度计算")
            return 50.0  # 返回中性分数，不影响总体计算
        
        print("计算成交量关系相似度...")
        
        try:
            # 计算成交量与价格变化的相关性
            stock_volume_correlation = stock_data['成交量'].corr(stock_data['涨跌幅'].abs())
            gold_volume_correlation = gold_data['成交量'].corr(gold_data['涨跌幅'].abs())
            
            # 计算相关性相似度
            correlation_similarity = 100 - abs(stock_volume_correlation - gold_volume_correlation) * 100
            correlation_similarity = max(0, correlation_similarity)
            
            # 计算成交量变异系数相似度
            stock_volume_cv = stock_data['成交量'].std() / stock_data['成交量'].mean()
            gold_volume_cv = gold_data['成交量'].std() / gold_data['成交量'].mean()
            
            volume_cv_similarity = 100 - abs(stock_volume_cv - gold_volume_cv) / max(stock_volume_cv, gold_volume_cv) * 100
            volume_cv_similarity = max(0, volume_cv_similarity)
            
            # 综合成交量相似度
            volume_similarity = (correlation_similarity * 0.7 + volume_cv_similarity * 0.3)
            
            print(f"   成交量相关性相似度: {correlation_similarity:.2f}")
            print(f"   成交量变异相似度: {volume_cv_similarity:.2f}")
            print(f"   成交量相似度: {volume_similarity:.2f}")
            
            return volume_similarity
            
        except Exception as e:
            print(f"   成交量计算失败: {e}")
            return 50.0  # 返回中性分数
    
    def calculate_comprehensive_similarity(self, stock_data, gold_data):
        """
        计算综合相似度分数
        
        算法说明：
        1. 计算各个维度的相似度
        2. 根据权重加权计算
        3. 返回最终相似度分数和详细分析
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            
        Returns:
            dict: 包含综合相似度和详细分析的字典
        """
        print("开始综合相似度分析...")
        print("=" * 50)
        
        # 数据预处理
        stock_processed, gold_processed, has_volume_data = self.preprocess_data(stock_data, gold_data)
        
        # 计算各个维度的相似度
        similarity_scores = {}
        
        # 1. 价格变化相关性
        similarity_scores['correlation'] = self.calculate_correlation_similarity(stock_processed, gold_processed)
        
        # 2. 趋势方向一致性
        similarity_scores['trend'] = self.calculate_trend_similarity(stock_processed, gold_processed)
        
        # 3. 波动性相似度
        similarity_scores['volatility'] = self.calculate_volatility_similarity(stock_processed, gold_processed)
        
        # 4. 价格模式匹配
        similarity_scores['pattern'] = self.calculate_pattern_similarity(stock_processed, gold_processed)
        
        # 5. 成交量关系
        similarity_scores['volume'] = self.calculate_volume_similarity(stock_processed, gold_processed, has_volume_data)
        
        # 计算加权综合相似度
        comprehensive_score = 0
        for dimension, score in similarity_scores.items():
            comprehensive_score += score * self.weights[dimension]
        
        # 计算每日相似度时间序列
        daily_similarity_data = self.calculate_daily_similarity(stock_data, gold_data)
        
        # 生成分析报告
        analysis_report = {
            'comprehensive_score': round(comprehensive_score, 2),
            'dimension_scores': similarity_scores,
            'weights': self.weights,
            'stock_data': stock_processed,
            'gold_data': gold_processed,
            'daily_similarity': daily_similarity_data,
            'analysis_summary': self._generate_analysis_summary(similarity_scores, comprehensive_score)
        }
        
        print("=" * 50)
        print("综合相似度分析结果:")
        print(f"   综合相似度分数: {comprehensive_score:.2f}/100")
        print(f"   各维度分数: {similarity_scores}")
        print(f"   分析摘要: {analysis_report['analysis_summary']}")
        
        return analysis_report
    
    def calculate_daily_similarity(self, stock_data, gold_data, window_size=5):
        """
        计算每日相似度时间序列
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            window_size: 滑动窗口大小
            
        Returns:
            dict: 包含每日相似度数据的字典
        """
        print(f"计算每日相似度，窗口大小: {window_size}")
        
        # 数据预处理
        stock_processed, gold_processed, has_volume_data = self.preprocess_data(stock_data, gold_data)
        
        # 确保数据长度一致
        min_length = min(len(stock_processed), len(gold_processed))
        stock_processed = stock_processed.iloc[-min_length:]
        gold_processed = gold_processed.iloc[-min_length:]
        
        print(f"   处理后的数据长度: 股票={len(stock_processed)}, 金价={len(gold_processed)}")
        print(f"   股票数据索引类型: {type(stock_processed.index)}")
        print(f"   金价数据索引类型: {type(gold_processed.index)}")
        if len(stock_processed) > 0:
            print(f"   股票数据索引示例: {stock_processed.index[0]} -> {type(stock_processed.index[0])}")
        if len(gold_processed) > 0:
            print(f"   金价数据索引示例: {gold_processed.index[0]} -> {type(gold_processed.index[0])}")
        
        daily_similarities = []
        dates = []
        
        # 使用滑动窗口计算每日相似度
        for i in range(window_size, len(stock_processed)):
            # 获取当前窗口的数据
            stock_window = stock_processed.iloc[i-window_size:i+1]
            gold_window = gold_processed.iloc[i-window_size:i+1]
            
            # 计算当前窗口的相似度
            try:
                # 1. 价格变化相关性
                correlation_score = self.calculate_correlation_similarity(stock_window, gold_window)
                
                # 2. 趋势相似度
                trend_score = self.calculate_trend_similarity(stock_window, gold_window)
                
                # 3. 波动性相似度
                volatility_score = self.calculate_volatility_similarity(stock_window, gold_window)
                
                # 4. 模式相似度
                pattern_score = self.calculate_pattern_similarity(stock_window, gold_window)
                
                # 5. 成交量相似度
                volume_score = self.calculate_volume_similarity(stock_window, gold_window, has_volume_data)
                
                # 计算加权综合相似度
                daily_score = (
                    correlation_score * self.weights['correlation'] +
                    trend_score * self.weights['trend'] +
                    volatility_score * self.weights['volatility'] +
                    pattern_score * self.weights['pattern'] +
                    volume_score * self.weights['volume']
                )
                
                daily_similarities.append(round(daily_score, 2))
                # 确保日期格式正确
                if hasattr(stock_processed.index[i], 'strftime'):
                    dates.append(stock_processed.index[i].strftime('%Y-%m-%d'))
                else:
                    dates.append(str(stock_processed.index[i]))
                
            except Exception as e:
                print(f"   第{i}天相似度计算失败: {e}")
                daily_similarities.append(0.0)
                # 确保日期格式正确
                if hasattr(stock_processed.index[i], 'strftime'):
                    dates.append(stock_processed.index[i].strftime('%Y-%m-%d'))
                else:
                    dates.append(str(stock_processed.index[i]))
        
        print(f"每日相似度计算完成，共{len(daily_similarities)}个数据点")
        if len(daily_similarities) > 0:
            print(f"   平均相似度: {np.mean(daily_similarities):.2f}")
            print(f"   最高相似度: {np.max(daily_similarities):.2f}")
            print(f"   最低相似度: {np.min(daily_similarities):.2f}")
        else:
            print("   没有计算到相似度数据")
        
        if len(daily_similarities) > 0:
            return {
                'dates': dates,
                'similarities': daily_similarities,
                'mean_similarity': round(np.mean(daily_similarities), 2),
                'max_similarity': round(np.max(daily_similarities), 2),
                'min_similarity': round(np.min(daily_similarities), 2),
                'std_similarity': round(np.std(daily_similarities), 2)
            }
        else:
            return {
                'dates': [],
                'similarities': [],
                'mean_similarity': 0,
                'max_similarity': 0,
                'min_similarity': 0,
                'std_similarity': 0
            }
    
    def _calculate_slope(self, data):
        """计算数据序列的斜率"""
        if len(data) < 2:
            return 0
        x = np.arange(len(data))
        y = data.values
        slope, _ = np.polyfit(x, y, 1)
        return slope
    
    def _direction_similarity(self, slope1, slope2):
        """计算斜率方向相似度"""
        if slope1 * slope2 > 0:  # 同方向
            return 100
        elif slope1 == 0 and slope2 == 0:  # 都是水平
            return 100
        else:  # 反方向
            return 0
    
    def _strength_similarity(self, slope1, slope2):
        """计算斜率强度相似度"""
        if slope1 == 0 and slope2 == 0:
            return 100
        
        ratio = min(abs(slope1), abs(slope2)) / max(abs(slope1), abs(slope2))
        return ratio * 100
    
    
    def _generate_analysis_summary(self, scores, comprehensive_score):
        """生成分析摘要"""
        if comprehensive_score >= 80:
            return "高度相似 - 两条K线走势高度一致"
        elif comprehensive_score >= 60:
            return "中度相似 - 两条K线走势有一定相似性"
        elif comprehensive_score >= 40:
            return "低度相似 - 两条K线走势相似性较低"
        else:
            return "几乎不相似 - 两条K线走势差异很大"


# 测试函数
def test_similarity_analyzer():
    """测试相似度分析器"""
    print("🧪 开始测试相似度分析器...")
    
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    
    # 模拟股票数据
    stock_data = pd.DataFrame({
        '日期': dates,
        '开盘': np.random.uniform(10, 15, 30),
        '收盘': np.random.uniform(10, 15, 30),
        '最高': np.random.uniform(12, 18, 30),
        '最低': np.random.uniform(8, 12, 30),
        '成交量': np.random.uniform(1000000, 5000000, 30)
    })
    stock_data.set_index('日期', inplace=True)
    
    # 模拟金价数据
    gold_data = pd.DataFrame({
        '日期': dates,
        '开盘': np.random.uniform(2000, 2100, 30),
        '收盘': np.random.uniform(2000, 2100, 30),
        '最高': np.random.uniform(2050, 2150, 30),
        '最低': np.random.uniform(1950, 2050, 30),
        '成交量': np.random.uniform(1000, 5000, 30)
    })
    gold_data.set_index('日期', inplace=True)
    
    # 创建分析器并测试
    analyzer = SimilarityAnalyzer()
    result = analyzer.calculate_comprehensive_similarity(stock_data, gold_data)
    
    print("测试完成!")
    return result

