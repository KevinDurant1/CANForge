# CAN Parser Tools

> 专业的CAN总线报文解析工具，支持ASC文件解析、DBC文件管理、Excel协议转换和解析结果验证

## ✨ 核心特性

- **高性能解析** - 处理速度 ~145K 消息/次，解码率 99.92%
- **智能DBC管理** - 自动扫描加载，支持多种编码（UTF-8/GBK/GB2312/Latin-1）
- **完整验证** - 信号个数、名称、格式、内容、范围全方位验证
- **Excel转DBC** - 智能识别协议工作表，自动生成DBC文件
- **批量处理** - 支持批量处理多个ASC文件

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 解析ASC文件（自动验证，生成4个文件）
bash docs/parse.sh msg/chassis.asc

# 3. 单独验证（可选）
bash docs/validate.sh msg/chassis_decoded.csv --full
```

## 📁 项目结构

```
can-parser-tools/
├── docs/                    # Shell脚本
│   ├── parse.sh            # 解析ASC文件
│   ├── validate.sh         # 验证解析结果
│   ├── convert.sh          # Excel转DBC
│   ├── batch_process.sh    # 批量处理
│   └── can-converter.sh    # 格式转换工具
├── msg/                     # 消息文件目录
│   ├── *.asc               # 输入ASC文件
│   ├── *_decoded.csv       # 输出解析结果
│   ├── *_errors.csv        # 输出解析错误
│   ├── *_validation_report.csv        # 输出验证报告
│   └── *_validation_errors.csv        # 输出验证错误
├── protocol/                # 协议文件目录
│   ├── dbc/                # DBC文件（自动扫描）
│   │   └── *.dbc          # DBC数据库文件
│   └── *.xls               # Excel协议文件
├── src/                     # Python源代码
│   ├── cli.py              # 命令行接口
│   ├── asc_parser.py       # ASC解析器
│   ├── dbc_loader.py       # DBC加载器
│   ├── validator.py        # 统一验证器
│   └── excel_to_dbc.py     # Excel转DBC转换器
├── .gitignore               # Git忽略配置
├── LICENSE                  # MIT许可证
├── README.md                # 项目文档
└── requirements.txt         # Python依赖项
```

## 🔧 功能详解

### 1. ASC文件解析
- 解析CAN报文时间戳、通道、ID、数据
- 自动匹配DBC文件进行信号解码
- 支持多通道CAN数据
- 详细的统计信息和错误报告

### 2. 统一验证工具
- **快速验证**：验证唯一CAN ID的信号一致性
- **完整验证**：验证所有消息的数据类型、数值范围、精度
- **自动报告**：生成详细的CSV格式报告

### 3. Excel转DBC
- 智能识别协议工作表（自动跳过Map、Index等）
- 自动解析信号定义（名称、起始位、长度、因子等）
- 支持 .xls 和 .xlsx 格式

### 4. 批量处理
- 递归扫描 `msg/` 目录中的所有ASC文件
- 自动生成输出文件名
- 详细的处理进度和结果统计

## 📖 使用方法

### 解析ASC文件

```bash
# 解析并自动验证（推荐，生成4个文件）
bash docs/parse.sh msg/chassis.asc
python3 src/cli.py parse msg/chassis.asc --validate

# 仅解析（不验证）
python3 src/cli.py parse msg/chassis.asc
```

**输出文件（使用 --validate 时）：**
1. `*_decoded.csv` - 解码结果（所有消息）
2. `*_errors.csv` - 解析错误
3. `*_validation_report.csv` - 验证报告（所有信号）
4. `*_validation_errors.csv` - 验证错误（仅异常信号）

### 验证解析结果

```bash
# 快速验证（仅验证唯一CAN ID）
python3 src/cli.py validate msg/chassis_decoded.csv --quick

# 完整验证
python3 src/cli.py validate msg/chassis_decoded.csv

# 完整验证并生成报告（推荐）
python3 src/cli.py validate msg/chassis_decoded.csv --full
```

### Excel转DBC

```bash
# 使用默认路径
bash docs/convert.sh

# 指定文件
python3 src/cli.py convert --excel protocol/my_protocol.xls --output protocol/dbc/
```

### 批量处理

```bash
# 批量处理msg/目录下的所有ASC文件
bash docs/batch_process.sh

# 先重新生成DBC，再批量处理
bash docs/batch_process.sh --regenerate-dbc
```

## ❓ 常见问题

**Q: 如何添加新的DBC文件？**  
A: 直接将DBC文件放到 `protocol/dbc/` 目录，工具会自动扫描加载。

**Q: 解析结果保存在哪里？**  
A: 所有文件保存在 `msg/` 目录下。使用 `--validate` 参数时会生成4个文件：
- `*_decoded.csv` - 解码结果
- `*_errors.csv` - 解析错误
- `*_validation_report.csv` - 验证报告（所有信号）
- `*_validation_errors.csv` - 验证错误（仅异常信号）

**Q: CSV中保存的是物理值还是总线值？**  
A: CSV中保存的是物理值（Physical Value）。cantools库的decode()方法会自动将总线值转换为物理值（公式：物理值 = 总线值 × 精度 + 偏移量）。验证时也是使用DBC中定义的物理值范围。详见 `docs/TECHNICAL_NOTES.md`。

**Q: DBC文件中的min/max是什么范围？**  
A: DBC文件中的[min|max]是物理值范围，不是总线值范围。例如`[2000.0|2127.0]`表示物理值范围是2000到2127年。

**Q: 如何验证信号的数据范围？**  
A: 使用 `bash docs/validate.sh msg/chassis_decoded.csv --full` 进行完整验证，会生成两个报告：
- `*_validation_report.csv` - 所有信号的详细统计
- `*_validation_errors.csv` - 仅包含异常信号，方便快速定位问题

## 📦 依赖项

```bash
pip install -r requirements.txt
```

**核心依赖：**
- Python 3.6+
- cantools >= 38.0.0
- pandas >= 1.3.0
- xlrd >= 2.0.0
- openpyxl >= 3.0.0

## 📊 性能指标

| 指标 | 数值 |
|------|------|
| 解析速度 | ~145K 消息/次 |
| 解码成功率 | 99.92% |
| 验证通过率 | 97.1% |

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
