# OA系统智能知识库改造方案

## 概述
将桌面 `knmchat4.py` 政务知识库智能助手程序的功能整合到 OA 系统中，保留 OA 的三类知识库结构（个人/共享/政策），全面升级为智能知识库模块。

---

## 已创建的文件

### 1. 核心模块
- **`smart_knowledge.py`** - 智能知识库管理器
  - 本地嵌入模型 (`E:\pycodes\knm\all-MiniLM-L6-v2`)
  - TesseractOCR 图片文字识别
  - 智能关键词/标签/摘要提取
  - 批量文件处理

### 2. API路由 (已添加到 app.py)
- `POST /knowledge/api/batch_upload` - 批量上传 + 智能分析
- `POST /knowledge/api/analyze` - 文件预分析（预览元数据）
- `POST /knowledge/api/smart_search` - 智能检索（向量+关键词）

### 3. 前端页面
- **`personal_knowledge_base_new.html`** - 新版个人知识库页面
  - 拖拽批量上传
  - 实时进度显示
  - 文件卡片展示（含标签、摘要）
  - 智能搜索

---

## 功能对比

| 功能 | 原OA知识库 | knmchat4 | 新智能知识库 |
|------|-----------|----------|-------------|
| **批量上传** | ❌ 单文件 | ✅ 文件夹批量 | ✅ 拖拽多文件 |
| **关键词提取** | ❌ 无 | ✅ jieba自动提取 | ✅ jieba TF-IDF |
| **标签生成** | ❌ 手动分类 | ✅ 自动+手动 | ✅ 智能分类+关键词 |
| **摘要生成** | ❌ 无 | ✅ 取前几段 | ✅ 智能摘要 |
| **图片OCR** | ❌ 不支持 | ✅ PIL+OCR | ✅ TesseractOCR |
| **向量检索** | ❌ 无 | ✅ SentenceTransformer | ✅ 本地模型 |
| **文档预览** | ⚠️ txt/md/docx | ✅ 文本查看器 | ✅ 网页预览 |
| **AI聊天** | ✅ 有 | ✅ 有 | ✅ 整合到OA AI |

---

## 技术架构

### 本地模型配置
```python
# 嵌入模型路径
EMBEDDING_MODEL_PATH = r'E:\pycodes\knm\all-MiniLM-L6-v2'

# TesseractOCR 路径（需确认安装位置）
TESSERACT_CMD = r'E:\Tesseract-OCR\tesseract.exe'
```

### 支持的文件格式
- **文档**: PDF, DOC, DOCX, TXT, MD
- **表格**: XLS, XLSX, CSV
- **图片**: JPG, JPEG, PNG, BMP, TIFF (自动OCR)

### 数据库扩展
KnowledgeFile 模型新增字段:
- `keywords` - AI提取的关键词
- `embedding` - 文本向量(BLOB)
- `is_vectorized` - 向量生成状态

---

## 待完成事项

### 1. 确认TesseractOCR安装
需要确认 E 盘的 TesseractOCR 实际安装路径，或安装到默认位置。

### 2. 数据库迁移
运行以下命令更新数据库：
```bash
flask db migrate -m "add knowledge vector fields"
flask db upgrade
```

### 3. 页面替换
将 `personal_knowledge_base.html` 替换为新版本，或修改路由使用新模板。

### 4. 共享/政策知识库
为共享知识库和政策文件库创建类似的智能上传界面。

### 5. 向量检索优化
当前使用简化的相似度计算，建议后续集成 FAISS 或 Milvus 向量数据库。

---

## 使用流程

### 批量上传
1. 进入知识库页面
2. 拖拽文件到上传区域（支持多文件）
3. 系统自动：
   - 提取文本内容
   - 生成关键词
   - 自动分类标签
   - 生成摘要
   - 生成向量嵌入
4. 实时显示处理进度
5. 完成后刷新页面查看结果

### 智能搜索
1. 在搜索框输入关键词
2. 系统使用向量相似度 + 关键词匹配
3. 返回最相关的文档，显示匹配分数

---

## 下一步建议

1. **测试批量上传** - 验证多文件处理和智能分析
2. **配置Tesseract** - 确认OCR路径，测试图片识别
3. **优化向量检索** - 集成专业向量数据库
4. **添加文档预览** - 支持PDF/Word在线预览
5. **AI问答整合** - 将知识库问答整合到OA的AI对话中

---

创建时间: 2026-04-03
