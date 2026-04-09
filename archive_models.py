# -*- coding: utf-8 -*-
"""
档案管理系统 - 数据模型
基于知识库功能扩展，符合档案国家标准
"""
from datetime import datetime
from models import db

class ArchiveFonds(db.Model):
    """全宗管理 - 档案管理的基本单位"""
    __tablename__ = 'archive_fonds'
    
    id = db.Column(db.Integer, primary_key=True)
    fonds_code = db.Column(db.String(20), unique=True, nullable=False, comment='全宗号')
    fonds_name = db.Column(db.String(200), nullable=False, comment='全宗名称')
    fonds_type = db.Column(db.String(50), comment='全宗类型（机关/企业/个人）')
    description = db.Column(db.Text, comment='全宗说明')
    start_date = db.Column(db.Date, comment='档案起始日期')
    end_date = db.Column(db.Date, comment='档案终止日期')
    total_volumes = db.Column(db.Integer, default=0, comment='案卷总数')
    total_files = db.Column(db.Integer, default=0, comment='文件总数')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 关联
    creator = db.relationship('User', foreign_keys=[created_by])
    catalogs = db.relationship('ArchiveCatalog', backref='fonds', lazy='dynamic')
    
    def __repr__(self):
        return f'<ArchiveFonds {self.fonds_code}: {self.fonds_name}>'


class ArchiveCatalog(db.Model):
    """档案目录 - 全宗下的分类目录"""
    __tablename__ = 'archive_catalogs'
    
    id = db.Column(db.Integer, primary_key=True)
    fonds_id = db.Column(db.Integer, db.ForeignKey('archive_fonds.id'), nullable=False)
    catalog_code = db.Column(db.String(20), nullable=False, comment='目录号/分类号')
    catalog_name = db.Column(db.String(200), nullable=False, comment='目录名称')
    catalog_type = db.Column(db.String(50), comment='目录类型')
    parent_id = db.Column(db.Integer, db.ForeignKey('archive_catalogs.id'), nullable=True)
    description = db.Column(db.Text, comment='目录说明')
    retention_period = db.Column(db.String(20), comment='保管期限（永久/30年/10年）')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 自关联 - 层级结构
    children = db.relationship('ArchiveCatalog', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    volumes = db.relationship('ArchiveVolume', backref='catalog', lazy='dynamic')
    
    def get_full_code(self):
        """获取完整目录代码"""
        if self.parent:
            return f"{self.parent.get_full_code()}-{self.catalog_code}"
        return self.catalog_code
    
    def __repr__(self):
        return f'<ArchiveCatalog {self.catalog_code}: {self.catalog_name}>'


class ArchiveVolume(db.Model):
    """案卷管理 - 档案的物理/逻辑卷"""
    __tablename__ = 'archive_volumes'
    
    id = db.Column(db.Integer, primary_key=True)
    fonds_id = db.Column(db.Integer, db.ForeignKey('archive_fonds.id'), nullable=False)
    catalog_id = db.Column(db.Integer, db.ForeignKey('archive_catalogs.id'), nullable=False)
    volume_code = db.Column(db.String(50), nullable=False, comment='案卷号')
    volume_title = db.Column(db.String(500), nullable=False, comment='案卷题名')
    volume_year = db.Column(db.Integer, comment='年度')
    start_date = db.Column(db.Date, comment='起始日期')
    end_date = db.Column(db.Date, comment='终止日期')
    total_pages = db.Column(db.Integer, default=0, comment='总页数')
    total_files = db.Column(db.Integer, default=0, comment='卷内文件数')
    
    # 档案属性
    retention_period = db.Column(db.String(20), comment='保管期限')
    security_level = db.Column(db.String(20), default='公开', comment='密级')
    responsibility = db.Column(db.String(200), comment='责任者')
    storage_location = db.Column(db.String(200), comment='存放位置')
    
    # 数字化信息
    is_digitized = db.Column(db.Boolean, default=False, comment='是否已数字化')
    digitized_at = db.Column(db.DateTime, comment='数字化日期')
    digitized_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    scan_quality = db.Column(db.String(50), comment='扫描质量')
    
    description = db.Column(db.Text, comment='案卷说明')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    files = db.relationship('ArchiveFile', backref='volume', lazy='dynamic')
    digitizer = db.relationship('User', foreign_keys=[digitized_by])
    
    def get_archive_code(self):
        """生成完整档号"""
        return f"{self.fonds.fonds_code}-{self.catalog.catalog_code}-{self.volume_code}"
    
    def __repr__(self):
        return f'<ArchiveVolume {self.volume_code}: {self.volume_title}>'


class ArchiveFile(db.Model):
    """
    档案文件 - 单份档案文件
    符合以下国家档案标准：
      DA/T 18-1999  《档案著录规则》
      DA/T 22-2015  《归档文件整理规则》
      DA/T 31-2005  《纸质档案数字化技术规范》
      DA/T 47-2009  《纸质档案数字化扫描工作规范》
      GB/T 9705-2008《文书档案案卷格式》
    """
    __tablename__ = 'archive_files'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ── 档号体系（DA/T 18 § 3.1 档号）──────────────
    fonds_id = db.Column(db.Integer, db.ForeignKey('archive_fonds.id'), nullable=False)
    catalog_id = db.Column(db.Integer, db.ForeignKey('archive_catalogs.id'), nullable=False)
    volume_id = db.Column(db.Integer, db.ForeignKey('archive_volumes.id'))
    file_code = db.Column(db.String(50), nullable=False, comment='件号/文件号')
    full_archive_code = db.Column(db.String(100), index=True, comment='完整档号（全宗-目录-案卷-件号）')
    
    # ── 核心著录项（DA/T 18 必填项）─────────────────
    title = db.Column(db.String(500), nullable=False, comment='题名（DA/T18 § 5.1，必填）')
    parallel_title = db.Column(db.String(500), comment='并列题名（DA/T18 § 5.2）')
    responsibility = db.Column(db.String(500), comment='责任者（形成单位/作者，DA/T18 § 5.3，必填）')
    file_date = db.Column(db.Date, comment='文件日期（DA/T18 § 5.4，必填）')
    file_year = db.Column(db.Integer, index=True, comment='年度（DA/T22 § 4.1）')
    
    # ── 档案管理属性（DA/T 22 必填项）───────────────
    retention_period = db.Column(db.String(20), comment='保管期限（永久/30年/10年，DA/T22，必填）')
    security_level = db.Column(db.String(20), default='公开', comment='密级（公开/内部/秘密/机密/绝密）')
    archive_type = db.Column(db.String(50), comment='档案类型（文书/科技/会计/声像/实物）')
    file_category = db.Column(db.String(100), comment='文件类别（大类/小类）')
    reference_number = db.Column(db.String(100), index=True, comment='文号/发文字号（DA/T18 § 5.5）')
    
    # ── 物理属性（DA/T 18 著录项）───────────────────
    page_count = db.Column(db.Integer, comment='页数（DA/T18 § 5.9）')
    carrier_type = db.Column(db.String(50), default='纸质', comment='载体类型（纸质/胶片/磁盘/光盘/数字）')
    storage_location = db.Column(db.String(200), comment='存放位置（库房/架位/盒号）')
    physical_condition = db.Column(db.String(50), comment='实物状况（良好/一般/破损）')
    
    # ── 扩展著录（DA/T 18 选填项，国标推荐）─────────
    abstract = db.Column(db.Text, comment='摘要（DA/T18 § 5.8）')
    subject_headings = db.Column(db.String(500), comment='主题词（DA/T18 § 5.7，分号分隔）')
    language = db.Column(db.String(20), default='中文', comment='语种（DA/T18 § 5.6）')
    related_archives = db.Column(db.String(500), comment='相关档案号（DA/T18 § 5.10）')
    
    # ── 开放/利用信息 ────────────────────────────────
    open_status = db.Column(db.String(20), default='开放', comment='开放状态（开放/控制使用/不开放）')
    open_date = db.Column(db.Date, comment='开放日期')
    use_restriction = db.Column(db.String(200), comment='利用限制说明')
    
    # ── 数字化信息（DA/T 31 § 5）────────────────────
    is_digitized = db.Column(db.Boolean, default=False, comment='是否已数字化')
    digitized_at = db.Column(db.DateTime, comment='数字化日期')
    digitized_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    scan_device = db.Column(db.String(200), comment='扫描设备型号')
    scan_operator = db.Column(db.String(100), comment='扫描操作员')
    scan_date = db.Column(db.Date, comment='扫描日期')
    
    # ── 数字文件技术元数据（DA/T 31 § 6）────────────
    original_filename = db.Column(db.String(500), comment='原始文件名')
    file_path = db.Column(db.String(500), comment='主存储路径（TIFF）')
    tiff_path = db.Column(db.String(500), comment='TIFF归档路径（DA/T31规定主格式）')
    jpeg_path = db.Column(db.String(500), comment='JPEG查阅副本路径')
    pdf_path = db.Column(db.String(500), comment='PDF/A路径（含OCR文字层）')
    file_size = db.Column(db.BigInteger, comment='文件大小（字节）')
    file_format = db.Column(db.String(20), comment='主格式（TIFF/PDF/JPG）')
    scan_resolution = db.Column(db.String(20), default='300', comment='扫描分辨率DPI（DA/T31 § 4.3，≥300）')
    actual_dpi = db.Column(db.Integer, comment='实测DPI值')
    color_mode = db.Column(db.String(20), comment='色彩模式（彩色/灰度/黑白）')
    compression_type = db.Column(db.String(50), comment='压缩方式（LZW/CCITT G4/JPEG等）')
    image_width = db.Column(db.Integer, comment='图像宽度（像素）')
    image_height = db.Column(db.Integer, comment='图像高度（像素）')
    
    # ── 图像处理信息（DA/T 47）───────────────────────
    deskew_angle = db.Column(db.Float, default=0.0, comment='纠偏角度（度）')
    border_removed = db.Column(db.Boolean, default=False, comment='是否已去黑边')
    enhanced = db.Column(db.Boolean, default=False, comment='是否已图像增强')
    
    # ── OCR信息（DA/T 31 § 4.5）─────────────────────
    has_ocr_layer = db.Column(db.Boolean, default=False, comment='PDF是否含OCR文字层')
    ocr_engine = db.Column(db.String(50), comment='OCR引擎（tesseract版本等）')
    ocr_language = db.Column(db.String(50), default='chi_sim+eng', comment='OCR识别语言')
    ocr_confidence = db.Column(db.Float, comment='OCR平均置信度（0-100）')
    
    # ── 质量检验（DA/T 47 § 5）───────────────────────
    quality_score = db.Column(db.Integer, comment='质量评分（0-100）')
    quality_checked = db.Column(db.Boolean, default=False, comment='是否已通过质检')
    quality_checked_at = db.Column(db.DateTime, comment='质检时间')
    quality_checked_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    quality_report = db.Column(db.Text, comment='质检报告（JSON）')
    dpi_compliant = db.Column(db.Boolean, comment='DPI是否达标（≥300）')
    format_compliant = db.Column(db.Boolean, comment='格式是否合规（有TIFF/PDF）')
    
    # ── 文件完整性（DA/T 31 § 4.6）──────────────────
    file_checksum = db.Column(db.String(64), comment='文件MD5/SHA256校验值')
    checksum_type = db.Column(db.String(10), default='MD5', comment='校验类型')
    
    # ── 智能提取内容（知识库功能）───────────────────
    content_text = db.Column(db.Text, comment='提取的文本内容（OCR或原文）')
    summary = db.Column(db.Text, comment='自动生成的摘要')
    keywords = db.Column(db.String(500), comment='关键词（逗号分隔）')
    tags = db.Column(db.String(500), comment='标签（逗号分隔）')
    
    # ── 向量检索（知识库功能）───────────────────────
    embedding = db.Column(db.LargeBinary, comment='文本向量嵌入')
    is_vectorized = db.Column(db.Boolean, default=False, comment='是否已生成向量')
    
    # ── 附注（DA/T 18 § 5.11）──────────────────────
    description = db.Column(db.Text, comment='附注/备注说明')
    
    # ── 管理信息 ─────────────────────────────────────
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(20), default='active', comment='状态（active/archived/deleted）')
    is_active = db.Column(db.Boolean, default=True, comment='是否有效')
    
    # ── 关联 ─────────────────────────────────────────
    fonds = db.relationship('ArchiveFonds', foreign_keys=[fonds_id])
    catalog = db.relationship('ArchiveCatalog', foreign_keys=[catalog_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    digitizer = db.relationship('User', foreign_keys=[digitized_by])
    quality_checker = db.relationship('User', foreign_keys=[quality_checked_by])
    borrow_records = db.relationship('ArchiveBorrow', backref='archive_file', lazy='dynamic')
    
    # ── 索引（优化查询性能）─────────────────────────
    __table_args__ = (
        db.Index('idx_archive_file_fonds', 'fonds_id'),
        db.Index('idx_archive_file_catalog', 'catalog_id'),
        db.Index('idx_archive_file_volume', 'volume_id'),
        db.Index('idx_archive_file_year', 'file_year'),
        db.Index('idx_archive_file_date', 'file_date'),
        db.Index('idx_archive_file_status', 'status'),
        db.Index('idx_archive_file_digitized', 'is_digitized'),
        db.Index('idx_archive_file_code', 'full_archive_code'),
        db.Index('idx_archive_file_ref', 'reference_number'),
        db.Index('idx_archive_file_quality', 'quality_checked', 'quality_score'),
        db.Index('idx_archive_file_dpi', 'dpi_compliant'),
        db.Index('idx_archive_retention', 'retention_period'),
        db.Index('idx_archive_security', 'security_level'),
        db.Index('idx_archive_open_status', 'open_status'),
    )
    
    def get_archive_code(self):
        """生成完整档号（DA/T 18格式）"""
        if self.full_archive_code:
            return self.full_archive_code
        parts = [
            self.fonds.fonds_code if self.fonds else '',
            self.catalog.catalog_code if self.catalog else '',
            self.volume.volume_code if self.volume else '',
            self.file_code
        ]
        return '-'.join(filter(None, parts))
    
    def get_keywords_list(self):
        """获取关键词列表"""
        return [k.strip() for k in self.keywords.split(',') if k.strip()] if self.keywords else []
    
    def get_tags_list(self):
        """获取标签列表"""
        return [t.strip() for t in self.tags.split(',') if t.strip()] if self.tags else []
    
    def get_subject_headings_list(self):
        """获取主题词列表"""
        return [s.strip() for s in self.subject_headings.split(';') if s.strip()] \
               if self.subject_headings else []
    
    def is_standard_compliant(self):
        """检查是否符合国标基本要求"""
        issues = []
        if not self.title:
            issues.append('缺少题名')
        if not self.responsibility:
            issues.append('缺少责任者')
        if not self.file_date:
            issues.append('缺少文件日期')
        if not self.retention_period:
            issues.append('缺少保管期限')
        if self.is_digitized:
            if not self.dpi_compliant:
                issues.append('DPI不达标（< 300）')
            if not self.format_compliant:
                issues.append('缺少TIFF或PDF格式')
        return len(issues) == 0, issues
    
    def to_catalog_dict(self):
        """转换为目录著录格式（用于目录打印）"""
        return {
            '档号': self.get_archive_code(),
            '题名': self.title,
            '责任者': self.responsibility or '',
            '文号': self.reference_number or '',
            '日期': self.file_date.strftime('%Y-%m-%d') if self.file_date else '',
            '页数': str(self.page_count or ''),
            '保管期限': self.retention_period or '',
            '密级': self.security_level or '公开',
            '备注': self.description or '',
        }
    
    def __repr__(self):
        return f'<ArchiveFile {self.file_code}: {self.title}>'


class ArchiveBorrow(db.Model):
    """档案借阅记录"""
    __tablename__ = 'archive_borrows'
    
    id = db.Column(db.Integer, primary_key=True)
    archive_file_id = db.Column(db.Integer, db.ForeignKey('archive_files.id'), nullable=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow, comment='借阅日期')
    return_date = db.Column(db.DateTime, comment='应还日期')
    actual_return_date = db.Column(db.DateTime, comment='实际归还日期')
    purpose = db.Column(db.String(500), comment='借阅目的')
    status = db.Column(db.String(20), default='borrowed', comment='状态')
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    notes = db.Column(db.Text, comment='备注/拒绝原因')
    
    # 关联
    borrower = db.relationship('User', foreign_keys=[borrower_id])
    approver = db.relationship('User', foreign_keys=[approver_id])

    @property
    def approved_by(self):
        """兼容旧字段名，映射到 approver_id。"""
        return self.approver_id

    @approved_by.setter
    def approved_by(self, value):
        self.approver_id = value

    @property
    def reject_reason(self):
        """兼容旧字段名，复用 notes 持久化拒绝原因。"""
        return self.notes

    @reject_reason.setter
    def reject_reason(self, value):
        self.notes = value

    @property
    def due_date(self):
        return self.return_date

    @property
    def file_id(self):
        return self.archive_file_id

    @property
    def file_title(self):
        return self.archive_file.title if self.archive_file else None

    @property
    def archive_code(self):
        return self.archive_file.get_archive_code() if self.archive_file else None

    @property
    def fonds_name(self):
        if self.archive_file and self.archive_file.fonds:
            return self.archive_file.fonds.fonds_name
        return None

    @property
    def is_overdue(self):
        return bool(
            self.status == 'borrowed' and
            self.return_date and
            datetime.now() > self.return_date
        )
    
    def __repr__(self):
        return f'<ArchiveBorrow {self.id}: {self.archive_file_id}>'


class ArchiveNotification(db.Model):
    """
    档案系统消息通知
    用于借阅审批结果推送、任务完成通知等
    """
    __tablename__ = 'archive_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='接收人')
    title = db.Column(db.String(200), nullable=False, comment='通知标题')
    content = db.Column(db.Text, comment='通知内容')
    notif_type = db.Column(db.String(20), default='info', comment='类型: info/success/warning/danger')
    link = db.Column(db.String(300), comment='相关链接（可点击跳转）')
    is_read = db.Column(db.Boolean, default=False, comment='是否已读')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    user = db.relationship('User', foreign_keys=[user_id])
    
    __table_args__ = (
        db.Index('idx_notif_user_read', 'user_id', 'is_read'),
        db.Index('idx_notif_user_time', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f'<ArchiveNotification {self.id}: {self.title[:30]}>'


class ArchiveDigitizationTask(db.Model):
    """档案数字化任务 - 批量数字化管理"""
    __tablename__ = 'archive_digitization_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), nullable=False, comment='任务名称')
    fonds_id = db.Column(db.Integer, db.ForeignKey('archive_fonds.id'))
    catalog_id = db.Column(db.Integer, db.ForeignKey('archive_catalogs.id'))
    
    # 任务范围
    year_start = db.Column(db.Integer, comment='起始年度')
    year_end = db.Column(db.Integer, comment='终止年度')
    retention_period = db.Column(db.String(20), comment='指定保管期限')
    
    # 任务统计
    total_files = db.Column(db.Integer, default=0, comment='总文件数')
    completed_files = db.Column(db.Integer, default=0, comment='已完成数')
    failed_files = db.Column(db.Integer, default=0, comment='失败数')
    
    # 数字化参数
    scan_resolution = db.Column(db.String(20), default='300', comment='扫描分辨率')
    color_mode = db.Column(db.String(20), default='color', comment='色彩模式')
    enable_ocr = db.Column(db.Boolean, default=True, comment='启用OCR')
    ocr_language = db.Column(db.String(50), default='chi_sim+eng', comment='OCR语言')
    
    # 任务状态
    status = db.Column(db.String(20), default='pending', comment='状态')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # 关联
    creator = db.relationship('User', foreign_keys=[created_by])
    fonds = db.relationship('ArchiveFonds')
    catalog = db.relationship('ArchiveCatalog')
    
    def __repr__(self):
        return f'<ArchiveDigitizationTask {self.task_name}>'
