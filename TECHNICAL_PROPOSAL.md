# 智能办公平台技术优化方案

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 编制日期 | 2026-04-01 |
| 适用范围 | 智能服务办公平台 v2.0 |

---

## 目录

1. [项目概述](#一项目概述)
2. [AI功能增强方案](#二ai功能增强方案)
3. [静态资源CDN配置方案](#三静态资源cdn配置方案)
4. [功能扩展方案](#四功能扩展方案)
5. [知识库管理优化方案](#五知识库管理优化方案)
6. [实施计划](#六实施计划)
7. [风险评估](#七风险评估)

---

## 一、项目概述

### 1.1 系统现状

当前智能办公平台基于 Flask 框架开发，采用 SQLite 数据库，已实现以下核心功能：

- **智能办公**：公文写作、润色、校对、拟办意见、会议纪要、PDF转换
- **知识库管理**：个人/共享/政策知识库
- **AI对话**：多模型支持（OpenAI、DeepSeek、SiliconFlow、本地模型）
- **专项报送**：信息报送与约稿管理
- **简报系统**：自动抓取生成简报
- **组织架构**：部门、岗位、人员管理

### 1.2 优化目标

| 优化方向 | 目标 | 优先级 |
|---------|------|--------|
| AI功能增强 | 流式输出、上下文记忆、重试机制 | P0 |
| CDN配置 | 静态资源加速、减轻服务器压力 | P1 |
| 功能扩展 | 消息通知、移动端适配、工作流 | P1 |
| 知识库优化 | 全文检索、智能标签、版本管理 | P1 |

---

## 二、AI功能增强方案

### 2.1 现状分析

当前AI调用存在的问题：

```python
# 现有代码问题
1. 无流式输出 - 用户需等待完整响应
2. 无重试机制 - 网络波动导致失败
3. 上下文管理简单 - 仅支持单轮对话
4. 无对话历史压缩 - 长对话token超限
5. 错误处理粗糙 - 直接返回错误字符串
```

### 2.2 技术方案

#### 2.2.1 流式输出（Streaming）

**技术选型**：Server-Sent Events (SSE)

**实现代码**：

```python
# utils/ai_service.py
import json
import time
from typing import Generator, Optional
import requests
from flask import Response, stream_with_context

class AIStreamService:
    """AI流式服务"""
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def stream_chat(
        self, 
        messages: list, 
        knowledge_context: str = ''
    ) -> Generator[str, None, None]:
        """
        流式对话接口
        
        Yields:
            SSE格式数据: data: {"type": "content", "data": "..."}\n\n
        """
        # 构建完整消息
        full_messages = self._build_messages(messages, knowledge_context)
        
        for attempt in range(self.max_retries):
            try:
                response = self._call_stream_api(full_messages)
                
                for chunk in response.iter_lines():
                    if chunk:
                        decoded = chunk.decode('utf-8')
                        if decoded.startswith('data: '):
                            data = decoded[6:]
                            if data == '[DONE]':
                                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                                return
                            
                            parsed = self._parse_chunk(data)
                            if parsed:
                                yield f"data: {json.dumps(parsed)}\n\n"
                                
                return  # 成功完成
                
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                yield f"data: {json.dumps({'type': 'error', 'message': '请求超时'})}\n\n"
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    def _call_stream_api(self, messages: list) -> requests.Response:
        """调用流式API"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True  # 启用流式
        }
        
        url = self._build_api_url(self.config.api_base, 'chat/completions')
        
        return requests.post(
            url, 
            headers=headers, 
            json=payload, 
            stream=True,
            timeout=120
        )
    
    def _parse_chunk(self, data: str) -> Optional[dict]:
        """解析流式数据块"""
        try:
            obj = json.loads(data)
            delta = obj['choices'][0].get('delta', {})
            
            if 'content' in delta:
                return {'type': 'content', 'data': delta['content']}
            elif 'role' in delta:
                return {'type': 'start', 'role': delta['role']}
                
        except (json.JSONDecodeError, KeyError):
            pass
        return None
    
    def _build_messages(self, messages: list, context: str) -> list:
        """构建完整消息列表"""
        result = []
        if context:
            result.append({
                'role': 'system',
                'content': f"参考资料：\n{context}\n\n请基于以上资料回答。"
            })
        result.extend(messages)
        return result
```

**Flask路由实现**：

```python
# app.py 新增路由

@app.route('/api/chat/stream', methods=['POST'])
@login_required
def chat_stream():
    """流式对话接口"""
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')
    
    if not message:
        return jsonify({'error': '消息不能为空'}), 400
    
    # 获取或创建对话会话
    chat_session = ChatSession.query.get(session_id) if session_id else None
    if not chat_session:
        chat_session = ChatSession(
            user_id=current_user.id,
            title=message[:20] + '...'
        )
        db.session.add(chat_session)
        db.session.commit()
    
    # 保存用户消息
    user_msg = ChatMessage(
        session_id=chat_session.id,
        role='user',
        content=message
    )
    db.session.add(user_msg)
    db.session.commit()
    
    # 获取历史消息（带上下文压缩）
    history = get_compressed_history(chat_session.id)
    
    # 获取知识库上下文
    knowledge_context = search_knowledge_context(message)
    
    # 获取默认AI配置
    ai_config = AIModelConfig.query.filter_by(is_active=True).first()
    if not ai_config:
        return jsonify({'error': '未配置AI模型'}), 500
    
    service = AIStreamService(ai_config)
    
    def generate():
        full_response = []
        
        for chunk in service.stream_chat(history + [{'role': 'user', 'content': message}], 
                                         knowledge_context):
            yield chunk
            
            # 收集完整响应用于保存
            try:
                data = json.loads(chunk.replace('data: ', ''))
                if data.get('type') == 'content':
                    full_response.append(data['data'])
            except:
                pass
        
        # 保存AI回复
        assistant_msg = ChatMessage(
            session_id=chat_session.id,
            role='assistant',
            content=''.join(full_response)
        )
        db.session.add(assistant_msg)
        db.session.commit()
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )
```

**前端实现**：

```javascript
// static/js/ai_chat_stream.js

class AIChatStream {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.messageBuffer = '';
        this.currentMessageDiv = null;
    }
    
    async sendMessage(message, sessionId) {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // 创建新消息容器
        this.currentMessageDiv = this.createMessageElement('assistant');
        this.container.appendChild(this.currentMessageDiv);
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    this.handleStreamData(data);
                }
            }
        }
    }
    
    handleStreamData(data) {
        switch (data.type) {
            case 'content':
                this.messageBuffer += data.data;
                this.currentMessageDiv.innerHTML = this.renderMarkdown(this.messageBuffer);
                this.scrollToBottom();
                break;
            case 'error':
                this.showError(data.message);
                break;
            case 'done':
                this.finalizeMessage();
                break;
        }
    }
    
    renderMarkdown(text) {
        // 使用 marked.js 或自定义渲染
        return marked.parse(text);
    }
}
```

#### 2.2.2 上下文记忆与压缩

```python
# utils/context_manager.py

from typing import List, Dict
import tiktoken  # OpenAI的token计算库

class ContextManager:
    """对话上下文管理器"""
    
    def __init__(self, max_tokens: int = 4000, keep_messages: int = 10):
        self.max_tokens = max_tokens
        self.keep_messages = keep_messages
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def get_compressed_history(
        self, 
        session_id: int, 
        current_message: str
    ) -> List[Dict]:
        """
        获取压缩后的历史消息
        
        策略：
        1. 保留最近的 N 条完整消息
        2. 更早的消息进行摘要压缩
        3. 确保总token数不超过限制
        """
        # 获取所有历史消息
        messages = ChatMessage.query.filter_by(
            session_id=session_id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        if len(messages) <= self.keep_messages:
            return self._convert_messages(messages)
        
        # 分割消息：保留的 + 需要压缩的
        keep_msgs = messages[-self.keep_messages:]
        old_msgs = messages[:-self.keep_messages]
        
        # 压缩旧消息
        summary = self._summarize_messages(old_msgs)
        
        result = []
        if summary:
            result.append({
                'role': 'system',
                'content': f'历史对话摘要：{summary}'
            })
        
        result.extend(self._convert_messages(keep_msgs))
        return result
    
    def _summarize_messages(self, messages: List[ChatMessage]) -> str:
        """使用AI对历史消息进行摘要"""
        # 构建摘要提示
        conversation = '\n'.join([
            f"{'用户' if m.role == 'user' else '助手'}：{m.content[:200]}"
            for m in messages
        ])
        
        summary_prompt = f"""请对以下对话进行简要摘要，保留关键信息：

{conversation}

摘要（100字以内）："""
        
        # 调用轻量级模型进行摘要
        # 实际实现中可以使用本地小模型或缓存摘要结果
        return "对话涉及公文写作、知识库查询等内容。"
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict]:
        """转换为标准格式"""
        return [{'role': m.role, 'content': m.content} for m in messages]
    
    def count_tokens(self, messages: List[Dict]) -> int:
        """计算消息token数"""
        total = 0
        for msg in messages:
            total += len(self.encoding.encode(msg['content']))
        return total
```

#### 2.2.3 智能重试与降级

```python
# utils/ai_retry.py

from functools import wraps
import time
import random
from enum import Enum

class FallbackStrategy(Enum):
    """降级策略"""
    RETRY_SAME = "retry_same"          # 重试同一模型
    SWITCH_MODEL = "switch_model"      # 切换备用模型
    LOCAL_FALLBACK = "local_fallback"  # 降级到本地模型
    CACHE_RESPONSE = "cache_response"  # 使用缓存响应

class AIRetryManager:
    """AI调用重试管理器"""
    
    def __init__(self):
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 1,
            'max_delay': 30,
            'exponential_base': 2
        }
    
    def call_with_retry(
        self,
        func,
        fallback_strategy: FallbackStrategy = FallbackStrategy.RETRY_SAME,
        *args,
        **kwargs
    ):
        """带重试的AI调用"""
        last_exception = None
        
        for attempt in range(self.retry_config['max_retries']):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.retry_config['max_retries'] - 1:
                    delay = self._calculate_delay(attempt)
                    time.sleep(delay)
                    
            except requests.exceptions.HTTPError as e:
                last_exception = e
                # 针对特定错误码处理
                if e.response.status_code == 429:  # Rate limit
                    delay = self._calculate_delay(attempt) + 5
                    time.sleep(delay)
                elif e.response.status_code >= 500:  # Server error
                    if attempt < self.retry_config['max_retries'] - 1:
                        delay = self._calculate_delay(attempt)
                        time.sleep(delay)
                else:
                    raise  # 客户端错误不重试
                    
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config['max_retries'] - 1:
                    delay = self._calculate_delay(attempt)
                    time.sleep(delay)
        
        # 所有重试失败，执行降级策略
        return self._execute_fallback(fallback_strategy, last_exception, func, *args, **kwargs)
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算退避延迟（指数退避 + 抖动）"""
        base = self.retry_config['base_delay'] * (
            self.retry_config['exponential_base'] ** attempt
        )
        delay = min(base, self.retry_config['max_delay'])
        # 添加随机抖动避免雪崩
        return delay + random.uniform(0, 1)
    
    def _execute_fallback(
        self,
        strategy: FallbackStrategy,
        exception: Exception,
        original_func,
        *args,
        **kwargs
    ):
        """执行降级策略"""
        if strategy == FallbackStrategy.SWITCH_MODEL:
            # 获取备用模型配置
            fallback_config = AIModelConfig.query.filter(
                AIModelConfig.is_active == True,
                AIModelConfig.id != kwargs.get('config').id
            ).first()
            
            if fallback_config:
                kwargs['config'] = fallback_config
                return original_func(*args, **kwargs)
                
        elif strategy == FallbackStrategy.LOCAL_FALLBACK:
            # 切换到本地模型
            local_config = AIModelConfig.query.filter_by(
                provider='local',
                is_active=True
            ).first()
            
            if local_config:
                kwargs['config'] = local_config
                return original_func(*args, **kwargs)
        
        # 默认：抛出异常
        raise exception
```

#### 2.2.4 知识库RAG增强

```python
# utils/rag_service.py

from typing import List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class RAGService:
    """检索增强生成服务"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.chunk_size = 500  # 文档分块大小
        self.top_k = 5  # 返回最相关的文档数
    
    def search_knowledge_context(
        self,
        query: str,
        knowledge_base_ids: List[int] = None,
        user_id: int = None
    ) -> str:
        """
        搜索知识库获取相关上下文
        
        Returns:
            拼接后的相关文档内容
        """
        # 构建查询
        kb_query = KnowledgeFile.query.filter(
            KnowledgeFile.status == 'approved'
        )
        
        if knowledge_base_ids:
            kb_query = kb_query.filter(
                KnowledgeFile.knowledge_base_id.in_(knowledge_base_ids)
            )
        
        # 获取可访问的知识库文件
        files = kb_query.all()
        
        if not files:
            return ''
        
        # 提取文档内容并分块
        chunks = []
        for file in files:
            content = self._extract_file_content(file)
            file_chunks = self._chunk_document(content, file.id)
            chunks.extend(file_chunks)
        
        # 计算相似度
        relevant_chunks = self._semantic_search(query, chunks)
        
        # 构建上下文
        context = self._build_context(relevant_chunks)
        
        return context
    
    def _extract_file_content(self, file: KnowledgeFile) -> str:
        """提取文件内容"""
        # 根据文件类型使用不同解析器
        ext = file.filename.rsplit('.', 1)[-1].lower()
        
        if ext == 'pdf':
            return pdf_to_text(file.file_path)
        elif ext in ['doc', 'docx']:
            return docx_to_text(file.file_path)
        elif ext == 'txt':
            with open(file.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ''
    
    def _chunk_document(self, content: str, file_id: int) -> List[dict]:
        """将文档分块"""
        chunks = []
        # 按段落分割
        paragraphs = content.split('\n\n')
        
        current_chunk = ''
        for para in paragraphs:
            if len(current_chunk) + len(para) < self.chunk_size:
                current_chunk += para + '\n\n'
            else:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk.strip(),
                        'file_id': file_id
                    })
                current_chunk = para + '\n\n'
        
        if current_chunk:
            chunks.append({
                'content': current_chunk.strip(),
                'file_id': file_id
            })
        
        return chunks
    
    def _semantic_search(
        self, 
        query: str, 
        chunks: List[dict]
    ) -> List[dict]:
        """语义搜索最相关的文档块"""
        if not chunks:
            return []
        
        # 构建语料库
        corpus = [chunk['content'] for chunk in chunks]
        corpus.append(query)
        
        # 计算TF-IDF
        tfidf_matrix = self.vectorizer.fit_transform(corpus)
        
        # 计算余弦相似度
        query_vector = tfidf_matrix[-1]
        chunk_vectors = tfidf_matrix[:-1]
        
        similarities = cosine_similarity(query_vector, chunk_vectors)[0]
        
        # 排序并返回top_k
        indexed_scores = list(enumerate(similarities))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in indexed_scores[:self.top_k]:
            if score > 0.1:  # 相似度阈值
                chunk = chunks[idx].copy()
                chunk['score'] = float(score)
                results.append(chunk)
        
        return results
    
    def _build_context(self, chunks: List[dict]) -> str:
        """构建上下文字符串"""
        if not chunks:
            return ''
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"【参考{i}】\n{chunk['content']}\n")
        
        return '\n'.join(context_parts)
```

### 2.3 数据库模型扩展

```python
# models.py 新增

class AIConversationMemory(db.Model):
    """AI对话记忆表 - 存储对话摘要和关键信息"""
    __tablename__ = 'ai_conversation_memories'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'))
    summary = db.Column(db.Text, comment='对话摘要')
    key_points = db.Column(db.Text, comment='关键要点JSON')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIPromptTemplate(db.Model):
    """AI提示词模板"""
    __tablename__ = 'ai_prompt_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))  # writing, analysis, translation
    template = db.Column(db.Text, nullable=False)
    variables = db.Column(db.Text, comment='变量列表JSON')
    is_system = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## 三、静态资源CDN配置方案

### 3.1 现状分析

当前静态资源问题：
- 所有静态资源从服务器本地加载
- 无缓存策略
- 大文件（字体、JS库）加载慢
- 服务器带宽压力大

### 3.2 CDN选型

| CDN服务商 | 优点 | 缺点 | 适用场景 |
|-----------|------|------|----------|
| 阿里云CDN | 国内节点多，稳定 | 收费 | 生产环境 |
| 腾讯云CDN | 性价比高 | 节点略少 | 生产环境 |
| jsDelivr | 免费，开源友好 | 国外节点 | 开源库 |
| unpkg | npm包直接引用 | 国外节点 | 开源库 |
| 又拍云 | 价格适中 | 知名度低 | 中小企业 |

**推荐方案**：国内使用阿里云/腾讯云CDN，开源库使用jsDelivr

### 3.3 实施步骤

#### 3.3.1 配置CDN域名

```python
# config.py 新增CDN配置

class Config:
    # ... 原有配置
    
    # CDN配置
    CDN_ENABLED = os.environ.get('CDN_ENABLED', 'false').lower() == 'true'
    CDN_DOMAIN = os.environ.get('CDN_DOMAIN', '')  # 如: cdn.example.com
    CDN_PROTOCOL = os.environ.get('CDN_PROTOCOL', 'https')
    
    # 静态资源版本控制
    STATIC_VERSION = os.environ.get('STATIC_VERSION', 'v1.0.0')
    
    # 本地静态资源URL（CDN回源）
    STATIC_URL = '/static/'
```

#### 3.3.2 创建CDN辅助函数

```python
# utils/cdn_helper.py

from flask import url_for
from config import Config

def static_url(filename):
    """
    生成静态资源URL
    
    根据配置返回CDN地址或本地地址
    """
    if not Config.CDN_ENABLED or not Config.CDN_DOMAIN:
        return url_for('static', filename=filename)
    
    # CDN地址
    return f"{Config.CDN_PROTOCOL}://{Config.CDN_DOMAIN}/static/{filename}?v={Config.STATIC_VERSION}"

def cdn_js(lib_name, version=None):
    """
    获取常用JS库的CDN地址
    
    Args:
        lib_name: 库名称，如 'jquery', 'vue', 'bootstrap'
        version: 版本号，默认使用推荐版本
    """
    cdn_libs = {
        'jquery': {
            'version': '3.6.0',
            'url': 'https://cdn.jsdelivr.net/npm/jquery@{version}/dist/jquery.min.js'
        },
        'vue': {
            'version': '3.3.4',
            'url': 'https://cdn.jsdelivr.net/npm/vue@{version}/dist/vue.global.js'
        },
        'bootstrap': {
            'version': '5.3.0',
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@{version}/dist/js/bootstrap.bundle.min.js'
        },
        'bootstrap_css': {
            'version': '5.3.0',
            'url': 'https://cdn.jsdelivr.net/npm/bootstrap@{version}/dist/css/bootstrap.min.css'
        },
        'marked': {
            'version': '5.1.0',
            'url': 'https://cdn.jsdelivr.net/npm/marked@{version}/marked.min.js'
        },
        'axios': {
            'version': '1.4.0',
            'url': 'https://cdn.jsdelivr.net/npm/axios@{version}/dist/axios.min.js'
        },
        'echarts': {
            'version': '5.4.3',
            'url': 'https://cdn.jsdelivr.net/npm/echarts@{version}/dist/echarts.min.js'
        },
        'fontawesome': {
            'version': '6.4.0',
            'url': 'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@{version}/css/all.min.css'
        }
    }
    
    lib = cdn_libs.get(lib_name)
    if not lib:
        return ''
    
    ver = version or lib['version']
    return lib['url'].format(version=ver)

# 注册为Jinja2全局函数
def init_cdn_helpers(app):
    app.jinja_env.globals['static_url'] = static_url
    app.jinja_env.globals['cdn_js'] = cdn_js
```

#### 3.3.3 修改模板引用

```html
<!-- templates/base.html 修改 -->
<!DOCTYPE html>
<html>
<head>
    <!-- 使用CDN加载第三方库 -->
    <link rel="stylesheet" href="{{ cdn_js('bootstrap_css') }}">
    <link rel="stylesheet" href="{{ cdn_js('fontawesome') }}">
    
    <!-- 本地样式使用CDN或本地 -->
    <link rel="stylesheet" href="{{ static_url('css/style.css') }}">
    
    <!-- 其他第三方库 -->
    <script src="{{ cdn_js('jquery') }}"></script>
    <script src="{{ cdn_js('bootstrap') }}"></script>
    <script src="{{ cdn_js('marked') }}"></script>
    <script src="{{ cdn_js('axios') }}"></script>
</head>
```

#### 3.3.4 静态资源上传脚本

```python
# scripts/upload_to_cdn.py

import os
import sys
import oss2  # 阿里云OSS SDK
from pathlib import Path

# 阿里云OSS配置
OSS_ACCESS_KEY_ID = os.environ.get('OSS_ACCESS_KEY_ID')
OSS_ACCESS_KEY_SECRET = os.environ.get('OSS_ACCESS_KEY_SECRET')
OSS_BUCKET_NAME = os.environ.get('OSS_BUCKET_NAME')
OSS_ENDPOINT = os.environ.get('OSS_ENDPOINT')  # 如: oss-cn-beijing.aliyuncs.com

def upload_static_files():
    """上传静态资源到CDN"""
    
    if not all([OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET_NAME]):
        print("错误：缺少OSS配置环境变量")
        sys.exit(1)
    
    # 创建OSS客户端
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    
    # 静态资源目录
    static_dir = Path('static')
    
    # 支持的文件类型
    allowed_extensions = {'.css', '.js', '.woff', '.woff2', '.ttf', '.png', '.jpg', '.svg'}
    
    uploaded = 0
    failed = 0
    
    for file_path in static_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix in allowed_extensions:
            # 构建OSS对象键
            relative_path = file_path.relative_to(static_dir)
            object_key = f"static/{relative_path}"
            
            # 设置Content-Type
            content_type = get_content_type(file_path.suffix)
            
            try:
                # 上传文件
                bucket.put_object_from_file(
                    object_key,
                    str(file_path),
                    headers={'Content-Type': content_type}
                )
                print(f"✓ 上传成功: {object_key}")
                uploaded += 1
            except Exception as e:
                print(f"✗ 上传失败: {object_key} - {e}")
                failed += 1
    
    print(f"\n上传完成: 成功 {uploaded} 个, 失败 {failed} 个")

def get_content_type(ext):
    """获取文件Content-Type"""
    types = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.svg': 'image/svg+xml'
    }
    return types.get(ext, 'application/octet-stream')

if __name__ == '__main__':
    upload_static_files()
```

#### 3.3.5 Nginx缓存配置

```nginx
# /etc/nginx/conf.d/static-cache.conf

# 静态资源缓存配置
location ~* \.(css|js|woff|woff2|ttf|png|jpg|jpeg|gif|svg|ico)$ {
    # 缓存1年
    expires 1y;
    add_header Cache-Control "public, immutable";
    
    # 开启gzip
    gzip on;
    gzip_types text/css application/javascript font/woff font/woff2;
    
    # 尝试从CDN回源
    try_files $uri $uri/ =404;
}

# HTML不缓存
location ~* \.html$ {
    expires -1;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

---

## 四、功能扩展方案

### 4.1 WebSocket消息通知系统

#### 4.1.1 技术选型

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| Flask-SocketIO | 集成简单，兼容性好 | 性能一般 | ★★★★ |
| 独立WebSocket服务 | 性能好，可扩展 | 架构复杂 | ★★★ |
| SSE (Server-Sent Events) | 实现简单，HTTP兼容 | 单向通信 | ★★★★ |

**推荐方案**：Flask-SocketIO + Redis适配器（支持多实例部署）

#### 4.1.2 实现方案

```python
# extensions/websocket.py

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

def init_websocket(app):
    """初始化WebSocket"""
    socketio.init_app(app, message_queue='redis://localhost:6379/0')
    
    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        if current_user.is_authenticated:
            join_room(f"user_{current_user.id}")
            join_room(f"dept_{current_user.dept_id}")
            emit('connected', {'status': 'success', 'user_id': current_user.id})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开"""
        if current_user.is_authenticated:
            leave_room(f"user_{current_user.id}")
            leave_room(f"dept_{current_user.dept_id}")

# 消息推送服务
class NotificationService:
    """消息推送服务"""
    
    @staticmethod
    def notify_user(user_id: int, message: dict):
        """向指定用户推送消息"""
        socketio.emit('notification', message, room=f"user_{user_id}")
    
    @staticmethod
    def notify_department(dept_id: int, message: dict):
        """向部门全员推送"""
        socketio.emit('notification', message, room=f"dept_{dept_id}")
    
    @staticmethod
    def broadcast(message: dict):
        """广播消息"""
        socketio.emit('notification', message, broadcast=True)
    
    @staticmethod
    def notify_task_assigned(task_id: int):
        """任务分配通知"""
        task = AssignmentTask.query.get(task_id)
        if task:
            user_ids = task.assigned_to.split(',')
            for uid in user_ids:
                NotificationService.notify_user(int(uid), {
                    'type': 'task_assigned',
                    'title': '新任务分配',
                    'content': f'您有一个新任务：{task.title}',
                    'link': f'/special_report/receiver/task/{task_id}',
                    'priority': task.urgency
                })
```

#### 4.1.3 前端实现

```javascript
// static/js/notifications.js

class NotificationManager {
    constructor() {
        this.socket = io();
        this.unreadCount = 0;
        this.notifications = [];
        this.init();
    }
    
    init() {
        // 连接成功
        this.socket.on('connected', (data) => {
            console.log('WebSocket已连接:', data);
        });
        
        // 接收通知
        this.socket.on('notification', (data) => {
            this.handleNotification(data);
        });
        
        // 请求桌面通知权限
        this.requestNotificationPermission();
    }
    
    handleNotification(data) {
        // 添加到通知列表
        this.notifications.unshift(data);
        this.unreadCount++;
        
        // 更新UI
        this.updateBadge();
        this.showToast(data);
        
        // 桌面通知
        if (data.priority === 'urgent') {
            this.showDesktopNotification(data);
        }
        
        // 播放提示音（可选）
        this.playSound();
    }
    
    showToast(data) {
        // 使用Toast组件显示通知
        Toastify({
            text: data.content,
            duration: 5000,
            gravity: "top",
            position: "right",
            style: {
                background: data.priority === 'urgent' ? '#e74c3c' : '#3498db'
            },
            onClick: () => {
                window.location.href = data.link;
            }
        }).showToast();
    }
    
    showDesktopNotification(data) {
        if (Notification.permission === 'granted') {
            new Notification(data.title, {
                body: data.content,
                icon: '/static/img/logo.png'
            });
        }
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
}

// 初始化
const notificationManager = new NotificationManager();
```

### 4.2 移动端适配

#### 4.2.1 响应式设计方案

```css
/* static/css/responsive.css */

/* 移动端优先设计 */
:root {
    --mobile-breakpoint: 768px;
    --tablet-breakpoint: 1024px;
}

/* 基础移动端样式 */
@media (max-width: 768px) {
    /* 侧边栏收起 */
    .sidebar {
        position: fixed;
        left: -250px;
        width: 250px;
        height: 100vh;
        transition: left 0.3s;
        z-index: 1000;
    }
    
    .sidebar.active {
        left: 0;
    }
    
    /* 主内容区全宽 */
    .main-content {
        margin-left: 0;
        padding: 10px;
    }
    
    /* 卡片单列布局 */
    .card-grid {
        grid-template-columns: 1fr;
    }
    
    /* 表格横向滚动 */
    .table-responsive {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    
    /* 底部导航 */
    .mobile-nav {
        display: flex;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #fff;
        border-top: 1px solid #ddd;
        padding: 10px 0;
        z-index: 999;
    }
    
    .mobile-nav-item {
        flex: 1;
        text-align: center;
        font-size: 12px;
    }
    
    /* 增加底部间距避免被导航遮挡 */
    body {
        padding-bottom: 60px;
    }
}

/* 平板适配 */
@media (min-width: 769px) and (max-width: 1024px) {
    .card-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
```

#### 4.2.2 PWA支持

```javascript
// static/js/pwa.js

// 注册Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(registration => {
                console.log('SW注册成功:', registration);
            })
            .catch(error => {
                console.log('SW注册失败:', error);
            });
    });
}

// 添加到主屏幕提示
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    // 显示安装按钮
    document.getElementById('install-btn').style.display = 'block';
});

document.getElementById('install-btn').addEventListener('click', async () => {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') {
            console.log('用户接受安装');
        }
        deferredPrompt = null;
    }
});
```

```javascript
// static/js/sw.js - Service Worker

const CACHE_NAME = 'oa-app-v1';
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/img/logo.png'
];

// 安装时缓存资源
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

// 拦截请求
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // 缓存命中直接返回
                if (response) {
                    return response;
                }
                // 否则请求网络
                return fetch(event.request);
            })
    );
});
```

### 4.3 工作流引擎

```python
# workflow/engine.py

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

class NodeType(Enum):
    START = "start"
    END = "end"
    TASK = "task"
    APPROVAL = "approval"
    CONDITION = "condition"
    PARALLEL = "parallel"

class WorkflowStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    REJECTED = "rejected"
    SUSPENDED = "suspended"

@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str
    type: NodeType
    name: str
    config: Dict
    next_nodes: List[str]

@dataclass
class WorkflowInstance:
    """工作流实例"""
    id: int
    definition_id: int
    status: WorkflowStatus
    current_node: str
    context: Dict
    started_at: datetime
    completed_at: Optional[datetime]

class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.node_handlers = {
            NodeType.TASK: self._handle_task,
            NodeType.APPROVAL: self._handle_approval,
            NodeType.CONDITION: self._handle_condition,
            NodeType.PARALLEL: self._handle_parallel
        }
    
    def start_workflow(self, definition_id: int, context: Dict) -> WorkflowInstance:
        """启动工作流"""
        definition = WorkflowDefinition.query.get(definition_id)
        
        instance = WorkflowInstance(
            definition_id=definition_id,
            status=WorkflowStatus.RUNNING,
            current_node=definition.start_node,
            context=context,
            started_at=datetime.utcnow()
        )
        db.session.add(instance)
        db.session.commit()
        
        # 执行第一个节点
        self._execute_node(instance, definition.start_node)
        
        return instance
    
    def _execute_node(self, instance: WorkflowInstance, node_id: str):
        """执行节点"""
        definition = WorkflowDefinition.query.get(instance.definition_id)
        node = definition.get_node(node_id)
        
        handler = self.node_handlers.get(node.type)
        if handler:
            result = handler(instance, node)
            
            if result == 'completed':
                # 流转到下一个节点
                if node.next_nodes:
                    next_node = node.next_nodes[0]
                    instance.current_node = next_node
                    self._execute_node(instance, next_node)
                else:
                    # 流程结束
                    instance.status = WorkflowStatus.COMPLETED
                    instance.completed_at = datetime.utcnow()
                    db.session.commit()
    
    def _handle_approval(self, instance: WorkflowInstance, node: WorkflowNode):
        """处理审批节点"""
        # 创建审批任务
        approval = ApprovalTask(
            instance_id=instance.id,
            node_id=node.id,
            approvers=node.config.get('approvers', []),
            approval_type=node.config.get('type', 'single'),  # single/parallel
            status='pending'
        )
        db.session.add(approval)
        db.session.commit()
        
        # 发送通知
        for approver_id in approval.approvers:
            NotificationService.notify_user(approver_id, {
                'type': 'approval_required',
                'title': '待审批',
                'content': f'您有一个待审批事项：{node.name}',
                'link': f'/workflow/approval/{approval.id}'
            })
        
        return 'waiting'  # 等待审批完成
    
    def complete_task(self, instance_id: int, node_id: str, result: Dict):
        """完成任务"""
        instance = WorkflowInstance.query.get(instance_id)
        
        # 更新上下文
        instance.context.update(result)
        
        # 获取节点定义
        definition = WorkflowDefinition.query.get(instance.definition_id)
        node = definition.get_node(node_id)
        
        # 确定下一个节点
        next_node = self._determine_next_node(node, result)
        
        if next_node:
            instance.current_node = next_node
            db.session.commit()
            self._execute_node(instance, next_node)
        else:
            # 流程结束
            instance.status = WorkflowStatus.COMPLETED
            instance.completed_at = datetime.utcnow()
            db.session.commit()
```

---

## 五、知识库管理优化方案

### 5.1 全文检索系统

#### 5.1.1 技术选型

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| Whoosh | 纯Python，无需外部依赖 | 性能一般 | ★★★ |
| Elasticsearch | 功能强大，性能优秀 | 需要额外部署 | ★★★★ |
| SQLite FTS | 集成简单，无需额外服务 | 功能有限 | ★★★ |
| Meilisearch | 轻量，易部署，中文支持好 | 相对较新 | ★★★★★ |

**推荐方案**：Meilisearch（轻量、中文分词好、部署简单）

#### 5.1.2 Meilisearch集成

```python
# extensions/search.py

import meilisearch
from config import Config

class KnowledgeSearch:
    """知识库全文检索服务"""
    
    INDEX_NAME = 'knowledge_files'
    
    def __init__(self):
        self.client = meilisearch.Client(
            Config.MEILISEARCH_URL,
            Config.MEILISEARCH_API_KEY
        )
        self._init_index()
    
    def _init_index(self):
        """初始化索引"""
        try:
            self.client.get_index(self.INDEX_NAME)
        except:
            # 创建索引
            self.client.create_index(self.INDEX_NAME, {'primaryKey': 'id'})
            
            # 配置可搜索字段
            self.client.index(self.INDEX_NAME).update_settings({
                'searchableAttributes': [
                    'title',
                    'content',
                    'tags',
                    'category'
                ],
                'filterableAttributes': [
                    'knowledge_base_id',
                    'uploaded_by',
                    'status',
                    'file_type',
                    'created_at'
                ],
                'sortableAttributes': [
                    'created_at',
                    'file_size'
                ],
                'rankingRules': [
                    'words',
                    'typo',
                    'proximity',
                    'attribute',
                    'sort',
                    'exactness'
                ]
            })
    
    def index_document(self, file: KnowledgeFile, content: str):
        """索引文档"""
        document = {
            'id': file.id,
            'title': file.original_name,
            'content': content[:100000],  # 限制内容长度
            'knowledge_base_id': file.knowledge_base_id,
            'uploaded_by': file.uploaded_by,
            'status': file.status,
            'file_type': file.filename.rsplit('.', 1)[-1],
            'created_at': int(file.upload_time.timestamp()),
            'file_size': self._get_file_size(file.file_path)
        }
        
        self.client.index(self.INDEX_NAME).add_documents([document])
    
    def search(
        self,
        query: str,
        filters: Dict = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict:
        """
        搜索文档
        
        Args:
            query: 搜索关键词
            filters: 过滤条件，如 {'knowledge_base_id': 1}
            limit: 返回数量
            offset: 偏移量
        """
        filter_str = self._build_filter(filters) if filters else None
        
        results = self.client.index(self.INDEX_NAME).search(
            query,
            {
                'limit': limit,
                'offset': offset,
                'filter': filter_str,
                'highlightPreTag': '<mark>',
                'highlightPostTag': '</mark>',
                'attributesToHighlight': ['title', 'content']
            }
        )
        
        return results
    
    def _build_filter(self, filters: Dict) -> str:
        """构建过滤条件"""
        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(f"{key} IN [{', '.join(map(str, value))}]")
            else:
                conditions.append(f"{key} = {value}")
        return ' AND '.join(conditions)
```

#### 5.1.3 文档内容提取优化

```python
# utils/document_parser.py

import fitz  # PyMuPDF
from docx import Document
import pandas as pd
from PIL import Image
import pytesseract

class DocumentParser:
    """文档解析器"""
    
    def parse(self, file_path: str, file_type: str) -> Dict:
        """
        解析文档内容
        
        Returns:
            {
                'text': '纯文本内容',
                'metadata': {...},
                'chunks': ['分段内容', ...]
            }
        """
        parsers = {
            'pdf': self._parse_pdf,
            'docx': self._parse_docx,
            'doc': self._parse_doc,
            'xlsx': self._parse_excel,
            'xls': self._parse_excel,
            'txt': self._parse_txt,
            'md': self._parse_markdown
        }
        
        parser = parsers.get(file_type.lower())
        if parser:
            return parser(file_path)
        
        return {'text': '', 'metadata': {}, 'chunks': []}
    
    def _parse_pdf(self, file_path: str) -> Dict:
        """解析PDF（支持OCR）"""
        doc = fitz.open(file_path)
        text_parts = []
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
            # 如果页面文字很少，可能是扫描件，进行OCR
            if len(text.strip()) < 50:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            
            text_parts.append(f"--- 第{page_num + 1}页 ---\n{text}")
        
        full_text = '\n\n'.join(text_parts)
        
        return {
            'text': full_text,
            'metadata': {
                'page_count': len(doc),
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', '')
            },
            'chunks': self._chunk_text(full_text)
        }
    
    def _parse_docx(self, file_path: str) -> Dict:
        """解析Word文档"""
        doc = Document(file_path)
        
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        # 提取表格内容
        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join([cell.text for cell in row.cells])
                text_parts.append(row_text)
        
        full_text = '\n'.join(text_parts)
        
        return {
            'text': full_text,
            'metadata': {
                'paragraph_count': len(doc.paragraphs),
                'table_count': len(doc.tables)
            },
            'chunks': self._chunk_text(full_text)
        }
    
    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """智能分块"""
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ''
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + '\n\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + '\n\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
```

### 5.2 智能标签系统

```python
# utils/auto_tagging.py

import jieba
import jieba.analyse
from collections import Counter

class AutoTaggingService:
    """自动标签服务"""
    
    def __init__(self):
        # 加载自定义词典
        jieba.load_userdict('dicts/custom_dict.txt')
        
        # 停用词
        self.stopwords = set()
        with open('dicts/stopwords.txt', 'r', encoding='utf-8') as f:
            self.stopwords = set(line.strip() for line in f)
    
    def extract_tags(self, content: str, top_k: int = 10) -> List[Dict]:
        """
        提取文档标签
        
        Returns:
            [{'tag': '标签', 'weight': 0.95, 'type': 'tfidf'}, ...]
        """
        # TF-IDF提取关键词
        keywords = jieba.analyse.extract_tags(
            content, 
            topK=top_k, 
            withWeight=True
        )
        
        # 命名实体识别（简单规则）
        entities = self._extract_entities(content)
        
        # 合并结果
        tags = []
        for word, weight in keywords:
            tags.append({
                'tag': word,
                'weight': weight,
                'type': 'keyword'
            })
        
        for entity in entities:
            tags.append({
                'tag': entity['text'],
                'weight': entity['confidence'],
                'type': entity['type']
            })
        
        # 去重并排序
        seen = set()
        unique_tags = []
        for tag in sorted(tags, key=lambda x: x['weight'], reverse=True):
            if tag['tag'] not in seen:
                seen.add(tag['tag'])
                unique_tags.append(tag)
        
        return unique_tags[:top_k]
    
    def _extract_entities(self, content: str) -> List[Dict]:
        """简单实体识别"""
        entities = []
        
        # 组织机构识别（基于关键词）
        org_patterns = ['公司', '集团', '部门', '局', '厅', '处', '科']
        words = jieba.lcut(content)
        
        i = 0
        while i < len(words):
            for pattern in org_patterns:
                if pattern in words[i] and i > 0:
                    org_name = words[i-1] + words[i]
                    entities.append({
                        'text': org_name,
                        'type': 'organization',
                        'confidence': 0.8
                    })
            i += 1
        
        return entities
    
    def suggest_category(self, content: str, tags: List[str]) -> str:
        """根据内容推荐分类"""
        # 基于关键词映射到分类
        category_mapping = {
            '通知': ['通知', '公告', '通报'],
            '报告': ['报告', '总结', '汇报'],
            '请示': ['请示', '申请', '请求'],
            '函': ['函', '商洽', '联系'],
            '会议纪要': ['纪要', '会议', '记录']
        }
        
        content_lower = content.lower()
        scores = {}
        
        for category, keywords in category_mapping.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return '其他'
```

### 5.3 版本管理

```python
# models.py 新增版本模型

class KnowledgeFileVersion(db.Model):
    """知识文件版本"""
    __tablename__ = 'knowledge_file_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('knowledge_files.id'))
    version_number = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    change_log = db.Column(db.Text, comment='变更说明')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    
    # 关系
    file = db.relationship('KnowledgeFile', backref='versions')
    creator = db.relationship('User')

class KnowledgeFile(db.Model):
    """扩展知识文件模型"""
    # ... 原有字段
    
    # 版本管理
    current_version = db.Column(db.Integer, default=1)
    is_version_controlled = db.Column(db.Boolean, default=False)
    
    def create_version(self, new_file_path: str, change_log: str, user_id: int):
        """创建新版本"""
        new_version_num = self.current_version + 1
        
        version = KnowledgeFileVersion(
            file_id=self.id,
            version_number=new_version_num,
            file_path=new_file_path,
            change_log=change_log,
            created_by=user_id,
            file_size=os.path.getsize(new_file_path)
        )
        
        self.current_version = new_version_num
        self.file_path = new_file_path
        
        db.session.add(version)
        db.session.commit()
        
        return version
    
    def rollback_to_version(self, version_number: int):
        """回滚到指定版本"""
        version = KnowledgeFileVersion.query.filter_by(
            file_id=self.id,
            version_number=version_number
        ).first()
        
        if version:
            self.file_path = version.file_path
            self.current_version = version_number
            db.session.commit()
            return True
        
        return False
```

---

## 六、实施计划

### 6.1 阶段划分

| 阶段 | 时间 | 内容 | 产出 |
|------|------|------|------|
| 第一阶段 | 第1-2周 | AI功能增强 | 流式对话、上下文管理、RAG |
| 第二阶段 | 第3-4周 | CDN配置 | 静态资源加速、缓存策略 |
| 第三阶段 | 第5-6周 | 功能扩展 | WebSocket通知、移动端适配 |
| 第四阶段 | 第7-8周 | 知识库优化 | 全文检索、智能标签、版本管理 |

### 6.2 依赖安装

```bash
# requirements.txt 新增依赖

# AI增强
openai>=1.0.0
tiktoken>=0.5.0

# WebSocket
flask-socketio>=5.3.0
redis>=4.5.0

# 全文检索
meilisearch>=0.28.0

# 文档解析
PyMuPDF>=1.23.0
python-docx>=0.8.11
openpyxl>=3.1.0
pytesseract>=0.3.10
Pillow>=10.0.0

# 中文分词
jieba>=0.42.1

# OSS上传
oss2>=2.18.0
```

### 6.3 数据库迁移

```python
# migrations/add_ai_enhancements.py

from flask_migrate import Migrate

def upgrade():
    """数据库升级脚本"""
    
    # 创建AI对话记忆表
    op.create_table(
        'ai_conversation_memories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('chat_sessions.id')),
        sa.Column('summary', sa.Text()),
        sa.Column('key_points', sa.Text()),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )
    
    # 创建AI提示词模板表
    op.create_table(
        'ai_prompt_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50)),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('variables', sa.Text()),
        sa.Column('is_system', sa.Boolean(), default=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )
    
    # 知识文件版本表
    op.create_table(
        'knowledge_file_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('file_id', sa.Integer(), sa.ForeignKey('knowledge_files.id')),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('change_log', sa.Text()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('file_size', sa.Integer())
    )
    
    # 添加字段到现有表
    op.add_column('knowledge_files', sa.Column('current_version', sa.Integer(), default=1))
    op.add_column('knowledge_files', sa.Column('is_version_controlled', sa.Boolean(), default=False))
```

---

## 七、风险评估

### 7.1 技术风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| Meilisearch部署复杂 | 中 | 中 | 提供Docker部署方案 |
| WebSocket连接不稳定 | 中 | 低 | 实现自动重连机制 |
| 流式输出兼容性问题 | 低 | 中 | 提供降级方案（非流式） |
| CDN回源失败 | 低 | 高 | 本地资源作为fallback |

### 7.2 性能风险

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 全文检索响应慢 | 中 | 中 | 添加缓存层 |
| AI调用超时 | 高 | 中 | 异步队列处理 |
| 静态资源缓存失效 | 低 | 低 | 版本号控制 |

### 7.3 回滚方案

```bash
# 回滚脚本
#!/bin/bash

# 1. 停止服务
systemctl stop oa-app

# 2. 恢复数据库
pg_restore -d oa_db backups/oa_backup_$(date -d "1 day ago" +%Y%m%d).sql

# 3. 恢复代码
cd /opt/oa-app
git reset --hard HEAD~1

# 4. 重启服务
systemctl start oa-app

echo "回滚完成"
```

---

## 附录

### A. 环境变量配置

```bash
# .env 新增配置

# AI配置
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...
DEFAULT_AI_MODEL=deepseek-chat

# CDN配置
CDN_ENABLED=true
CDN_DOMAIN=cdn.yourdomain.com
STATIC_VERSION=v2.0.0

# Meilisearch
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your_master_key

# Redis
REDIS_URL=redis://localhost:6379/0

# OSS配置
OSS_ACCESS_KEY_ID=...
OSS_ACCESS_KEY_SECRET=...
OSS_BUCKET_NAME=oa-static
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
```

### B. 部署架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  PC浏览器 │  │ 移动浏览器│  │ 微信内置 │  │   APP    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        CDN层                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  阿里云CDN / 腾讯云CDN                                │  │
│  │  - 静态资源缓存 (CSS/JS/字体/图片)                     │  │
│  │  - 全球加速节点                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       负载均衡层                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Nginx                              │  │
│  │  - 反向代理 / 负载均衡 / SSL终止 / 静态资源缓存         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Flask App 1   │ │   Flask App 2   │ │   Flask App N   │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
│  │  WebSocket │  │ │  │  WebSocket │  │ │  │  WebSocket │  │
│  │  消息服务  │  │ │  │  消息服务  │  │ │  │  消息服务  │  │
│  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   SQLite/MySQL  │ │     Redis       │ │   Meilisearch   │
│    主数据库      │ │  缓存/WebSocket  │ │   全文检索引擎   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

**文档结束**
