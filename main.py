import xml.etree.ElementTree as ET
import json
import os
import sys
import argparse
from typing import List, Dict, Any, Optional

def parse_keil_project(keil_project_file_path: str) -> List[Dict[str, Any]]:
    """
    解析Keil项目文件（.uvprojx），提取编译宏定义、包含路径和源文件，
    并生成符合compile_commands.json格式的编译命令列表。
    
    :param keil_project_file_path: Keil项目文件的路径。
    :return: 包含编译命令字典的列表，每个字典代表一个源文件的编译命令。
    """
    try:
        tree = ET.parse(keil_project_file_path)
        root = tree.getroot()
        
        # 提取目标信息
        target = root.find('.//Target')
        if target is None:
            print("Error: Target element not found in Keil project file.")
            return []
        
        # 提取编译选项
        target_option = target.find('.//TargetOption')
        if target_option is None:
            print("Error: TargetOption element not found in Keil project file.")
            return []
        
        # 宏定义
        cads = target_option.find('.//Cads')
        define: str = ''
        include_path: str = ''
        if cads is not None:
            define_element = cads.find('VariousControls/Define')
            if define_element is not None and define_element.text is not None:
                define = define_element.text
 
            include_path_element = cads.find('VariousControls/IncludePath')
            if include_path_element is not None and include_path_element.text is not None:
                include_path = include_path_element.text
 
        macros: List[str] = [f"-D{macro}" for macro in define.split(',') if macro]
        
 
        # 包含路径
        uvprojx_dir: str = os.path.dirname(os.path.abspath(keil_project_file_path)) # Keil 项目文件所在目录
        output_dir: str = os.getcwd() # 假设 compile_commands.json 在当前目录生成
 
        raw_includes: List[str] = [inc for inc in include_path.split(';') if inc]
        includes: List[str] = []
        for inc in raw_includes:
            # 将相对于 uvprojx 目录的包含路径转换为相对于 output_dir 的路径
            abs_inc_path: str = os.path.abspath(os.path.join(uvprojx_dir, inc))
            rel_inc_path: str = os.path.relpath(abs_inc_path, output_dir)
            # 确保路径分隔符是 '/'
            rel_inc_path = rel_inc_path.replace("\\", "/")
            includes.append(f"-I{rel_inc_path}")
 
        # 提取源文件路径
        groups = target.findall('.//Group')
        files: List[str] = []
        for group in groups:
            group_files = group.findall('.//File')
            for file in group_files:
                file_type_element = file.find('FileType')
                file_path_element = file.find('FilePath')
                
                file_type: Optional[int] = None
                if file_type_element is not None and file_type_element.text is not None:
                    try:
                        file_type = int(file_type_element.text)
                    except ValueError:
                        # Handle cases where text is not a valid integer
                        print(f"Warning: Invalid FileType value: {file_type_element.text}")
                        continue # Skip this file
 
                file_path: Optional[str] = None
                if file_path_element is not None and file_path_element.text is not None:
                    file_path = file_path_element.text
                
                # Only process C/C++ source files and assembly files if file_type and file_path are valid
                if file_type in [1, 2] and file_path is not None:
                    if file_path.endswith('.c') or file_path.endswith('.s'):
                        files.append(file_path)
        
        # 构建compile_commands.json内容
        compiler: str = get_clangd_query_driver()
        last_backslash_index = compiler.rfind('\\')
        if last_backslash_index != -1:
            # 截取最后一个 \ 之前的部分，并拼接 include 目录
            second_last_backslash_index = compiler.rfind('\\', 0, last_backslash_index)
            if second_last_backslash_index != -1:
                # 截取倒数第二个 \ 之前的部分，并拼接 include 目录
                compiler_include = "-I" + compiler[:second_last_backslash_index] + '\\include'
        compile_commands: List[Dict[str, Any]] = []
        for source_file_rel_to_proj in files: # 重命名变量
            # 计算源文件的绝对路径
            abs_source_file_path: str = os.path.abspath(os.path.join(uvprojx_dir, source_file_rel_to_proj))
 
            # 计算相对于输出目录 (cwd) 的相对路径
            relative_file_path: str = os.path.relpath(abs_source_file_path, output_dir)
            # 确保路径分隔符是 '/'
            relative_file_path = relative_file_path.replace("\\", "/")
            
            command: Dict[str, Any] = {
                "arguments": [compiler] + [compiler_include] + includes + macros,
                "directory": output_dir,
                "file": relative_file_path
            }
            compile_commands.append(command)
 
        return compile_commands
        
    except ET.ParseError as e:
        print(f"Failed to parse XML: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
 
def write_compile_commands(compile_commands: List[Dict[str, Any]], output_file: str = 'compile_commands.json') -> None:
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
        print(f"Failed to write to {output_file} file: {e}")
 
def create_clangd_directory(cache_dir: Optional[str] = None) -> None:
    """
    创建clangd缓存文件夹并写入.gitignore文件
    
    :param cache_dir: 自定义缓存目录路径，默认为None表示使用默认.cache目录
    """
    if cache_dir is None:
        cache_dir = os.path.join('.', '.cache')
    try:
        os.makedirs(cache_dir, exist_ok=True)
        gitignore_path: str = os.path.join(cache_dir, '.gitignore')
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write('*')
        print(f"Successfully created {cache_dir} directory and .gitignore file")
    except Exception as e:
        print(f"Failed to create {cache_dir} directory or .gitignore file: {e}")
 
 
def get_clangd_query_driver() -> str:
    """
    获取clangd的query-driver路径。
    首先尝试从当前工作目录下的.vscode/settings.json中读取，
    如果未找到，则尝试从全局VSCode settings.json中读取。
    如果仍然未找到，则返回默认值并打印提示信息。
    
    :return: clangd的query-driver路径字符串。
    """
    def read_json_file(file_path: str) -> Dict[str, Any]:
        import json5  # 使用json5库来支持注释和更灵活的JSON格式
        """读取JSON文件的辅助函数"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json5.load(f)  # 直接支持JSON5标准（含注释）
        
    def find_compiler_in_settings(settings_path: str) -> Optional[str]:
        if os.path.exists(settings_path):
            data = read_json_file(settings_path)
            if data and 'clangd.arguments' in data:
                for arg in data['clangd.arguments']:
                    if isinstance(arg, str) and arg.startswith('--query-driver='):
                        compilers: List[str] = arg.split('=')[1].split(',')
                        print(f"Found compiler: {compilers}")
                        return compilers[0]
        return None
    
    # 1. 尝试读取当前目录下的.vscode/settings.json
    local_settings: str = os.path.join('.vscode', 'settings.json')
    compiler: Optional[str] = find_compiler_in_settings(local_settings)
    if compiler:
        return compiler
    
    # 2. 尝试读取全局settings.json
    app_data: Optional[str] = os.getenv('AppData')
    if app_data:
        global_settings: str = os.path.join(app_data, 'Code', 'User', 'settings.json')
        compiler = find_compiler_in_settings(global_settings)
        if compiler:
            return compiler
    
    # 3. 如果都没找到，返回默认值
    print("Please add the following to your VSCode settings.json (use absolute path):")
    print('"clangd.arguments": ["--query-driver=<absolute_path_to_compiler>"]')
    return "<compilerPath>"
    
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse Keil project file and generate compile_commands.json')
    parser.add_argument('project_file', type=str, help='Path to Keil project file (.uvprojx .uvproj)')
    parser.add_argument('-d', nargs='?', const='.cache', metavar='CACHE_DIR',
                      help='Create clangd cache directory (default: .cache)')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.project_file):
        parser.error(f"The specified Keil project file does not exist: {args.project_file}")
        parser.print_help()
        sys.exit(1)
    
    compile_info: List[Dict[str, Any]] = parse_keil_project(args.project_file)
    write_compile_commands(compile_info)
    if args.d is not None:
        create_clangd_directory(args.d)
