#!/bin/bash
# batch_process.sh
# 递归处理所有子目录中的.asc文件
# 支持从Excel重新生成DBC文件

# 获取脚本所在目录的父目录
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PARENT_DIR=$(dirname "$SCRIPT_DIR")
INPUT_DIR="$PARENT_DIR/msg"
OUTPUT_DIR="$PARENT_DIR/msg"
DBC_DIR="$PARENT_DIR/protocol/dbc"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "====================================="
echo "CAN报文解析工具 - 批处理模式"
echo "====================================="

# 检查是否需要重新生成DBC文件
if [ "$1" == "--regenerate-dbc" ] || [ "$1" == "-r" ]; then
    echo ""
    echo "步骤 1: 从Excel重新生成DBC文件..."
    echo "-------------------------------------"
    bash "$SCRIPT_DIR/convert.sh"
    if [ $? -ne 0 ]; then
        echo "错误: DBC文件生成失败"
        exit 1
    fi
    echo ""
fi

# 检查DBC文件是否存在
DBC_COUNT=0
for dbc_file in "$DBC_DIR"/*.dbc; do
    if [ -f "$dbc_file" ]; then
        DBC_COUNT=$((DBC_COUNT + 1))
    fi
done

if [ $DBC_COUNT -eq 0 ]; then
    echo "警告: protocol/dbc目录中没有找到DBC文件"
    echo "尝试从Excel生成DBC文件..."
    bash "$SCRIPT_DIR/convert.sh"
    if [ $? -ne 0 ]; then
        echo "错误: DBC文件生成失败"
        exit 1
    fi
fi

echo ""
echo "步骤 2: 开始批量处理.asc文件..."
echo "-------------------------------------"
echo "搜索所有.asc文件..."

# 使用find命令递归查找所有.asc文件
FILE_COUNT=0
find "$INPUT_DIR" -name "*.asc" -type f | while read -r asc_file; do
    FILE_COUNT=$((FILE_COUNT + 1))
    # 获取文件名（不含路径）
    filename=$(basename "$asc_file")
    # 获取文件名（不含扩展名）
    filename_noext=${filename%.asc}
    # 生成输出文件名
    output_file="$OUTPUT_DIR/${filename_noext}_decoded.csv"
    
    echo ""
    echo "[$FILE_COUNT] 处理文件: $asc_file"
    echo "    输出文件: $output_file"
    
    # 执行解析脚本
    bash "$SCRIPT_DIR/parse.sh" "$asc_file" -o "$output_file"
    
    if [ $? -eq 0 ]; then
        echo "    ✓ 已完成"
    else
        echo "    ✗ 处理失败"
    fi
done

echo ""
echo "====================================="
echo "批量处理完成!"
echo "解码结果和错误信息保存在: $OUTPUT_DIR"
echo "====================================="
echo ""
echo "用法提示:"
echo "  bash docs/batch_process.sh              # 批量解析ASC文件"
echo "  bash docs/batch_process.sh -r           # 先重新生成DBC，再解析"
echo "  bash docs/batch_process.sh --regenerate-dbc  # 同上"
