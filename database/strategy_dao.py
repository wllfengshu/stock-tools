#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
数据库操作类
负责MySQL数据库的连接和CRUD操作
"""

import pymysql
import pymysql.cursors
from typing import Optional
from datetime import datetime
import logging
import sys

try:
    from .table_entity import ToolStockToolsGold
except ImportError:
    # 当直接运行此文件时，使用绝对导入
    from table_entity import ToolStockToolsGold

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('database.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class StrategyDAO:
    """量化交易策略数据访问对象"""
    
    def __init__(self, host='localhost', user='root', password='root', database='wisehair', port=3306):
        """初始化数据库连接参数"""
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None
        self.cursor = None
        
        logger.info(f"数据库配置: {host}:{port}, 用户: {user}, 数据库: {database}")
    
    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            logger.info("正在连接数据库...")
            logger.info(f"连接参数: host={self.host}, port={self.port}, user={self.user}, database={self.database}")
            
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            self.cursor = self.connection.cursor()
            logger.info("数据库连接成功")
            return True
                
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
    
    def disconnect(self) -> None:
        """关闭数据库连接"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {e}")
    
    def save_user_info(self, strategy_data: ToolStockToolsGold) -> bool:
        """保存用户信息"""
        try:
            if not self.connect():
                return False
            
            # 检查记录是否存在
            self.cursor.execute(
                "SELECT id FROM tool_stock_tools_gold WHERE tool_stock_tools_gold_id = %s",
                (strategy_data.tool_stock_tools_gold_id,)
            )
            existing = self.cursor.fetchone()
            
            if existing:
                # 更新现有记录
                sql = """
                UPDATE tool_stock_tools_gold SET
                    total_cost = %s, total_shares = %s, history_max_profit = %s, last_total_profit = %s,
                    position = %s, trade_history = %s, last_trade_date = %s, update_time = %s
                WHERE tool_stock_tools_gold_id = %s
                """
                self.cursor.execute(sql, (
                    strategy_data.total_cost,
                    strategy_data.total_shares,
                    strategy_data.history_max_profit,
                    strategy_data.last_total_profit,
                    strategy_data.position,
                    strategy_data.trade_history,
                    strategy_data.last_trade_date,
                    datetime.now(),
                    strategy_data.tool_stock_tools_gold_id
                ))
            else:
                # 插入新记录
                sql = """
                INSERT INTO tool_stock_tools_gold 
                (tool_stock_tools_gold_id, total_cost, total_shares, history_max_profit, last_total_profit, 
                 position, trade_history, last_trade_date, create_time, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                self.cursor.execute(sql, (
                    strategy_data.tool_stock_tools_gold_id,
                    strategy_data.total_cost,
                    strategy_data.total_shares,
                    strategy_data.history_max_profit,
                    strategy_data.last_total_profit,
                    strategy_data.position,
                    strategy_data.trade_history,
                    strategy_data.last_trade_date,
                    datetime.now(),
                    datetime.now()
                ))
            
            self.connection.commit()
            logger.info("策略状态保存成功")
            return True
            
        except Exception as e:
            logger.error(f"保存策略状态失败: {e}")
            return False
        finally:
            self.disconnect()
    
    def load_user_info_by_id(self, tool_stock_tools_gold_id: int) -> Optional[ToolStockToolsGold]:
        """按照用户id加载用户信息"""
        try:
            if not self.connect():
                return None
            
            self.cursor.execute(
                "SELECT * FROM tool_stock_tools_gold WHERE tool_stock_tools_gold_id = %s",
                (tool_stock_tools_gold_id,)
            )
            result = self.cursor.fetchone()
            
            if result:
                strategy_data = ToolStockToolsGold(
                    tool_stock_tools_gold_id=result['tool_stock_tools_gold_id'],
                    auth=result.get('auth', ''),
                    expire_time=result.get('expire_time'),
                    deleted=result.get('deleted', 'F'),
                    updater=result.get('updater', ''),
                    creator=result.get('creator', ''),
                    update_time=result.get('update_time'),
                    create_time=result.get('create_time'),
                    start_time=result.get('start_time'),
                    end_time=result.get('end_time'),
                    switched=result.get('switched', ''),
                    total_cost=result.get('total_cost', 0.0),
                    total_shares=result.get('total_shares', 0),
                    history_max_profit=result.get('history_max_profit', 0.0),
                    last_total_profit=result.get('last_total_profit', 0.0),
                    position=result.get('position', '{}'),
                    trade_history=result.get('trade_history', '[]'),
                    last_trade_date=result.get('last_trade_date')
                )
                logger.info("用户信息加载成功")
                return strategy_data
            else:
                logger.info("未找到用户信息记录")
                return None
                
        except Exception as e:
            logger.error(f"加载策略状态失败: {e}")
            return None
        finally:
            self.disconnect()

    def load_user_info_by_auth(self, auth: str) -> Optional[ToolStockToolsGold]:
        """按照auth加载用户信息"""
        try:
            if not self.connect():
                return None
            
            self.cursor.execute(
                "SELECT * FROM tool_stock_tools_gold WHERE auth = %s",
                (auth,)
            )
            result = self.cursor.fetchone()
            
            if result:
                strategy_data = ToolStockToolsGold(
                    tool_stock_tools_gold_id=result['tool_stock_tools_gold_id'],
                    auth=result.get('auth', ''),
                    expire_time=result.get('expire_time'),
                    deleted=result.get('deleted', 'F'),
                    updater=result.get('updater', ''),
                    creator=result.get('creator', ''),
                    update_time=result.get('update_time'),
                    create_time=result.get('create_time'),
                    start_time=result.get('start_time'),
                    end_time=result.get('end_time'),
                    switched=result.get('switched', ''),
                    total_cost=result.get('total_cost', 0.0),
                    total_shares=result.get('total_shares', 0),
                    history_max_profit=result.get('history_max_profit', 0.0),
                    last_total_profit=result.get('last_total_profit', 0.0),
                    position=result.get('position', '{}'),
                    trade_history=result.get('trade_history', '[]'),
                    last_trade_date=result.get('last_trade_date')
                )
                logger.info("用户信息加载成功")
                return strategy_data
            else:
                logger.info("未找到用户信息记录")
                return None
                
        except Exception as e:
            logger.error(f"加载用户信息失败: {e}")
            return None
        finally:
            self.disconnect()

# 使用示例
if __name__ == "__main__":
    import os
    import sys
    
    # 添加父目录到Python路径，以便导入其他模块
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # 测试数据库连接
    dao = StrategyDAO()
    
    print("测试数据库连接...")
    if dao.connect():
        print("✅ 数据库连接成功")
        # print(dao.load_user_info_by_id(100001))
        print(dao.load_user_info_by_auth('abcdefaddd'))
    else:
        print("❌ 数据库连接失败")
        print("请检查:")
        print("1. MySQL服务是否启动")
        print("2. 数据库连接参数是否正确")
        print("3. 数据库'wisehair'是否存在")