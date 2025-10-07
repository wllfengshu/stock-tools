-- 量化交易系统数据库表结构
-- 基于 tool_stock_tools_gold 表，支持多用户量化交易策略

-- 1. 创建基础表（如果不存在）
DROP TABLE IF EXISTS `tool_stock_tools_gold`;
CREATE TABLE `tool_stock_tools_gold`  (
  `tool_stock_tools_gold_id` bigint UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'ID，自增，用户唯一标识',
  `auth` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL DEFAULT '' COMMENT '授权码',
  `expire_time` timestamp NOT NULL COMMENT '账号过期时间',
  `deleted` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'F' COMMENT '已删除（T删除，F未删除）',
  `updater` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '更新者',
  `creator` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '创建者',
  `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `start_time` time NOT NULL COMMENT '开始时间',
  `end_time` time NOT NULL COMMENT '结束时间',
  `switched` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT '开关（T开；F关）',
  `total_cost` decimal(15, 2) NOT NULL DEFAULT 0.00 COMMENT '投资成本，累计投入的资金总额（单位：元）',
  `total_shares` int NOT NULL DEFAULT 0 COMMENT '总持股数，当前持有的股票数量（单位：股）',
  `history_max_profit` decimal(15, 2) NOT NULL DEFAULT 0.00 COMMENT '历史最大盈利，曾经达到过的最大盈利金额（单位：元）',
  `last_total_profit` decimal(15, 2) NOT NULL DEFAULT 0.00 COMMENT '上次总盈利，最后一次交易的总盈利（单位：元）',
  `position` json NOT NULL COMMENT '持仓信息JSON，包含has_position、buy_price、shares、amount、current_profit_rate、max_profit_rate等字段',
  `trade_history` json NOT NULL COMMENT '交易历史JSON数组，记录所有买卖交易的详细信息',
  `last_trade_date` datetime NOT NULL DEFAULT '2001-01-01 00:00:00' COMMENT '最后交易日期，用于计算投资天数和年化收益率',
  PRIMARY KEY (`tool_stock_tools_gold_id`) USING BTREE,
  UNIQUE INDEX `idx_auth`(`auth` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 100001 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_bin ROW_FORMAT = Dynamic;

-- 2. 插入默认用户数据
-- 创建默认用户策略记录，用于系统初始化
INSERT INTO `tool_stock_tools_gold` (
    `auth`,                    -- 用户认证标识
    `expire_time`,             -- 账号过期时间
    `total_cost`,              -- 投资成本
    `total_shares`,            -- 持股数量
    `history_max_profit`,      -- 历史最大盈利
    `last_total_profit`,       -- 上次总盈利
    `position`,                -- 持仓信息JSON
    `trade_history`,           -- 交易历史JSON
    `last_trade_date`,         -- 最后交易日期
    `updater`,                 -- 更新者
    `creator`,                 -- 创建者
    `deleted`,                 -- 删除标志
    `switched`,                -- 开关状态
    `start_time`,              -- 开始时间
    `end_time`                 -- 结束时间
) VALUES (
    'default_user',          -- 默认用户认证
    '2030-12-31 23:59:59',  -- 账号过期时间（10年后）
    30000.00,               -- 初始投资成本3万元
    210,                    -- 初始持股210股
    0.00,                   -- 历史最大盈利为0
    0.00,                   -- 上次总盈利为0
    JSON_OBJECT(             -- 持仓信息JSON对象
        'has_position', false,           -- 当前无持仓
        'buy_price', 0,                  -- 买入价格为0
        'shares', 0,                     -- 持仓股数为0
        'amount', 0,                     -- 持仓金额为0
        'current_profit_rate', 0,        -- 当前盈利率为0
        'max_profit_rate', 0             -- 最大盈利率为0
    ),
    JSON_ARRAY(),            -- 交易历史为空数组
    '2025-10-05 00:00:00',  -- 最后交易日期
    'system',               -- 系统创建
    'system',               -- 系统创建
    'F',                    -- 未删除
    'T',                    -- 功能开启
    '00:00:00',             -- 开始时间
    '23:59:59'              -- 结束时间
) ON DUPLICATE KEY UPDATE    -- 如果用户已存在，则更新数据
    `total_cost` = VALUES(`total_cost`),     -- 更新投资成本
    `total_shares` = VALUES(`total_shares`), -- 更新持股数量
    `update_time` = NOW();                 -- 更新修改时间


-- ========================================
-- 使用说明
-- ========================================

-- 1. 执行建表SQL
-- mysql -u root -p wisehair < database/create_table.sql

-- 2. 查看表结构
-- DESCRIBE tool_stock_tools_gold;

-- 3. 查看所有索引
-- SHOW INDEX FROM tool_stock_tools_gold;

-- 4. 查看JSON字段内容
-- SELECT auth, JSON_EXTRACT(position, '$.has_position') as has_position FROM tool_stock_tools_gold;
-- SELECT auth, JSON_LENGTH(trade_history) as trade_count FROM tool_stock_tools_gold;

-- 5. 查询用户策略数据
-- SELECT * FROM `tool_stock_tools_gold` WHERE `auth` = 'default_user' AND `deleted` = 'F';

-- 6. 更新用户策略数据
-- UPDATE `tool_stock_tools_gold` 
-- SET `total_cost` = 35000, `total_shares` = 250, `position` = JSON_OBJECT('has_position', true, 'buy_price', 22.5)
-- WHERE `auth` = 'default_user';

-- 7. 添加交易记录
-- UPDATE `tool_stock_tools_gold` 
-- SET `trade_history` = JSON_ARRAY_APPEND(`trade_history`, '$', JSON_OBJECT('date', '2025-01-15', 'type', 'buy', 'price', 22.5, 'shares', 100))
-- WHERE `auth` = 'default_user';

-- 8. 查询JSON字段内容
-- SELECT `auth`, JSON_EXTRACT(`position`, '$.has_position') as has_position FROM `tool_stock_tools_gold`;
-- SELECT `auth`, JSON_LENGTH(`trade_history`) as trade_count FROM `tool_stock_tools_gold`;

-- 9. 更新账号过期时间
-- UPDATE `tool_stock_tools_gold` 
-- SET `expire_time` = '2035-12-31 23:59:59' 
-- WHERE `auth` = 'default_user';

-- 注意：所有业务逻辑计算都在Python代码中实现，MySQL只负责数据存储
