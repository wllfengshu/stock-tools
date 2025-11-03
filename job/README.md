# 股票管理
这是一个个人的股票管理项目（模块化重构版）
我提供：当前日期、当前股价数据、指标信号，后期可能还会增加政策新闻等，把这些数据全部给到ai，让它给出指导性意见，比如加仓、减仓等等

## 总体架构
按照“配置 -> 数据获取 -> 指标计算 -> 报告生成 -> AI调用 -> 消息发送 -> 调度”的流水线设计，支持后期快速扩展。

```
config.py            配置：股票池、指标默认参数、运行周期
data_fetcher.py      数据获取：封装 AKShare，统一输出标准 OHLCV(DataFrame)
indicator_calculator.py 指标计算：KDJ / MACD / RSI（可扩展）
report_generator.py  报告生成：聚合价格 + 指标信号 -> 结构化报告
ai_client.py         AI接口占位：格式化 Prompt、模拟返回
message_sender.py    消息发送占位：后续接入公众号/企业微信
scheduler.py         调度：按照配置时间循环处理股票列表
```

## 功能说明（流水线）
1. 配置模块：提供一个股票列表 + 指标默认参数
```python
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
```
2. 调度：每天早上 09:00 和下午 14:30 依次循环处理股票池：
   - 数据获取：近 N 个月历史 + 简单实时价
   - 指标计算：KDJ 金叉、MACD 金叉、RSI 超卖
   - （预留）资金流、新闻、政策利好
   - 生成结构化报告 -> AI 接口 -> 消息发送
3. 交易策略与回测：保留现有 `trading_strategy.py`（可后续与指标模块融合）
4. Web层：保留现有 `web_server.py`，可逐步替换为对新模块的调用

## 模块设计与扩展点
- 配置：新增板块 / 股票，只修改 `config.py`
- 数据获取：新增数据源（外汇、期货、指数）只加方法，不影响其他层
- 指标计算：新增指标例如 BOLL、ATR，只需增加 calc_xxx 并在 `calculate_indicators` 注册
- 报告生成：可以拼接更多信号（如资金流、新闻情绪）
- AI接口：后续对接真实模型，替换 `AIClient.call`
- 消息发送：实现公众号/企业微信推送，替换 `MessageSender.send`
- 调度：可升级为 APScheduler / Celery，支持并发、失败重试

## 快速开始
```bash
pip install -r requirements.txt
python start.py        # 启动 Web 服务 (默认端口 3010)
python -c "from scheduler import Scheduler; Scheduler().loop()"  # 启动调度循环
```

## 指标输出示例（signals 字段）
```json
{
  "signals": {
    "kdj_golden_cross": true,
    "macd_golden_cross": false,
    "rsi_oversold": false
  },
  "summary": {
    "signal_count": 1,
    "active_signals": ["kdj_golden_cross"],
    "suggestion": "检测到多头信号: kdj_golden_cross，可考虑小仓试探。"
  }
}
```

## 后续规划
- [ ] 接入资金流向数据接口
- [ ] 接入资讯 / 公告 / 政策情绪分析
- [ ] 增强 AI 生成自然语言报告
- [ ] 指标参数可视化配置（前端界面）
- [ ] 策略与指标融合，形成条件触发交易
- [ ] 统一缓存与重试机制
- [ ] 完整的单元测试覆盖
