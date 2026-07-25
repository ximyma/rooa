# OOA 智能服务办公平台 — 代码审计报告

> 审计日期：2026-07-25
> 审计范围：全部 Python 代码 (92 文件, ~13,000+ 行)、115 个模板文件、配置文件
> 审计方法：静态代码分析 + 模式检测 + 结构审查

---

## 一、问题总览

| 严重级别 | 数量 | 类别 |
|----------|------|------|
| 🔴 高危 | 8 | 安全漏洞、数据泄露风险 |
| 🟠 中危 | 14 | 代码缺陷、健壮性问题 |
| 🟡 低危 | 12 | 代码质量、可维护性 |
| 🔵 建议 | 10 | 架构优化、性能改进 |

---

## 二、🔴 高危问题

### 2.1 SECRET_KEY 硬编码在源码中

**文件**: `config.py` 第 9 行

```python
SECRET_KEY = 'ooa-secret-key-2026-fixed-do-not-change'
```

**风险**: Flask Session 签名密钥明文硬编码。任何获取源码的人都能伪造 session、绕过 CSRF 保护，完全接管任意用户会话。

**修复方案**:
```python
# config.py
import os
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
```
并在 `.env` 文件中设置真正的密钥，从源码中移除明文值。

---

### 2.2 默认管理员密码硬编码（4处）

| 文件 | 行号 |
|------|------|
| `app.py` | 302 |
| `init_database.py` | 43 |
| `init_db_standalone.py` | 64 |
| `init_db_standalone_simple.py` | 69 |

全部使用 `generate_password_hash('admin123')`。

**风险**: 默认密码 `admin123` 极其脆弱。如果生产环境未修改，攻击者可轻易登录。

**修复方案**: 首次启动时生成随机密码并通过控制台/日志输出，强制首次登录后修改；或从环境变量读取初始密码。

---

### 2.3 过多路由豁免 CSRF 保护（30处）

`app.py` 中有 **30 个路由**使用 `@csrf.exempt` 装饰器，包括：

| 路由 | 行号 | 风险 |
|------|------|------|
| `/login` (POST) | 829 | 登录免 CSRF 可接受，但缺 rate limiting |
| `/smart_office/document_writing` | 970 | AI 写作接口暴露，可被 CSRF 攻击滥用 API |
| `/smart_office/document_polish` | 1004 | 同上 |
| `/smart_office/document_proofread` | 1035 | 同上，且涉及文件上传 |
| `/admin/system_config/save` | 8323 | **高危**：配置写入接口免 CSRF |
| 以及 25 个其他 API 端点 | ... | 大量数据操作接口免保护 |

**风险**: 任何外部网站可通过 CSRF 攻击以已登录用户身份操作数据、修改配置。

**修复方案**: 
- 所有非 GET 请求必须带 CSRF token
- AJAX 请求在 header 中携带 `X-CSRFToken`
- 仅对真正需要跨站调用的外部 API 做有选择的豁免
- 全局 AJAX 拦截器统一注入 token（在 `static/js/main.js` 中）

---

### 2.4 知识库文件下载缺少路径遍历防护

**文件**: `app.py` 第 2758 行

```python
return send_from_directory(app.config['UPLOAD_FOLDER'], secure_name, as_attachment=True)
```

**问题**: `secure_name` 来自哪里？如果用户可操控 `secure_name` 参数，可能通过 `../` 读取系统任意文件。

**修复方案**: 
- 使用 `werkzeug.utils.safe_join()` 确保路径安全
- 确保文件名在数据库中有记录且属于当前用户
- 不要信任前端传过来的路径参数

---

### 2.5 用户输入未做充分验证

**文件**: `app.py` 第 911-920 行（个人中心更新）

```python
current_user.name = request.form.get('name')
current_user.department = request.form.get('department')
current_user.phone = request.form.get('phone')
current_user.email = request.form.get('email')
```

**问题**: 没有验证 email 格式、phone 格式、name 长度，可能导致：
- 存储非法数据
- XSS 攻击（如果模板未转义，虽然 Jinja2 默认转义但应加防护）

**修复方案**: 添加服务端验证：
```python
import re
if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
    flash('邮箱格式不正确')
    return redirect(...)
if name and len(name) > 80:
    flash('姓名过长')
    return redirect(...)
```

---

### 2.6 登录接口无限试错

**文件**: `app.py` 第 827-846 行

```python
@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    # ...无任何失败次数限制
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
    else:
        flash('用户名或密码错误')
```

**风险**: 无 rate limiting、无账户锁定、无验证码，可暴力破解。

**修复方案**: 
- 添加 Flask-Limiter 限流（5次/分钟）
- 连续失败 5 次锁定账户 15 分钟
- 或至少增加登录尝试延时

---

### 2.7 临时密钥散落各处

| 文件 | 硬编码值 |
|------|----------|
| `debug_init.py:15` | `'temp-key'` |
| `init_db_standalone.py:24` | `'temp-secret-key-for-init'` |
| `init_db_standalone_simple.py:28` | `'temp-secret-key-for-init'` |
| `verify_data.py:19` | `'temp-secret-key-for-verify'` |
| `verify_data_simple.py:17` | `'temp-secret-key-for-verify'` |

**风险**: 这些脚本如果在生产环境被误执行，会使用弱密钥，导致 session 可被伪造。

**修复方案**: 统一从 `config.py` 或环境变量读取。

---

### 2.8 AI API Key 明文存储在数据库

**文件**: `models.py` 第 198 行

```python
api_key = db.Column(db.String(500))
```

**风险**: API Key（OpenAI/DeepSeek等）明文存储在 SQLite 数据库，任何有数据库访问权限的人可获取。

**修复方案**: 使用 `cryptography` 库对 API Key 加密存储，或者使用环境变量方式（不存数据库）。

---

## 三、🟠 中危问题

### 3.1 过度裸露的 `except Exception: pass`

**共 12 处**，典型：

```python
# app.py:1175
except:
    pass
# app.py:294  
except Exception:
    db.session.rollback()  # 还算好
# app.py:1306
except Exception:
    pass  # 完全吞掉异常
# app.py:3359, 3373, 3376, 4338 -- 全部 pass
```

**风险**: 生产环境无法排查问题，异常被静默吞没。

**修复方案**: 至少记录日志 `logger.exception("...")`，不要空 `pass`。

---

### 3.2 模型类中嵌入静态日志方法——循环依赖风险

**文件**: `models.py` 第 449-460 行 (`BriefingSystemLog.log()`)、第 1053-1064 行 (`MonitorSystemLog.log()`)

```python
@staticmethod
def log(level, module, message, details=None):
    log_entry = BriefingSystemLog(...)
    db.session.add(log_entry)
    db.session.commit()  # 直接操作 db.session
```

**问题**: 
- 模型文件直接依赖 `db` 全局对象
- `db.session.commit()` 在模型层会导致事务边界不可控
- 如果外部已有未提交事务，此处 commit 会连带提交不完整数据

**修复方案**: 将日志逻辑移到 service 层或在路由层调用时传入 session。

---

### 3.3 AI API 调用函数严重重复（4个几乎相同的函数）

**文件**: `utils.py` 第 52-116 行

`call_openai`, `call_deepseek`, `call_siliconflow` 三个函数代码几乎100%相同，只有错误消息中的名称不同。

**修复方案**: 合并为统一函数，仅 provider 名称参数化：
```python
def call_openai_compatible(config, messages, provider_name='OpenAI'):
    # 统一实现
```

---

### 3.4 双系统配置并存——数据一致性问题

系统有两套配置机制：
1. `SystemConfig` 数据库模型（`models.py:1343`）
2. `ConfigManager` JSON 文件（`config_manager.py`）

两套系统独立运行，可能出现配置值不一致。且初始化时分别写入两套数据。

**修复方案**: 二选一，推荐保留 JSON 文件方案（启动快、不依赖数据库迁移），废弃数据库配置表。

---

### 3.5 FTS 索引延迟初始化可能造成首次搜索慢

**文件**: `app.py` 第 1528-1547 行

`_ensure_fts()` 在首次搜索时才初始化 FTS 表。如果知识库有大量文件，首次搜索会触发全量索引重建，用户等待时间长。

**修复方案**: 在 `initialize_db()` 中主动调用 `rebuild_fts_index()`。

---

### 3.6 LIKE 回退搜索的 N+1 查询问题

**文件**: `app.py` 第 1617 行

```python
for kf in files:
    kb = KnowledgeBase.query.get(kf.knowledge_base_id)  # N+1!
```

每个文件单独查询 knowledge_base，100个结果 = 101次数据库查询。

**修复方案**: 使用 `joinedload` 或 `selectinload` 预加载关联数据：
```python
files = query.options(db.joinedload(KnowledgeFile.knowledge_base)).all()
```

---

### 3.7 `BriefingWebScraper` Session 永不关闭

**文件**: `utils.py` 第 381-393 行

```python
class BriefingWebScraper:
    def __init__(self, ...):
        self.session = requests.Session()  # 创建但永不关闭
```

**风险**: 连接泄漏，长时间运行可能耗尽文件描述符。

**修复方案**: 实现 `__del__` 或 `close()` 方法，或使用上下文管理器。

---

### 3.8 `initialize_db()` 在生产环境写入测试数据

**文件**: `app.py` 第 281-824 行

数据库为空时自动创建 10 条示例档案、5 个默认部门、3 个默认会议室、默认用户等。这在生产环境可能不合适。

**修复方案**: 通过环境变量控制（如 `OA_ENV=production` 时跳过示例数据）。

---

### 3.9 `save_upload_file` 仅检查扩展名未验证文件内容

**文件**: `utils.py` 第 161-171 行

```python
def save_upload_file(file, subfolder=''):
    if file and allowed_file(file.filename):  # 仅检查扩展名
        filename = secure_filename(file.filename)
```

**风险**: 攻击者可上传 `malicious.pdf` 实际内容是 `.exe`，绕过扩展名检查。

**修复方案**: 使用 `python-magic` 或 `filetype` 验证文件 MIME 类型头。

---

### 3.10 `send_from_directory` 的目录参数来自配置但路径需验证

**文件**: `app.py` 第 2758 行、第 3635 行

```python
send_from_directory(app.config['UPLOAD_FOLDER'], secure_name, as_attachment=True)
send_from_directory(directory, filename, as_attachment=True, download_name=...)
```

`secure_name` 和 `filename` 的来源需要仔细验证。应始终使用 `werkzeug.utils.safe_join(directory, filename)` 防护。

---

### 3.11 PDF 解析无超时、无大文件限制

**文件**: `utils.py` 第 194-207 行

```python
def pdf_to_text(pdf_path):
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            extracted = page.extract_text()
```

**风险**: 恶意的畸形 PDF 可能导致无限循环或内存耗尽。

**修复方案**: 添加页数上限（如 500 页）、文件大小上限。

---

### 3.12 `doc_convert_tasks` 全局字典无锁

**文件**: `app.py` 第 1191 行

```python
doc_convert_tasks = {}  # 全局变量，无锁保护
```

**风险**: 多线程/多 worker 并发访问时数据竞争。

**修复方案**: 使用 `threading.Lock` 或改用数据库存储任务状态。

---

### 3.13 config.py 重复赋值

**文件**: `config.py` 第 22-23 行

```python
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')  # 重复赋值
```

应删除重复行。

---

### 3.14 `_build_api_url` 潜在的 URL 错误

**文件**: `utils.py` 第 117-124 行

```python
def _build_api_url(api_base, path):
    base = api_base.rstrip('/')
    if base.endswith('/v1'):
        return f"{base}/{path.lstrip('/')}"
    return f"{base}/v1/{path.lstrip('/')}"
```

**问题**: 如果 `api_base = "https://api.example.com/v1/extra"`（即 `/v1` 不在末尾），函数会生成 `https://api.example.com/v1/extra/v1/chat/completions`，产生双重 `/v1`。

**修复方案**: 改为检查 `base.endswith('/v1')` 的后缀匹配更精确，或使用 `urljoin`。

---

## 四、🟡 低危问题

### 4.1 app.py 过于臃肿

**现状**: `app.py` 8480 行，包含所有路由、服务逻辑、模型关系配置、工具函数。

**影响**: 难以维护、难以测试、多人协作冲突频繁。

**建议**: 按模块拆分为蓝图：
```
routes/
  auth.py, doc.py, knowledge.py, smart_office.py,
  meeting.py, supervision.py, performance.py, worklog.py,
  briefing.py, admin.py, monitor.py
```

---

### 4.2 Jinja2 模板中大量内联 CSS/JS

115 个 HTML 模板中很多包含 `<style>` 和 `<script>` 内联代码，不利于缓存和 CSP 策略。

**建议**: 提取到 `static/` 目录下的独立文件。

---

### 4.3 缺少结构化日志

全部使用 `print()` 或 `logger.info()` 自由格式，无统一请求 ID、无链路追踪。

**建议**: 引入 `request_id` 中间件，统一日志格式（JSON）。

---

### 4.4 无自动化测试

`tests/` 目录不存在，测试脚本散落在根目录，无 CI/CD。

**建议**: 创建 `tests/` 目录，使用 `pytest` + `pytest-flask`，优先覆盖核心路由和业务逻辑。

---

### 4.5 `datetime.now` 而非 `datetime.now()` 

**文件**: `models.py` 多处

```python
created_at = db.Column(db.DateTime, default=datetime.now)
```

这是正确的——SQLAlchemy 接受 callable。但如果写成 `default=datetime.now()` 则会是定义时的时间（错误）。当前代码是**正确的**，但需警惕后续修改的人可能加括号。

---

### 4.6 锁屏页/500页缺少更友好的设计

`templates/404.html` 和 `templates/500.html` 存在但简陋。

**建议**: 提供返回首页链接、错误参考 ID（便于排查）。

---

### 4.7 `random` 模块用于安全无关场景可用但应标记

```python
import random
# ...用于示例档案生成，非安全场景，无问题
```

确认当前无 `random` 用于 token/密码生成（密码用 `werkzeug.security`），**当前安全**。

---

### 4.8 简报系统 scheduler 和 monitor scheduler 重复逻辑

`briefing_scheduler.py` 和 `monitor_scheduler.py` 有相似的调度逻辑。

**建议**: 提取公共的 `BaseScheduler` 类。

---

### 4.9 文档转换的 LibreOffice 路径硬编码

```python
def _find_soffice():
    paths = [
        "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
        ...
    ]
```

**建议**: 通过环境变量或系统配置指定路径。

---

### 4.10 表单验证不充分

`forms.py` 的表单定义过于简单，缺少长度限制、格式验证、自定义校验器。

---

### 4.11 FTS term 清理逻辑可优化

```python
cleaned = re.sub("[\\\"':*]", ' ', term).strip()
```

FTS5 的保留字符还有 `^`, `(`, `)`, `+`, `-`, `AND`, `OR`, `NOT`, `NEAR` 等，此正则未覆盖全部。

---

### 4.12 缓存仅用于首页

```python
@cache.cached(timeout=300, key_prefix=lambda: f'index_{current_user.id}')
```

其他页面（知识库列表、公文列表、会议列表）未使用缓存。

---

## 五、🔵 架构优化建议

### 5.1 引入服务层（Service Layer）

当前模式：路由直接操作 ORM，业务逻辑与 HTTP 层耦合。

建议引入三层架构：
```
routes/   → 只处理 HTTP 请求/响应
services/ → 业务逻辑
models/   → 数据定义
```

### 5.2 配置统一管理

合并 `SystemConfig` (DB) 和 `ConfigManager` (JSON) → 保留一个。

### 5.3 API 版本化

如果未来需要开放 API，建议加 `/api/v1/` 前缀。

### 5.4 引入 Alembic 数据库迁移

当前手动 SQL ALTER TABLE 迁移（如 `crawler_tasks.max_depth` 补列）在复杂升级场景下容易出错。

### 5.5 前端构建优化

Bootstrap 5 和 Chart.js 加载了完整 bundle，可考虑按需加载或使用 CDN。

### 5.6 异步任务队列

LibreOffice 转换、PDF 解析、FTS 重建等长任务应放入队列（如 Celery / RQ / 线程池），避免阻塞 Web worker。

### 5.7 配置文件分离

将 `config.py` 中的 ALLOWED_EXTENSIONS、SQLITE_PRAGMAS 等移至 YAML/TOML/JSON。

### 5.8 SQLite → PostgreSQL（生产环境）

SQLite 不支持并发写入、无用户认证，适合开发/单机场景。生产环境建议迁移到 PostgreSQL。

### 5.9 健康检查端点

添加 `/health` 端点，返回数据库连接状态、FTS 状态等。

### 5.10 静态资源版本化

CSS/JS 文件加版本号或 hash 防缓存问题：
```html
<link href="{{ url_for('static', filename='css/style.css') }}?v=20260725">
```

---

## 六、修复优先级建议

| 优先级 | 问题 | 预计工时 |
|--------|------|----------|
| P0 | SECRET_KEY 硬编码 + 默认密码 (2.1, 2.2) | 0.5天 |
| P0 | CSRF 豁免过多 (2.3) | 1天 |
| P0 | 文件下载路径遍历 (2.4) | 0.5天 |
| P0 | 登录暴力破解防护 (2.6) | 0.5天 |
| P1 | API Key 加密存储 (2.8) | 0.5天 |
| P1 | 异常吞没修复 (3.1) | 1天 |
| P1 | AI 函数去重 (3.3) | 0.5天 |
| P1 | N+1 查询优化 (3.6) | 0.5天 |
| P1 | 文件内容验证 (3.9) | 0.5天 |
| P2 | 架构拆分 (4.1, 5.1) | 3-5天 |
| P2 | 测试覆盖 (4.4) | 2天 |
| P2 | 配置统一 (3.4) | 1天 |
| P3 | 其余低危和优化项 | 按需 |

---

## 七、正面发现

以下方面做得较好，值得保留：

- ✅ **SQL 参数化**: FTS 查询使用 `:param` 绑定参数，无字符串拼接 SQL 注入
- ✅ **密码哈希**: 使用 `werkzeug.security.generate_password_hash`，非明文存储
- ✅ **文件扩展名过滤**: `secure_filename` + 白名单阻止了基本的上传攻击
- ✅ **数据库索引**: 关键表都有合理的索引设计
- ✅ **登录态管理**: AJAX 返回 JSON 401 而非 HTML 重定向（`unauthorized_handler`）
- ✅ **SQLite WAL 模式**: PRAGMA 已启用性能优化
- ✅ **文档转换隔离**: LibreOffice 在临时目录操作，防止文件权限问题
- ✅ **模型分离**: 核心模型和档案模型分别在不同文件
- ✅ **FTS5 回退**: 全文搜索不可用时自动回退 LIKE 查询
