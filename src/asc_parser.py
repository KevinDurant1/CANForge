"""
ASC文件解析器
解析ASC格式的CAN报文记录文件，使用DBC文件进行信号解码
"""

import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dbc_loader import DBCLoader


class ASCParser:
    """ASC文件解析器"""
    
    def __init__(self, dbc_loader: DBCLoader):
        """
        初始化解析器
        
        Args:
            dbc_loader: DBC加载器实例
        """
        self.dbc_loader = dbc_loader
        self.stats = defaultdict(int)
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """
        解析单行ASC数据
        
        Args:
            line: ASC文件的一行
            
        Returns:
            解析后的数据字典或None
        """
        parts = line.split()
        if len(parts) < 6:
            return None
        
        try:
            timestamp = float(parts[0])
            channel = parts[1]
            can_id_hex = parts[2]
            direction = parts[3]
            data_length = int(parts[5])
            hex_data = parts[6:6+data_length]
            
            can_id = int(can_id_hex, 16)
            data_bytes = bytes.fromhex(''.join(hex_data))
            
            return {
                'timestamp': timestamp,
                'channel': channel,
                'direction': direction,
                'can_id': can_id,
                'can_id_hex': can_id_hex,
                'data_bytes': data_bytes,
                'data_hex': data_bytes.hex()
            }
        except Exception:
            return None
    
    def decode_message(self, parsed_data: Dict) -> Dict:
        """
        解码CAN消息
        
        Args:
            parsed_data: 解析后的数据
            
        Returns:
            解码结果字典
        """
        result = self.dbc_loader.find_message(parsed_data['can_id'])
        
        if result:
            db, db_name, message = result
            try:
                decoded = message.decode(parsed_data['data_bytes'])
                
                # 同时保存信号的元数据（用于格式化输出）
                signal_metadata = {}
                for signal in message.signals:
                    signal_metadata[signal.name] = {
                        'scale': signal.scale,
                        'offset': signal.offset,
                        'unit': signal.unit
                    }
                
                self.stats[f"通道{parsed_data['channel']}解码成功"] += 1
                return {
                    'message_name': message.name,
                    'decoded': decoded,
                    'signal_metadata': signal_metadata,
                    'db_name': db_name,
                    'error': None
                }
            except Exception as e:
                self.stats[f"通道{parsed_data['channel']}解码失败"] += 1
                return {
                    'message_name': message.name,
                    'decoded': None,
                    'signal_metadata': None,
                    'db_name': db_name,
                    'error': str(e)
                }
        else:
            self.stats[f"通道{parsed_data['channel']}无DBC文件"] += 1
            return {
                'message_name': '未知',
                'decoded': None,
                'signal_metadata': None,
                'db_name': '未知',
                'error': '无对应DBC文件'
            }
    
    def parse_file(self, asc_file: str) -> Tuple[List[Dict], List[Dict]]:
        """
        解析ASC文件
        
        Args:
            asc_file: ASC文件路径
            
        Returns:
            (解码消息列表, 错误消息列表)
        """
        if not os.path.exists(asc_file):
            print(f"错误: 文件 {asc_file} 不存在")
            return [], []
        
        print(f"\n正在解析 {asc_file}...")
        
        self.stats.clear()
        decoded_messages = []
        error_messages = []
        
        try:
            with open(asc_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # 跳过空行、注释和文件头
                if not line or line.startswith('//') or line.startswith(';'):
                    continue
                if line.startswith('date') or line.startswith('base'):
                    continue
                
                # 解析行数据
                parsed_data = self.parse_line(line)
                if not parsed_data:
                    self.stats["格式错误"] += 1
                    error_messages.append({
                        'line': line_num,
                        'timestamp': None,
                        'channel': None,
                        'can_id': None,
                        'error': f"格式错误: {line}"
                    })
                    continue
                
                # 解码消息
                decode_result = self.decode_message(parsed_data)
                
                # 保存解码结果
                decoded_messages.append({
                    'timestamp': parsed_data['timestamp'],
                    'channel': parsed_data['channel'],
                    'direction': parsed_data['direction'],
                    'can_id': parsed_data['can_id_hex'],
                    'data': parsed_data['data_hex'],
                    'message_name': decode_result['message_name'],
                    'decoded': decode_result['decoded'],
                    'signal_metadata': decode_result.get('signal_metadata'),
                    'db_name': decode_result['db_name']
                })
                
                # 记录错误
                if decode_result['error']:
                    error_messages.append({
                        'line': line_num,
                        'timestamp': parsed_data['timestamp'],
                        'channel': parsed_data['channel'],
                        'can_id': parsed_data['can_id_hex'],
                        'error': decode_result['error']
                    })
            
            # 打印统计信息
            print(f"\n解析完成!")
            print(f"总消息数: {len(decoded_messages)}")
            print(f"错误消息数: {len(error_messages)}")
            print(f"统计信息:")
            for key, value in sorted(self.stats.items()):
                print(f"  {key}: {value}")
            
            return decoded_messages, error_messages
            
        except Exception as e:
            print(f"解析文件时出错: {e}")
            import traceback
            traceback.print_exc()
            return [], []
