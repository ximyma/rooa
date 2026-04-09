# -*- coding: utf-8 -*-
"""初始化档案管理示例数据"""
from app import app, db
from archive_models import ArchiveFonds, ArchiveCatalog, ArchiveVolume, ArchiveFile, ArchiveBorrow
from datetime import datetime
import random

def init_archive_data():
    with app.app_context():
        # 检查是否已有数据
        if ArchiveFonds.query.count() > 0:
            print('[INFO] 数据库中已有全宗数据')
            return
        
        # 创建全宗
        fonds = ArchiveFonds(
            fonds_code='DATIAN',
            fonds_name='达天科技有限公司',
            fonds_type='企业',
            description='达天科技企业档案全宗',
            total_volumes=0,
            total_files=0,
            is_active=True
        )
        db.session.add(fonds)
        db.session.flush()
        
        # 创建目录
        catalogs = []
        catalog_names = [
            ('WL', '文书档案', '30年'),
            ('KJ', '科技档案', '永久'),
            ('KUAI', '会计档案', '30年'),
            ('RS', '人事档案', '永久'),
            ('HT', '合同档案', '30年'),
        ]
        for code, name, retention in catalog_names:
            cat = ArchiveCatalog(
                fonds_id=fonds.id,
                catalog_code=code,
                catalog_name=name,
                retention_period=retention
            )
            catalogs.append(cat)
            db.session.add(cat)
        db.session.flush()
        
        # 为文书档案创建年度子目录
        wl_catalog = catalogs[0]
        for year in [2022, 2023, 2024]:
            sub_cat = ArchiveCatalog(
                fonds_id=fonds.id,
                catalog_code='WL-' + str(year),
                catalog_name=str(year) + '年度文书',
                parent_id=wl_catalog.id,
                retention_period='30年'
            )
            db.session.add(sub_cat)
        
        # 创建案卷
        volumes = []
        vol_titles = ['综合管理类', '人事劳资类', '财务会计类', '市场营销类', '技术研发类']
        for i, title in enumerate(vol_titles):
            vol = ArchiveVolume(
                fonds_id=fonds.id,
                catalog_id=catalogs[0].id,
                volume_code='2024-' + str(i+1).zfill(3),
                volume_title=title + '第' + str(i+1) + '卷',
                volume_year=2024,
                retention_period='30年',
                security_level='公开',
                responsibility='达天科技综合管理部',
                storage_location='A-' + str(random.randint(1,5)).zfill(2) + '-' + str(random.randint(1,20)).zfill(2)
            )
            volumes.append(vol)
            db.session.add(vol)
        db.session.flush()
        
        # 创建示例档案
        titles = [
            '关于2024年度工作总结的通知',
            '关于表彰先进的报告',
            '关于人员招聘的请示',
            '设备采购合同',
            '场地租赁协议',
            '关于加强安全管理的通知',
            '年度财务审计报告',
            '新产品研发立项报告',
            '员工绩效考核办法',
            '办公室管理规定',
        ]
        
        keywords_list = [
            '通知,总结,年度',
            '表彰,先进,报告',
            '招聘,人员,请示',
            '设备,采购,合同',
            '场地,租赁,协议',
            '安全,管理,通知',
            '财务,审计,报告',
            '研发,立项,产品',
            '绩效,考核,员工',
            '办公,管理,规定',
        ]
        
        for i, (title, keywords) in enumerate(zip(titles, keywords_list)):
            year = random.choice([2022, 2023, 2024])
            file_date = datetime(year, random.randint(1, 12), random.randint(1, 28))
            
            archive = ArchiveFile(
                fonds_id=fonds.id,
                catalog_id=catalogs[0].id,
                volume_id=random.choice(volumes).id if random.random() > 0.3 else None,
                file_code=str(year) + '-' + str(i+1).zfill(4),
                title=title,
                responsibility='达天科技综合管理部',
                file_date=file_date,
                file_year=year,
                retention_period=random.choice(['永久', '30年', '10年']),
                security_level=random.choice(['公开', '内部']),
                archive_type=random.choice(['通知', '报告', '请示', '合同', '制度']),
                page_count=random.randint(1, 50),
                keywords=keywords,
                content_text='这是' + title + '的正文内容...',
                summary=title + '的主要内容摘要...',
                is_digitized=True,
                status='active'
            )
            db.session.add(archive)
        
        db.session.commit()
        print('[OK] 档案管理示例数据创建成功!')
        print('  - 全宗: 1 个 (达天科技有限公司)')
        print('  - 目录: ' + str(ArchiveCatalog.query.count()) + ' 个')
        print('  - 案卷: ' + str(ArchiveVolume.query.count()) + ' 个')
        print('  - 档案: ' + str(ArchiveFile.query.count()) + ' 个')

if __name__ == '__main__':
    init_archive_data()
