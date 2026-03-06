"""
DBC加载器 - 智能编码检测
自动扫描并加载DBC文件，支持多种编码格式（UTF-8/GBK/GB2312/Latin-1）
"""

import cantools
import os
from typing import Dict, Optional


class DBCLoader:
    """DBC文件加载器"""
    
    def __init__(self, dbc_dir: str = None):
        """
        初始化DBC加载器
        
        Args:
            dbc_dir: DBC文件目录，默认为protocol/dbc
        """
        if dbc_dir is None:
            # 默认使用protocol/dbc目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dbc_dir = os.path.join(project_root, 'protocol', 'dbc')
        
        self.dbc_dir = dbc_dir
        self.databases: Dict[str, cantools.database.Database] = {}
    
    def load_all(self) -> Dict[str, cantools.database.Database]:
        """
        自动扫描并加载所有DBC文件（智能编码检测）
        
        Returns:
            字典，键为DBC文件名（不含扩展名），值为数据库对象
        """
        if not os.path.exists(self.dbc_dir):
            print(f"警告: DBC目录不存在: {self.dbc_dir}")
            return {}
        
        self.databases.clear()
        
        # 扫描目录下的所有.dbc文件
        for filename in sorted(os.listdir(self.dbc_dir)):
            if filename.endswith('.dbc'):
                dbc_path = os.path.join(self.dbc_dir, filename)
                db_name = os.path.splitext(filename)[0]
                
                try:
                    print(f"正在加载 {dbc_path}...")
                    
                    # 智能编码检测：尝试多种编码
                    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
                    loaded = False
                    
                    for encoding in encodings:
                        try:
                            db = cantools.database.load_file(dbc_path, encoding=encoding)
                            
                            # 验证是否有乱码：检查信号的choices中是否有中文
                            has_chinese = False
                            has_garbled = False
                            
                            for msg in db.messages:
                                for signal in msg.signals:
                                    if signal.choices:
                                        for value_desc in signal.choices.values():
                                            # 检查是否包含中文
                                            if any('\u4e00' <= c <= '\u9fa5' for c in str(value_desc)):
                                                has_chinese = True
                                            # 检查是否包含常见乱码字符
                                            garbled_chars = ['Ã', 'Â', 'Ö', 'Î', 'Ò', 'Ñ', '±', '¶', '¨', '¤']
                                            if any(gc in str(value_desc) for gc in garbled_chars):
                                                has_garbled = True
                                                break
                                    if has_garbled:
                                        break
                                if has_garbled:
                                    break
                            
                            # 如果检测到乱码，尝试下一个编码
                            if has_garbled:
                                continue
                            
                            # 成功加载且无乱码
                            self.databases[db_name] = db
                            loaded = True
                            
                            if has_chinese:
                                print(f"  成功加载 {len(db.messages)} 条消息 (编码: {encoding}, 包含中文)")
                            else:
                                print(f"  成功加载 {len(db.messages)} 条消息 (编码: {encoding})")
                            break
                            
                        except Exception:
                            continue
                    
                    if not loaded:
                        # 如果所有编码都失败，使用默认编码
                        self.databases[db_name] = cantools.database.load_file(dbc_path)
                        print(f"  成功加载 {len(self.databases[db_name].messages)} 条消息 (默认编码)")
                        
                except Exception as e:
                    print(f"加载 {dbc_path} 时出错: {e}")
        
        if not self.databases:
            print("警告: 未找到任何DBC文件")
        else:
            print(f"\n总共加载了 {len(self.databases)} 个DBC文件")
        
        return self.databases
    
    def find_message(self, can_id: int) -> Optional[tuple]:
        """
        在所有DBC中查找CAN ID对应的消息
        
        Args:
            can_id: CAN ID
            
        Returns:
            (database, db_name, message) 或 None
        """
        for db_name, db in self.databases.items():
            try:
                message = db.get_message_by_frame_id(can_id)
                if message:
                    return db, db_name, message
            except:
                pass
        return None
