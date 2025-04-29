# Keil to Compile Commands Converter

这是一个 Python 脚本，用于解析 Keil MDK 项目文件 (.uvprojx、.uvproj) 并生成 `compile_commands.json` 文件。这个文件可以被 Clangd 等语言服务器使用，以提供更准确的代码补全、导航和诊断功能。

## 功能

*   解析 Keil `.uvprojx` XML 文件。
*   提取项目中包含的 C/C++ 源文件 (`.c`) 和汇编文件 (`.s`)。
*   提取在 Keil 项目设置中定义的宏 (`-D` 标志)。
*   提取在 Keil 项目设置中指定的包含路径 (`-I` 标志)。
*   根据提取的信息生成 `compile_commands.json` 文件。

## 依赖

*   Python 3.x
*   标准库: `xml.etree.ElementTree`, `json`, `os`, `sys` (无需额外安装)

## 使用方法

在命令行中运行脚本，并将 Keil 项目文件 (`.uvprojx`) 的路径作为参数传递：

```bash
python main.py <path_to_your_keil_project.uvprojx>
```

**示例:**

```bash
python main.py C:/Path/To/Your/Project/YourProject.uvprojx
```

或者使用相对路径：

```bash
python main.py ../../MyKeilProject/MyProject.uvprojx
```

脚本将在运行 `main.py` 的目录下生成一个名为 `compile_commands.json` 的文件。

## `compile_commands.json`

生成的 `compile_commands.json` 文件包含一个 JSON 数组，其中每个对象代表项目中的一个源文件及其编译参数。结构如下：

```json
[
  {
    "directory": "/path/to/source/file/directory",
    "arguments": [
      "-Iinclude/path1",
      "-Iinclude/path2",
      "-DMACRO1",
      "-DMACRO2"
    ],
    "file": "/path/to/source/file/filename.c"
  },
  ...
]
```

这个文件可以被许多开发工具（如 VS Code 配合 Clangd 插件）使用，以增强代码编辑体验。