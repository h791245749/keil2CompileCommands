import xml.etree.ElementTree as ET
import json
import os
import sys

def parse_keil_project(file_path):
    """
    解析Keil项目文件（.uvprojx），提取编译信息。
    
    :param file_path: Keil项目文件的路径
    :return: 包含编译信息的字典
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # 提取目标信息
        target = root.find('.//Target')
        
        # 提取编译选项
        target_option = target.find('.//TargetOption')
        
        # 宏定义
        cads = target_option.find('.//Cads')
        define = cads.find('VariousControls/Define').text if cads.find('VariousControls/Define') is not None else ''
        macros = [f"-D{macro}" for macro in define.split(',') if macro]
        

        # 包含路径
        uvprojx_dir = os.path.dirname(os.path.abspath(file_path)) # Keil 项目文件所在目录
        output_dir = os.getcwd() # 假设 compile_commands.json 在当前目录生成

        include_path = cads.find('VariousControls/IncludePath').text if cads.find('VariousControls/IncludePath') is not None else ''
        raw_includes = [inc for inc in include_path.split(';') if inc]
        includes = []
        for inc in raw_includes:
            # 将相对于 uvprojx 目录的包含路径转换为相对于 output_dir 的路径
            abs_inc_path = os.path.abspath(os.path.join(uvprojx_dir, inc))
            rel_inc_path = os.path.relpath(abs_inc_path, output_dir)
            # 确保路径分隔符是 '/'
            rel_inc_path = rel_inc_path.replace("\\", "/")
            # 检查目录是否存在
            if os.path.isdir(abs_inc_path):
                includes.append(f"-I{rel_inc_path}")
            else:
                # 可以选择打印警告或记录日志
                print(f"警告：包含路径目录不存在，已跳过: {abs_inc_path}")

        # 提取源文件路径
        groups = target.findall('.//Group')
        files = []
        for group in groups:
            group_files = group.findall('.//File')
            for file in group_files:
                file_type = int(file.find('FileType').text)
                # 只处理C/C++源文件和汇编文件
                if file_type == 1 or file_type == 2:
                    file_path = file.find('FilePath').text
                    if file_path.endswith('.c') or file_path.endswith('.s'):
                        files.append(file_path)
        
        # 构建compile_commands.json内容
        compile_commands = []
        for source_file_rel_to_proj in files: # 重命名变量
            # 计算源文件的绝对路径
            abs_source_file_path = os.path.abspath(os.path.join(uvprojx_dir, source_file_rel_to_proj))

            # 计算相对于输出目录 (cwd) 的相对路径
            relative_file_path = os.path.relpath(abs_source_file_path, output_dir)
            # 确保路径分隔符是 '/'
            relative_file_path = relative_file_path.replace("\\", "/")
            
            compiler = "g++" if relative_file_path.endswith(('.cpp', '.cc', '.cxx', '.c++')) else "gcc"
            command = {
                "arguments": [compiler] + includes + macros,
                "directory": output_dir,
                "file": relative_file_path
            }
            compile_commands.append(command)

        return compile_commands
        
    except ET.ParseError as e:
        print(f"Failed to parse XML: {e}")
        return {}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

def write_compile_commands(compile_commands, output_file='compile_commands.json'):
    """
    将编译命令写入compile_commands.json文件。
    
    :param compile_commands: 编译命令数据
    :param output_file: 输出文件的路径
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(compile_commands, f, indent=4, ensure_ascii=False)
        print(f"Successfully wrote compile commands to {output_file}")
    except IOError as e:
        print(f"Failed to write to file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <keil_project_file>")
        sys.exit(1)
    
    keil_project_file = sys.argv[1]
    if not os.path.exists(keil_project_file):
        print(f"The specified Keil project file does not exist: {keil_project_file}")
        sys.exit(1)
    
    compile_info = parse_keil_project(keil_project_file)
    write_compile_commands(compile_info)
