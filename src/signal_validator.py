#!/usr/bin/env python3
"""
CAN报文验证工具 - 信号验证器
从解析后的CSV文件中提取每个唯一CAN ID，验证解析结果是否与DBC文件一致

用法:
    python3 src/cli.py validate msg/chassis_decoded.csv
    bash docs/validate.sh msg/chassis_decoded.csv
"""

import csv
import sys
import os
from collections import OrderedDict

# 导入DBCLoader以使用智能编码检测
from dbc_loader import DBCLoader


def load_dbc_files():
    """使用DBCLoader加载所有DBC文件（智能编码检测）"""
    loader = DBCLoader()
    databases = loader.load_all()
    return databases


def extract_unique_messages_from_csv(csv_file):
    """从CSV文件中提取每个唯一CAN ID的第一次出现"""
    unique_msgs = OrderedDict()
    
    print(f"正在读取CSV文件: {csv_file}")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            can_id = row['CAN_ID']
            
            # 只保存每个CAN ID的第一次出现
            if can_id not in unique_msgs:
                unique_msgs[can_id] = {
                    'timestamp': row['时间戳'],
                    'channel': row['通道'],
                    'direction': row['方向'],
                    'can_id': can_id,
                    'message_name': row['消息名称'],
                    'dbc_name': row['DBC'],
                    'raw_data': row['原始数据'],
                    'decoded_result': row['解码结果']
                }
    
    print(f"提取到 {len(unique_msgs)} 个唯一CAN ID")
    return unique_msgs


def parse_decoded_result(decoded_str):
    """解析CSV中的解码结果字符串"""
    signals = {}
    
    if not decoded_str or decoded_str.strip() == '':
        return signals
    
    # 按行分割
    lines = decoded_str.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if ':' in line:
            # 移除前导空格和制表符
            line = line.lstrip()
            parts = line.split(':', 1)
            if len(parts) == 2:
                signal_name = parts[0].strip()
                signal_value = parts[1].strip()
                
                # 尝试转换为数值
                try:
                    if '.' in signal_value:
                        signals[signal_name] = float(signal_value)
                    else:
                        signals[signal_name] = int(signal_value)
                except ValueError:
                    # 保持字符串
                    signals[signal_name] = signal_value
    
    return signals


def verify_message(msg_info, databases):
    """验证单个消息的解析结果：信号个数、数据格式、数据内容"""
    can_id_hex = msg_info['can_id']
    dbc_name = msg_info['dbc_name']
    raw_data = msg_info['raw_data']
    csv_decoded = msg_info['decoded_result']
    
    # 跳过未知消息
    if dbc_name == '未知' or msg_info['message_name'] == '未知':
        return {
            'status': 'skip',
            'reason': '无对应DBC文件'
        }
    
    # 获取DBC数据库
    if dbc_name not in databases:
        return {
            'status': 'error',
            'reason': f'DBC文件 {dbc_name} 未加载'
        }
    
    db = databases[dbc_name]
    
    try:
        # 解析CAN ID
        can_id = int(can_id_hex, 16)
        
        # 从DBC解码
        message = db.get_message_by_frame_id(can_id)
        data_bytes = bytes.fromhex(raw_data)
        dbc_decoded = message.decode(data_bytes)
        
        # 解析CSV中的解码结果
        csv_signals = parse_decoded_result(csv_decoded)
        
        # 验证1: 信号个数
        dbc_signal_count = len(dbc_decoded)
        csv_signal_count = len(csv_signals)
        
        if dbc_signal_count != csv_signal_count:
            return {
                'status': 'mismatch',
                'reason': f'信号个数不一致: DBC有{dbc_signal_count}个, CSV有{csv_signal_count}个',
                'mismatches': [f"信号个数: DBC={dbc_signal_count}, CSV={csv_signal_count}"],
                'dbc_decoded': dbc_decoded,
                'csv_decoded': csv_signals
            }
        
        # 验证2: 信号名称和数据内容
        mismatches = []
        all_signals = set(dbc_decoded.keys()) | set(csv_signals.keys())
        
        for signal_name in all_signals:
            dbc_value = dbc_decoded.get(signal_name)
            csv_value = csv_signals.get(signal_name)
            
            # 检查信号是否存在
            if dbc_value is None:
                mismatches.append(f"{signal_name}: CSV有但DBC无")
            elif csv_value is None:
                mismatches.append(f"{signal_name}: DBC有但CSV无")
            else:
                # 验证3: 数据格式和内容
                dbc_type = type(dbc_value).__name__
                csv_type = type(csv_value).__name__
                
                # 数值类型比较
                if isinstance(dbc_value, (int, float)) and isinstance(csv_value, (int, float)):
                    # 允许小误差
                    if abs(dbc_value - csv_value) > 0.0001:
                        mismatches.append(
                            f"{signal_name}: 值不一致 DBC={dbc_value}({dbc_type}), CSV={csv_value}({csv_type})"
                        )
                # 字符串类型比较
                elif str(dbc_value) != str(csv_value):
                    mismatches.append(
                        f"{signal_name}: 值不一致 DBC={dbc_value}({dbc_type}), CSV={csv_value}({csv_type})"
                    )
        
        if mismatches:
            return {
                'status': 'mismatch',
                'reason': f'发现{len(mismatches)}个差异',
                'mismatches': mismatches,
                'dbc_decoded': dbc_decoded,
                'csv_decoded': csv_signals
            }
        else:
            return {
                'status': 'match',
                'signal_count': len(dbc_decoded),
                'details': f'信号个数: {len(dbc_decoded)}, 所有信号值一致'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'reason': str(e)
        }


def print_verification_results(unique_msgs, databases):
    """打印验证结果"""
    print("\n" + "=" * 100)
    print(f"唯一CAN ID验证结果 (共 {len(unique_msgs)} 个)")
    print("=" * 100)
    
    match_count = 0
    mismatch_count = 0
    skip_count = 0
    error_count = 0
    
    results = []
    
    for i, (can_id, msg_info) in enumerate(unique_msgs.items(), 1):
        result = verify_message(msg_info, databases)
        results.append((can_id, msg_info, result))
        
        if result['status'] == 'match':
            match_count += 1
            status_icon = "✓"
            status_text = result.get('details', f"一致 ({result['signal_count']}个信号)")
        elif result['status'] == 'mismatch':
            mismatch_count += 1
            status_icon = "✗"
            status_text = result.get('reason', f"不一致 ({len(result.get('mismatches', []))}个差异)")
        elif result['status'] == 'skip':
            skip_count += 1
            status_icon = "○"
            status_text = f"跳过 ({result['reason']})"
        else:
            error_count += 1
            status_icon = "✗"
            status_text = f"错误 ({result['reason']})"
        
        print(f"\n[{i}] {status_icon} CAN ID: {can_id} | "
              f"消息名称: {msg_info['message_name']} | "
              f"DBC: {msg_info['dbc_name']}")
        print(f"    时间: {msg_info['timestamp']}s | "
              f"通道: {msg_info['channel']} | "
              f"原始数据: {msg_info['raw_data']}")
        print(f"    验证结果: {status_text}")
        
        # 显示不一致的详细信息
        if result['status'] == 'mismatch':
            print(f"    差异详情:")
            for mismatch in result['mismatches'][:5]:  # 只显示前5个
                print(f"        - {mismatch}")
            if len(result['mismatches']) > 5:
                print(f"        ... (还有 {len(result['mismatches']) - 5} 个差异)")
    
    # 打印统计信息
    print("\n" + "=" * 100)
    print(f"验证统计:")
    print(f"  总数: {len(unique_msgs)}")
    print(f"  一致: {match_count} ({match_count/len(unique_msgs)*100:.1f}%)")
    print(f"  不一致: {mismatch_count} ({mismatch_count/len(unique_msgs)*100:.1f}%)")
    print(f"  跳过: {skip_count} ({skip_count/len(unique_msgs)*100:.1f}%)")
    print(f"  错误: {error_count} ({error_count/len(unique_msgs)*100:.1f}%)")
    print("=" * 100)
    
    return match_count, mismatch_count, skip_count, error_count


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 verify_unique_ids.py <chassis_decoded.csv>")
        print("示例: python3 scripts/validation/verify_unique_ids.py output/chassis_decoded.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"错误: 文件 {csv_file} 不存在")
        sys.exit(1)
    
    print("=" * 100)
    print("唯一CAN ID验证工具")
    print("=" * 100)
    
    # 1. 加载DBC文件
    print("\n1. 加载DBC文件...")
    databases = load_dbc_files()
    print(f"   已加载 {len(databases)} 个DBC文件")
    
    # 2. 从CSV提取唯一消息
    print("\n2. 从CSV提取唯一CAN ID...")
    unique_msgs = extract_unique_messages_from_csv(csv_file)
    
    # 3. 验证每个唯一消息
    print("\n3. 验证解析结果...")
    match_count, mismatch_count, skip_count, error_count = print_verification_results(
        unique_msgs, databases
    )
    
    # 返回状态码
    if mismatch_count > 0 or error_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
