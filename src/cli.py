#!/usr/bin/env python3
"""
CAN解析工具 - 命令行接口
统一的命令行入口，支持多个子命令
"""

import sys
import os
import argparse
import shutil

# 确保可以导入本目录的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dbc_loader import DBCLoader
from asc_parser import ASCParser
from excel_to_dbc import ExcelToDBCConverter
from validator import CANValidator


def cleanup_pycache():
    """清理Python缓存文件"""
    try:
        src_dir = os.path.dirname(os.path.abspath(__file__))
        pycache_dir = os.path.join(src_dir, '__pycache__')
        
        if os.path.exists(pycache_dir):
            shutil.rmtree(pycache_dir)
    except Exception:
        pass


def get_decimal_places(factor):
    """根据factor计算应该保留的小数位数"""
    if factor == int(factor):
        return 0
    # 将factor转换为字符串，计算小数位数
    factor_str = f"{factor:.10f}".rstrip('0')
    if '.' in factor_str:
        return len(factor_str.split('.')[1])
    return 0


def format_value(value, signal=None):
    """
    格式化输出值，根据DBC定义的精度处理浮点数
    
    Args:
        value: 要格式化的值
        signal: cantools信号对象（可选），用于获取factor信息
    """
    if isinstance(value, float):
        if signal and hasattr(signal, 'scale'):
            # 根据DBC中的factor（scale）确定小数位数
            decimal_places = get_decimal_places(signal.scale)
            return f"{value:.{decimal_places}f}"
        else:
            # 如果没有信号信息，使用智能格式化
            # 保留最多6位小数，去除尾部的0
            formatted = f"{value:.6f}".rstrip('0').rstrip('.')
            return formatted
    return value


def save_to_csv(messages, output_file):
    """保存解码结果到CSV文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("时间戳,通道,方向,CAN_ID,消息名称,DBC,原始数据,解码结果\n")
            
            for msg in messages:
                decoded_str = ""
                if msg['decoded']:
                    decoded_lines = []
                    signal_metadata = msg.get('signal_metadata', {})
                    
                    for name, value in msg['decoded'].items():
                        # 根据信号的scale（factor）来格式化浮点数
                        if isinstance(value, float) and name in signal_metadata:
                            scale = signal_metadata[name]['scale']
                            decimal_places = get_decimal_places(scale)
                            formatted_value = f"{value:.{decimal_places}f}"
                        else:
                            formatted_value = format_value(value)
                        
                        decoded_lines.append(f"     {name}: {formatted_value}")
                    decoded_str = " \n" + " \n".join(decoded_lines)
                
                f.write(f"{msg['timestamp']},{msg['channel']},{msg['direction']},"
                       f"0x{msg['can_id']},{msg.get('message_name', '未知')},"
                       f"{msg.get('db_name', '未知')},{msg['data']},\"{decoded_str}\"\n")
        
        print(f"\n解码结果已保存到: {output_file}")
    except Exception as e:
        print(f"保存文件时出错: {e}")


def save_errors_to_csv(error_messages, output_file):
    """保存错误消息到CSV文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("行号,时间戳,通道,CAN_ID,错误信息\n")
            for error_msg in error_messages:
                f.write(f"{error_msg['line']},{error_msg['timestamp'] or 'N/A'},"
                       f"{error_msg['channel'] or 'N/A'},{error_msg['can_id'] or 'N/A'},"
                       f"\"{error_msg['error']}\"\n")
        print(f"错误消息已保存到: {output_file}")
    except Exception as e:
        print(f"保存错误文件时出错: {e}")


def cmd_parse(args):
    """解析ASC文件"""
    asc_file = args.asc_file
    auto_validate = args.validate
    
    # 自动生成输出文件名
    if args.output:
        output_file = args.output
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(project_root, 'msg')
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(asc_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}_decoded.csv")
    
    # 1. 加载DBC文件
    print("=" * 60)
    print("加载DBC文件...")
    print("=" * 60)
    dbc_loader = DBCLoader()
    dbc_loader.load_all()
    
    # 2. 解析ASC文件
    print("\n" + "=" * 60)
    print("解析ASC文件...")
    print("=" * 60)
    parser = ASCParser(dbc_loader)
    messages, error_messages = parser.parse_file(asc_file)
    
    if messages:
        # 3. 保存解码结果
        save_to_csv(messages, output_file)
        
        # 4. 保存解析错误
        if error_messages:
            error_output_file = f"{output_file.rsplit('.', 1)[0]}_errors.csv"
            save_errors_to_csv(error_messages, error_output_file)
        
        # 5. 自动验证（如果启用）
        if auto_validate and os.path.exists(output_file):
            print("\n" + "=" * 60)
            print("自动验证解析结果...")
            print("=" * 60)
            
            validator = CANValidator(quick_mode=False)  # 使用完整验证模式
            if validator.load_dbc_files():
                validator.process_csv_file(output_file)
                
                # 快速验证
                match_count, mismatch_count, skip_count, error_count = validator.print_quick_validation()
                
                # 范围验证
                valid_count, invalid_count = validator.print_range_validation()
                
                # 自动生成验证报告
                report_file = output_file.replace('.csv', '_validation_report.csv')
                validator.export_report(report_file)
                
                # 自动生成验证错误报告
                error_report_file = output_file.replace('.csv', '_validation_errors.csv')
                validator.export_error_report(error_report_file)
                
                print("\n" + "=" * 60)
                print("生成的文件:")
                print("=" * 60)
                print(f"1. 解码结果: {output_file}")
                if error_messages:
                    print(f"2. 解析错误: {error_output_file}")
                print(f"3. 验证报告: {report_file}")
                print(f"4. 验证错误: {error_report_file}")
            else:
                print("警告: 无法加载DBC文件进行验证")


def cmd_validate(args):
    """验证解析结果"""
    csv_file = args.csv_file
    quick_mode = args.quick
    full_mode = args.full
    
    if not os.path.exists(csv_file):
        print(f"错误: 文件 {csv_file} 不存在")
        return 1
    
    # 创建验证器
    validator = CANValidator(quick_mode=quick_mode)
    
    # 加载DBC文件
    if not validator.load_dbc_files():
        print("错误: 未能加载任何DBC文件")
        return 1
    
    # 处理CSV文件
    validator.process_csv_file(csv_file)
    
    # 快速验证
    match_count, mismatch_count, skip_count, error_count = validator.print_quick_validation()
    
    # 范围验证（非快速模式）
    invalid_count = 0
    if not quick_mode:
        valid_count, invalid_count = validator.print_range_validation()
        
        # 导出报告（完整模式）
        if full_mode:
            report_file = csv_file.replace('.csv', '_validation_report.csv')
            validator.export_report(report_file)
            
            # 导出错误报告
            error_report_file = csv_file.replace('.csv', '_validation_errors.csv')
            validator.export_error_report(error_report_file)
    
    # 返回状态码
    return 1 if mismatch_count > 0 or error_count > 0 or invalid_count > 0 else 0


def cmd_validate_range(args):
    """验证信号范围（已废弃，使用 validate 命令）"""
    print("注意: validate-range 命令已合并到 validate 命令")
    print("请使用: python3 src/cli.py validate <csv_file>")
    return 1


def cmd_convert(args):
    """Excel转DBC"""
    excel_path = args.excel
    output_dir = args.output
    
    # 使用默认路径
    if not excel_path:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        excel_path = os.path.join(project_root, 'protocol', 'can_protocol_W2_500k.xls')
    
    if not output_dir:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(project_root, 'protocol', 'dbc')
    
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


def main():
    """主函数 - 命令行入口"""
    parser = argparse.ArgumentParser(
        description='CAN报文解析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 解析ASC文件
  python3 src/cli.py parse msg/chassis.asc
  
  # 解析并自动验证
  python3 src/cli.py parse msg/chassis.asc --validate
  
  # 快速验证（仅验证唯一CAN ID）
  python3 src/cli.py validate msg/chassis_decoded.csv --quick
  
  # 完整验证（包含范围检查）
  python3 src/cli.py validate msg/chassis_decoded.csv
  
  # 完整验证并生成报告
  python3 src/cli.py validate msg/chassis_decoded.csv --full
  
  # Excel转DBC
  python3 src/cli.py convert
  python3 src/cli.py convert --excel protocol/can_protocol.xls --output protocol/dbc/
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # parse子命令
    parse_parser = subparsers.add_parser('parse', help='解析ASC文件')
    parse_parser.add_argument('asc_file', help='ASC文件路径')
    parse_parser.add_argument('-o', '--output', help='输出CSV文件路径')
    parse_parser.add_argument('-v', '--validate', action='store_true', help='解析后自动验证')
    parse_parser.set_defaults(func=cmd_parse)
    
    # validate子命令
    validate_parser = subparsers.add_parser('validate', help='验证解析结果')
    validate_parser.add_argument('csv_file', help='CSV文件路径')
    validate_parser.add_argument('--quick', action='store_true', help='快速验证（仅验证唯一CAN ID）')
    validate_parser.add_argument('--full', action='store_true', help='完整验证并生成报告')
    validate_parser.set_defaults(func=cmd_validate)
    
    # convert子命令
    convert_parser = subparsers.add_parser('convert', help='Excel转DBC')
    convert_parser.add_argument('-e', '--excel', help='Excel文件路径')
    convert_parser.add_argument('-o', '--output', help='输出目录')
    convert_parser.set_defaults(func=cmd_convert)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        result = args.func(args)
        return result if result is not None else 0
    finally:
        cleanup_pycache()


if __name__ == "__main__":
    sys.exit(main())
