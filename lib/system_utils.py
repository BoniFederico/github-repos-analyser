import subprocess
import os
import shutil

def exc(command:str,params:list=None,cwd:str=None,shell:bool=False):
    proc = subprocess.Popen(([command]+params) if params is not None else command, 
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, 
                                shell=shell,
                                cwd=cwd)
    output, error = proc.communicate()
    if proc.returncode != 0: 
        raise subprocess.CalledProcessError(proc.returncode,command+str(output))
    return output.decode("utf-8")



def delete_file_with(path:str,tokens:list):
    
    for element in os.listdir(path):
        for token in tokens:
            if token in element:
 
                if os.path.isfile(os.path.join(path,element)):
                    os.remove(os.path.join(path,element))
                else:
                    shutil.rmtree(os.path.join(path,element), ignore_errors=True, onerror=None)
                continue
        if os.path.isdir(os.path.join(path,element)):
            delete_file_with(os.path.join(path,element),tokens)

def delete_files_from_tokens(path:str,tokens:list):
    for element in os.listdir(path):
        for token in tokens:
            if token in element:
                if os.path.isfile(os.path.join(path,element)):
                    os.remove(os.path.join(path,element))
                else:
                    shutil.rmtree(os.path.join(path,element), ignore_errors=True, onerror=None)
                continue
        if os.path.isdir(os.path.join(path,element)):
            delete_file_with(os.path.join(path,element),tokens)

# https://stackoverflow.com/questions/3462143/get-difference-between-two-lists-with-unique-entries#:~:text=The%20difference%20between%20two%20lists,using%20the%20following%20simple%20function.&text=By%20Using%20the%20above%20function,Four'%2C%20'Three'%5D%20.
def diff(list1:list, list2:list):
    c = set(list1).union(set(list2))  # or c = set(list1) | set(list2)
    d = set(list1).intersection(set(list2))  # or d = set(list1) & set(list2)
    return list(c - d)

# https://stackoverflow.com/questions/9427163/remove-duplicate-dict-in-list-in-python
def unique_dictionaries(data:list):
    return {frozenset(item.items()):item for item in data}.values()