# HuRAG Command Line Interface (CLI) Documentation

HuRAG 提供了丰富的命令行工具用于系统后台管理和维护，包括知识库管理维护命令 `hurag`、文档库管理维护命令 `hurag-corpus` 和知识图谱维护管理命令 `hurag-graph`。

本文档详细介绍了各个命令的用法和参数，也可以在命令行中使用 `--help` 参数查看帮助信息，例如：

```bash
hurag --help
```

## 知识库管理

命令 `hurag` 用于管理和维护 HuRAG 后台知识库，包括初始化知识库、查看知识库信息等功能。

知识库是指实现 HuRAG 问答系统所依赖的后台文档存储和管理系统，知识库中的文档经过预处理和索引，供问答系统进行检索和回答生成。

*知识库管理不包括知识图谱的生成和维护等功能，知识图谱管理是独立的模块，由 `kgraph` 命令进行管理。*

### 初始化知识库

使用以下命令初始化后台知识库：

```bash
hurag init
```

*注意：初始化命令会清空当前知识库中的所有数据，包括知识图谱，请谨慎操作。*

### 查看知识库信息

使用以下命令查看后台知识库信息：

```bash
hurag info
```

知识库信息包括当前知识库中的文档数量、知识图谱节点数量等，将以列表的形式展示。

### 列出库内文档

使用以下命令列出当前知识库中的文档：

```bash
hurag list [--keyword <keyword>] [--order <title|date|org>]
```

- `--keyword <keyword>`: 可选参数，简写 `-k`，按关键字过滤文档标题，不提供则列出所有文档。
- `--order <title|date|org>`: 可选参数，简写 `-o`，指定排序方式，可选值为 `title`（标题）、`date`（日期）或 `org`（发布机构），默认为按标题排序。

### 文档入库

使用以下命令将文档存入知识库：

```bash
hurag store <path>
```

- `<path>`: 必需参数，指定包含待入库文档的文集目录路径。

## 文集管理

命令 `corpus` 用于以文集的形式管理和维护知识文档，包括文档转换等功能。

### 文档转换

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

### 文集预标注

使用以下命令为文档库中的文档生成标注文件：

```bash
corpus markup --path <corpus_path>
```

- `--path <corpus_path>`: 必需参数，指定包含待标注文档的文集路径。

该命令会在指定路径下生成 `corpus.json` 文件，记录文集中的所有文档及其元数据，对于在 HuRAG 早期内测版本中已经完成分割的文档，会读取其元数据并将该文档标注为 `v1_doc` 布局。

*注意：该命令不会对文档进行分割操作，仅生成标注文件，标注文件自动提取的元数据不保证准确，进行分割前应当检查维护确保所有标注信息准确。*

### 文档分割

使用以下命令对归属于一个文集中的文档进行分割：

```bash
corpus split --path <corpus_path>
```

- `--path <corpus_path>`: 必需参数，指定包含待分割文档的文集路径。

该命令会对指定路径下的 `corpus.json` 文件中标注的所有布局为 `text` 或 `regu` 的文档进行分割操作，分割结果保存在与源文件相同的目录下。

`text` 布局的 TXT 文件会被递归拆分为 size = 500, overlap = 100 的小块；`text` 布局的 Markdown 文件会先按标题拆分为若干段落，然后将每个段落拆分为 size = 500, overlap = 0 的小块；`regu` 布局的文件会以条文和附件为单位进行拆分，每段一条条文或一个附件，段内按照长度进一步拆分为 size = 500, overlap = 0 的小块。其他布局包括 'manual', 'v1_doc' 和 8 种 CSV 表格布局不会进行分割。

文档的拆分结果会被写入一个与源文件同名、后缀为 '.idx' 的文本文件中。

## 知识图谱管理

命令 `kgraph` 用于管理和维护 HuRAG 知识图谱，包括实体-关系提取、图谱构建、社区生成等功能。

TODO: constructing, coming soon...
