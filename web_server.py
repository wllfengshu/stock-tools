#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
黄金板块交易系统Web服务器
提供HTML界面进行时间范围查询和股票分析
"""

from flask import Flask, render_template, request, jsonify, send_file

# 导入系统
from advanced_interactive_system_professional import ProfessionalInteractiveSystem

# 配置参数
TARGET_STOCK_NAME = "湖南黄金"
BASE_INVESTMENT = 10000
STOP_LOSS_RATE = 0.05
PROFIT_TAKE_RATE = 0.15
import plotly.graph_objects as go
from plotly.subplots import make_subplots

app = Flask(__name__, static_folder='templates', static_url_path='')

# 全局系统实例
system = ProfessionalInteractiveSystem()

def create_chart_data(data, stock_name, gold_data=None):
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
        
        # 使用业务逻辑层准备数据
        print("Web服务器：调用业务逻辑层准备数据...")
        print(f"请求参数: months={months}, stock_code={stock_code}, stock_name={stock_name}")
        
        # 调用业务逻辑层
        if not system.prepare_data(months):
            return jsonify({
                'success': False,
                'message': '无法获取股票数据'
            })
        
        print(f"业务逻辑层数据准备完成，形状: {system.data.shape}")
        
        # 创建图表数据 - 只负责图表展示
        chart_data = create_chart_data(system.data, stock_name, system.gold_data)
        
        return jsonify({
            'success': True,
            'message': '分析完成',
            'chart_data': chart_data,
            'stock_name': stock_name,
            'months': months
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'分析失败: {str(e)}'
        })

@app.route('/api/current_status')
def get_current_status():
    """获取当前策略状态 - 调用业务逻辑层"""
    try:
        # 调用业务逻辑层获取状态
        status = system.get_strategy_status()
        
        if status is None:
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
        
        # 计算持仓状态
        position_info = {}
        if system.current_position:
            buy_price = system.current_position['buy_price']
            current_profit_rate = (status['current_price'] - buy_price) / buy_price
            position_info = {
                'has_position': True,
                'buy_price': buy_price,
                'shares': system.current_position['shares'],
                'amount': system.current_position['amount'],
                'current_profit_rate': current_profit_rate,
                'max_profit_rate': system.current_position['max_profit_rate']
            }
        else:
            position_info = {'has_position': False}
        
        return jsonify({
            'current_price': status['current_price'],
            'stock_change_rate': status['stock_change_rate'],
            'gold_price': status['gold_price'],
            'gold_change_rate': status['gold_change_rate'],
            'position': position_info,
            'trade_count': status['trade_count'],
            'base_investment': status['base_investment'],
            'stop_loss_rate': status['stop_loss_rate'],
            'profit_take_rate': status['profit_take_rate']
        })
        
    except Exception as e:
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
