import os
import chardet

def should_exclude_file(filename):
    """
    Determines if a file should be excluded from concatenation.
    """
    exclude_patterns = [
        '.log',
        '.env',
        '.gitignore',
        '.DS_Store',
        'Thumbs.db',
        '__pycache__',
        '.pyc',
        '.pyo',
        '.pyd',
        '.db',
        '.sqlite',
        '.swp',
        '.swo',
        '~',
    ]
    
    return any(filename.endswith(pattern) or pattern in filename for pattern in exclude_patterns)

def should_include_file(filename):
    """
    Determines if a file should be included in concatenation.
    """
    include_extensions = {
        '.py',    # Python files
        '.js',    # JavaScript files
        '.css',   # CSS files
        '.html',  # HTML files
    }
    
    return any(filename.endswith(ext) for ext in include_extensions)

def read_file_content(file_path):
    """
    Reads the content of a file, attempting to detect its encoding.
    """
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
        
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        
        if encoding is None:
            encoding = 'utf-8'
        
        try:
            return raw_data.decode(encoding)
        except UnicodeDecodeError:
            return raw_data.decode('latin-1')
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def concatenate_scripts(target_folder):
    """
    Concatenates all scripts within the target_folder into a single text file.
    """
    if target_folder == "ALL MODULES":
        modules = [d for d in os.listdir() if os.path.isdir(d) and not d.startswith('.') and d != 'ai_smif']
        output_file_name = "CONCAT ALL MODULES.txt"
    else:
        if not os.path.isdir(target_folder):
            print(f"Error: The folder '{target_folder}' does not exist.")
            return
        modules = [target_folder]
        top_folder_name = os.path.basename(os.path.normpath(target_folder))
        output_file_name = f"CONCAT {top_folder_name}.txt"

    output_file_path = os.path.join(os.getcwd(), output_file_name)

    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        for module in modules:
            if module == 'ai_smif':
                continue
            outfile.write(f"# Module: {module}\n\n")
            for root, dirs, files in os.walk(module):
                dirs[:] = [d for d in dirs if d != '__pycache__']
                
                for file in sorted(files):
                    if should_include_file(file) and not should_exclude_file(file):
                        file_path = os.path.join(root, file)
                        outfile.write(f"# File: {file_path}\n")
                        outfile.write(f"# Type: {os.path.splitext(file)[1][1:]}\n\n")
                        
                        content = read_file_content(file_path)
                        if content is not None:
                            outfile.write(content)
                            outfile.write("\n\n")
                        else:
                            outfile.write(f"# Error: Unable to read file {file_path}\n\n")

    print(f"Scripts concatenated into '{output_file_name}'.")

if __name__ == "__main__":
    target_folder = "components/trading_execution_engine"
    concatenate_scripts(target_folder)