import os

input_list = r'demo.list'
output_dir = 'txts'

os.makedirs(output_dir, exist_ok=True)

with open(input_list, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split('|')
        if len(parts) < 4:
            continue
        wav_path = parts[0]
        text = parts[3]
        base_name = os.path.splitext(os.path.basename(wav_path))[0]
        out_path = os.path.join(output_dir, base_name + '.txt')
        with open(out_path, 'w', encoding='utf-8') as fout:
            fout.write(text)
print(f'已完成，将所有文本写入 {output_dir} 文件夹。')