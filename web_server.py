#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
黄金板块交易系统Web服务器
提供HTML界面的api定义
"""

from flask import Flask, render_template, request, jsonify, send_file

# 配置参数
import math
from decimal import Decimal

app = Flask(__name__, static_folder='templates', static_url_path='')

# 导入系统
from database.data_provider import DataProvider
from similarity_analyzer import SimilarityAnalyzer
from trading_strategy import TradingStrategy
from common_util import CommonUtil
data_provider = DataProvider()
similarity_analyzer = SimilarityAnalyzer()
trading_strategy = TradingStrategy()
common_util = CommonUtil()

# 跟踪当前加载的股票代码
current_loaded_stock = None
# 全局股票列表
gold_stocks = [
        {"code": "002155", "name": "湖南黄金", "sector": "黄金开采"},
        {"code": "600547", "name": "山东黄金", "sector": "黄金开采"},
        {"code": "000975", "name": "银泰黄金", "sector": "黄金开采"},
        {"code": "600489", "name": "中金黄金", "sector": "黄金开采"},
        {"code": "002237", "name": "恒邦股份", "sector": "黄金冶炼"},
        {"code": "600988", "name": "赤峰黄金", "sector": "黄金开采"},
        {"code": "600311", "name": "荣华实业", "sector": "黄金开采"},
        {"code": "000060", "name": "中金岭南", "sector": "有色金属"},
        {"code": "600362", "name": "江西铜业", "sector": "有色金属"},
        {"code": "000630", "name": "铜陵有色", "sector": "有色金属"}
    ]

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/validate_auth')
def validate_auth():
    """验证auth参数是否合法"""
    try:
        auth = request.args.get('auth') or (request.json.get('auth') if request.is_json and request.json else None)
        ok, reason = common_util.auth_is_valid(auth)
        return jsonify({
            'success': ok,
            'auth': auth or '',
            'message': reason
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'auth': '',
            'message': f'校验失败: {str(e)}'
        })

@app.route('/api/stock_list')
def get_stock_list():
    """获取黄金板块股票列表"""
    return jsonify(gold_stocks)

@app.route('/api/analyze', methods=['POST'])
def analyze_stock():
    """分析股票数据"""
    try:
        data = request.get_json()
        months = data.get('months')
        if not months:
            return jsonify({
                'success': False,
                'message': '请提供时间范围参数'
            })
        months = int(months)
        
        # 获取当前配置值
        stock_code = data.get('stock_code')
        
        if not stock_code:
            return jsonify({
                'success': False,
                'message': '请选择股票代码'
            })
        
        # 获取交易历史数据
        trade_points = []
        try:
            # 这里可以从数据库或文件读取交易历史
            # 暂时返回空列表，实际实现时需要从策略系统获取
            trade_points = []
        except Exception as e:
            trade_points = []
        
        # 加载需要的数据
        stock_data = common_util.get_stock_data(months=months, stock_code=stock_code)
        gold_data = common_util.get_gold_data(months=months)
        if stock_data is None or getattr(stock_data, 'empty', True):
            return jsonify({
                'success': False,
                'message': f'无法获取股票{stock_code}数据'
            })
        if gold_data is None or getattr(gold_data, 'empty', True):
            return jsonify({
                'success': False,
                'message': '无法获取金价数据'
            })
        
        # 创建图表数据 - 包含交易点标识
        chart_data = data_provider.create_chart_data(stock_data, gold_data, trade_points)
        
        return jsonify({
            'success': True,
            'message': '分析完成',
            'chart_data': chart_data,
            'stock_name': '股票数据',
            'months': months,
            'trade_points': trade_points
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'分析失败: {str(e)}'
        })

@app.route('/api/similarity_analysis', methods=['POST'])
def analyze_similarity():
    """分析股票与金价的走势相似度"""
    try:
        data = request.get_json()
        stock_code = data.get('stock_code')
        months = data.get('months')
        
        # 获取新的参数配置
        window_size = data.get('window_size', 5)
        correlation_weight = data.get('correlation_weight', 30) / 100.0
        trend_weight = data.get('trend_weight', 25) / 100.0
        volatility_weight = data.get('volatility_weight', 20) / 100.0
        pattern_weight = data.get('pattern_weight', 15) / 100.0
        volume_weight = data.get('volume_weight', 10) / 100.0
        ma_window = data.get('ma_window', 20)
        
        # 新增参数：平移天数和数据缺失处理
        move_day = data.get('move_day', 0)  # 平移天数，负数左移，正数右移
        data_missing = data.get('data_missing', 1)  # 数据缺失处理方式：0=不处理，1=跳过，2=用前一天数据填充
        
        if not months:
            return jsonify({
                'success': False,
                'message': '请提供时间范围参数'
            })
        months = int(months)
        
        if not stock_code:
            return jsonify({
                'success': False,
                'message': '请选择股票代码'
            })
        
        # 从数据提供层获取数据，避免依赖未定义的实例属性
        stock_data = common_util.get_stock_data(months=months, stock_code=stock_code)
        gold_data = common_util.get_gold_data(months=months)
        
        if stock_data is None or stock_data.empty:
            return jsonify({
                'success': False,
                'message': f'无法获取股票{stock_code}数据'
            })
        
        if gold_data is None or gold_data.empty:
            return jsonify({
                'success': False,
                'message': '无法获取金价数据'
            })
        
        # 进行相似度分析
        # 准备移动平均线窗口配置
        ma_windows = [5, 10, ma_window] if ma_window not in [5, 10] else [5, 10, 20]
        
        # 使用自定义窗口大小计算每日相似度，传入新参数
        analysis_result = similarity_analyzer.calculate_comprehensive_similarity(
            stock_data, gold_data, ma_windows, 
            move_day=move_day, data_missing_handling=data_missing, window_size=window_size
        )
        
        # 注意：现在calculate_comprehensive_similarity函数已经正确处理了window_size参数
        # 不需要重复计算每日相似度
        
        # 生成相似度图表数据
        similarity_chart_data = similarity_analyzer.create_similarity_chart(analysis_result)
        
        # 从股票列表中，根据股票代码，获取股票名称
        stock_name = next((stock['name'] for stock in gold_stocks if stock['code'] == stock_code), '未知股票')

        return jsonify({
            'success': True,
            'similarity_score': analysis_result['comprehensive_score'],
            'dimension_scores': analysis_result['dimension_scores'],
            'analysis_summary': analysis_result['analysis_summary'],
            'daily_similarity': analysis_result.get('daily_similarity', {}),
            'chart_data': similarity_chart_data,
            'stock_name': stock_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'相似度分析失败: {str(e)}'
        })

@app.route('/api/current_status')
def get_current_status():
    """获取当前状态 - 调用业务逻辑层"""
    global current_loaded_stock
    
    try:
        # 获取请求参数中的股票代码
        stock_code = request.args.get('stock_code')
        months = request.args.get('months', default=6, type=int)
        
        if not stock_code:
            return jsonify({
                'error': '请选择股票代码'
            })
            
        current_loaded_stock = stock_code
        
        # 调用数据提供者获取状态（传入代码与时间范围，内部懒加载）
        status = data_provider.get_current_status(stock_code=stock_code, months=months)
        
        if status is None:
            return jsonify({
                'error': '无法获取股票状态数据，请重试'
            })
        
        # 检查关键数据是否有效
        if status.get('current_price', 0) == 0:
            return jsonify({
                'error': '股票价格数据异常，请重试'
            })
        
        # 处理NaN值，确保JSON序列化正常
        def clean_nan(value):
            """清理NaN值，如果为NaN则报错，并转换Decimal为float"""
            # 转换Decimal为float
            if isinstance(value, Decimal):
                value = float(value)
            
            if isinstance(value, float) and math.isnan(value):
                raise ValueError(f"数据包含NaN值: {value}")
            return value
        
        # 检查数据完整性
        required_fields = ['current_price', 'stock_change_rate', 'gold_price', 'gold_change_rate']
        for field in required_fields:
            if field not in status:
                return jsonify({
                    'error': f'缺少必要数据字段: {field}'
                })
        
        # 清理所有可能包含NaN的值
        try:
            cleaned_status = {
                # 实时数据
                'current_price': clean_nan(status['current_price']),
                'stock_change_rate': clean_nan(status['stock_change_rate']),
                'gold_price': clean_nan(status['gold_price']),
                'gold_change_rate': clean_nan(status['gold_change_rate']),
                'total_assets': clean_nan(status.get('total_assets', 0)),
                
                # 持久化数据（来自JSON文件）
                'total_cost': status.get('total_cost', 0),
                'total_shares': status.get('total_shares', 0),
                'cumulative_return': status.get('cumulative_return', 0),
                'annual_return': status.get('annual_return', 0),
                
                # 其他数据
                'trade_count': status.get('trade_count', 0),
                'base_investment': status.get('base_investment', 0),
                'stop_loss_rate': status.get('stop_loss_rate', 0),
                'profit_take_rate': status.get('profit_take_rate', 0)
            }
        except ValueError as e:
            return jsonify({
                'error': f'数据异常: {str(e)}'
            })
        
        # 计算持仓状态
        position_info = status.get('position', {})
        if not position_info:
            return jsonify({
                'error': '缺少持仓状态数据'
            })
        
        cleaned_status['position'] = position_info
        
        return jsonify(cleaned_status)
        
    except Exception as e:
        return jsonify({
            'error': f'获取状态失败: {str(e)}'
        })

@app.route('/api/trade_history')
def get_trade_history():
    """获取交易历史"""
    # 这里可以添加交易历史获取逻辑
    return jsonify([])

@app.route('/download/<filename>')
def download_file(filename):
    """下载生成的HTML文件"""
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return f"文件下载失败: {str(e)}", 404

@app.route('/api/execute_strategy', methods=['POST'])
def execute_strategy():
    """执行量化交易策略"""
    try:
        data = request.get_json()
        
        # 获取策略参数 - 所有参数都必须提供
        base_investment = data.get('base_investment')
        stop_loss_rate = data.get('stop_loss_rate')
        max_profit_rate = data.get('max_profit_rate')
        profit_callback_rate = data.get('profit_callback_rate')
        min_gold_change = data.get('min_gold_change')
        min_buy_amount = data.get('min_buy_amount')
        transaction_cost_rate = data.get('transaction_cost_rate')
        max_hold_days = data.get('max_hold_days')
        stock_code = data.get('stock_code')
        strategy_mode = data.get('strategy_mode')
        
        # 检查必要参数
        required_params = {
            'base_investment': base_investment,
            'stop_loss_rate': stop_loss_rate,
            'max_profit_rate': max_profit_rate,
            'profit_callback_rate': profit_callback_rate,
            'min_gold_change': min_gold_change,
            'min_buy_amount': min_buy_amount,
            'transaction_cost_rate': transaction_cost_rate,
            'max_hold_days': max_hold_days,
            'stock_code': stock_code,
            'strategy_mode': strategy_mode
        }
        
        missing_params = [param for param, value in required_params.items() if value is None]
        if missing_params:
            return jsonify({
                'success': False,
                'error': f'缺少必要参数: {", ".join(missing_params)}'
            })
        
        # 获取高级参数 - 所有参数都必须提供
        min_gold_change = data.get('min_gold_change')
        min_buy_amount = data.get('min_buy_amount')
        transaction_cost_rate = data.get('transaction_cost_rate')
        
        # 检查高级参数
        advanced_params = {
            'min_gold_change': min_gold_change,
            'min_buy_amount': min_buy_amount,
            'transaction_cost_rate': transaction_cost_rate
        }
        
        missing_advanced = [param for param, value in advanced_params.items() if value is None]
        if missing_advanced:
            return jsonify({
                'success': False,
                'error': f'缺少高级参数: {", ".join(missing_advanced)}'
            })
        
        # 转换数据类型
        min_gold_change = float(min_gold_change) / 100  # 转换为小数
        min_buy_amount = float(min_buy_amount)
        transaction_cost_rate = float(transaction_cost_rate) / 100  # 转换为小数
        max_hold_days = int(max_hold_days)
        
        if strategy_mode == 'improved':
            # 获取用户参数（从请求中获取或使用默认值）
            user_id = data.get('user_id', 100001)
            auth = data.get('auth', 'default_user')
            
            # 更新全局策略实例的参数
            trading_strategy.update_strategy_params(
                user_id=user_id,
                auth=auth,
                base_investment=base_investment,
                stop_loss_rate=stop_loss_rate,
                profit_callback_rate=profit_callback_rate,
                max_profit_rate=max_profit_rate,
                min_gold_change=min_gold_change,
                min_buy_amount=min_buy_amount,
                transaction_cost_rate=transaction_cost_rate,
                max_hold_days=max_hold_days
            )
            
            # 执行改进版策略
            result = trading_strategy.execute_strategy_improved(stock_code)
            strategy_summary = trading_strategy.get_strategy_summary_improved()
        else:
            # 其他策略
            return jsonify({
                'success': False,
                'error': '其他策略未实现'
            })
        
        return jsonify({
            'success': True,
            'strategy_result': result,
            'strategy_summary': strategy_summary,
            'strategy_mode': strategy_mode,
            'message': '策略执行成功'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'策略执行失败: {str(e)}'
        })

@app.route('/api/strategy_status', methods=['GET', 'POST'])
def get_strategy_status():
    """获取策略状态信息"""
    try:
        stock_code = request.args.get('stock_code')

        # 获取用户参数
        if request.method == 'POST':
            data = request.get_json()
            user_id = data.get('user_id', 100001)
            auth = data.get('auth', 'default_user')
        else:
            user_id = request.args.get('user_id', 100001, type=int)
            auth = request.args.get('auth', 'default_user')
        
        # 更新全局策略实例的参数
        trading_strategy.update_strategy_params(user_id=user_id, auth=auth)
        
        # 获取策略状态
        status = trading_strategy.get_strategy_status_improved(refresh_from_db=True, stock_code=stock_code)
        summary = trading_strategy.get_strategy_summary_improved(refresh_from_db=True, stock_code=stock_code)
        
        return jsonify({
            'success': True,
            'status': status,
            'summary': summary,
            'user_id': user_id,
            'auth': auth
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取策略状态失败: {str(e)}'
        })

@app.route('/api/strategy_stats')
def get_strategy_stats():
    """获取策略统计信息"""
    try:
        # 获取用户参数
        user_id = request.args.get('user_id', 100001, type=int)
        auth = request.args.get('auth', 'default_user')
        
        # 更新全局策略实例的参数
        trading_strategy.update_strategy_params(user_id=user_id, auth=auth)
        summary = trading_strategy.get_strategy_summary_improved(refresh_from_db=True)
        
        return jsonify({
            'success': True,
            'total_trades': summary.get('total_trades', 0),
            'total_profit': summary.get('total_net_profit', 0.0),
            'win_trades': summary.get('win_trades', 0),
            'win_rate': summary.get('win_rate', 0.0),
            'total_transaction_cost': summary.get('total_transaction_cost', 0.0),
            'current_position': summary.get('current_position', False),
            'total_shares': summary.get('total_shares', 0),
            'total_cost': summary.get('total_cost', 0),
            'history_max_profit': summary.get('history_max_profit', 0),
            'last_trade_date': summary.get('last_trade_date'),
            'user_id': user_id,
            'auth': auth
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取策略统计失败: {str(e)}'
        })

@app.route('/api/strategy_trades')
def get_strategy_trades():
    """获取策略交易历史"""
    try:
        # 获取用户参数
        user_id = request.args.get('user_id', 100001, type=int)
        auth = request.args.get('auth', 'default_user')
        
        # 更新全局策略实例的参数
        trading_strategy.update_strategy_params(user_id=user_id, auth=auth)
        
        # 获取交易历史
        trade_history = trading_strategy.trade_history
        
        return jsonify({
            'success': True,
            'trades': trade_history,
            'total_trades': len(trade_history),
            'user_id': user_id,
            'auth': auth
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取交易历史失败: {str(e)}'
        })

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """运行历史回测"""
    try:
        data = request.get_json()
        
        # 获取回测参数
        stock_code = data.get('stock_code')
        months = data.get('months', 6)
        
        # 获取策略参数
        base_investment = data.get('base_investment', 10000)
        stop_loss_rate = data.get('stop_loss_rate', 0.10)
        profit_callback_rate = data.get('profit_callback_rate', 0.01)
        max_profit_rate = data.get('max_profit_rate', 0.50)
        min_gold_change = data.get('min_gold_change', 0.002)
        min_buy_amount = data.get('min_buy_amount', 100)
        transaction_cost_rate = data.get('transaction_cost_rate', 0.001)
        max_hold_days = data.get('max_hold_days', 30)
        
        # 获取用户参数
        user_id = data.get('user_id', 100001)
        auth = data.get('auth', 'default_user')
        
        # 检查必要参数
        if not stock_code:
            return jsonify({
                'success': False,
                'error': '请提供股票代码'
            })
        
        # 更新全局策略实例的参数
        trading_strategy.update_strategy_params(
            user_id=user_id,
            auth=auth,
            base_investment=base_investment,
            stop_loss_rate=stop_loss_rate,
            profit_callback_rate=profit_callback_rate,
            max_profit_rate=max_profit_rate,
            min_gold_change=min_gold_change,
            min_buy_amount=min_buy_amount,
            transaction_cost_rate=transaction_cost_rate,
            max_hold_days=max_hold_days
        )
        
        # 运行回测
        backtest_result = trading_strategy.run_backtest(
            stock_code=stock_code,
            months=months
        )
        
        if 'error' in backtest_result:
            return jsonify({
                'success': False,
                'error': backtest_result['error']
            })
        
        # 组装结构化图表数据：价格OHLC、收益曲线、交易点
        try:
            profit_curve = backtest_result.get('profit_curve', [])
            if profit_curve:
                # 提取回测时间范围
                start_date = backtest_result.get('backtest_period', {}).get('start_date')
                end_date = backtest_result.get('backtest_period', {}).get('end_date')

                # 重取一次股票数据（与回测一致的区间）
                stock_df = common_util.get_stock_data(stock_code=stock_code, months=months)
                if start_date and end_date and stock_df is not None and not stock_df.empty:
                    import pandas as pd
                    try:
                        stock_df = stock_df.loc[(stock_df.index >= pd.to_datetime(start_date)) & (stock_df.index <= pd.to_datetime(end_date))]
                    except Exception:
                        pass

                # 构建OHLC按照profit_curve日期对齐，若当日缺失则跳过
                dates = []
                open_list, high_list, low_list, close_list = [], [], [], []
                for point in profit_curve:
                    d = point.get('date')
                    if not d:
                        continue
                    dates.append(d)
                    if stock_df is not None and not stock_df.empty and d in stock_df.index.strftime('%Y-%m-%d').tolist():
                        # 定位到该日期的行
                        try:
                            row = stock_df.loc[pd.to_datetime(d)]
                        except Exception:
                            row = None
                        if row is not None:
                            open_list.append(float(row.get('开盘', row.get('open', row.get('Open', 0)))))
                            high_list.append(float(row.get('最高', row.get('high', row.get('High', 0)))))
                            low_list.append(float(row.get('最低', row.get('low', row.get('Low', 0)))))
                            close_list.append(float(row.get('收盘', row.get('close', row.get('Close', 0)))))
                        else:
                            # 回退到profit_curve提供的收盘价
                            cp = float(point.get('stock_price', 0))
                            open_list.append(cp); high_list.append(cp); low_list.append(cp); close_list.append(cp)
                    else:
                        cp = float(point.get('stock_price', 0))
                        open_list.append(cp); high_list.append(cp); low_list.append(cp); close_list.append(cp)

                # 交易点：来自profit_curve.trade_action 与 stock_price
                trades = []
                for point in profit_curve:
                    action = (point.get('trade_action') or '').upper()
                    if action in ('BUY', 'SELL'):
                        trades.append({
                            'time': point.get('date'),
                            'price': float(point.get('stock_price', 0)),
                            'side': 'buy' if action == 'BUY' else 'sell'
                        })

                # 收益曲线
                equity_time = [p.get('date') for p in profit_curve]
                equity_value = [float(p.get('market_value', 0)) for p in profit_curve]

                backtest_result.setdefault('charts', {})
                backtest_result['charts']['price_series'] = {
                    'ohlc': {
                        'time': dates,
                        'open': open_list,
                        'high': high_list,
                        'low': low_list,
                        'close': close_list
                    }
                }
                backtest_result['charts']['equity_series'] = {
                    'time': equity_time,
                    'equity': equity_value
                }
                backtest_result['charts']['trades'] = trades

                # 仍保留旧的合成图以兼容前端老逻辑
                chart_data = create_backtest_chart(profit_curve, stock_code)
                backtest_result['chart_data'] = chart_data
        except Exception as e:
            print(f"构建结构化图表数据失败: {e}")
        
        return jsonify({
            'success': True,
            'backtest_result': backtest_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'回测失败: {str(e)}'
        })

def create_backtest_chart(profit_curve, stock_code):
    """创建回测收益曲线图表"""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        if not profit_curve:
            return None
        
        # 提取数据
        dates = [point['date'] for point in profit_curve]
        market_values = [point['market_value'] for point in profit_curve]
        total_costs = [point['total_cost'] for point in profit_curve]
        profit_rates = [point['profit_rate'] * 100 for point in profit_curve]  # 转换为百分比
        stock_prices = [point['stock_price'] for point in profit_curve]
        gold_prices = [point['gold_price'] for point in profit_curve]
        trade_actions = [point['trade_action'] for point in profit_curve]
        
        # 创建子图
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=('收益曲线', '股票价格', '金价走势'),
            row_heights=[0.4, 0.3, 0.3]
        )
        
        # 1. 收益曲线图
        fig.add_trace(go.Scatter(
            x=dates,
            y=market_values,
            mode='lines',
            name='总资产',
            line=dict(color='blue', width=2),
            hovertemplate='<b>日期:</b> %{x}<br><b>总资产:</b> ¥%{y:.2f}<extra></extra>'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=total_costs,
            mode='lines',
            name='投资成本',
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='<b>日期:</b> %{x}<br><b>投资成本:</b> ¥%{y:.2f}<extra></extra>'
        ), row=1, col=1)
        
        # 添加交易点标记
        buy_dates = [dates[i] for i, action in enumerate(trade_actions) if action == 'BUY']
        buy_values = [market_values[i] for i, action in enumerate(trade_actions) if action == 'BUY']
        
        sell_dates = [dates[i] for i, action in enumerate(trade_actions) if action == 'SELL']
        sell_values = [market_values[i] for i, action in enumerate(trade_actions) if action == 'SELL']
        
        if buy_dates:
            fig.add_trace(go.Scatter(
                x=buy_dates,
                y=buy_values,
                mode='markers',
                name='买入点',
                marker=dict(
                    symbol='triangle-up',
                    size=10,
                    color='green',
                    line=dict(width=2, color='darkgreen')
                ),
                hovertemplate='<b>买入点</b><br>日期: %{x}<br>总资产: ¥%{y:.2f}<extra></extra>'
            ), row=1, col=1)
        
        if sell_dates:
            fig.add_trace(go.Scatter(
                x=sell_dates,
                y=sell_values,
                mode='markers',
                name='卖出点',
                marker=dict(
                    symbol='triangle-down',
                    size=10,
                    color='red',
                    line=dict(width=2, color='darkred')
                ),
                hovertemplate='<b>卖出点</b><br>日期: %{x}<br>总资产: ¥%{y:.2f}<extra></extra>'
            ), row=1, col=1)
        
        # 2. 股票价格图
        fig.add_trace(go.Scatter(
            x=dates,
            y=stock_prices,
            mode='lines',
            name='股票价格',
            line=dict(color='orange', width=2),
            hovertemplate='<b>日期:</b> %{x}<br><b>股票价格:</b> ¥%{y:.2f}<extra></extra>'
        ), row=2, col=1)
        
        # 3. 金价走势图
        fig.add_trace(go.Scatter(
            x=dates,
            y=gold_prices,
            mode='lines',
            name='金价',
            line=dict(color='gold', width=2),
            hovertemplate='<b>日期:</b> %{x}<br><b>金价:</b> $%{y:.2f}<extra></extra>'
        ), row=3, col=1)
        
        # 更新布局
        fig.update_layout(
            title=f'{stock_code} 历史回测收益曲线',
            height=800,
            showlegend=True,
            template='plotly_white',
            autosize=True,
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        # 设置Y轴标题
        fig.update_yaxes(title_text="资产价值 (元)", row=1, col=1)
        fig.update_yaxes(title_text="股票价格 (元)", row=2, col=1)
        fig.update_yaxes(title_text="金价 (美元)", row=3, col=1)
        
        # 隐藏底部缩略图
        fig.update_xaxes(rangeslider=dict(visible=False))
        
        return fig.to_json()
        
    except Exception as e:
        print(f"创建回测图表失败: {e}")
        return None
