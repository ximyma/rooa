#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修改 app.py，添加 initialize_db() 调用"""

with open('d:\\myapps\\rooa\\app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 if __name__ == '__main__' 的位置
search_str = "if __name__ == '__main__':"
start_idx = content.find(search_str)

if start_idx != -1:
    # 获取从该位置开始的部分
    old_part = content[start_idx:]
    
    # 创建新的部分
    new_part = """if __name__ == '__main__':
    # 初始化数据库和默认数据
    initialize_db()
    
    # DEBUG 模式：从环境变量读取，默认关闭（公网访问时不暴露调试信息）
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    # HOST：0.0.0.0 监听所有网络接口，允许公网访问
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    # PORT：默认 5000，可通过环境变量覆盖
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host=host, port=port, debug=debug_mode)"""
    
    # 替换
    new_content = content[:start_idx] + new_part
    
    with open('d:\\myapps\\rooa\\app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('Successfully updated app.py!')
else:
    print('Could not find if __name__ == \'__main__\': section')
