from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional, Dict, Any
import json
import logging

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class ToolStockToolsGold:
    """工具库存黄金工具实体类
    
    对应数据库表：tool_stock_tools_gold
    用于管理黄金工具的库存信息和访问权限控制
    """
    
    # ID字段，主键，自增（这个字段也就是用户ID）
    tool_stock_tools_gold_id: Optional[int] = field(default=None, metadata={"comment": "ID"})
    
    # 请求凭证，唯一索引
    auth: str = field(default='', metadata={"comment": "请求凭证"})
    
    # 过期时间
    expire_time: Optional[datetime] = field(default=None, metadata={"comment": "过期时间"})
    
    # 删除标志
    deleted: str = field(default='F', metadata={"comment": "已删除（T删除，F未删除）"})
    
    # 更新者信息
    updater: str = field(default='', metadata={"comment": "更新者"})
    
    # 创建者信息
    creator: str = field(default='', metadata={"comment": "创建者"})
    
    # 更新时间，自动更新
    update_time: Optional[datetime] = field(default=None, metadata={"comment": "更新时间"})
    
    # 创建时间，默认当前时间
    create_time: Optional[datetime] = field(default=None, metadata={"comment": "创建时间"})
    
    # 每天开始时间
    start_time: Optional[time] = field(default=None, metadata={"comment": "每天开始时间"})
    
    # 每天结束时间
    end_time: Optional[time] = field(default=None, metadata={"comment": "每天结束时间"})
    
    # 开关状态
    switched: str = field(default='', metadata={"comment": "开关（T开；F关）"})
    
    # 量化交易策略相关字段
    # 投资成本（累计投入资金）
    total_cost: float = field(default=0.0, metadata={"comment": "投资成本"})
    
    # 总持股数
    total_shares: int = field(default=0, metadata={"comment": "总持股数"})
    
    # 历史最大盈利
    history_max_profit: float = field(default=0.0, metadata={"comment": "历史最大盈利"})
    
    # 上次总盈利
    last_total_profit: float = field(default=0.0, metadata={"comment": "上次总盈利"})
    
    # 持仓信息（JSON格式存储）
    position: str = field(default='{}', metadata={"comment": "持仓信息JSON"})
    
    # 交易历史（JSON格式存储）
    trade_history: str = field(default='[]', metadata={"comment": "交易历史JSON"})
    
    # 最后交易日期
    last_trade_date: Optional[datetime] = field(default=None, metadata={"comment": "最后交易日期"})
    
    # 业务逻辑方法
    def is_deleted(self) -> bool:
        """检查是否已删除"""
        return self.deleted == 'T'
    
    def is_switched_on(self) -> bool:
        """检查开关是否打开"""
        return self.switched == 'T'
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        if not self.expire_time:
            return False
        return datetime.now() > self.expire_time
    
    def is_active(self) -> bool:
        """检查是否有效（未删除且未过期）"""
        return not self.is_deleted() and not self.is_expired()
    
    # 策略相关业务逻辑方法
    def get_position_dict(self) -> Dict[str, Any]:
        """获取持仓信息字典"""
        try:
            return json.loads(self.position) if self.position else {}
        except json.JSONDecodeError as e:
            logger.warning(f"解析持仓信息JSON失败: {e}")
            return {}
    
    def set_position_dict(self, position_dict: Dict[str, Any]) -> None:
        """设置持仓信息字典"""
        self.position = json.dumps(position_dict, ensure_ascii=False)
    
    def get_trade_history_list(self) -> list:
        """获取交易历史列表"""
        try:
            return json.loads(self.trade_history) if self.trade_history else []
        except json.JSONDecodeError as e:
            logger.warning(f"解析交易历史JSON失败: {e}")
            return []
    
    def set_trade_history_list(self, trade_history_list: list) -> None:
        """设置交易历史列表"""
        self.trade_history = json.dumps(trade_history_list, ensure_ascii=False)
    
    def has_position(self) -> bool:
        """检查是否有持仓"""
        position_dict = self.get_position_dict()
        return position_dict.get('has_position', False)
    
    def get_current_profit_rate(self) -> float:
        """获取当前盈利率"""
        position_dict = self.get_position_dict()
        return position_dict.get('current_profit_rate', 0.0)
    
    def get_max_profit_rate(self) -> float:
        """获取最大盈利率"""
        position_dict = self.get_position_dict()
        return position_dict.get('max_profit_rate', 0.0)

