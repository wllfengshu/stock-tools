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

# 导入图表相关库
import plotly.graph_objects as go

# 使用tslearn库进行DTW计算 - 专业的时间序列分析库
from tslearn.metrics import dtw

class SimilarityAnalyzer:
    """
    K线图走势相似度分析器
    
    基于多维度综合分析，计算两条K线图的走势相似度
    适用于股票价格与金价走势的对比分析
    """
    
    def __init__(self, correlation=0.30, trend=0.25, volatility=0.20, 
                pattern=0.15, volume=0.10):
        """
        初始化相似度分析器
        
        权重配置：
        - correlation: 价格变化相关性 (30%)
        - trend: 趋势方向一致性 (25%) 
        - volatility: 波动性相似度 (20%)
        - pattern: 价格模式匹配 (15%)
        - volume: 成交量关系 (10%)
        """
        # 使用传入的参数设置权重
        self.weights = {
            'correlation': correlation,      # 价格变化相关性
            'trend': trend,                  # 趋势方向一致性  
            'volatility': volatility,        # 波动性相似度
            'pattern': pattern,              # 价格模式匹配
            'volume': volume                 # 成交量关系
        }
        
        print("K线图走势相似度分析器初始化完成")
        print(f"权重配置: {self.weights}")
    
    def update_weights(self, correlation=None, trend=None, volatility=None, 
                      pattern=None, volume=None):
        """
        动态更新权重配置
        
        Args:
            correlation: 价格变化相关性权重
            trend: 趋势方向一致性权重
            volatility: 波动性相似度权重
            pattern: 价格模式匹配权重
            volume: 成交量关系权重
        """
        if correlation is not None:
            self.weights['correlation'] = correlation
        if trend is not None:
            self.weights['trend'] = trend
        if volatility is not None:
            self.weights['volatility'] = volatility
        if pattern is not None:
            self.weights['pattern'] = pattern
        if volume is not None:
            self.weights['volume'] = volume
            
        print(f"权重配置已更新: {self.weights}")
    
    
    def preprocess_data(self, stock_data, gold_data, ma_windows=[5, 10, 20], 
                       move_day=0, data_missing_handling=1):
        """
        数据预处理和标准化
        
        Args:
            stock_data: 股票数据 (DataFrame)
            gold_data: 金价数据 (DataFrame)
            ma_windows: 移动平均线窗口列表，默认[5, 10, 20]
            move_day: 平移天数，负数左移，正数右移
            data_missing_handling: 数据缺失处理方式，0=不处理，1=跳过，2=用前一天数据填充
            
        Returns:
            tuple: (处理后的股票数据, 处理后的金价数据, 是否有成交量数据)
        """
        print("开始数据预处理...")
        print(f"平移天数: {move_day}, 数据缺失处理: {data_missing_handling}")
        print(f"移动平均线窗口: {ma_windows}")
        # 保持传入的数据结构，勿覆盖为列表
        # 1. 数据缺失处理
        if data_missing_handling == 2:  # 用前一天数据填充
            print("使用前一天数据填充缺失值...")
            stock_data = stock_data.ffill()
            gold_data = gold_data.ffill()
        elif data_missing_handling == 1:  # 跳过缺失数据
            print("跳过缺失数据...")
            stock_data = stock_data.dropna()
            gold_data = gold_data.dropna()
        # data_missing_handling == 0 时不处理，保持原样
        
        # 2. 平移天数处理
        if move_day != 0:
            print(f"应用平移天数: {move_day}天")
            if move_day > 0:  # 正数右移：金价数据向右移动，即用前几天的金价数据
                # 金价数据向右移动move_day天，相当于用前move_day天的金价数据
                gold_data = gold_data.shift(move_day)
                print(f"金价数据向右移动{move_day}天")
            else:  # 负数左移：金价数据向左移动，即用后几天的金价数据
                # 金价数据向左移动|move_day|天，相当于用后|move_day|天的金价数据
                gold_data = gold_data.shift(move_day)
                print(f"金价数据向左移动{abs(move_day)}天")
        
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
        for window in ma_windows:
            stock_data[f'MA{window}'] = stock_data['收盘'].rolling(window=window).mean()
            gold_data[f'MA{window}'] = gold_data['收盘'].rolling(window=window).mean()
        
        # 计算波动率
        stock_data['波动率'] = stock_data['涨跌幅'].rolling(window=5).std()
        gold_data['波动率'] = gold_data['涨跌幅'].rolling(window=5).std()
        
        # 只删除必要的NaN值，保留更多数据
        # 删除前几行的NaN（由于移动平均线计算）
        # 使用最大的移动平均线窗口来确定需要删除的NaN行数
        max_ma_window = max(ma_windows)
        stock_data = stock_data.dropna(subset=[f'MA{max_ma_window}'])
        gold_data = gold_data.dropna(subset=[f'MA{max_ma_window}'])
        
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
        
        # 使用传入的数据，勿覆盖

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
    
    def calculate_comprehensive_similarity(self, stock_data, gold_data, ma_windows=[5, 10, 20],
                                         move_day=0, data_missing_handling=1, window_size=5):
        """
        计算综合相似度分数
        
        算法说明：
        1. 计算各个维度的相似度
        2. 根据权重加权计算
        3. 返回最终相似度分数和详细分析
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            ma_windows: 移动平均线窗口列表，默认[5, 10, 20]
            move_day: 平移天数，负数左移，正数右移
            data_missing_handling: 数据缺失处理方式，0=不处理，1=跳过，2=用前一天数据填充
            window_size: 滑动窗口大小，用于计算每日相似度
            
        Returns:
            dict: 包含综合相似度和详细分析的字典
        """
        print("开始综合相似度分析...")
        print("=" * 50)
        print(f"参数配置: 滑动窗口={window_size}, 移动平均线窗口={ma_windows}, 平移天数={move_day}, 数据缺失处理={data_missing_handling}")
        
        # 数据预处理
        stock_processed, gold_processed, has_volume_data = self.preprocess_data(
            stock_data, gold_data, ma_windows, move_day, data_missing_handling
        )
        
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
        daily_similarity_data = self.calculate_daily_similarity(
            stock_data, gold_data, window_size, ma_windows, move_day, data_missing_handling
        )
        
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
    
    def calculate_daily_similarity(self, stock_data, gold_data, window_size=5, ma_windows=[5, 10, 20],
                                 move_day=0, data_missing_handling=1):
        """
        计算每日相似度时间序列
        
        Args:
            stock_data: 股票数据
            gold_data: 金价数据
            window_size: 滑动窗口大小
            ma_windows: 移动平均线窗口列表，默认[5, 10, 20]
            move_day: 平移天数，负数左移，正数右移
            data_missing_handling: 数据缺失处理方式，0=不处理，1=跳过，2=用前一天数据填充
            
        Returns:
            dict: 包含每日相似度数据的字典
        """
        print(f"计算每日相似度，窗口大小: {window_size}")
        
        # 数据预处理
        stock_processed, gold_processed, has_volume_data = self.preprocess_data(
            stock_data, gold_data, ma_windows, move_day, data_missing_handling
        )
        
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
    
    def create_similarity_chart(self, analysis_result):
        """创建相似度分析图表数据 - 显示每日相似度折线图"""
        # 获取分析结果
        comprehensive_score = analysis_result['comprehensive_score']
        dimension_scores = analysis_result['dimension_scores']
        daily_similarity_data = analysis_result.get('daily_similarity', {})
        
        # 创建图表
        fig = go.Figure()
        
        # 添加每日相似度折线图
        if daily_similarity_data and 'dates' in daily_similarity_data and 'similarities' in daily_similarity_data:
            dates = daily_similarity_data['dates']
            similarities = daily_similarity_data['similarities']
            
            # 确保日期格式正确
            formatted_dates = []
            for date in dates:
                if isinstance(date, str):
                    formatted_dates.append(date)
                elif hasattr(date, 'strftime'):
                    formatted_dates.append(date.strftime('%Y-%m-%d'))
                else:
                    formatted_dates.append(str(date))
            
            # 添加相似度折线
            fig.add_trace(go.Scatter(
                x=formatted_dates,
                y=similarities,
                mode='lines+markers',
                name='每日相似度',
                line=dict(color='#2E8B57', width=2),
                marker=dict(size=4, color='#2E8B57'),
                hovertemplate='<b>日期:</b> %{x}<br><b>相似度:</b> %{y:.2f}%<extra></extra>'
            ))
            
            # 添加平均相似度水平线
            mean_similarity = daily_similarity_data.get('mean_similarity', np.mean(similarities))
            fig.add_hline(
                y=mean_similarity,
                line_dash="dash",
                line_color="red",
                annotation_text=f"平均相似度: {mean_similarity:.2f}%",
                annotation_position="top right"
            )
            
            # 添加相似度区间背景
            fig.add_hrect(
                y0=80, y1=100,
                fillcolor="green", opacity=0.1,
                annotation_text="高相似度区间", annotation_position="top left"
            )
            fig.add_hrect(
                y0=60, y1=80,
                fillcolor="yellow", opacity=0.1,
                annotation_text="中等相似度区间", annotation_position="top left"
            )
            fig.add_hrect(
                y0=0, y1=60,
                fillcolor="red", opacity=0.1,
                annotation_text="低相似度区间", annotation_position="top left"
            )
        else:
            fig.add_annotation(
                text="没有每日相似度数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
        
        # 更新布局
        fig.update_layout(
            title=f'股票与金价走势相似度分析 - 综合分数: {comprehensive_score:.1f}/100',
            yaxis_title='相似度 (%)',
            height=600,
            showlegend=True,
            template='plotly_white',
            hovermode='x unified'
        )
        
        # 设置Y轴范围
        fig.update_yaxes(range=[0, 100])
        
        # 设置X轴格式
        fig.update_xaxes(
            tickangle=45,
            tickformat='%Y-%m-%d'
        )
        
        return fig.to_json()

