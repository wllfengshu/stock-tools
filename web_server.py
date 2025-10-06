#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
黄金板块交易系统Web服务器
提供HTML界面进行时间范围查询和股票分析
"""

from flask import Flask, render_template, request, jsonify, send_file

# 导入系统
from advanced_interactive_system_professional import ProfessionalInteractiveSystem
from kline_similarity_analyzer import KlineSimilarityAnalyzer

# 配置参数
TARGET_STOCK_NAME = "湖南黄金"
BASE_INVESTMENT = 10000
STOP_LOSS_RATE = 0.05
PROFIT_TAKE_RATE = 0.15
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

app = Flask(__name__, static_folder='templates', static_url_path='')

# 全局系统实例
system = ProfessionalInteractiveSystem()
similarity_analyzer = KlineSimilarityAnalyzer()

def create_similarity_chart(analysis_result):
    """创建相似度分析图表数据 - 显示每日相似度折线图"""
    print("创建相似度分析图表...")
    
    # 获取分析结果
    comprehensive_score = analysis_result['comprehensive_score']
    dimension_scores = analysis_result['dimension_scores']
    daily_similarity_data = analysis_result.get('daily_similarity', {})
    
    print(f"综合相似度分数: {comprehensive_score}")
    print(f"各维度分数: {dimension_scores}")
    print(f"每日相似度数据: {len(daily_similarity_data.get('dates', []))} 个数据点")
    
    # 创建图表
    fig = go.Figure()
    
    # 添加每日相似度折线图
    if daily_similarity_data and 'dates' in daily_similarity_data and 'similarities' in daily_similarity_data:
        dates = daily_similarity_data['dates']
        similarities = daily_similarity_data['similarities']
        
        print(f"添加每日相似度折线图，数据点: {len(dates)}")
        
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
        print("⚠️ 没有每日相似度数据，创建空图表")
        fig.add_annotation(
            text="没有每日相似度数据",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # 更新布局
    fig.update_layout(
        title=f'股票与金价走势相似度分析 - 综合分数: {comprehensive_score:.1f}/100',
        xaxis_title='日期',
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
    
    print("相似度图表创建完成")
    return fig.to_json()

def create_chart_data(data, stock_name, gold_data=None, trade_points=None):
    """创建专业图表数据 - 支持双K线图显示"""
    print(f"=== 创建K线图 ===")
    print(f"股票数据形状: {data.shape}")
    print(f"伦敦金数据形状: {gold_data.shape if gold_data is not None else 'None'}")
    print(f"数据示例:")
    print(data.head(3))
    print(f"开盘价数据: {data['开盘'].tolist()[:5]}")
    print(f"日期范围: {data.index[0]} 到 {data.index[-1]}")
    print(f"数据点数: {len(data)}")
    
    # 创建子图 - 如果有伦敦金数据，增加一个子图
    if gold_data is not None and not gold_data.empty:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(f'{stock_name} K线图', '伦敦金K线图', '成交量'),
            row_heights=[0.4, 0.3, 0.3]
        )
    else:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(f'{stock_name} K线图', '成交量'),
            row_heights=[0.7, 0.3]
        )
    
    # 添加K线图 - 按照标准示例格式
    print(f"正在添加K线图...")
    
    # 将pandas数据转换为标准格式
    kline_data = {
        'date': data.index.strftime('%Y-%m-%d').tolist(),
        'open': data['开盘'].tolist(),
        'high': data['最高'].tolist(),
        'low': data['最低'].tolist(),
        'close': data['收盘'].tolist()
    }
    
    print(f"转换后的K线数据:")
    print(f"日期数量: {len(kline_data['date'])}")
    print(f"开盘价数量: {len(kline_data['open'])}")
    print(f"前3个日期: {kline_data['date'][:3]}")
    print(f"前3个开盘价: {kline_data['open'][:3]}")
    
    # 添加K线图 - 使用标准格式
    fig.add_trace(go.Candlestick(
        x=kline_data['date'],        # 时间序列
        open=kline_data['open'],     # 开盘价
        high=kline_data['high'],     # 最高价
        low=kline_data['low'],       # 最低价
        close=kline_data['close']    # 收盘价
    ))
    print(f"K线图已添加")
    
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
        print(f"MA5已添加")
    
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
        print(f"MA20已添加")
    
    # 添加伦敦金K线图
    if gold_data is not None and not gold_data.empty:
        print(f"正在添加伦敦金K线图...")
        
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
            decreasing_line_color='green'
        ), row=2, col=1)
        print(f"伦敦金K线图已添加")
    
    # 添加交易点标识
    if trade_points and len(trade_points) > 0:
        print(f"正在添加交易点标识...")
        
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
            print(f"买入点已添加: {len(buy_points)}个")
        
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
            print(f"卖出点已添加: {len(sell_points)}个")
    
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
    print(f"成交量已添加")
    
    # 更新布局 - 修复xaxis警告并强制设置宽度
    if gold_data is not None and not gold_data.empty:
        # 三子图布局
        fig.update_layout(
            title=f'{stock_name} & 伦敦金 K线图交易系统',
            xaxis_title='日期',
            yaxis_title='股票价格 (元)',
            yaxis2_title='伦敦金价格 (美元)',
            yaxis3_title='成交量',
            height=1000,
            width=None,
            showlegend=True,
            template='plotly_white',
            autosize=True,
            margin=dict(l=50, r=50, t=80, b=50),
            xaxis=dict(
                type='category',
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                matches=None
            ),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
            yaxis2=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
            yaxis3=dict(showgrid=True, gridwidth=1, gridcolor='lightgray')
        )
    else:
        # 二子图布局
        fig.update_layout(
            title=f'{stock_name} K线图交易系统',
            xaxis_title='日期',
            yaxis_title='价格 (元)',
            yaxis2_title='成交量',
            height=800,
            width=None,
            showlegend=True,
            template='plotly_white',
            autosize=True,
            margin=dict(l=50, r=50, t=80, b=50),
            xaxis=dict(
                type='category',
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                matches=None
            ),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
            yaxis2=dict(showgrid=True, gridwidth=1, gridcolor='lightgray')
        )
    
    # 强制设置所有xaxis和yaxis配置，确保网格密度完全一致
    if gold_data is not None and not gold_data.empty:
        # 三子图配置 - 强制统一网格设置
        # 股票K线图 (row=1) - 减少网格密度
        fig.update_xaxes(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            matches=None,
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=10,  # 限制网格数量
            tickformat='%Y-%m-%d',  # 设置日期格式
            row=1, col=1
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=8,  # 限制网格数量
            row=1, col=1
        )
        
        # 伦敦金K线图 (row=2) - 增加网格密度
        fig.update_xaxes(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            matches=None,
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=10,  # 限制网格数量
            tickformat='%Y-%m-%d',  # 设置日期格式
            row=2, col=1
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=8,  # 限制网格数量
            row=2, col=1
        )
        
        # 成交量图 (row=3) - 增加网格密度
        fig.update_xaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            matches=None,
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=10,  # 限制网格数量
            tickformat='%Y-%m-%d',  # 设置日期格式
            row=3, col=1
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=8,  # 限制网格数量
            row=3, col=1
        )
    else:
        # 二子图配置 - 强制统一网格设置
        # 股票K线图 (row=1) - 减少网格密度
        fig.update_xaxes(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            matches=None,
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=10,  # 限制网格数量
            tickformat='%Y-%m-%d',  # 设置日期格式
            row=1, col=1
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=8,  # 限制网格数量
            row=1, col=1
        )
        
        # 成交量图 (row=2) - 增加网格密度
        fig.update_xaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            matches=None,
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=10,  # 限制网格数量
            tickformat='%Y-%m-%d',  # 设置日期格式
            row=2, col=1
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='lightgray',
            dtick=None,  # 禁用自动网格间隔
            tickmode='auto',
            nticks=8,  # 限制网格数量
            row=2, col=1
        )
    
    print(f"图表创建完成")
    print(f"图表布局信息:")
    print(f"  - 宽度: {fig.layout.width}")
    print(f"  - 高度: {fig.layout.height}")
    print(f"  - 自动调整大小: {fig.layout.autosize}")
    print(f"  - 边距: {fig.layout.margin}")
    print(f"  - X轴配置: {fig.layout.xaxis}")
    print(f"  - Y轴配置: {fig.layout.yaxis}")
    
    # 转换为JSON格式
    chart_json = fig.to_json()
    print(f"JSON数据长度: {len(chart_json)} 字符")
    return chart_json

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/stock_list')
def get_stock_list():
    """获取黄金板块股票列表"""
    gold_stocks = [
        {"code": "002155", "name": "湖南黄金", "sector": "黄金开采"},
        {"code": "600547", "name": "山东黄金", "sector": "黄金开采"},
        {"code": "000975", "name": "银泰黄金", "sector": "黄金开采"},
        {"code": "600489", "name": "中金黄金", "sector": "黄金开采"},
        {"code": "002237", "name": "恒邦股份", "sector": "黄金冶炼"},
        {"code": "600988", "name": "赤峰黄金", "sector": "黄金开采"},
        {"code": "002155", "name": "湖南黄金", "sector": "黄金开采"},
        {"code": "600311", "name": "荣华实业", "sector": "黄金开采"}
    ]
    return jsonify(gold_stocks)

@app.route('/api/analyze', methods=['POST'])
def analyze_stock():
    """分析股票数据"""
    try:
        data = request.get_json()
        months = int(data.get('months', 6))
        
        # 获取当前配置值
        stock_code = data.get('stock_code', '002155')
        stock_name = data.get('stock_name', TARGET_STOCK_NAME)
        
        # 如果stock_name为undefined或空，使用默认值
        if not stock_name or stock_name == 'undefined' or stock_name == 'null':
            stock_name = TARGET_STOCK_NAME
            print(f"股票名称为空，使用默认值: {stock_name}")
        
        print(f"最终使用的股票名称: {stock_name}")
        
        # 使用业务逻辑层准备数据
        print("Web服务器：调用业务逻辑层准备数据...")
        print(f"请求参数: months={months}, stock_code={stock_code}, stock_name={stock_name}")
        
        # 调用业务逻辑层
        if not system.prepare_data(months, stock_code):
            return jsonify({
                'success': False,
                'message': f'无法获取股票{stock_code}({stock_name})的数据，请检查股票代码是否正确或网络连接'
            })
        
        print(f"业务逻辑层数据准备完成，形状: {system.data.shape}")
        
        # 获取交易历史数据
        trade_points = []
        try:
            # 这里可以从数据库或文件读取交易历史
            # 暂时返回空列表，实际实现时需要从策略系统获取
            trade_points = []
        except Exception as e:
            print(f"获取交易历史失败: {e}")
            trade_points = []
        
        # 创建图表数据 - 包含交易点标识
        chart_data = create_chart_data(system.data, stock_name, system.gold_data, trade_points)
        
        return jsonify({
            'success': True,
            'message': '分析完成',
            'chart_data': chart_data,
            'stock_name': stock_name,
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
        stock_code = data.get('stock_code', '002155')
        months = data.get('months', 6)
        
        print(f"🔍 开始相似度分析...")
        print(f"   股票代码: {stock_code}")
        print(f"   时间范围: {months}个月")
        
        # 获取股票数据
        stock_data = system.get_stock_data(months, stock_code)
        if stock_data is None or stock_data.empty:
            return jsonify({
                'success': False,
                'message': f'无法获取股票{stock_code}数据'
            })
        
        # 获取金价数据
        gold_data = system.get_gold_historical_data(months)
        if gold_data is None or gold_data.empty:
            return jsonify({
                'success': False,
                'message': '无法获取金价数据'
            })
        
        # 进行相似度分析
        print(f"开始相似度分析，股票数据形状: {stock_data.shape}, 金价数据形状: {gold_data.shape}")
        print(f"股票数据索引类型: {type(stock_data.index)}, 金价数据索引类型: {type(gold_data.index)}")
        print(f"股票数据索引示例: {stock_data.index[:3]}")
        print(f"金价数据索引示例: {gold_data.index[:3]}")
        
        analysis_result = similarity_analyzer.calculate_comprehensive_similarity(stock_data, gold_data)
        
        # 生成相似度图表数据
        print("开始生成相似度图表...")
        similarity_chart_data = create_similarity_chart(analysis_result)
        print("相似度图表生成完成")
        
        return jsonify({
            'success': True,
            'similarity_score': analysis_result['comprehensive_score'],
            'dimension_scores': analysis_result['dimension_scores'],
            'analysis_summary': analysis_result['analysis_summary'],
            'daily_similarity': analysis_result.get('daily_similarity', {}),
            'chart_data': similarity_chart_data,
            'stock_name': system.get_stock_name(stock_code)
        })
        
    except Exception as e:
        print(f"❌ 相似度分析失败: {e}")
        return jsonify({
            'success': False,
            'message': f'相似度分析失败: {str(e)}'
        })

@app.route('/api/current_status')
def get_current_status():
    """获取当前策略状态 - 调用业务逻辑层"""
    try:
        # 获取请求参数中的股票代码
        stock_code = request.args.get('stock_code', '002155')
        print(f"🔍 获取当前策略状态... 股票代码: {stock_code}")
        print(f"📊 系统数据状态: data={system.data is not None and not system.data.empty if system.data is not None else 'None'}")
        
        # 检查是否需要重新准备数据
        need_refresh = False
        if system.data is None or system.data.empty:
            print(f"⚠️ 系统数据为空，需要准备股票{stock_code}数据...")
            need_refresh = True
        else:
            # 检查当前数据是否匹配请求的股票代码
            # 这里我们简化处理：如果用户切换了股票，就重新获取数据
            print(f"✅ 系统已有数据，形状: {system.data.shape}")
            print(f"📊 最新收盘价: {system.data['收盘'].iloc[-1]}")
            # 为了确保数据是最新的，我们总是重新获取数据
            need_refresh = True
        
        if need_refresh:
            print(f"🔄 准备股票{stock_code}数据...")
            if system.prepare_data(6, stock_code):
                print("✅ 数据准备成功")
                print(f"📊 准备后的数据形状: {system.data.shape}")
                print(f"📊 准备后的最新收盘价: {system.data['收盘'].iloc[-1]}")
            else:
                print("❌ 数据准备失败，返回错误状态")
                return jsonify({
                    'error': f'无法获取股票{stock_code}数据，请检查股票代码或网络连接',
                    'current_price': -1,
                    'stock_change_rate': -1,
                    'gold_price': -1,
                    'gold_change_rate': -1,
                    'position': {'has_position': False},
                    'trade_count': 0,
                    'base_investment': BASE_INVESTMENT,
                    'stop_loss_rate': STOP_LOSS_RATE,
                    'profit_take_rate': PROFIT_TAKE_RATE
                })
        
        # 调用业务逻辑层获取状态
        status = system.get_strategy_status()
        print(f"📊 业务逻辑层返回状态: {status}")
        
        if status is None:
            print("⚠️ 业务逻辑层返回None，使用默认状态")
            # 如果没有数据，返回默认状态
            return jsonify({
                'current_price': 14.5,
                'stock_change_rate': 0.0,
                'gold_price': 2000.0,
                'gold_change_rate': 0.0,
                'position': {'has_position': False},
                'trade_count': 0,
                'base_investment': BASE_INVESTMENT,
                'stop_loss_rate': STOP_LOSS_RATE,
                'profit_take_rate': PROFIT_TAKE_RATE
            })
        
        # 检查关键数据是否有效
        if status.get('current_price', 0) == 0:
            print("⚠️ 当前股价为0，使用默认值")
            status['current_price'] = 14.5
            status['stock_change_rate'] = 0.0
        
        # 处理NaN值，确保JSON序列化正常
        def clean_nan(value):
            """清理NaN值，替换为0或默认值"""
            import math
            if isinstance(value, float) and math.isnan(value):
                return 0.0
            return value
        
        # 清理所有可能包含NaN的值
        cleaned_status = {
            'current_price': clean_nan(status['current_price']),
            'stock_change_rate': clean_nan(status['stock_change_rate']),
            'gold_price': clean_nan(status['gold_price']),
            'gold_change_rate': clean_nan(status['gold_change_rate']),
            'trade_count': status['trade_count'],
            'base_investment': status['base_investment'],
            'stop_loss_rate': status['stop_loss_rate'],
            'profit_take_rate': status['profit_take_rate']
        }
        
        # 计算持仓状态
        position_info = {}
        if system.current_position:
            buy_price = clean_nan(system.current_position['buy_price'])
            current_price = clean_nan(status['current_price'])
            current_profit_rate = clean_nan((current_price - buy_price) / buy_price if buy_price != 0 else 0.0)
            
            position_info = {
                'has_position': True,
                'buy_price': buy_price,
                'shares': clean_nan(system.current_position['shares']),
                'amount': clean_nan(system.current_position.get('amount', 0)),
                'current_profit_rate': current_profit_rate,
                'max_profit_rate': clean_nan(system.current_position.get('max_profit_rate', 0))
            }
        else:
            position_info = {'has_position': False}
        
        cleaned_status['position'] = position_info
        
        print(f"清理后的状态数据: {cleaned_status}")
        return jsonify(cleaned_status)
        
    except Exception as e:
        print(f"获取状态失败: {str(e)}")
        return jsonify({
            'error': f'获取状态失败: {str(e)}'
        })

@app.route('/api/trade_history')
def get_trade_history():
    """获取交易历史"""
    return jsonify(system.trade_history)

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
        
        # 获取策略参数
        base_investment = data.get('base_investment', 10000)
        stop_loss_rate = data.get('stop_loss_rate', 0.10)
        max_profit_rate = data.get('max_profit_rate', 0.05)
        profit_callback_rate = data.get('profit_callback_rate', 0.01)
        stock_code = data.get('stock_code', '002155')
        strategy_mode = data.get('strategy_mode', 'improved')
        
        # 获取高级参数
        min_gold_change = data.get('min_gold_change', 2.0) / 100  # 转换为小数
        min_buy_amount = data.get('min_buy_amount', 1000)
        transaction_cost_rate = data.get('transaction_cost_rate', 0.1) / 100  # 转换为小数
        
        print(f"执行策略参数:")
        print(f"  策略模式: {strategy_mode}")
        print(f"  基础投资: {base_investment}元")
        print(f"  止损率: {stop_loss_rate*100}%")
        print(f"  最大盈利率: {max_profit_rate*100}%")
        print(f"  盈利回调率: {profit_callback_rate*100}%")
        print(f"  最小金价涨幅阈值: {min_gold_change*100}%")
        print(f"  最小买入金额: {min_buy_amount}元")
        print(f"  交易成本率: {transaction_cost_rate*100}%")
        print(f"  股票代码: {stock_code}")
        
        if strategy_mode == 'improved':
            # 使用改进版策略
            from trading_strategy_improved import ImprovedGoldTradingStrategy
            strategy = ImprovedGoldTradingStrategy(
                base_investment=base_investment,
                stop_loss_rate=stop_loss_rate,
                profit_callback_rate=profit_callback_rate,
                max_profit_rate=max_profit_rate,
                min_gold_change=min_gold_change,
                min_buy_amount=min_buy_amount,
                transaction_cost_rate=transaction_cost_rate
            )
            
            # 执行改进版策略
            result = strategy.execute_strategy_improved(stock_code)
            strategy_summary = strategy.get_strategy_summary_improved()
        else:
            # 使用基础版策略
            from trading_strategy import GoldTradingStrategy
            strategy = GoldTradingStrategy(
                base_investment=base_investment,
                stop_loss_rate=stop_loss_rate,
                profit_callback_rate=profit_callback_rate,
                max_profit_rate=max_profit_rate
            )
            
            # 执行基础版策略
            result = strategy.execute_strategy(stock_code)
            strategy_summary = strategy.get_strategy_summary()
        
        return jsonify({
            'success': True,
            'strategy_result': result,
            'strategy_summary': strategy_summary,
            'strategy_mode': strategy_mode,
            'message': '策略执行成功'
        })
        
    except Exception as e:
        print(f"策略执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'策略执行失败: {str(e)}'
        })

@app.route('/api/strategy_stats')
def get_strategy_stats():
    """获取策略统计信息"""
    try:
        # 这里可以从数据库或文件读取历史统计
        # 暂时返回模拟数据
        return jsonify({
            'total_trades': 0,
            'total_profit': 0.0,
            'win_trades': 0,
            'win_rate': 0.0
        })
    except Exception as e:
        return jsonify({
            'error': f'获取策略统计失败: {str(e)}'
        })

@app.route('/api/strategy_trades')
def get_strategy_trades():
    """获取策略交易历史"""
    try:
        # 这里可以从数据库或文件读取交易历史
        # 暂时返回空列表
        return jsonify({
            'trades': []
        })
    except Exception as e:
        return jsonify({
            'error': f'获取交易历史失败: {str(e)}'
        })
