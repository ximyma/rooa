# OOA 智能服务办公平台 - 工作记忆

> 最后整理：2026-04-07
> 整理原因：合并重复记录，保留当前仍有长期价值的项目事实、约定和关键修复。

## 1. 项目基础
- **项目路径**：`c:\Users\Administrator\Desktop\ooa`
- **技术栈**：Flask + SQLAlchemy + SQLite + Jinja2 + Bootstrap 5
- **启动方式**：`python app.py`
- **默认访问地址**：`http://127.0.0.1:5000`
- **管理员账号**：`admin / admin123`

## 2. 用户偏好
- 用户名：笑卿
- 偏好直接解决问题，不喜欢空话。
- 系统故障场景下，优先排查、修复、重启并验证结果。
- 当前主要维护项目：OOA 智能服务办公平台。

## 3. 当前系统主要模块
- **电子公文**：已具备起草、审批、发送、办理、退回、撤回、归档、待办公文等流程。
- **智能办公**：公文写作、润色、校对、意见建议、会议纪要、文档转换。
- **知识管理**：知识库、政策文件库，支持政策库批量上传。
- **网站采集与栏目监测**：整站爬虫、内容检索、高级检索、网址库监测。
- **档案管理**：全宗、目录、案卷、文件、借阅、统计、数字化管理、数字化任务。
- **办公协同扩展（2026-04-07）**：会议管理、督查督办、绩效考核、工作日志、公文工作台。

## 4. 关键长期约定与修复

### 4.1 登录与会话
- `config.py` 的 `SECRET_KEY` 已固定为 `ooa-secret-key-2026-fixed-do-not-change`。
- 原因：随机 SECRET_KEY 会导致 session 失效、CSRF token 对不上。
- 登录验证码已完全移除；`LoginForm` 禁用 CSRF；登录路由已做 CSRF 豁免。
- AJAX 未登录访问统一返回 JSON 401，避免前端把登录页 HTML 当 JSON 解析。

### 4.2 时间、错误处理与兼容性
- 全系统时间统一使用 `datetime.now`，不再使用 `datetime.utcnow`，避免本地时间慢 8 小时。
- 首页 6 套模板的电子公文入口已从错误端点修正到 `doc_*` 系列路由。
- `app.py` 已补齐 `@app.errorhandler(500)` 与 `templates/500.html`，异常页渲染前会尝试 `db.session.rollback()` 清理失败事务。
- 登录态用户加载已从 `User.query.get()` 切换为 `db.session.get(User, id)`，兼容 SQLAlchemy 2.0。
- 简报 `Briefing.task_id` 已改为"时间戳 + UUID 片段"，避免同秒提交时出现唯一键冲突。


### 4.3 网站采集与栏目监测
- 爬虫中文乱码问题已修复：优先用 `chardet` 检测编码，低置信度时优先尝试 GBK。
- `crawler_core.py` 已支持 `max_depth` 抓取层级；数据库缺列时，`app.py` 启动会自动轻量迁移补列。
- 爬虫做了 URL 规范化、连接复用、轻量重试，并跳过非 HTML 内容。
- 监测中心显示网址数量时应使用 `UrlLibrary.item_count`，不是 `MonitorResult` 数量。
- 栏目监测后台线程不得持有跨线程 ORM 对象；`UrlItem` 已改为纯字典载入。
- 涉及后台线程的数据库操作需放在 `app.app_context()` 内执行。

### 4.4 文档转换
- "PDF转换"已改名为"文档转换"。
- 当前为**同步转换**方案，不再使用 SSE 进度推送和异步任务结果端点。
- 转换逻辑参考 `crawler/transdoc9.py` 的 LibreOffice headless 方案。

### 4.5 知识库与政策库
- 政策文件库支持多文件批量上传，含分类标签。
- 智能办公相关页面已能关联政策文件库。
- 知识库搜索、智能检索与问答检索已修复为可用状态。
- `templates/knowledge/search_results.html` 的筛选表单必须保留 `id="knowledgeSearchForm"`，否则知识库搜索结果页的单选筛选联动会因 JS 拿不到表单对象而失效。

### 4.6 档案管理
- `archive_models.py` 中 `ArchiveDigitizationTask` 已补齐模型声明并注册。
- 档案数字化任务页面 `templates/archive/digitization_tasks.html` 已补建。
- `/knowledge` 已增加重定向路由；`archive_batch_upload` 已有兼容入口。
- 档案侧边栏、全宗/目录/案卷页面、上传页、借阅页、检索页已完成一轮系统性修复。

## 5. 现阶段新增办公协同能力（2026-04-07）

### 5.1 新增模型
- `MeetingRoom`
- `Meeting`
- `SupervisionTask`
- `SupervisionProgress`
- `PerformancePeriod`
- `PerformanceAssessment`
- `WorkLog`

### 5.2 新增模块入口
- **公文工作台**：`/official_doc/dashboard`
- **会议管理**：`/meeting`、`/meeting/new`、`/meeting/calendar`、`/meeting/rooms`
- **督查督办**：`/supervision`、`/supervision/new`
- **绩效考核**：`/performance`、`/performance/new`、`/performance/periods`
- **工作日志**：`/worklog`、`/worklog/new`

### 5.3 公文模块优化
- 发件箱、收件箱已增加统计卡片和关键词检索。
- 起草页已增加 `sign_dept`（主办单位）字段。
- 公文详情页支持"转督办""发起会议"，并展示关联事项。
- 公文必须审批通过后才能正式发送，更贴近真实政企流程。
- 公文附件上传已改为专属白名单 + `secure_filename` 净化，允许 `pdf/doc/docx/xls/xlsx/txt/zip/rar/7z/jpg/jpeg/png`；非法扩展名会跳过并给出 warning，前端 `accept` 也已同步。


### 5.4 办公协同增强补齐（2026-04-07 晚）
- `models.py` 已补齐 `MeetingAttendance` 模型，会议签到/请假/缺席/反馈不再依赖缺失数据表。
- `app.py` 已补齐 `MeetingAttendance`、`WorkLogReview` 导入，避免会议签到页与日志审批留痕页运行时报 `NameError`。
- `templates/work_log/new.html` 已补齐"最新退回意见""最近审批留痕"展示，并改为真实的"保存草稿 / 提交日志 / 重新提交日志"动作按钮。
- 已验证工作日志从 `returned` 重新提交到 `submitted` 时会新增 `resubmit` 留痕。

### 5.5 办公协同表单校验优化（2026-04-07 夜）
- 会议发起在"提交发布"时已增加结束时间、会议室维护状态、会议室容量、同会议室时间冲突校验；草稿仍可先保存。
- 绩效记录发布已增加 `score/full_score/weight` 数值合法性校验，并禁止向已关闭的考核周期直接发布记录。
- 考核周期新增时已要求起止日期完整且不倒挂，同名周期不可重复，启用中的同类型周期时间不能重叠。
- 工作日志工时已限制为 `0-24` 小时，且新建日志对象改为在校验通过后再创建，避免无效提交导致 SQLAlchemy 事务脏状态。

### 5.6 办公协同增强动作与看板验证补齐（2026-04-07 深夜）
- 已补建文件式回归脚本 `c:\Users\Administrator\Desktop\ooa\.workbuddy\verify_office_collab_regression.py`，用于绕开 PowerShell 内联 Python 的编码问题。
- 已通过 34 项回归检查，确认以下新增能力真实可用：会议编辑/取消、督办编辑/批量催办/关闭、绩效编辑/撤回、考核周期关闭/启用、工作台提醒聚合、会议/督办/日志快捷筛选。
- 回归脚本已按真实页面提交方式补带 CSRF token；验证过程中插入的临时测试数据已清理。

## 6. 验证现状



- 2026-04-07 已验证以下入口可访问：
  - `/official_doc/dashboard`
  - `/meeting`
  - `/meeting/calendar`
  - `/meeting/rooms`
  - `/supervision`
  - `/performance`
  - `/performance/periods`
  - `/worklog`
- 2026-04-07 已完成办公协同模块闭环验证：公文提交审批/发送、会议创建与状态流转、督办下发与办结、绩效周期与记录发布、工作日志创建与审核均已跑通，且测试数据已清理。
- 公文详情页已确认具备"转督办""发起会议"快捷入口，并能展示"关联会议""关联督办"；公文工作台可联动展示会议与督办信息。
- 档案模块重点路由已完成一轮 17 条路由 200 OK 回归验证。

## 7. 系统配置与文档长度限制（2026-04-08）

### 7.1 现有系统配置系统整合
- **重要发现**: 系统已有完善的配置系统 (`config_manager.py` + `/admin/system_config`路由)
- **配置格式**: JSON文件存储在 `config/system_config.json`
- **使用约定**: 
  - 现有配置包含 `knowledge_base`, `ocr`, `ai`, `monitoring` 章节
  - 新增 `document` 章节处理文档长度限制
  - 配置更新使用 `config_manager.update_section(section, values)`

### 7.2 文档提取长度限制配置
- **配置项** (`document`章节):
  - `max_extracted_length`: -1（无限制）
  - `max_preview_length`: 100000
  - `max_ai_sample_length`: 5000  
  - `max_file_preview_length`: 50000
  - `max_upload_size_mb`: 1024
- **代码适配**: 
  - `app.py` 中所有硬编码限制替换为 `config_manager.get("document.max_*", 默认值)`
  - `utils.py` 中 `extract_file_content()` 使用 `config_manager.get("document.max_extracted_length", -1)`
  - 支持 `-1` 表示无限制

### 7.3 系统配置页面兼容性
- **模板格式**: `templates/admin/system_config.html` 使用 `categories` 字典格式
- **路由适配**: `/admin/system_config` 路由转换 `config` -> `categories` 格式
- **前端修复**: 更新 `saveConfig()` JS函数解析点分隔键名，适配现有的保存路由

### 7.4 关键路由与方法
- **配置管理**: `/admin/system_config` (GET)
- **保存配置**: `/admin/system_config/save` (POST) - 需要 `section` 和 `values` 参数
- **配置管理器** (`config_manager.py`):
  - `get_all()` - 获取所有配置
  - `get(key_path)` - 获取特定配置值
  - `set(key_path, value)` - 设置配置值
  - `update_section(section, values)` - 更新配置章节

### 7.5 验证要点
- **文档上传**: 大文件内容提取不再截断（默认 `max_extracted_length = -1`）
- **系统配置**: 管理员可访问 `/admin/system_config` 调整文档长度限制
- **配置生效**: 修改配置后实时生效，无需重启应用
- **向后兼容**: 配置获取失败时使用 `config.py` 中的默认常量

