import os
import shutil

def copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)

def copy_folder_files(src_folder, dst_folder):
    os.makedirs(dst_folder, exist_ok=True)
    for filename in os.listdir(src_folder):
        src_path = os.path.join(src_folder, filename)
        dst_path = os.path.join(dst_folder, filename)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)

def rename_files_in_folder(folder, speaker_id):
    # 收集所有wav和txt文件
    wav_files = [f for f in os.listdir(folder) if f.lower().endswith('.wav')]
    txt_files = [f for f in os.listdir(folder) if f.lower().endswith('.txt')]
    # 按文件名排序，确保一一对应
    wav_files.sort()
    txt_files.sort()
    count = 0
    for wav_file, txt_file in zip(wav_files, txt_files):
        audio_name = f"{count:04d}"
        mp3_filename = f"{speaker_id}_{audio_name}.mp3"
        txt_filename = f"{speaker_id}_{audio_name}.normalized.txt"
        wav_src = os.path.join(folder, wav_file)
        txt_src = os.path.join(folder, txt_file)
        mp3_dst = os.path.join(folder, mp3_filename)
        txt_dst = os.path.join(folder, txt_filename)
        # wav重命名为mp3后缀（如需转换可自行添加转换代码）
        os.rename(wav_src, mp3_dst)
        os.rename(txt_src, txt_dst)
        count += 1
    print(f"已完成重命名 {count} 对文件。")

if __name__ == "__main__":
    # 1. 移动 demo.list
    src_demo = "./demo.list"
    dst_demo = "./_Final_Output/demo.list"
    if os.path.exists(src_demo):
        copy_file(src_demo, dst_demo)
        print(f"已复制 {src_demo} 到 {dst_demo}")
    else:
        print(f"未找到 {src_demo}")

    # 2. 获取 fragment_resample 下 funina 文件夹名
    fragment_resample_dir = "./fragment_resample"
    subfolders = [f for f in os.listdir(fragment_resample_dir) if os.path.isdir(os.path.join(fragment_resample_dir, f))]
    if not subfolders:
        print(f"未找到 {fragment_resample_dir} 下的子文件夹")
        exit(1)
    target_folder_name = subfolders[0]  # 取第一个子文件夹名
    print(f"目标子文件夹名: {target_folder_name}")

    # 3. 移动 dataset\funina 和 txts 下的所有文件
    src_dataset = os.path.join("./dataset", target_folder_name)
    src_txts = "./txts"
    dst_subfolder = os.path.join("./_Final_Output", target_folder_name)

    if os.path.exists(src_dataset):
        copy_folder_files(src_dataset, dst_subfolder)
        print(f"已复制 {src_dataset} 下所有文件到 {dst_subfolder}")
    else:
        print(f"未找到 {src_dataset}")

    if os.path.exists(src_txts):
        copy_folder_files(src_txts, dst_subfolder)
        print(f"已复制 {src_txts} 下所有文件到 {dst_subfolder}")
    else:
        print(f"未找到 {src_txts}")

    # 4. 重命名新子文件夹下的文件
    speaker_id = target_folder_name
    rename_files_in_folder(dst_subfolder, speaker_id)