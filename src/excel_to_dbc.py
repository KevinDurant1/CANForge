#!/usr/bin/env python3
"""
Excel转DBC转换器
从Excel协议文件自动生成DBC文件，支持智能工作表识别

用法:
    python3 src/cli.py convert
    python3 src/cli.py convert --excel path/to/excel.xls --output path/to/output/
    bash scripts/convert.sh
"""

import pandas as pd
import os
import argparse
import re
from typing import Dict, List, Optional, Tuple

# DBC文件头模板
DBC_HEADER = '''VERSION ""

NS_ : 
\tNS_DESC_
\tCM_
\tBA_DEF_
\tBA_
\tVAL_
\tCAT_DEF_
\tCAT_
\tFILTER
\tBA_DEF_DEF_
\tEV_DATA_
\tENVVAR_DATA_
\tSGTYPE_
\tSGTYPE_VAL_
\tBA_DEF_SGTYPE_
\tBA_SGTYPE_
\tSIG_TYPE_REF_
\tVAL_TABLE_
\tSIG_GROUP_
\tSIG_VALTYPE_
\tSIGTYPE_VALTYPE_
\tBO_TX_BU_
\tBA_DEF_REL_
\tBA_REL_
\tBA_DEF_DEF_REL_
\tBU_SG_REL_
\tBU_EV_REL_
\tBU_BO_REL_
\tSG_MUL_VAL_

BS_:

BU_:

'''

# DBC属性定义模板
DBC_BA_DEF = '''BA_DEF_ SG_  "GenSigSendType" ENUM  "Cyclic","OnWrite","OnWriteWithRepetition","OnChange","OnChangeWithRepetition","IfActive","IfActiveWithRepetition","NoSigSendType";
BA_DEF_ SG_  "GenSigInactiveValue" INT 0 0;
BA_DEF_ BO_  "GenMsgCycleTime" INT 0 10000;
BA_DEF_ BO_  "GenMsgSendType" ENUM  "Cyclic","not_used","not_used","not_used","not_used","Cyclic","not_used","IfActive","NoMsgSendType";
BA_DEF_  "DBName" STRING ;
BA_DEF_  "BusType" STRING ;
BA_DEF_DEF_  "GenSigSendType" "Cyclic";
BA_DEF_DEF_  "GenSigInactiveValue" 0;
BA_DEF_DEF_  "GenMsgCycleTime" 0;
BA_DEF_DEF_  "GenMsgSendType" "NoMsgSendType";
BA_DEF_DEF_  "DBName" "";
BA_DEF_DEF_  "BusType" "CAN";
'''


class Signal:
    """CAN信号定义"""
    def __init__(self, name: str, start_bit: int, bit_length: int, 
                 byte_order: str = 'Intel', data_type: str = 'unsigned',
                 factor: float = 1.0, offset: float = 0.0,
                 min_val: float = 0.0, max_val: float = 0.0,
                 unit: str = '', description: str = ''):
        self.name = self._sanitize_name(name)
        self.start_bit = start_bit
        self.bit_length = bit_length
        self.byte_order = byte_order  # Intel = Little Endian, Motorola = Big Endian
        self.data_type = data_type  # signed or unsigned
        self.factor = factor
        self.offset = offset
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.description = description
    
    def _sanitize_name(self, name: str) -> str:
        """清理信号名称，只保留字母、数字和下划线"""
        if pd.isna(name) or not name:
            return "Unknown_Signal"
        # 替换非法字符
        name = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
        # 确保不以数字开头
        if name and name[0].isdigit():
            name = '_' + name
        return name or "Unknown_Signal"
    
    def to_dbc_string(self, receiver: str = "Vector__XXX") -> str:
        """生成DBC格式的信号定义字符串"""
        # 字节序标记: @1+ = Little Endian (Intel), @0+ = Big Endian (Motorola)
        byte_order_flag = "1" if self.byte_order.lower() == 'intel' else "0"
        # 符号标记: + = unsigned, - = signed
        sign_flag = "-" if self.data_type.lower() == 'signed' else "+"
        
        return f' SG_ {self.name} : {self.start_bit}|{self.bit_length}@{byte_order_flag}{sign_flag} ({self.factor},{self.offset}) [{self.min_val}|{self.max_val}] "{self.unit}"  {receiver}'


class Message:
    """CAN消息定义"""
    def __init__(self, name: str, msg_id: int, dlc: int = 8, 
                 transmitter: str = 'Vector__XXX', cycle_time: int = 0):
        self.name = self._sanitize_name(name)
        self.msg_id = msg_id
        self.dlc = dlc
        self.transmitter = transmitter
        self.cycle_time = cycle_time
        self.signals: List[Signal] = []
    
    def _sanitize_name(self, name: str) -> str:
        """清理消息名称"""
        if pd.isna(name) or not name:
            return "Unknown_Message"
        name = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
        if name and name[0].isdigit():
            name = '_' + name
        return name or "Unknown_Message"
    
    def add_signal(self, signal: Signal):
        """添加信号到消息"""
        self.signals.append(signal)
    
    def to_dbc_string(self) -> str:
        """生成DBC格式的消息定义字符串"""
        lines = [f'BO_ {self.msg_id} {self.name}: {self.dlc} {self.transmitter}']
        for signal in self.signals:
            lines.append(signal.to_dbc_string())
        return '\n'.join(lines)


class ExcelToDBCConverter:
    """Excel到DBC转换器"""
    
    # 列名映射（支持不同格式的列名）
    COLUMN_MAPPING = {
        'msg_name': ['Msg Name', '报文名称', 'Message Name'],
        'msg_id': ['Msg ID', '报文标识符', 'Message ID', 'CAN ID'],
        'msg_cycle': ['Msg Cycle Time', '报文周期时间', 'Cycle Time'],
        'msg_length': ['Msg Length', '报文长度', 'DLC'],
        'signal_name': ['Signal Name', '信号名称'],
        'signal_desc': ['Signal Description', '信号描述'],
        'byte_order': ['Byte Order', '排列格式'],
        'start_byte': ['Start Byte', '起始字节'],
        'start_bit': ['Start Bit', '起始位'],
        'bit_length': ['Bit Length', '信号长度'],
        'data_type': ['Date Type', 'Data Type', '数据类型'],
        'resolution': ['Resolution', '精度', 'Factor'],
        'offset': ['Offset', '偏移量'],
        'min_val': ['Signal Min. Value (phys)', '物理最小值', 'Min Value'],
        'max_val': ['Signal Max. Value (phys)', '物理最大值', 'Max Value'],
        'unit': ['Unit', '单位'],
        'value_desc': ['Signal Value Description', '信号值描述'],
    }
    
    def __init__(self, excel_path: str):
        """初始化转换器"""
        self.excel_path = excel_path
        self.xls = pd.ExcelFile(excel_path)
        print(f"已加载Excel文件: {excel_path}")
        print(f"工作表: {self.xls.sheet_names}")
    
    def _find_column(self, df: pd.DataFrame, col_key: str) -> Optional[str]:
        """根据列名映射查找实际列名"""
        patterns = self.COLUMN_MAPPING.get(col_key, [])
        for col in df.columns:
            col_str = str(col)
            for pattern in patterns:
                if pattern.lower() in col_str.lower():
                    return col
        return None
    
    def _parse_msg_id(self, id_value) -> Optional[int]:
        """解析消息ID（支持十六进制和十进制）"""
        if pd.isna(id_value):
            return None
        id_str = str(id_value).strip()
        try:
            if id_str.lower().startswith('0x'):
                return int(id_str, 16)
            else:
                return int(float(id_str))
        except (ValueError, TypeError):
            return None
    
    def _parse_float(self, value, default: float = 0.0) -> float:
        """安全地解析浮点数"""
        if pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _parse_int(self, value, default: int = 0) -> int:
        """安全地解析整数"""
        if pd.isna(value):
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    def _parse_byte_order(self, value) -> str:
        """解析字节序"""
        if pd.isna(value):
            return 'Intel'
        val_str = str(value).lower()
        if 'motorola' in val_str or 'big' in val_str:
            return 'Motorola'
        return 'Intel'
    
    def _parse_data_type(self, value) -> str:
        """解析数据类型"""
        if pd.isna(value):
            return 'unsigned'
        val_str = str(value).lower()
        if 'signed' in val_str and 'unsigned' not in val_str:
            return 'signed'
        return 'unsigned'
    
    def parse_sheet(self, sheet_name: str) -> List[Message]:
        """解析单个工作表，返回消息列表"""
        print(f"\n解析工作表: {sheet_name}")
        
        # 读取工作表，第一行作为表头
        df = pd.read_excel(self.xls, sheet_name=sheet_name, header=0)
        
        # 查找列名
        col_msg_name = self._find_column(df, 'msg_name')
        col_msg_id = self._find_column(df, 'msg_id')
        col_msg_cycle = self._find_column(df, 'msg_cycle')
        col_msg_length = self._find_column(df, 'msg_length')
        col_signal_name = self._find_column(df, 'signal_name')
        col_signal_desc = self._find_column(df, 'signal_desc')
        col_byte_order = self._find_column(df, 'byte_order')
        col_start_byte = self._find_column(df, 'start_byte')
        col_start_bit = self._find_column(df, 'start_bit')
        col_bit_length = self._find_column(df, 'bit_length')
        col_data_type = self._find_column(df, 'data_type')
        col_resolution = self._find_column(df, 'resolution')
        col_offset = self._find_column(df, 'offset')
        col_min_val = self._find_column(df, 'min_val')
        col_max_val = self._find_column(df, 'max_val')
        col_unit = self._find_column(df, 'unit')
        col_value_desc = self._find_column(df, 'value_desc')
        
        print(f"  找到列: msg_name={col_msg_name}, msg_id={col_msg_id}, signal_name={col_signal_name}")
        
        if not col_msg_id or not col_signal_name:
            print(f"  警告: 缺少必要列，跳过此工作表")
            return []
        
        messages: Dict[int, Message] = {}
        current_msg: Optional[Message] = None
        
        for idx, row in df.iterrows():
            # 检查是否是新消息行（有消息ID和消息名称）
            msg_id = self._parse_msg_id(row.get(col_msg_id) if col_msg_id else None)
            msg_name = row.get(col_msg_name) if col_msg_name else None
            
            if msg_id is not None and not pd.isna(msg_name):
                # 新消息
                msg_cycle = self._parse_int(row.get(col_msg_cycle) if col_msg_cycle else None, 0)
                msg_length = self._parse_int(row.get(col_msg_length) if col_msg_length else None, 8)
                
                current_msg = Message(
                    name=str(msg_name),
                    msg_id=msg_id,
                    dlc=msg_length,
                    cycle_time=msg_cycle
                )
                messages[msg_id] = current_msg
            
            # 检查是否有信号定义
            signal_name = row.get(col_signal_name) if col_signal_name else None
            if current_msg and not pd.isna(signal_name) and str(signal_name).strip():
                # Excel中的"Start Bit"已经是绝对位位置（从bit0开始计数）
                # 直接使用该值作为DBC的起始位
                start_bit = self._parse_int(row.get(col_start_bit) if col_start_bit else None, 0)
                
                bit_length = self._parse_int(row.get(col_bit_length) if col_bit_length else None, 1)
                byte_order = self._parse_byte_order(row.get(col_byte_order) if col_byte_order else None)
                data_type = self._parse_data_type(row.get(col_data_type) if col_data_type else None)
                factor = self._parse_float(row.get(col_resolution) if col_resolution else None, 1.0)
                offset = self._parse_float(row.get(col_offset) if col_offset else None, 0.0)
                min_val = self._parse_float(row.get(col_min_val) if col_min_val else None, 0.0)
                max_val = self._parse_float(row.get(col_max_val) if col_max_val else None, 0.0)
                unit = str(row.get(col_unit) if col_unit else '') if not pd.isna(row.get(col_unit) if col_unit else None) else ''
                description = str(row.get(col_signal_desc) if col_signal_desc else '') if not pd.isna(row.get(col_signal_desc) if col_signal_desc else None) else ''
                
                signal = Signal(
                    name=str(signal_name),
                    start_bit=start_bit,
                    bit_length=bit_length,
                    byte_order=byte_order,
                    data_type=data_type,
                    factor=factor,
                    offset=offset,
                    min_val=min_val,
                    max_val=max_val,
                    unit=unit,
                    description=description
                )
                current_msg.add_signal(signal)
        
        msg_list = list(messages.values())
        print(f"  解析完成: {len(msg_list)} 条消息")
        for msg in msg_list:
            print(f"    - {msg.name} (0x{msg.msg_id:X}): {len(msg.signals)} 个信号")
        
        return msg_list
    
    def generate_dbc(self, messages: List[Message], db_name: str) -> str:
        """生成DBC文件内容"""
        lines = [DBC_HEADER]
        
        # 消息和信号定义
        for msg in messages:
            lines.append(msg.to_dbc_string())
            lines.append('')
        
        # 信号注释
        lines.append('')
        for msg in messages:
            for signal in msg.signals:
                if signal.description:
                    # 转义引号和处理换行
                    desc = signal.description.replace('"', '\\"').replace('\n', ' ')
                    lines.append(f'CM_ SG_ {msg.msg_id} {signal.name} "{desc}";')
        
        # 属性定义
        lines.append('')
        lines.append(DBC_BA_DEF)
        
        # 数据库名称
        lines.append(f'BA_ "DBName" "{db_name}";')
        
        # 消息周期时间
        for msg in messages:
            if msg.cycle_time > 0:
                lines.append(f'BA_ "GenMsgCycleTime" BO_ {msg.msg_id} {msg.cycle_time};')
                lines.append(f'BA_ "GenMsgSendType" BO_ {msg.msg_id} 0;')
        
        lines.append('')
        return '\n'.join(lines)
    
    def convert_all(self, output_dir: str):
        """转换所有工作表并保存DBC文件（智能处理，跳过非协议工作表）"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 智能识别需要处理的工作表
        # 跳过常见的非协议工作表（如索引、说明、Map等）
        skip_patterns = ['map', 'index', '索引', '说明', 'readme', 'info', '目录']
        sheets_to_process = []
        
        for sheet_name in self.xls.sheet_names:
            # 检查是否应该跳过
            should_skip = False
            for pattern in skip_patterns:
                if pattern.lower() in sheet_name.lower():
                    should_skip = True
                    break
            
            if not should_skip:
                sheets_to_process.append(sheet_name)
            else:
                print(f"跳过非协议工作表: {sheet_name}")
        
        if not sheets_to_process:
            print("警告: 没有找到需要处理的工作表")
            return
        
        print(f"\n将处理以下工作表: {sheets_to_process}")
        
        for sheet_name in sheets_to_process:
            messages = self.parse_sheet(sheet_name)
            
            if not messages:
                print(f"警告: 工作表 {sheet_name} 没有有效消息，跳过")
                continue
            
            # 生成DBC文件名（保持原工作表名称）
            # 如果工作表名已经包含.dbc，则直接使用；否则添加.dbc后缀
            if sheet_name.lower().endswith('.dbc'):
                dbc_filename = sheet_name
            else:
                dbc_filename = f"{sheet_name}.dbc"
            
            dbc_path = os.path.join(output_dir, dbc_filename)
            
            # 生成DBC内容
            dbc_content = self.generate_dbc(messages, sheet_name)
            
            # 保存文件
            with open(dbc_path, 'w', encoding='utf-8') as f:
                f.write(dbc_content)
            
            print(f"已生成: {dbc_path}")
        
        print(f"\nDBC文件生成完成，输出目录: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='从Excel协议文件生成DBC文件')
    parser.add_argument('--excel', '-e', default=None,
                       help='Excel文件路径 (默认: protocol/can_protocol_W2_500k.xls)')
    parser.add_argument('--output', '-o', default=None,
                       help='输出目录 (默认: protocol/dbc/)')
    
    args = parser.parse_args()
    
    # 确定路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    
    excel_path = args.excel or os.path.join(parent_dir, 'protocol', 'can_protocol_W2_500k.xls')
    output_dir = args.output or os.path.join(parent_dir, 'protocol', 'dbc')
    
    if not os.path.exists(excel_path):
        print(f"错误: Excel文件不存在: {excel_path}")
        return 1
    
    try:
        converter = ExcelToDBCConverter(excel_path)
        converter.convert_all(output_dir)
        return 0
    except Exception as e:
        print(f"转换失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
