# HuRAG Command Line Interface (CLI) Documentation

HuRAG 提供了丰富的命令行工具用于系统后台管理和维护，包括知识库管理维护命令 `hurag`、文档库管理维护命令 `hurag-corpus` 和知识图谱维护管理命令 `hurag-graph`。

本文档详细介绍了各个命令的用法和参数，也可以在命令行中使用 `--help` 参数查看帮助信息，例如：

```bash
hurag --help
```

## Knowledge Base Management

命令 `hurag` 用于管理和维护 HuRAG 后台知识库，包括初始化知识库、查看知识库信息等功能。

### Initialize Knowledge Base

使用以下命令初始化后台知识库：

```bash
hurag init
```

*注意：初始化命令会清空当前知识库中的所有数据，请谨慎操作。*

### View Knowledge Base Information

使用以下命令查看后台知识库信息：

```bash
hurag info
```

知识库信息包括当前知识库中的文档数量、知识图谱节点数量等，将以列表的形式展示。

### List Documents in Knowledge Base

使用以下命令列出当前知识库中的文档：

```bash
hurag list [--keyword <keyword>] [--order <title|date|org>]
```

- `--keyword <keyword>`: 可选参数，简写 `-k`，按关键字过滤文档标题，不提供则列出所有文档。
- `--order <title|date|org>`: 可选参数，简写 `-o`，指定排序方式，可选值为 `title`（标题）、`date`（日期）或 `org`（发布机构），默认为按标题排序。

## Corpus Management

命令 `corpus` 用于管理和维护 HuRAG 文档库，包括文档转换等功能。

### Document Conversion

使用以下命令进行文档格式或编码的转换：

```bash
corpus convert --src <source_file> [--tgt <target_file>] [--enc]
```

- `--src <source_file>`: 必需参数，指定源文件路径。
- `--tgt <target_file>`: 可选参数，指定目标文件路径。如果未提供，默认在源文件同目录下创建同名文件，用于 TXT 文件转换编码时，使用 `.utf8.txt` 后缀；用于转换为 Markdown 格式时，使用 `.md` 后缀。
- `--enc`: 可选参数，简写 `-e`，指定进行编码转换（GBK 转 UTF-8）。如果未提供，则进行格式转换（转 Markdown）。

该命令支持两种模式：

1. 不使用 `--enc` 参数，则提取 PDF, Word, Excel, Powerpoint, CSV, HTML, JSON, XML 文件的内容，保存为 Markdown 文件。默认情况下，使用微软开源工具 markitdown 从 PDF, Word, Excel, Powerpoint, CSV, HTML, JSON, XML 文件中提取内容，转为 Markdown 格式文件。
2. 使用 `--enc` 参数则为将 Windows 环境下生成的 GBK 编码文本文件转为 UTF-8 编码。编码转换模式不能处理 PDF, Word 等二进制文件，仅对 TXT, CSV, HTML, JSON, XML, MD 等文本型文件进行处理，源格式保存，不会转为 Markdown 格式。


TODO: constructing, coming soon...

## Graph Management

TODO: constructing, coming soon...
