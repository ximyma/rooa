from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(80))
    department = db.Column(db.String(80))   # 兼容旧数据，新增 dept_id 关联
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    role = db.Column(db.String(20), default='employee')  # employee, manager, admin
    is_reporter = db.Column(db.Boolean, default=False)
    is_receiver = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    home_style = db.Column(db.String(20), default='default')  # default, dark, anime, fresh
    # 通知设置
    email_notify = db.Column(db.Boolean, default=True)
    task_notify = db.Column(db.Boolean, default=True)
    system_notify = db.Column(db.Boolean, default=True)
    # ===== 组织架构关联字段 =====
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), comment='所属机构')
    dept_id = db.Column(db.Integer, db.ForeignKey('departments.id'), comment='所属部门')
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), comment='岗位')
    employee_no = db.Column(db.String(30), unique=True, comment='工号')
    avatar = db.Column(db.String(200), comment='头像路径')
    gender = db.Column(db.String(5), default='未知', comment='性别')
    is_active = db.Column(db.Boolean, default=True, comment='是否在职')
    remark = db.Column(db.String(300), comment='备注')

    # 所属机构关系
    organization = db.relationship('Organization', foreign_keys=[org_id], backref='members')
    # 部门和岗位关系（显式定义，避免 backref 冲突；移除 Department.members 和 Position.users 的 backref）
    dept = db.relationship('Department', foreign_keys=[dept_id], viewonly=True)
    position = db.relationship('Position', foreign_keys=[position_id], viewonly=True)

    __table_args__ = (
        db.Index('idx_user_department', 'department'),
        db.Index('idx_user_role', 'role'),
        db.Index('idx_user_dept_id', 'dept_id'),
        db.Index('idx_user_org_id', 'org_id'),
        db.Index('idx_user_position_id', 'position_id'),
        db.Index('idx_user_is_active', 'is_active'),
    )

class KnowledgeBase(db.Model):
    __tablename__ = 'knowledge_bases'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20))  # personal, shared, policy
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # ===== P1 知识库分类 =====
    category = db.Column(db.String(80), comment='知识库分类：制度规范/技术文档/培训资料/会议记录/常见问题/工作模板')
    description = db.Column(db.String(500), comment='知识库描述')

    # 添加关系属性
    owner = db.relationship('User', foreign_keys=[owner_id], backref='knowledge_bases')
    files = db.relationship('KnowledgeFile', backref='knowledge_base', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_kb_owner_type', 'owner_id', 'type'),
        db.Index('idx_kb_type_public', 'type', 'is_public'),
        db.Index('idx_kb_owner', 'owner_id'),
        db.Index('idx_kb_category', 'category'),
    )

class KnowledgeFile(db.Model):
    __tablename__ = 'knowledge_files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200))
    file_path = db.Column(db.String(500))
    knowledge_base_id = db.Column(db.Integer, db.ForeignKey('knowledge_bases.id'))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    upload_time = db.Column(db.DateTime, default=datetime.now)

    # ===== P0 文件内容提取 =====
    content_text = db.Column(db.Text, comment='提取的文件文本内容')
    file_size = db.Column(db.Integer, comment='文件大小(字节)')
    file_type = db.Column(db.String(20), comment='文件类型 pdf/docx/doc/txt/md')
    word_count = db.Column(db.Integer, comment='字数')

    # ===== P1 分类标签 =====
    category = db.Column(db.String(80), comment='文件分类')
    tags = db.Column(db.String(500), comment='标签，逗号分隔')
    summary = db.Column(db.String(500), comment='AI生成的摘要')
    
    # ===== P2 智能知识库 - 向量和关键词 =====
    keywords = db.Column(db.String(500), comment='AI提取的关键词，逗号分隔')
    embedding = db.Column(db.LargeBinary, comment='文本向量嵌入(BLOB)')
    is_vectorized = db.Column(db.Boolean, default=False, comment='是否已生成向量')

    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    __table_args__ = (
        db.Index('idx_kf_kb_id', 'knowledge_base_id'),
        db.Index('idx_kf_kb_id_status', 'knowledge_base_id', 'status'),
        db.Index('idx_kf_uploaded_by', 'uploaded_by'),
        db.Index('idx_kf_status', 'status'),
        db.Index('idx_kf_category', 'category'),
        db.Index('idx_kf_file_type', 'file_type'),
    )

    def get_tags_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()] if self.tags else []


class SpecialReport(db.Model):
    __tablename__ = 'special_reports'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80))
    content = db.Column(db.Text)
    attachments = db.Column(db.String(500))
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reporter_name = db.Column(db.String(80))
    reporter_phone = db.Column(db.String(20))
    target_department = db.Column(db.String(200))  # 接收部门ID列表
    status = db.Column(db.String(20), default='draft')  # draft, pending, approved, rejected, adopted
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        db.Index('idx_sr_reporter_id', 'reporter_id'),
        db.Index('idx_sr_reporter_status', 'reporter_id', 'status'),
        db.Index('idx_sr_status', 'status'),
        db.Index('idx_sr_updated_at', 'updated_at'),
        db.Index('idx_sr_target_department', 'target_department'),
        db.Index('idx_sr_reporter_updated', 'reporter_id', 'updated_at'),
    )

class AssignmentTask(db.Model):
    __tablename__ = 'assignment_tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80))
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    urgency = db.Column(db.String(20))  # normal, urgent
    attachments = db.Column(db.String(500))
    assigned_to = db.Column(db.String(500))  # 用户ID列表，逗号分隔
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='active')  # active, closed
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系属性：任务创建者
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tasks')

    __table_args__ = (
        db.Index('idx_task_status', 'status'),
        db.Index('idx_task_created_by', 'created_by'),
        db.Index('idx_task_end_time', 'end_time'),
        db.Index('idx_task_status_created', 'status', 'created_at'),
    )

class TaskSubmission(db.Model):
    __tablename__ = 'task_submissions'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('assignment_tasks.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    report_id = db.Column(db.Integer, db.ForeignKey('special_reports.id'))
    status = db.Column(db.String(20), default='submitted')  # submitted, approved, rejected
    submitted_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.Index('idx_submission_task_user', 'task_id', 'user_id'),
        db.Index('idx_submission_user_status', 'user_id', 'status'),
        db.Index('idx_submission_task', 'task_id'),
        db.Index('idx_submission_user', 'user_id'),
    )

class AIConversation(db.Model):
    __tablename__ = 'ai_conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_id = db.Column(db.String(100))
    question = db.Column(db.Text)
    answer = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

# models.py 新增部分（在原有表定义后添加）

class AIModelConfig(db.Model):
    __tablename__ = 'ai_model_configs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)          # 配置名称，如"GPT-4"
    provider = db.Column(db.String(50), nullable=False)       # openai, deepseek, siliconflow, local
    api_key = db.Column(db.String(500))
    api_base = db.Column(db.String(500))                      # API地址，本地模型需指定
    model_name = db.Column(db.String(100))                    # 模型名称，如gpt-4
    temperature = db.Column(db.Float, default=0.7)            # 温度
    max_tokens = db.Column(db.Integer, default=2000)          # 最大输出token
    context_length = db.Column(db.Integer, default=4000)      # 上下文长度（输入token限制）
    delay = db.Column(db.Integer, default=0)                  # 延时（毫秒）
    is_active = db.Column(db.Boolean, default=True)           # 是否启用
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.Index('idx_aimc_is_active', 'is_active'),
        db.Index('idx_aimc_provider', 'provider'),
    )

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(200), default='新对话')
    model_config_id = db.Column(db.Integer, db.ForeignKey('ai_model_configs.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        db.Index('idx_chatsession_user_id', 'user_id'),
        db.Index('idx_chatsession_updated_at', 'updated_at'),
        db.Index('idx_chatsession_user_updated', 'user_id', 'updated_at'),
    )

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'))
    role = db.Column(db.String(20))        # user, assistant
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.Index('idx_chatmsg_session_id', 'session_id'),
        db.Index('idx_chatmsg_created_at', 'created_at'),
        db.Index('idx_chatmsg_session_created', 'session_id', 'created_at'),
    )


# ==================== 简报生成系统模型 ====================

class BriefingSource(db.Model):
    """简报数据源模型"""
    __tablename__ = 'briefing_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='数据源名称')
    url = db.Column(db.String(500), nullable=False, comment='网站URL')
    source_type = db.Column(db.String(20), default='website', comment='类型: website/api')
    category = db.Column(db.String(50), comment='分类')
    config = db.Column(db.Text, comment='配置信息(JSON)')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    priority = db.Column(db.Integer, default=0, comment='优先级')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 统计信息
    total_articles = db.Column(db.Integer, default=0, comment='累计抓取文章数')
    last_crawl_time = db.Column(db.DateTime, comment='最后抓取时间')
    
    def get_config(self):
        """获取配置字典"""
        import json
        return json.loads(self.config) if self.config else {}
    
    def set_config(self, config_dict):
        """设置配置"""
        import json
        self.config = json.dumps(config_dict, ensure_ascii=False)

    __table_args__ = (
        db.Index('idx_bsrc_is_active', 'is_active'),
        db.Index('idx_bsrc_category', 'category'),
    )


class BriefingKeyword(db.Model):
    """简报关键词模型"""
    __tablename__ = 'briefing_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(100), nullable=False, unique=True, comment='关键词')
    category = db.Column(db.String(50), comment='分类')
    description = db.Column(db.String(200), comment='描述')
    color = db.Column(db.String(10), default='#3498db', comment='标签颜色')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    use_count = db.Column(db.Integer, default=0, comment='使用次数')
    created_at = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.Index('idx_bkw_text', 'text'),
        db.Index('idx_bkw_is_active', 'is_active'),
    )


class Briefing(db.Model):
    """简报模型"""
    __tablename__ = 'briefings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, comment='简报标题')
    task_id = db.Column(db.String(50), unique=True, comment='任务ID')
    status = db.Column(db.String(20), default='pending', comment='状态')
    keywords = db.Column(db.Text, comment='关键词列表(JSON)')
    sources = db.Column(db.Text, comment='数据源列表(JSON)')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='创建用户')
    
    # 文件信息
    docx_path = db.Column(db.String(500), comment='Word文档路径')
    pdf_path = db.Column(db.String(500), comment='PDF文档路径')
    
    # 统计信息
    article_count = db.Column(db.Integer, default=0, comment='文章数量')
    total_words = db.Column(db.Integer, default=0, comment='总字数')
    
    # 时间信息
    target_date = db.Column(db.String(20), comment='目标日期')
    start_time = db.Column(db.DateTime, default=datetime.now, comment='开始时间')
    end_time = db.Column(db.DateTime, comment='结束时间')
    duration = db.Column(db.Integer, comment='耗时(秒)')
    
    # 日志和错误
    log = db.Column(db.Text, comment='执行日志')
    error_message = db.Column(db.Text, comment='错误信息')
    
    # 关联
    creator = db.relationship('User', backref='briefings')
    articles = db.relationship('BriefingArticle', backref='briefing', lazy='dynamic', 
                               cascade='all, delete-orphan')
    
    def get_keywords(self):
        import json
        return json.loads(self.keywords) if self.keywords else []
    
    def set_keywords(self, kw_list):
        import json
        self.keywords = json.dumps(kw_list, ensure_ascii=False)
    
    def get_sources(self):
        import json
        return json.loads(self.sources) if self.sources else []
    
    def set_sources(self, src_list):
        import json
        self.sources = json.dumps(src_list, ensure_ascii=False)

    __table_args__ = (
        db.Index('idx_briefing_task_id', 'task_id'),
        db.Index('idx_briefing_status', 'status'),
        db.Index('idx_briefing_user_id', 'user_id'),
        db.Index('idx_briefing_start_time', 'start_time'),
    )


class BriefingArticle(db.Model):
    """简报文章模型"""
    __tablename__ = 'briefing_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    briefing_id = db.Column(db.Integer, db.ForeignKey('briefings.id'), comment='所属简报')
    
    title = db.Column(db.String(300), nullable=False, comment='标题')
    content = db.Column(db.Text, comment='正文')
    summary = db.Column(db.Text, comment='摘要')
    
    source_name = db.Column(db.String(100), comment='来源名称')
    source_url = db.Column(db.String(500), comment='原文链接')
    publish_date = db.Column(db.String(20), comment='发布日期')
    
    keyword = db.Column(db.String(100), comment='匹配的关键词')
    author = db.Column(db.String(50), comment='作者')
    
    # 元数据
    word_count = db.Column(db.Integer, default=0, comment='字数')
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    __table_args__ = (
        db.Index('idx_bart_briefing_id', 'briefing_id'),
        db.Index('idx_bart_keyword', 'keyword'),
    )


class BriefingScheduledTask(db.Model):
    """简报定时任务模型"""
    __tablename__ = 'briefing_scheduled_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='任务名称')
    task_type = db.Column(db.String(20), default='briefing', comment='任务类型')
    
    # 调度配置
    cron_expression = db.Column(db.String(100), comment='Cron表达式')
    schedule_type = db.Column(db.String(20), default='daily', comment='调度类型')
    schedule_config = db.Column(db.Text, comment='调度配置(JSON)')
    
    # 任务参数
    keywords = db.Column(db.Text, comment='关键词(JSON)')
    sources = db.Column(db.Text, comment='数据源(JSON)')
    email_recipients = db.Column(db.Text, comment='邮件接收人(JSON)')
    
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    last_run_time = db.Column(db.DateTime, comment='最后执行时间')
    next_run_time = db.Column(db.DateTime, comment='下次执行时间')
    run_count = db.Column(db.Integer, default=0, comment='执行次数')
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.Index('idx_bst_is_active', 'is_active'),
    )


class BriefingStatistics(db.Model):
    """简报统计信息模型"""
    __tablename__ = 'briefing_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), unique=True, comment='日期')
    
    briefings_count = db.Column(db.Integer, default=0, comment='简报数量')
    articles_count = db.Column(db.Integer, default=0, comment='文章数量')
    words_count = db.Column(db.Integer, default=0, comment='总字数')
    
    top_keywords = db.Column(db.Text, comment='热门关键词(JSON)')
    top_sources = db.Column(db.Text, comment='热门数据源(JSON)')
    
    created_at = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.Index('idx_bstat_date', 'date'),
    )


class BriefingSystemLog(db.Model):
    """简报系统日志模型"""
    __tablename__ = 'briefing_system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(10), default='INFO', comment='日志级别')
    module = db.Column(db.String(50), comment='模块')
    message = db.Column(db.Text, comment='日志内容')
    details = db.Column(db.Text, comment='详细信息(JSON)')
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    
    @staticmethod
    def log(level, module, message, details=None):
        """记录日志"""
        import json
        log_entry = BriefingSystemLog(
            level=level,
            module=module,
            message=message,
            details=json.dumps(details, ensure_ascii=False) if details else None
        )
        db.session.add(log_entry)
        db.session.commit()

    __table_args__ = (
        db.Index('idx_bsl_created_at', 'created_at'),
        db.Index('idx_bsl_level', 'level'),
    )


# ==================== 系统管理扩展模型 ====================

class Role(db.Model):
    """角色模型（细化权限）"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, comment='角色标识')
    display_name = db.Column(db.String(100), nullable=False, comment='显示名称')
    description = db.Column(db.String(300), comment='角色描述')
    permissions = db.Column(db.Text, comment='权限列表(JSON数组)')
    is_system = db.Column(db.Boolean, default=False, comment='是否系统内置角色')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def get_permissions(self):
        import json
        return json.loads(self.permissions) if self.permissions else []

    def set_permissions(self, perm_list):
        import json
        self.permissions = json.dumps(perm_list, ensure_ascii=False)

    def has_permission(self, perm):
        return perm in self.get_permissions()

    __table_args__ = (
        db.Index('idx_role_name', 'name'),
    )


class SystemOperationLog(db.Model):
    """系统操作日志（全局审计）"""
    __tablename__ = 'system_operation_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='操作用户')
    username = db.Column(db.String(80), comment='用户名快照')
    module = db.Column(db.String(50), comment='功能模块')
    action = db.Column(db.String(50), comment='操作类型 create/update/delete/login/logout')
    target = db.Column(db.String(200), comment='操作对象')
    detail = db.Column(db.Text, comment='详细描述')
    ip_addr = db.Column(db.String(50), comment='IP地址')
    created_at = db.Column(db.DateTime, default=datetime.now)

    operator = db.relationship('User', foreign_keys=[user_id])

    __table_args__ = (
        db.Index('idx_sol_user_id', 'user_id'),
        db.Index('idx_sol_module', 'module'),
        db.Index('idx_sol_created_at', 'created_at'),
        db.Index('idx_sol_action', 'action'),
    )


class DocTemplate(db.Model):
    """公文模板（动态管理）"""
    __tablename__ = 'doc_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment='模板名称')
    category = db.Column(db.String(80), default='通用', comment='模板分类')
    description = db.Column(db.String(500), comment='模板描述')
    file_path = db.Column(db.String(500), comment='文件存储路径')
    file_type = db.Column(db.String(20), default='txt', comment='文件类型 txt/docx/html')
    content = db.Column(db.Text, comment='模板正文内容（txt/html类型）')
    tags = db.Column(db.String(300), comment='标签，逗号分隔')
    sort_order = db.Column(db.Integer, default=0, comment='排序权重')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    use_count = db.Column(db.Integer, default=0, comment='使用次数')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), comment='创建者')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), comment='最后修改者')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    creator = db.relationship('User', foreign_keys=[created_by])
    updater = db.relationship('User', foreign_keys=[updated_by])

    def get_tags(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()] if self.tags else []

    __table_args__ = (
        db.Index('idx_dt_category', 'category'),
        db.Index('idx_dt_is_active', 'is_active'),
        db.Index('idx_dt_created_by', 'created_by'),
    )


class SystemUsageStat(db.Model):
    """系统功能使用统计"""
    __tablename__ = 'system_usage_stats'

    id = db.Column(db.Integer, primary_key=True)
    stat_date = db.Column(db.String(10), nullable=False, comment='日期 YYYY-MM-DD')
    module = db.Column(db.String(50), nullable=False, comment='功能模块')
    action = db.Column(db.String(50), nullable=False, comment='操作类型')
    count = db.Column(db.Integer, default=0, comment='次数')
    user_count = db.Column(db.Integer, default=0, comment='独立用户数')
    
    __table_args__ = (
        db.UniqueConstraint('stat_date', 'module', 'action', name='uq_stat_date_module_action'),
        db.Index('idx_sus_stat_date', 'stat_date'),
        db.Index('idx_sus_module', 'module'),
    )


# ==================== 电子公文收发模型 ====================

class OfficialDoc(db.Model):
    """电子公文主表"""
    __tablename__ = 'official_docs'

    id = db.Column(db.Integer, primary_key=True)
    doc_no = db.Column(db.String(50), unique=True, comment='公文编号，自动生成')
    title = db.Column(db.String(300), nullable=False, comment='公文标题')
    doc_type = db.Column(db.String(30), default='通知', comment='公文种类：通知/请示/报告/函/批复/决定/意见/纪要')
    urgency = db.Column(db.String(20), default='普通', comment='紧急程度：普通/紧急/特急')
    secrecy = db.Column(db.String(20), default='普通', comment='密级：普通/内部/秘密/机密')
    content = db.Column(db.Text, comment='公文正文')
    attachments = db.Column(db.Text, comment='附件路径列表(JSON)')

    # 发文方
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='起草人')
    sender_dept = db.Column(db.String(100), comment='发文部门')
    sign_dept = db.Column(db.String(200), comment='主办单位')

    # 收文方（支持多人/多部门）
    receiver_ids = db.Column(db.Text, comment='接收人ID列表(JSON)')
    receiver_depts = db.Column(db.String(500), comment='接收部门，逗号分隔')

    # 流程状态
    # draft-草稿 / pending_approve-待审批 / approved-已审批 / sent-已发送
    # recalled-已撤回 / archived-已归档
    status = db.Column(db.String(30), default='draft', comment='公文状态')

    # 时间
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    sent_at = db.Column(db.DateTime, comment='发送时间')
    archived_at = db.Column(db.DateTime, comment='归档时间')

    # 关联
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_docs')
    flows = db.relationship('DocFlow', backref='doc', lazy='dynamic', cascade='all, delete-orphan')
    read_records = db.relationship('DocReadRecord', backref='doc', lazy='dynamic', cascade='all, delete-orphan')

    def get_receiver_ids(self):
        import json
        return json.loads(self.receiver_ids) if self.receiver_ids else []

    def set_receiver_ids(self, id_list):
        import json
        self.receiver_ids = json.dumps(id_list, ensure_ascii=False)

    def get_attachments(self):
        import json
        import os

        if not self.attachments:
            return []

        try:
            raw_items = json.loads(self.attachments)
        except Exception:
            raw_items = []

        normalized = []
        if not isinstance(raw_items, list):
            raw_items = [raw_items]

        for item in raw_items:
            if isinstance(item, dict):
                path = str(item.get('path') or '').strip()
                name = str(item.get('name') or path or '').strip()
                if path:
                    normalized.append({'name': name or os.path.basename(path), 'path': path})
            elif isinstance(item, str):
                path = item.strip()
                if path:
                    normalized.append({'name': os.path.basename(path), 'path': path})

        return normalized


    def set_attachments(self, att_list):
        import json
        self.attachments = json.dumps(att_list, ensure_ascii=False)

    __table_args__ = (
        db.Index('idx_od_sender_id', 'sender_id'),
        db.Index('idx_od_status', 'status'),
        db.Index('idx_od_doc_type', 'doc_type'),
        db.Index('idx_od_created_at', 'created_at'),
        db.Index('idx_od_doc_no', 'doc_no'),
    )


class DocFlow(db.Model):
    """公文流转记录（审批/办理/退回等）"""
    __tablename__ = 'doc_flows'

    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey('official_docs.id'), comment='公文ID')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='操作人')
    # 操作类型：submit-提交审批 / approve-审批通过 / reject-退回 / send-发送 
    #          receive-已接收 / handle-办理 / recall-撤回 / archive-归档 / comment-批注
    action = db.Column(db.String(30), nullable=False, comment='操作类型')
    opinion = db.Column(db.Text, comment='意见/批注')
    created_at = db.Column(db.DateTime, default=datetime.now)

    operator = db.relationship('User', foreign_keys=[operator_id])

    __table_args__ = (
        db.Index('idx_df_doc_id', 'doc_id'),
        db.Index('idx_df_operator_id', 'operator_id'),
        db.Index('idx_df_created_at', 'created_at'),
    )


class DocReadRecord(db.Model):
    """公文阅读记录"""
    __tablename__ = 'doc_read_records'

    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey('official_docs.id'), comment='公文ID')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='阅读人')
    # unread-未读 / read-已读 / handled-已办理 / returned-已退回
    handle_status = db.Column(db.String(20), default='unread', comment='处理状态')
    handle_opinion = db.Column(db.Text, comment='办理意见')
    read_at = db.Column(db.DateTime, comment='阅读时间')
    handled_at = db.Column(db.DateTime, comment='办理时间')
    created_at = db.Column(db.DateTime, default=datetime.now)

    reader = db.relationship('User', foreign_keys=[user_id])

    __table_args__ = (
        db.UniqueConstraint('doc_id', 'user_id', name='uq_doc_read_user'),
        db.Index('idx_drr_doc_id', 'doc_id'),
        db.Index('idx_drr_user_id', 'user_id'),
        db.Index('idx_drr_handle_status', 'handle_status'),
    )


# ==================== 组织机构管理模型 ====================

class Organization(db.Model):
    """组织机构（单位/公司层级）"""
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment='机构名称')
    short_name = db.Column(db.String(50), comment='机构简称')
    code = db.Column(db.String(50), unique=True, comment='机构编码')
    parent_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), comment='上级机构ID')
    org_type = db.Column(db.String(30), default='unit', comment='类型: unit-单位/company-公司/group-集团')
    level = db.Column(db.Integer, default=1, comment='层级深度')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    address = db.Column(db.String(300), comment='地址')
    phone = db.Column(db.String(50), comment='联系电话')
    description = db.Column(db.Text, comment='机构描述')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 自关联：子机构
    children = db.relationship('Organization', backref=db.backref('parent', remote_side=[id]),
                                lazy='dynamic')
    # 下属部门
    departments = db.relationship('Department', backref='organization', lazy='dynamic')

    __table_args__ = (
        db.Index('idx_org_parent_id', 'parent_id'),
        db.Index('idx_org_code', 'code'),
        db.Index('idx_org_is_active', 'is_active'),
    )

    def get_full_name(self):
        """获取完整路径名称"""
        if self.parent:
            return f"{self.parent.get_full_name()} / {self.name}"
        return self.name


class Department(db.Model):
    """部门"""
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment='部门名称')
    code = db.Column(db.String(50), comment='部门编码')
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), comment='所属机构')
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'), comment='上级部门')
    dept_type = db.Column(db.String(30), default='functional', comment='类型: functional-职能部门/business-业务部门/support-支撑部门')
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='部门负责人')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    description = db.Column(db.Text, comment='部门描述')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    children = db.relationship('Department', backref=db.backref('parent', remote_side=[id]),
                                lazy='dynamic')
    manager = db.relationship('User', foreign_keys=[manager_id])
    positions = db.relationship('Position', backref='department', lazy='dynamic')
    members = db.relationship('User', foreign_keys='User.dept_id', lazy='select')

    __table_args__ = (
        db.Index('idx_dept_org_id', 'org_id'),
        db.Index('idx_dept_parent_id', 'parent_id'),
        db.Index('idx_dept_manager_id', 'manager_id'),
        db.Index('idx_dept_is_active', 'is_active'),
    )

    def get_member_count(self):
        return User.query.filter_by(dept_id=self.id, is_active=True).count()

    def get_full_path(self):
        """获取部门的完整路径"""
        if self.parent is None:
            return self.name
        return self.parent.get_full_path() + ' > ' + self.name

    def get_ancestors(self):
        """获取部门的所有上级部门"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors


# ==================== 知识库增强模型（P1） ====================

class KnowledgeFavorite(db.Model):
    """知识库文件收藏"""
    __tablename__ = 'knowledge_favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    file_id = db.Column(db.Integer, db.ForeignKey('knowledge_files.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', foreign_keys=[user_id])
    file = db.relationship('KnowledgeFile', foreign_keys=[file_id])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'file_id', name='uq_kb_fav_user_file'),
        db.Index('idx_kbf_user_id', 'user_id'),
        db.Index('idx_kbf_file_id', 'file_id'),
    )


class KnowledgeBrowseLog(db.Model):
    """知识库浏览记录"""
    __tablename__ = 'knowledge_browse_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    file_id = db.Column(db.Integer, db.ForeignKey('knowledge_files.id'))
    browsed_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', foreign_keys=[user_id])
    file = db.relationship('KnowledgeFile', foreign_keys=[file_id])

    __table_args__ = (
        db.Index('idx_kbbl_user_id', 'user_id'),
        db.Index('idx_kbbl_file_id', 'file_id'),
        db.Index('idx_kbbl_browsed_at', 'browsed_at'),
    )



class Position(db.Model):

    """岗位"""
    __tablename__ = 'positions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='岗位名称')
    code = db.Column(db.String(50), comment='岗位编码')
    dept_id = db.Column(db.Integer, db.ForeignKey('departments.id'), comment='所属部门')
    role_name = db.Column(db.String(50), comment='对应系统角色（关联roles.name）')
    level = db.Column(db.String(20), default='staff', comment='岗位级别: executive/manager/supervisor/staff')
    headcount = db.Column(db.Integer, default=1, comment='核定人数')
    description = db.Column(db.Text, comment='岗位职责描述')
    requirements = db.Column(db.Text, comment='任职要求')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 该岗位上的用户
    users = db.relationship('User', foreign_keys='User.position_id', lazy='select')

    __table_args__ = (
        db.Index('idx_pos_dept_id', 'dept_id'),
        db.Index('idx_pos_role_name', 'role_name'),
        db.Index('idx_pos_is_active', 'is_active'),
    )


# ==================== 网站爬虫模块 ====================
class CrawlerTask(db.Model):
    """爬虫任务配置"""
    __tablename__ = 'crawler_tasks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment='任务名称')
    base_url = db.Column(db.String(500), nullable=False, comment='起始网址')
    status = db.Column(db.String(20), default='idle', comment='状态: idle/running/paused/stopped')
    max_threads = db.Column(db.Integer, default=5, comment='线程数')
    max_depth = db.Column(db.Integer, default=3, comment='最大抓取层级：0=仅起始页，1=一级下级页')
    attachment_handling = db.Column(db.String(20), default='skip', comment='附件处理: skip/log/db/download')
    download_dir = db.Column(db.String(500), comment='下载目录')
    schedule_enabled = db.Column(db.Boolean, default=False, comment='启用调度')

    schedule_interval = db.Column(db.Integer, default=24, comment='调度间隔(小时)')
    schedule_time = db.Column(db.String(10), default='00:00', comment='每日执行时间')
    pages_count = db.Column(db.Integer, default=0, comment='已爬取页面数')
    last_run_at = db.Column(db.DateTime, comment='上次运行时间')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.Index('idx_ct_status', 'status'),
        db.Index('idx_ct_base_url', 'base_url'),
    )


class CrawlerPage(db.Model):
    """爬虫存储的页面"""
    __tablename__ = 'crawler_pages'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('crawler_tasks.id'), comment='所属任务')
    url = db.Column(db.String(1000), unique=True, nullable=False, comment='页面URL')
    title = db.Column(db.String(500), comment='页面标题')
    content = db.Column(db.Text, comment='原始HTML')
    text_content = db.Column(db.Text, comment='纯文本内容')
    status = db.Column(db.String(20), default='pending', comment='状态: pending/completed/error/skipped')
    error_msg = db.Column(db.Text, comment='错误信息')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.Index('idx_cp_task_id', 'task_id'),
        db.Index('idx_cp_status', 'status'),
        db.Index('idx_cp_url', 'url'),
        db.Index('idx_cp_text', 'text_content'),
    )


class CrawlerAttachment(db.Model):
    """爬虫附件记录"""
    __tablename__ = 'crawler_attachments'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('crawler_tasks.id'))
    url = db.Column(db.String(1000), unique=True, nullable=False)
    filename = db.Column(db.String(255))
    content_type = db.Column(db.String(100))
    file_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)


# ==================== 栏目监测模块 ====================
class UrlLibrary(db.Model):
    """网址库"""
    __tablename__ = 'url_libraries'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment='库名称')
    description = db.Column(db.String(500), comment='库描述')
    category = db.Column(db.String(100), comment='分类')
    item_count = db.Column(db.Integer, default=0, comment='网址数量')
    expiring_days = db.Column(db.Integer, default=8, comment='即将逾期天数阈值')
    last_monitor_at = db.Column(db.DateTime, comment='上次监测时间')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.Index('idx_ul_name', 'name'),
    )


class UrlItem(db.Model):
    """网址库中的单个网址"""
    __tablename__ = 'url_items'

    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey('url_libraries.id'), nullable=False)
    serial_no = db.Column(db.String(50), comment='序号')
    column_name = db.Column(db.String(500), comment='栏目名称')
    url = db.Column(db.String(1000), nullable=False, comment='网址')
    column_category = db.Column(db.String(100), comment='栏目分类')
    update_deadline = db.Column(db.String(50), comment='更新期限(如:2周)')
    deadline_days = db.Column(db.Integer, comment='期限天数')
    website_name = db.Column(db.String(200), comment='网站名称')
    website_code = db.Column(db.String(100), comment='网站标识码')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.Index('idx_ui_library_id', 'library_id'),
        db.Index('idx_ui_url', 'url'),
    )


class MonitorResult(db.Model):
    """栏目监测结果"""
    __tablename__ = 'monitor_results'

    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey('url_libraries.id'))
    url_item_id = db.Column(db.Integer, db.ForeignKey('url_items.id'))
    url = db.Column(db.String(1000), nullable=False)
    column_name = db.Column(db.String(500))
    column_category = db.Column(db.String(100))
    update_deadline = db.Column(db.String(50))
    deadline_days = db.Column(db.Integer)
    last_max_date = db.Column(db.Date, comment='页面中提取到的最大日期')
    days_since_update = db.Column(db.Integer, comment='距今天数')
    is_overdue = db.Column(db.Boolean, default=False, comment='是否逾期')
    is_expiring = db.Column(db.Boolean, default=False, comment='即将逾期(3天内)')
    status = db.Column(db.String(20), default='pending', comment='pending/completed/error')
    error_msg = db.Column(db.Text)
    monitor_time = db.Column(db.DateTime, default=datetime.now, comment='监测时间')

    __table_args__ = (
        db.Index('idx_mr_library_id', 'library_id'),
        db.Index('idx_mr_is_overdue', 'is_overdue'),
        db.Index('idx_mr_monitor_time', 'monitor_time'),
    )


class MonitorLog(db.Model):
    """监测日志"""
    __tablename__ = 'monitor_logs'

    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey('url_libraries.id'))
    level = db.Column(db.String(10), default='info')  # info/warning/error
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


class MonitorScheduledTask(db.Model):
    """栏目监测定时任务"""
    __tablename__ = 'monitor_scheduled_tasks'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment='任务名称')
    library_id = db.Column(db.Integer, db.ForeignKey('url_libraries.id'), nullable=False, comment='监测的网址库')
    cron_expression = db.Column(db.String(100), comment='Cron表达式，如"每天 08:00"')
    email_recipients = db.Column(db.Text, comment='邮件接收人(JSON数组)')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    last_run_time = db.Column(db.DateTime, comment='最后执行时间')
    run_count = db.Column(db.Integer, default=0, comment='执行次数')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    library = db.relationship('UrlLibrary', backref='scheduled_tasks')

    __table_args__ = (
        db.Index('idx_mst_library_id', 'library_id'),
        db.Index('idx_mst_is_active', 'is_active'),
    )


class MonitorSystemLog(db.Model):
    """栏目监测系统日志"""
    __tablename__ = 'monitor_system_logs'

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(10), default='INFO', comment='日志级别')
    module = db.Column(db.String(50), comment='模块')
    message = db.Column(db.Text, comment='日志内容')
    details = db.Column(db.Text, comment='详细信息(JSON)')
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)

    @staticmethod
    def log(level, module, message, details=None):
        """记录日志"""
        import json
        log_entry = MonitorSystemLog(
            level=level,
            module=module,
            message=message,
            details=json.dumps(details, ensure_ascii=False) if details else None
        )
        db.session.add(log_entry)
        db.session.commit()

    __table_args__ = (
        db.Index('idx_msl_created_at', 'created_at'),
    )


# ==================== 会议管理模块 ====================
class MeetingRoom(db.Model):
    """会议室管理"""
    __tablename__ = 'meeting_rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='会议室名称')
    location = db.Column(db.String(200), comment='位置')
    capacity = db.Column(db.Integer, default=10, comment='容纳人数')
    equipment = db.Column(db.String(500), comment='设备信息')
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='会议室管理员')
    status = db.Column(db.String(20), default='available', comment='状态: available/maintenance/disabled')
    remark = db.Column(db.String(300), comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    manager = db.relationship('User', foreign_keys=[manager_id])
    meetings = db.relationship('Meeting', backref='room', lazy='dynamic')

    __table_args__ = (
        db.Index('idx_mr_name', 'name'),
        db.Index('idx_mr_status', 'status'),
    )


class Meeting(db.Model):
    """会议管理"""
    __tablename__ = 'meetings'

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False, comment='会议主题')
    meeting_type = db.Column(db.String(50), default='办公会', comment='会议类型')
    level = db.Column(db.String(30), default='部门级', comment='会议层级')
    priority = db.Column(db.String(20), default='普通', comment='优先级')
    room_id = db.Column(db.Integer, db.ForeignKey('meeting_rooms.id'), comment='会议室')
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='主持人')
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='发起人')
    attendee_ids = db.Column(db.Text, comment='参会人员ID列表(JSON)')
    attendee_depts = db.Column(db.String(500), comment='参会部门')
    agenda = db.Column(db.Text, comment='会议议程')
    minutes = db.Column(db.Text, comment='会议纪要')
    related_doc_id = db.Column(db.Integer, db.ForeignKey('official_docs.id'), comment='关联公文')
    require_signin = db.Column(db.Boolean, default=True, comment='是否签到')
    status = db.Column(db.String(20), default='draft', comment='状态: draft/pending/confirmed/in_progress/completed/cancelled')
    start_time = db.Column(db.DateTime, comment='开始时间')
    end_time = db.Column(db.DateTime, comment='结束时间')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    host = db.relationship('User', foreign_keys=[host_id], backref='hosted_meetings')
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_meetings')
    related_doc = db.relationship('OfficialDoc', foreign_keys=[related_doc_id])

    def get_attendee_ids(self):
        import json
        return json.loads(self.attendee_ids) if self.attendee_ids else []

    def set_attendee_ids(self, id_list):
        import json
        self.attendee_ids = json.dumps(id_list, ensure_ascii=False)

    __table_args__ = (
        db.Index('idx_meeting_status', 'status'),
        db.Index('idx_meeting_start_time', 'start_time'),
        db.Index('idx_meeting_creator', 'creator_id'),
        db.Index('idx_meeting_host', 'host_id'),
    )


class MeetingAttendance(db.Model):
    """会议签到与参会反馈"""
    __tablename__ = 'meeting_attendances'

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=False, comment='会议ID')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='参会人')
    attendance_status = db.Column(db.String(20), default='pending', comment='状态: pending/signed/leave/absent')
    signin_time = db.Column(db.DateTime, comment='签到时间')
    feedback = db.Column(db.Text, comment='参会反馈')
    remark = db.Column(db.String(300), comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    meeting = db.relationship('Meeting', backref=db.backref('attendance_records', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', foreign_keys=[user_id], backref='meeting_attendances')

    __table_args__ = (
        db.UniqueConstraint('meeting_id', 'user_id', name='uq_meeting_attendance_user'),
        db.Index('idx_ma_meeting_id', 'meeting_id'),
        db.Index('idx_ma_user_id', 'user_id'),
        db.Index('idx_ma_status', 'attendance_status'),
    )


# ==================== 督查督办模块 ====================
class SupervisionTask(db.Model):

    """督查督办任务"""
    __tablename__ = 'supervision_tasks'

    id = db.Column(db.Integer, primary_key=True)
    task_no = db.Column(db.String(50), unique=True, comment='任务编号')
    title = db.Column(db.String(200), nullable=False, comment='任务标题')
    category = db.Column(db.String(50), default='重点工作', comment='任务分类')
    source = db.Column(db.String(100), default='领导交办', comment='任务来源')
    content = db.Column(db.Text, comment='任务内容')
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='下达人')
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='负责人')
    helper_ids = db.Column(db.Text, comment='协办人员ID列表(JSON)')
    priority = db.Column(db.String(20), default='中', comment='优先级')
    status = db.Column(db.String(20), default='draft', comment='状态: draft/issued/processing/review/completed/overdue/cancelled')
    progress_percent = db.Column(db.Integer, default=0, comment='进度百分比')
    due_date = db.Column(db.DateTime, comment='办结时限')
    completed_at = db.Column(db.DateTime, comment='完成时间')
    result_summary = db.Column(db.Text, comment='办理结果')
    source_doc_id = db.Column(db.Integer, db.ForeignKey('official_docs.id'), comment='来源公文')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_supervision_tasks')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_supervision_tasks')
    source_doc = db.relationship('OfficialDoc', foreign_keys=[source_doc_id])
    progress_logs = db.relationship('SupervisionProgress', backref='task', lazy='dynamic', cascade='all, delete-orphan')

    def get_helper_ids(self):
        import json
        return json.loads(self.helper_ids) if self.helper_ids else []

    def set_helper_ids(self, id_list):
        import json
        self.helper_ids = json.dumps(id_list, ensure_ascii=False)

    __table_args__ = (
        db.Index('idx_st_task_no', 'task_no'),
        db.Index('idx_st_owner_id', 'owner_id'),
        db.Index('idx_st_creator_id', 'creator_id'),
        db.Index('idx_st_status', 'status'),
        db.Index('idx_st_due_date', 'due_date'),
    )


class SupervisionProgress(db.Model):
    """督办办理记录"""
    __tablename__ = 'supervision_progresses'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('supervision_tasks.id'), nullable=False, comment='任务ID')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='操作人')
    action = db.Column(db.String(30), default='update', comment='动作类型')
    progress_percent = db.Column(db.Integer, default=0, comment='进度')
    note = db.Column(db.Text, comment='办理说明')
    created_at = db.Column(db.DateTime, default=datetime.now)

    operator = db.relationship('User', foreign_keys=[operator_id])

    __table_args__ = (
        db.Index('idx_sp_task_id', 'task_id'),
        db.Index('idx_sp_operator_id', 'operator_id'),
        db.Index('idx_sp_created_at', 'created_at'),
    )


# ==================== 绩效考核模块 ====================
class PerformancePeriod(db.Model):
    """绩效考核周期"""
    __tablename__ = 'performance_periods'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, comment='周期名称')
    period_type = db.Column(db.String(20), default='monthly', comment='周期类型')
    start_date = db.Column(db.Date, comment='开始日期')
    end_date = db.Column(db.Date, comment='结束日期')
    status = db.Column(db.String(20), default='active', comment='状态: active/closed')
    remark = db.Column(db.String(300), comment='备注')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), comment='创建人')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    creator = db.relationship('User', foreign_keys=[created_by])
    assessments = db.relationship('PerformanceAssessment', backref='period', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_pp_status', 'status'),
        db.Index('idx_pp_start_end', 'start_date', 'end_date'),
    )


class PerformanceAssessment(db.Model):
    """绩效台账记录"""
    __tablename__ = 'performance_assessments'

    id = db.Column(db.Integer, primary_key=True)
    period_id = db.Column(db.Integer, db.ForeignKey('performance_periods.id'), comment='考核周期')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='被考核人')
    assessor_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='考核人')
    project_name = db.Column(db.String(200), nullable=False, comment='考核项目')
    category = db.Column(db.String(50), default='重点工作', comment='项目分类')
    score = db.Column(db.Float, default=0, comment='得分')
    full_score = db.Column(db.Float, default=100, comment='满分')
    weight = db.Column(db.Float, default=1, comment='权重')
    evaluation = db.Column(db.Text, comment='评价')
    highlights = db.Column(db.Text, comment='亮点或改进项')
    status = db.Column(db.String(20), default='draft', comment='状态: draft/published')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    employee = db.relationship('User', foreign_keys=[user_id], backref='performance_records')
    assessor = db.relationship('User', foreign_keys=[assessor_id], backref='performance_created_records')

    __table_args__ = (
        db.Index('idx_pa_user_id', 'user_id'),
        db.Index('idx_pa_period_id', 'period_id'),
        db.Index('idx_pa_status', 'status'),
    )


# ==================== 工作日志模块 ====================
class WorkLog(db.Model):
    """工作日志"""
    __tablename__ = 'work_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='填写人')
    log_date = db.Column(db.Date, default=lambda: datetime.now().date(), comment='日志日期')
    title = db.Column(db.String(200), nullable=False, comment='日志标题')
    category = db.Column(db.String(50), default='日常工作', comment='日志分类')
    content = db.Column(db.Text, comment='工作内容')
    achievements = db.Column(db.Text, comment='工作成果')
    issues = db.Column(db.Text, comment='存在问题')
    tomorrow_plan = db.Column(db.Text, comment='明日计划')
    hours = db.Column(db.Float, default=8, comment='投入工时')
    status = db.Column(db.String(20), default='draft', comment='状态: draft/submitted/returned/reviewed')

    related_task_id = db.Column(db.Integer, db.ForeignKey('supervision_tasks.id'), comment='关联督办任务')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    user = db.relationship('User', foreign_keys=[user_id], backref='work_logs')
    related_task = db.relationship('SupervisionTask', foreign_keys=[related_task_id])

    __table_args__ = (
        db.Index('idx_wl_user_date', 'user_id', 'log_date'),
        db.Index('idx_wl_status', 'status'),
        db.Index('idx_wl_log_date', 'log_date'),
    )


class WorkLogReview(db.Model):
    """工作日志审批留痕"""
    __tablename__ = 'work_log_reviews'

    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('work_logs.id'), nullable=False, comment='日志ID')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment='操作人')
    action = db.Column(db.String(20), default='submit', comment='动作: save_draft/submit/resubmit/review/return')
    from_status = db.Column(db.String(20), comment='原状态')
    to_status = db.Column(db.String(20), comment='目标状态')
    comment = db.Column(db.Text, comment='审批意见')
    created_at = db.Column(db.DateTime, default=datetime.now)

    log = db.relationship('WorkLog', backref=db.backref('review_logs', lazy='dynamic', cascade='all, delete-orphan'))
    operator = db.relationship('User', foreign_keys=[operator_id])

    __table_args__ = (
        db.Index('idx_wlr_log_id', 'log_id'),
        db.Index('idx_wlr_operator_id', 'operator_id'),
        db.Index('idx_wlr_action', 'action'),
        db.Index('idx_wlr_created_at', 'created_at'),
    )


# ==================== 系统配置管理模型 ====================
class SystemConfig(db.Model):
    """系统配置表 - 存储动态配置参数"""
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False, comment='配置键名')
    config_value = db.Column(db.Text, comment='配置值')
    config_type = db.Column(db.String(20), default='string', comment='配置类型: string/integer/float/boolean/json')
    category = db.Column(db.String(50), default='system', comment='配置分类: system/knowledge/upload/ai/security')
    module = db.Column(db.String(50), comment='所属模块')
    description = db.Column(db.String(500), comment='配置描述')
    is_public = db.Column(db.Boolean, default=False, comment='是否公开配置（对用户可见）')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), comment='最后修改人')
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    updater = db.relationship('User', foreign_keys=[updated_by])
    
    def get_value(self):
        """根据类型解析配置值"""
        if not self.config_value:
            return None
        
        if self.config_type == 'integer':
            return int(self.config_value)
        elif self.config_type == 'float':
            return float(self.config_value)
        elif self.config_type == 'boolean':
            return self.config_value.lower() in ('true', 'yes', '1', 'on')
        elif self.config_type == 'json':
            import json
            return json.loads(self.config_value)
        else:  # string
            return str(self.config_value)
    
    def set_value(self, value):
        """根据类型设置配置值"""
        if value is None:
            self.config_value = ''
        elif self.config_type == 'integer':
            self.config_value = str(int(value))
        elif self.config_type == 'float':
            self.config_value = str(float(value))
        elif self.config_type == 'boolean':
            self.config_value = 'true' if value else 'false'
        elif self.config_type == 'json':
            import json
            self.config_value = json.dumps(value, ensure_ascii=False)
        else:  # string
            self.config_value = str(value)
    
    __table_args__ = (
        db.Index('idx_sc_config_key', 'config_key'),
        db.Index('idx_sc_category', 'category'),
        db.Index('idx_sc_module', 'module'),
    )

