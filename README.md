# QMTPython 项目说明书 📋

## 📖 项目简介

**QMTPython** 是一个基于迅投QMT平台的股票数据获取、处理和Web服务系统。该项目专注于为个人投资者提供便捷的股票数据访问和分析工具。

### 🎯 核心价值
- **数据获取**: 自动化获取实时股价和历史K线数据
- **数据服务**: 提供HTTP API和Web界面访问股票数据  
- **格式转换**: 支持CSV和JSON双格式数据输出
- **安全访问**: 多种认证方式保护数据安全

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────┐
│               Web界面 & API接口                │
├─────────────────────────────────────────────┤
│               Flask Web服务器                 │
├─────────────────────────────────────────────┤
│         数据处理层 (Pandas + 业务逻辑)          │
├─────────────────────────────────────────────┤
│       数据获取层 (QMT API + 文件系统)           │
└─────────────────────────────────────────────┘
```

## 📂 核心模块

### 1. 数据获取模块
- **RealTimePrice.py**: 实时股价获取和监控
- **AllKLineData.py**: 多周期K线数据获取
- 支持周期: 1m, 5m, 15m, 30m, 60m, 1d, 1w, 1month

### 2. Web服务模块  
- **WebServer.py**: Flask Web服务器
- RESTful API设计
- 多种认证支持（Bearer Token、Query参数、Session）
- 美观的Web管理界面

### 3. 自动化脚本
- 数据更新bat脚本
- 服务启动和监控脚本  
- 股票代码测试工具

## 🔧 技术栈

| 层级 | 技术 | 版本要求 | 用途 |
|------|------|----------|------|
| 后端 | Python | 3.7+ | 核心开发语言 |
| Web框架 | Flask | 2.x | HTTP服务和API |
| 数据处理 | Pandas | 1.x | CSV/JSON数据处理 |
| 跨域支持 | Flask-CORS | - | API跨域访问 |
| 量化接口 | QMT API | - | 股票数据获取 |
| 前端 | HTML/CSS/JS | - | Web界面（内嵌） |

## 📊 支持的数据类型

### K线数据字段
- **基础字段**: 开盘价、最高价、最低价、收盘价
- **交易量**: 成交量、成交额
- **时间信息**: 交易日期、时间戳
- **技术指标**: (可扩展)

### 实时股价字段  
- **价格信息**: 当前价、涨跌额、涨跌幅
- **交易数据**: 成交量、成交额、换手率
- **盘口数据**: 买卖五档、委比

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <项目地址>
cd QMTPython

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务
```bash
# 基础启动
python WebServer.py

# 带认证启动  
python WebServer.py --api-key your-secret-key

# 自定义端口
python WebServer.py --port 9999
```

### 3. 访问服务
- **Web界面**: http://localhost:8888
- **API文档**: http://localhost:8888/api/files
- **文件下载**: http://localhost:8888/api/download/filename

## 🔐 认证方式

### 1. Bearer Token
```bash
curl -H "Authorization: Bearer your-key" http://localhost:8888/api/files
```

### 2. Query参数  
```bash
curl http://localhost:8888/api/files?api_key=your-key
```

### 3. Web登录
浏览器访问主页，输入API密钥登录

## 📊 API接口示例

### 获取文件列表
```http
GET /api/files
Response: {
  "success": true,
  "count": 25,
  "files": [...]
}
```

### 获取K线数据
```http
GET /api/files/000001_SH_1d_front_kline.csv?format=json&limit=100
Response: {
  "success": true,
  "total_rows": 1500,
  "returned_rows": 100,
  "data": [...]
}
```

## 📈 使用场景

### 个人投资者
- 查看股票历史K线数据
- 监控实时股价变化
- 导出数据进行分析

### 量化研究
- 策略回测数据源
- 技术指标计算基础
- 自动化交易系统对接

### 学习教育
- Python金融编程学习
- Web API开发实践
- 数据处理技能训练

## 🎯 扩展方向

### 短期扩展
- [ ] 增加更多股票代码支持
- [ ] WebSocket实时数据推送
- [ ] 移动端界面优化
- [ ] Docker容器化部署

### 长期规划
- [ ] 技术指标计算模块
- [ ] 策略回测系统
- [ ] 多用户权限管理
- [ ] 数据库存储优化

## 📝 许可证与支持

### 开源许可
本项目采用 MIT 许可证，允许自由使用和修改。

### 技术支持
- 项目文档: `docs/` 目录
- 问题反馈: GitHub Issues
- 使用交流: 项目讨论区

### 免责声明
本项目仅供学习和研究使用，不构成投资建议。使用者需自行承担投资风险。

---

**最后更新**: 2024年当前时间  
**项目状态**: 开发中 (v1.0)  
**维护者**: 项目开发团队 