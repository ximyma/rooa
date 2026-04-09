/**
 * md-editor.js - 轻量级 Markdown 富文本编辑器
 * 纯 JS 实现，无外部依赖，配合 marked.js 使用
 */
(function(global) {
  'use strict';

  var MdEditor = function(textarea, options) {
    this.textarea = typeof textarea === 'string' ? document.getElementById(textarea) : textarea;
    if (!this.textarea) return;
    this.options = Object.assign({
      height: 380,
      previewMode: false,
      placeholder: '请输入内容（支持 Markdown 格式）...',
      toolbar: ['bold','italic','strikethrough','|','h1','h2','h3','|','ul','ol','quote','code','|','link','table','hr','|','preview','fullscreen']
    }, options || {});
    this._init();
  };

  MdEditor.prototype._init = function() {
    var self = this;
    var ta = this.textarea;

    // 隐藏原 textarea
    ta.style.display = 'none';

    // 外层容器
    var wrap = document.createElement('div');
    wrap.className = 'md-editor-wrap border rounded';
    wrap.style.cssText = 'font-family: inherit; background:#fff;';
    ta.parentNode.insertBefore(wrap, ta);
    wrap.appendChild(ta);
    this.wrap = wrap;

    // 工具栏
    var toolbar = document.createElement('div');
    toolbar.className = 'md-editor-toolbar d-flex flex-wrap gap-1 p-2 border-bottom bg-light';
    toolbar.style.cssText = 'user-select:none;';
    wrap.insertBefore(toolbar, ta);
    this.toolbar = toolbar;
    this._buildToolbar();

    // 编辑/预览区
    var body = document.createElement('div');
    body.style.cssText = 'display:flex;height:' + this.options.height + 'px;';
    wrap.insertBefore(body, ta);
    this.body = body;

    // 编辑区
    var editor = document.createElement('textarea');
    editor.className = 'md-editor-input';
    editor.style.cssText = 'flex:1;resize:none;border:none;outline:none;padding:12px 16px;font-size:14px;font-family:\'Consolas\',\'Courier New\',monospace;line-height:1.7;overflow-y:auto;background:#fafafa;';
    editor.placeholder = this.options.placeholder;
    editor.value = ta.value;
    body.appendChild(editor);
    this.editor = editor;

    // 预览区
    var preview = document.createElement('div');
    preview.className = 'md-editor-preview markdown-body';
    preview.style.cssText = 'flex:1;padding:12px 16px;overflow-y:auto;display:none;border-left:1px solid #e9ecef;background:#fff;font-size:14px;line-height:1.8;';
    body.appendChild(preview);
    this.preview = preview;

    // 状态栏
    var statusbar = document.createElement('div');
    statusbar.className = 'md-editor-statusbar d-flex justify-content-between px-3 py-1 border-top bg-light';
    statusbar.style.cssText = 'font-size:12px;color:#888;';
    statusbar.innerHTML = '<span class="md-word-count">字数: 0</span><span><kbd>Ctrl+B</kbd> 粗体 &nbsp;<kbd>Ctrl+I</kbd> 斜体 &nbsp;<kbd>Ctrl+K</kbd> 链接</span>';
    wrap.insertBefore(statusbar, ta);
    this.statusbar = statusbar;
    this.wordCount = statusbar.querySelector('.md-word-count');

    // 同步内容到原 textarea
    editor.addEventListener('input', function() {
      ta.value = editor.value;
      self._updateWordCount();
      if (self._previewActive) self._renderPreview();
    });

    // 快捷键
    editor.addEventListener('keydown', function(e) {
      self._handleKeydown(e);
    });

    // Tab 键 → 插入2空格
    editor.addEventListener('keydown', function(e) {
      if (e.key === 'Tab') {
        e.preventDefault();
        self._insertText('  ');
      }
    });

    this._updateWordCount();
    this._previewActive = false;
  };

  MdEditor.prototype._buildToolbar = function() {
    var self = this;
    var toolbar = this.toolbar;
    var defs = {
      bold:        { icon:'B', title:'粗体 Ctrl+B', style:'font-weight:bold', action: function(){ self._wrapText('**','**','粗体文本'); }},
      italic:      { icon:'I', title:'斜体 Ctrl+I', style:'font-style:italic', action: function(){ self._wrapText('*','*','斜体文本'); }},
      strikethrough:{ icon:'S̶', title:'删除线', style:'text-decoration:line-through', action: function(){ self._wrapText('~~','~~','删除文本'); }},
      h1:          { icon:'H1', title:'一级标题', action: function(){ self._prefixLine('# '); }},
      h2:          { icon:'H2', title:'二级标题', action: function(){ self._prefixLine('## '); }},
      h3:          { icon:'H3', title:'三级标题', action: function(){ self._prefixLine('### '); }},
      ul:          { icon:'⁜', title:'无序列表', action: function(){ self._prefixLine('- '); }},
      ol:          { icon:'①', title:'有序列表', action: function(){ self._prefixLines(function(line, i){ return (i+1)+'. '+line; }); }},
      quote:       { icon:'❝', title:'引用', action: function(){ self._prefixLine('> '); }},
      code:        { icon:'<>', title:'代码块', action: function(){ self._wrapText('\n```\n','\n```\n','代码'); }},
      link:        { icon:'🔗', title:'插入链接 Ctrl+K', action: function(){
        var url = prompt('请输入链接地址:', 'https://');
        if (url) self._wrapText('[',']('+url+')','链接文本');
      }},
      table:       { icon:'⊞', title:'插入表格', action: function(){
        self._insertText('\n| 列1 | 列2 | 列3 |\n| --- | --- | --- |\n| 内容 | 内容 | 内容 |\n');
      }},
      hr:          { icon:'—', title:'分隔线', action: function(){ self._insertText('\n---\n'); }},
      preview:     { icon:'👁', title:'预览', toggle: true, action: function(btn){ self._togglePreview(btn); }},
      fullscreen:  { icon:'⛶', title:'全屏', toggle: true, action: function(btn){ self._toggleFullscreen(btn); }},
    };

    this.options.toolbar.forEach(function(name) {
      if (name === '|') {
        var sep = document.createElement('span');
        sep.style.cssText = 'border-left:1px solid #dee2e6;margin:2px 4px;';
        toolbar.appendChild(sep);
        return;
      }
      var def = defs[name];
      if (!def) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.title = def.title;
      btn.className = 'btn btn-sm btn-outline-secondary md-toolbar-btn';
      btn.style.cssText = 'min-width:32px;padding:2px 6px;font-size:13px;' + (def.style || '');
      btn.textContent = def.icon;
      btn.addEventListener('click', function() {
        def.action(btn);
        // 让编辑器重新获取焦点
        setTimeout(function(){ self.editor.focus(); }, 10);
      });
      toolbar.appendChild(btn);
    });
  };

  MdEditor.prototype._handleKeydown = function(e) {
    if (e.ctrlKey || e.metaKey) {
      if (e.key === 'b' || e.key === 'B') { e.preventDefault(); this._wrapText('**','**','粗体文本'); }
      if (e.key === 'i' || e.key === 'I') { e.preventDefault(); this._wrapText('*','*','斜体文本'); }
      if (e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        var url = prompt('请输入链接地址:', 'https://');
        if (url) this._wrapText('[',']('+url+')','链接文本');
      }
    }
  };

  MdEditor.prototype._getSelection = function() {
    var ta = this.editor;
    return { start: ta.selectionStart, end: ta.selectionEnd, text: ta.value.substring(ta.selectionStart, ta.selectionEnd) };
  };

  MdEditor.prototype._insertText = function(text) {
    var ta = this.editor;
    var sel = this._getSelection();
    var before = ta.value.substring(0, sel.start);
    var after = ta.value.substring(sel.end);
    ta.value = before + text + after;
    ta.selectionStart = ta.selectionEnd = sel.start + text.length;
    this.textarea.value = ta.value;
    this._updateWordCount();
    if (this._previewActive) this._renderPreview();
  };

  MdEditor.prototype._wrapText = function(before, after, placeholder) {
    var ta = this.editor;
    var sel = this._getSelection();
    var selectedText = sel.text || placeholder;
    var newText = before + selectedText + after;
    var beforeVal = ta.value.substring(0, sel.start);
    var afterVal = ta.value.substring(sel.end);
    ta.value = beforeVal + newText + afterVal;
    var newStart = sel.start + before.length;
    var newEnd = newStart + selectedText.length;
    ta.selectionStart = newStart;
    ta.selectionEnd = newEnd;
    this.textarea.value = ta.value;
    this._updateWordCount();
    if (this._previewActive) this._renderPreview();
  };

  MdEditor.prototype._prefixLine = function(prefix) {
    var ta = this.editor;
    var sel = this._getSelection();
    var lineStart = ta.value.lastIndexOf('\n', sel.start - 1) + 1;
    var before = ta.value.substring(0, lineStart);
    var after = ta.value.substring(lineStart);
    ta.value = before + prefix + after;
    ta.selectionStart = ta.selectionEnd = sel.start + prefix.length;
    this.textarea.value = ta.value;
    this._updateWordCount();
    if (this._previewActive) this._renderPreview();
  };

  MdEditor.prototype._prefixLines = function(fn) {
    var ta = this.editor;
    var sel = this._getSelection();
    var selected = sel.text;
    if (!selected) { this._prefixLine('1. '); return; }
    var lines = selected.split('\n');
    var replaced = lines.map(fn).join('\n');
    ta.value = ta.value.substring(0, sel.start) + replaced + ta.value.substring(sel.end);
    this.textarea.value = ta.value;
    this._updateWordCount();
    if (this._previewActive) this._renderPreview();
  };

  MdEditor.prototype._togglePreview = function(btn) {
    this._previewActive = !this._previewActive;
    if (this._previewActive) {
      this._renderPreview();
      this.preview.style.display = 'block';
      this.editor.style.flex = '1';
      btn.classList.add('active', 'btn-primary');
      btn.classList.remove('btn-outline-secondary');
    } else {
      this.preview.style.display = 'none';
      btn.classList.remove('active', 'btn-primary');
      btn.classList.add('btn-outline-secondary');
    }
  };

  MdEditor.prototype._renderPreview = function() {
    var md = this.editor.value;
    if (typeof marked !== 'undefined') {
      this.preview.innerHTML = marked.parse(md);
    } else {
      // 简单回退
      this.preview.innerHTML = '<pre>' + md.replace(/</g,'&lt;') + '</pre>';
    }
  };

  MdEditor.prototype._toggleFullscreen = function(btn) {
    var wrap = this.wrap;
    if (!this._fullscreen) {
      wrap._origStyle = wrap.style.cssText;
      wrap.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;margin:0;border-radius:0;background:#fff;display:flex;flex-direction:column;';
      this.body.style.height = (window.innerHeight - 90) + 'px';
      this._fullscreen = true;
      btn.title = '退出全屏';
      btn.textContent = '✕';
      document.body.style.overflow = 'hidden';
    } else {
      wrap.style.cssText = wrap._origStyle || '';
      this.body.style.height = this.options.height + 'px';
      this._fullscreen = false;
      btn.title = '全屏';
      btn.textContent = '⛶';
      document.body.style.overflow = '';
    }
  };

  MdEditor.prototype._updateWordCount = function() {
    var text = this.editor.value;
    var count = text.replace(/\s/g, '').length;
    if (this.wordCount) this.wordCount.textContent = '字数: ' + count;
  };

  MdEditor.prototype.getValue = function() {
    return this.editor.value;
  };

  MdEditor.prototype.setValue = function(val) {
    this.editor.value = val;
    this.textarea.value = val;
    this._updateWordCount();
    if (this._previewActive) this._renderPreview();
  };

  // 便捷初始化：将页面中所有 .md-editor 的 textarea 自动初始化
  MdEditor.initAll = function(selector, options) {
    var elems = document.querySelectorAll(selector || 'textarea.md-editor');
    var instances = [];
    elems.forEach(function(el) {
      instances.push(new MdEditor(el, options));
    });
    return instances;
  };

  global.MdEditor = MdEditor;
})(window);
