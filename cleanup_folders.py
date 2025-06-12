import os
import shutil

def clean_folder(folder_path):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    print(f"已删除文件: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"已删除文件夹: {file_path}")
            except Exception as e:
                print(f"删除 {file_path} 时出错: {e}")
    else:
        print(f"文件夹不存在: {folder_path}")

folders_to_clean = [
    './txts',
    './fragment_resample',
    './fragment',
    './dataset',
    './origin',
    './_Final_Output'
]

if __name__ == "__main__":
    for folder in folders_to_clean:
        clean_folder(folder)
    print("清理完成，文件夹本身已保留，接下来请将音频数据放入origin文件夹")