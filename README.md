# 股票分析系统

一个功能完整的量化股票分析系统，支持技术分析、战法匹配、概率预测、海龟交易法则和历史回测。

## 功能特性

### 1. 数据集成
- ✅ Tushare数据同步
- ✅ 沪深300成分股数据
- ✅ 日线/周线/月线K线数据
- ✅ 实时数据更新
- ✅ 自选股票管理

### 2. 技术分析
- ✅ 多周期趋势分析（短/中/长期）
- ✅ 移动平均线（MA5/10/20/60/120/250）
- ✅ MACD指标
- ✅ RSI指标
- ✅ KDJ指标
- ✅ 布林带
- ✅ ATR指标
- ✅ 支撑阻力位分析

### 3. 战法匹配系统
- ✅ 金叉/死叉战法
- ✅ MACD背离战法
- ✅ 突破/回调战法
- ✅ 量价背离战法
- ✅ RSI反转战法
- ✅ 布林带挤压战法
- ✅ 经典形态识别（头肩顶/底、双底、三角形、旗形）

### 4. 走势概率预测
- ✅ 上涨/下跌/横盘概率预测
- ✅ 基于技术指标的概率计算
- ✅ 基于历史模式的概率计算
- ✅ 基于波动率的概率计算
- ✅ 目标价位预测

### 5. 海龟交易法则
- ✅ 唐奇安通道突破系统
- ✅ ATR仓位管理
- ✅ 动态止盈止损
- ✅ 加仓点位计算
- ✅ 完整回测支持

### 6. 买卖建议
- ✅ 综合评分系统
- ✅ 多档入场价位建议（激进/稳健/保守）
- ✅ 止盈止损评估
- ✅ 仓位管理建议
- ✅ 风险提示

### 7. 历史回测
- ✅ 多策略回测对比
- ✅ 资金曲线展示
- ✅ 收益率、胜率、最大回撤统计
- ✅ 交易记录明细
- ✅ 策略绩效对比

### 8. Web界面
- ✅ 响应式设计
- ✅ 股票搜索
- ✅ K线图表展示
- ✅ 分析结果可视化
- ✅ 自选股票管理

### 9. API接口
- ✅ RESTful API
- ✅ 股票列表查询
- ✅ K线数据获取
- ✅ 实时分析接口
- ✅ 回测接口

### 10. 定时任务
- ✅ 每日收盘后自动更新数据
- ✅ 每日盘后自动分析
- ✅ 定时报告生成

## 技术栈

- **后端**: Python + Flask + SQLAlchemy
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **数据分析**: Pandas, NumPy
- **可视化**: Plotly
- **前端**: HTML + JavaScript + Bootstrap 5
- **数据源**: Tushare Pro API

## 安装部署

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置Tushare Token

在 `config.py` 中配置你的Tushare Token：

```python
TUSHARE_TOKEN = "your_token_here"
```

### 3. 初始化数据库

```bash
python run.py init
```

### 4. 同步数据

```bash
# 同步沪深300股票数据
python run.py sync --pool hs300

# 同步全部A股数据
python run.py sync --pool all
```

### 5. 启动服务器

```bash
# 生产模式
python run.py server

# 调试模式
python run.py server --debug

# 指定端口
python run.py server --port 8080
```

访问 http://localhost:5000 即可使用Web界面。

## 使用指南

### Web界面

1. **首页**: 查看系统状态、今日买入信号、快速搜索
2. **股票列表**: 浏览所有股票，添加自选
3. **自选股票**: 管理自选列表，批量分析
4. **分析页面**: 查看详细技术分析、战法匹配、概率预测
5. **回测页面**: 对股票进行策略回测和对比

### 命令行工具

```bash
# 分析单个股票
python run.py analyze --code 000001.SZ

# 回测股票
python run.py backtest --code 000001.SZ --strategy turtle_trading

# 生成每日报告
python run.py report
```

### API接口

#### 获取股票列表
```
GET /api/stocks?type=hs300
```

#### 搜索股票
```
GET /api/stocks/search?keyword=平安
```

#### 获取K线数据
```
GET /api/kline/000001.SZ?freq=D&limit=250
```

#### 分析股票
```
GET /api/analysis/000001.SZ
```

#### 回测股票
```
GET /api/backtest/000001.SZ?strategy=turtle_trading
```

#### 对比策略
```
GET /api/backtest/compare/000001.SZ
```

#### 同步数据
```
POST /api/sync/stocks
{"pool": "hs300"}

POST /api/sync/kline
{"ts_code": "000001.SZ", "freq": "D"}
```

#### 自选股票管理
```
POST /api/stocks/custom
{"ts_code": "000001.SZ"}

DELETE /api/stocks/custom/000001.SZ
```

## 项目结构

```
stock_analyzer/
├── app.py                 # Flask应用主文件
├── config.py             # 配置文件
├── run.py                # 启动脚本
├── requirements.txt      # 依赖列表
├── models/               # 数据库模型
│   ├── __init__.py
│   ├── stock.py
│   ├── kline.py
│   ├── analysis.py
│   └── backtest.py
├── data_sync/            # 数据同步模块
│   ├── __init__.py
│   ├── tushare_client.py
│   └── data_updater.py
├── analysis/             # 分析模块
│   ├── __init__.py
│   ├── technical_analyzer.py
│   ├── strategy_matcher.py
│   ├── probability_predictor.py
│   ├── turtle_trading.py
│   └── recommendation_engine.py
├── backtest/             # 回测模块
│   ├── __init__.py
│   └── backtest_engine.py
├── templates/            # HTML模板
│   ├── base.html
│   ├── index.html
│   ├── stocks.html
│   ├── analysis.html
│   ├── custom_stocks.html
│   └── backtest.html
└── README.md
```

## 配置说明

### config.py 配置项

```python
# Tushare API配置
TUSHARE_TOKEN = "your_token"

# 数据库配置
DATABASE_URL = "sqlite:///stock_analyzer.db"

# 数据更新频率（分钟）
UPDATE_INTERVAL_MINUTES = 5

# 分析周期配置
SHORT_TERM_DAYS = 20
MID_TERM_DAYS = 60
LONG_TERM_DAYS = 250

# 海龟交易配置
TURTLE_ENTRY_DAYS = 20
TURTLE_EXIT_DAYS = 10
TURTLE_ATR_DAYS = 20
TURTLE_RISK_PERCENT = 0.01

# API配置
API_HOST = "0.0.0.0"
API_PORT = 5000
```

## 注意事项

1. **数据限制**: Tushare免费版有API调用频率限制，请合理设置更新频率
2. **风险提示**: 本系统仅供参考，不构成投资建议
3. **数据准确性**: 请确保Tushare数据源的准确性
4. **回测局限**: 历史回测不代表未来表现

## 更新计划

- [ ] 支持更多技术指标
- [ ] 机器学习预测模型
- [ ] 实时行情推送
- [ ] 邮件/微信通知
- [ ] 多因子选股模型
- [ ] 投资组合优化
- [ ] 更多战法策略

## License

MIT License

## 联系方式

如有问题或建议，欢迎反馈！
