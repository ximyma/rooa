# 智能服务办公平台 (OOA)

基于 Flask 的企业级智能 OA 办公系统，集成 AI 辅助写作、知识管理、电子公文、档案管理、会议协同、督查督办、绩效考核等功能。

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端框架 | Flask 2.3 + SQLAlchemy 3.1 |
| 数据库 | SQLite (WAL 模式) |
| 前端 | Jinja2 + Bootstrap 5 + Chart.js |
| AI 集成 | OpenAI / DeepSeek / 硅基流动 / 本地模型 |
| 安全加固 | Fernet API Key 加密、CSRF 保护、登录限流 |
| 打包部署 | PyInstaller + Waitress |

## 功能模块

### 核心办公
- **电子公文** — 起草、审批、发送、办理、退回、撤回、归档
- **公文工作台** — 统计卡片、关键词检索、关联会议/督办事项
- **智能办公** — AI 公文写作、润色、校对、拟办意见、会议纪要
- **文档转换** — LibreOffice 无头模式转换 (Word/PDF/HTML)

### 知识管理
- **个人知识库** — 文件上传、全文搜索 (FTS5)、分类标签
- **共享知识库** — 团队协作、公开分享
- **政策文件库** — 批量上传、政策检索
- **AI 智能检索** — 向量化搜索 (sentence-transformers)

### 信息采集
- **网站爬虫** — 多层级整站爬取、关键词过滤
- **栏目监测** — 网址库管理、定时监测、逾期预警、Excel 导入导出
- **每日简报** — 自动抓取新闻、AI 生成简报、定时发送

### 档案管理
- **全宗/目录/案卷/文件** — 四级档案管理体系
- **数字化管理** — 批量上传、OCR 识别、质量检查
- **借阅管理** — 借阅/归还流程、逾期提醒
- **统计报表** — 档案数量、数字化率、借阅统计

### 办公协同
- **会议管理** — 会议室预约、会议发布、签到/请假、会议纪要
- **督查督办** — 任务下发、进度跟踪、催办、办结
- **绩效考核** — 考核周期、台账记录、成绩管理
- **工作日志** — 日志填报、上级审核、退回修改

### 系统管理
- **组织架构** — 机构/部门/岗位管理
- **用户角色** — 管理员/部门经理/信息员/普通员工
- **系统配置** — 可视化配置面板 (AI/OCR/知识库/安全)
- **操作日志** — 全局审计追踪

## 快速开始

### 环境要求

- Windows 10/11 或 Linux/macOS
- Python 3.8+
- LibreOffice (可选，用于文档转换)

### 安装运行

```bash
# 1. 克隆仓库
git clone https://gitee.com/ximyma/ooa.git
cd ooa

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量 (复制模板)
cp .env.example .env
# 编辑 .env 设置 SECRET_KEY (必须!)

# 4. 启动
python app.py
```

浏览器访问 `http://127.0.0.1:5000`

### 安全配置

首次启动会自动生成管理员账号，初始密码在控制台输出：

```
管理员账号已创建
用户名: admin
初始密码: X7kQm2...（随机 16 位）
请登录后立即修改密码！
```

**生产环境必须配置的环境变量** (`~/.env`)：

```ini
SECRET_KEY=使用-secrets-token-hex-32-生成
API_ENCRYPTION_KEY=用于加密AI服务的API密钥
ADMIN_INITIAL_PASSWORD=首次初始化管理员密码(可选)
```

## 目录结构

```
rooa/
├── app.py                     # 主应用入口 (路由、服务)
├── models.py                  # 核心数据模型
├── archive_models.py          # 档案管理模型
├── archive_routes.py          # 档案管理蓝图
├── utils.py                   # 工具函数 (AI调用、文件处理)
├── config.py                  # Flask 配置
├── config_manager.py          # 系统配置管理器 (JSON)
├── api_key_crypto.py          # API Key 加密模块
├── smart_knowledge.py         # 智能知识库核心
├── crawler_core.py            # 爬虫引擎
├── scraper_engine.py          # 抓取引擎
├── batch_processor.py         # 批量处理
├── briefing_scheduler.py      # 简报调度器
├── monitor_core.py            # 监测核心
├── build_exe.py               # PyInstaller 打包
├── config/                    # 配置文件
│   └── system_config.json
├── templates/                 # Jinja2 模板 (115 个)
├── static/                    # 静态资源
└── crawler/                   # 爬虫子模块
```

## 安全加固 (2026-07)

| 项目 | 状态 |
|------|------|
| SECRET_KEY 环境变量化 | ✅ 随机 fallback |
| 管理员密码随机生成 | ✅ 16 位随机 |
| CSRF 保护 | ✅ 仅 /login 豁免 |
| 登录限流 | ✅ 5次/60s 限流 |
| API Key 加密存储 | ✅ Fernet 对称加密 |
| 文件路径遍历防护 | ✅ safe_join |
| 文件魔数内容验证 | ✅ 扩展名+文件头双重检查 |
| 用户输入验证 | ✅ email/phone/name |

详细审计报告见 [CODE_AUDIT_REPORT.md](CODE_AUDIT_REPORT.md)

## 许可证

内部使用，保留所有权利。
