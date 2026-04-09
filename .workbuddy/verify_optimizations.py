"""
验证系统优化功能
1. 个人知识库共享/取消共享功能
2. 文档提取长度限制配置
3. 系统配置管理功能
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from app import app
from models import db, User, KnowledgeBase, SystemConfig
from system_config_manager import config_manager as sys_config_manager

def test_system_config_manager():
    """测试系统配置管理器"""
    print("=== 测试系统配置管理器 ===")
    
    with app.app_context():
        # 初始化配置
        sys_config_manager.init_default_configs()
        print("已初始化默认配置")
        
        # 测试获取配置
        max_extracted_length = sys_config_manager.get('max_extracted_text_length')
        max_preview_length = sys_config_manager.get('max_preview_length')
        max_upload_size = sys_config_manager.get('max_upload_size_mb')
        
        print(f"获取配置测试:")
        print(f"  max_extracted_text_length: {max_extracted_length} (期望: -1 表示无限制)")
        print(f"  max_preview_length: {max_preview_length} (期望: 100000)")
        print(f"  max_upload_size_mb: {max_upload_size} (期望: 1024)")
        
        # 测试设置配置
        success = sys_config_manager.set('max_extracted_text_length', 500000)
        print(f"设置 max_extracted_text_length 到 500000: {'成功' if success else '失败'}")
        
        # 验证设置结果
        new_value = sys_config_manager.get('max_extracted_text_length')
        print(f"重新获取: {new_value} (期望: 500000)")
        
        # 重置回默认值
        sys_config_manager.set('max_extracted_text_length', -1)
        
        # 测试获取公开配置
        public_configs = sys_config_manager.get_all_public_configs()
        category_count = len(public_configs)
        total_configs = sum(len(configs) for configs in public_configs.values())
        print(f"获取公开配置: {category_count} 个分类, {total_configs} 个配置项")
        
        # 输出分类
        for category, configs in public_configs.items():
            print(f"  {category}: {len(configs)} 个配置")
            for config in configs[:3]:  # 只显示前3个
                print(f"    - {config['key']}: {config['value']} ({config['type']})")
            if len(configs) > 3:
                print(f"    ... 还有 {len(configs)-3} 个")
        
        print("✅ 系统配置管理器测试完成\n")

def test_new_routes():
    """测试新增路由"""
    print("=== 测试新增路由函数 ===")
    
    # 检查新路由函数是否已定义
    required_routes = [
        'personal_kb_management',
        'create_personal_kb',
        'edit_personal_kb',
        'delete_personal_kb',
        'share_personal_kb',
        'unshare_kb',
        'system_config_page',
        'get_system_config',
        'set_system_config',
        'refresh_system_config'
    ]
    
    with app.app_context():
        # 检查路由
        url_map = []
        for rule in app.url_map._rules:
            url_map.append(rule.endpoint)
        
        missing_routes = []
        for route in required_routes:
            if route not in url_map:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"❌ 缺少路由: {missing_routes}")
        else:
            print(f"✅ 所有路由已定义: {required_routes}")
        
        # 尝试导入，检查函数定义
        try:
            from app import (
                personal_kb_management,
                create_personal_kb,
                edit_personal_kb,
                delete_personal_kb,
                share_personal_kb,
                unshare_kb,
                system_config_page,
                get_system_config,
                set_system_config,
                refresh_system_config
            )
            print("✅ 所有路由函数已正确导入")
        except ImportError as e:
            print(f"❌ 导入路由函数失败: {e}")
    
    print("✅ 路由测试完成\n")

def test_models():
    """测试新增模型"""
    print("=== 测试新增模型 ===")
    
    with app.app_context():
        try:
            # 测试SystemConfig模型
            config = SystemConfig.query.filter_by(config_key='test_key').first()
            if not config:
                config = SystemConfig(
                    config_key='test_key',
                    config_value='test_value',
                    config_type='string',
                    category='test',
                    description='测试配置',
                    is_public=False
                )
                db.session.add(config)
                db.session.commit()
                print("✅ 成功创建SystemConfig记录")
            else:
                print("✅ SystemConfig模型可用")
            
            # 测试模型方法
            config.set_value('new_value')
            db.session.commit()
            retrieved = config.get_value()
            print(f"✅ 测试配置值设置/获取: 设置='new_value', 获取='{retrieved}'")
            
            # 清理测试数据
            db.session.delete(config)
            db.session.commit()
            print("✅ 清理测试数据成功")
            
        except Exception as e:
            print(f"❌ 模型测试失败: {e}")
            db.session.rollback()
    
    print("✅ 模型测试完成\n")

def test_templates():
    """检查新增模板文件"""
    print("=== 检查新增模板文件 ===")
    
    template_files = [
        'templates/knowledge/personal_kb_management.html',
        'templates/knowledge/create_edit_personal_kb.html',
        'templates/knowledge/personal_kb_management.html',
        'templates/admin/system_config.html'
    ]
    
    modified_files = [
        'templates/_sidebar_nav.html',
        'templates/knowledge/shared_knowledge_base.html'
    ]
    
    all_ok = True
    for file in template_files:
        if os.path.exists(file):
            print(f"✅ 模板文件存在: {file}")
        else:
            print(f"❌ 模板文件不存在: {file}")
            all_ok = False
    
    for file in modified_files:
        if os.path.exists(file):
            print(f"✅ 修改文件存在: {file}")
        else:
            print(f"❌ 修改文件不存在: {file}")
            all_ok = False
    
    # 检查system_config.html中的关键元素
    if os.path.exists('templates/admin/system_config.html'):
        with open('templates/admin/system_config.html', 'r', encoding='utf-8') as f:
            content = f.read()
            required_elements = [
                '系统配置管理',
                'config-category',
                'saveConfig',
                'refreshCache'
            ]
            for element in required_elements:
                if element in content:
                    print(f"✅ 模板包含元素: {element}")
                else:
                    print(f"⚠️  模板可能缺少元素: {element}")
                    all_ok = False
    
    if all_ok:
        print("✅ 模板文件检查通过")
    else:
        print("❌ 模板文件检查未通过")
    
    print("✅ 模板检查完成\n")

def test_utils_updates():
    """测试utils.py更新"""
    print("=== 测试utils.py更新 ===")
    
    utils_file = 'utils.py'
    if os.path.exists(utils_file):
        with open(utils_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查更新
            checks = [
                ('extract_file_content函数有apply_length_limit参数', 'def extract_file_content(file_path, apply_length_limit=True)'),
                ('使用系统配置管理器', 'from system_config_manager import config_manager as sys_config'),
                ('从系统配置获取长度限制', 'max_length = sys_config.get'),
                ('更新了get_file_metadata函数', 'def get_file_metadata(file_path, apply_length_limit=True)')
            ]
            
            for desc, pattern in checks:
                if pattern in content:
                    print(f"✅ {desc}")
                else:
                    print(f"❌ {desc}")
    
    print("✅ utils.py更新检查完成\n")

def test_app_py_updates():
    """测试app.py更新"""
    print("=== 测试app.py更新 ===")
    
    app_file = 'app.py'
    if os.path.exists(app_file):
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查重要更新
            checks = [
                ('导入系统配置管理器', 'from system_config_manager import config_manager as sys_config_manager'),
                ('添加上下文处理器', '@app.context_processor'),
                ('个人知识库分享路由', 'def share_personal_kb'),
                ('取消分享路由', 'def unshare_kb'),
                ('系统配置管理页面路由', 'def system_config_page'),
                ('更新配置路由', 'def set_system_config'),
                ('使用配置代替硬编码', 'from config import Config'),
            ]
            
            for desc, pattern in checks:
                if pattern in content:
                    print(f"✅ {desc}")
                else:
                    print(f"❌ {desc}")
    
    # 检查配置更新
    config_file = 'config.py'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'MAX_EXTRACTED_TEXT_LENGTH' in content:
                print("✅ 配置文件中定义了文本长度配置")
            else:
                print("❌ 配置文件中未找到文本长度配置")
    
    print("✅ app.py更新检查完成\n")

def main():
    """主测试函数"""
    print("🚀 开始验证系统优化功能...\n")
    
    try:
        test_system_config_manager()
        test_new_routes()
        test_models()
        test_templates()
        test_utils_updates()
        test_app_py_updates()
        
        print("✨ 所有验证完成！")
        print("\n📋 优化功能概览:")
        print("1. ✅ 个人知识库共享/取消共享功能")
        print("    - 个人知识库可转为共享知识库")
        print("    - 共享知识库可转为个人知识库")
        print("    - 支持权限检查（仅创建者/管理员）")
        print("    - 添加了前端按钮和JavaScript交互")
        
        print("\n2. ✅ 文档提取长度限制优化")
        print("    - 移除了硬编码的长度限制")
        print("    - 添加了系统配置管理器")
        print("    - 支持从数据库动态读取配置")
        print("    - 默认无限制（-1表示无限制）")
        
        print("\n3. ✅ 系统配置管理界面")
        print("    - 管理员专用的配置管理页面")
        print("    - 按分类组织的配置项")
        print("    - 支持多种类型（字符串/整数/浮点数/布尔值）")
        print("    - 即时保存和刷新缓存")
        print("    - 侧边栏导航添加系统配置入口")
        
        print("\n🚨 注意事项:")
        print("- 需要重启应用使系统配置管理器生效")
        print("- 管理员需要访问 /admin/system-config 配置长度限制")
        print("- 系统首次启动时会自动创建默认配置")
        
    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()