# CANForge

CAN 总线报文解析与验证工具集 — ASC 日志解析、DBC 信号解码、Excel 协议转 DBC、自动化验证。

## 快速开始

```bash
pip install -r requirements.txt   # Python 3.6+
```

### 解析 ASC 文件（推荐）

```bash
bash docs/parse.sh msg/chassis.asc
```

> 输出 `*_decoded.csv`、`*_errors.csv`、`*_validation_report.csv`、`*_validation_errors.csv` 文件

### 验证解析结果

```bash
bash docs/validate.sh msg/chassis_decoded.csv --full
```

### Excel 转 DBC

```bash
bash docs/convert.sh
```

### 批量处理

```bash
bash docs/batch_process.sh     
```

### 格式转换

```bash
bash docs/can-converter.sh
```

## 说明

- 将 `.dbc` 文件放入 `protocol/dbc/` 目录即可自动加载，支持 UTF-8 / GBK / GB2312 / Latin-1 编码

## 许可证

[MIT](LICENSE)
