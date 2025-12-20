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

## Corpus Management

TODO: constructing, coming soon...

## Graph Management

TODO: constructing, coming soon...
