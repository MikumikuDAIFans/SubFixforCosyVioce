## 本项目基于[SubFix](https://github.com/cronrpc/SubFix)搭建,用于对音频文件进行切分和打标

## 环境搭建参考[subfix_readme](https://github.com/cronrpc/SubFix/blob/main/README_zh.md)

## 使用指南

00.文件夹路径栏输入cmd，启动命令行

01.清理文件夹内容

```cmd
Miniconda3\python.exe cleanup_folders.py
```

02.复制音频文件到origin文件夹下

03.裁剪音频

```cmd
Miniconda3\python.exe audio_cut.py --fragment_name fufu
#--fragment_name {自定义数据集名称}
```

04.生成数据集

```cmd
Miniconda3\python.exe subfix_create_dataset.py
#--multi_split 可选择是否根据标点符号进一步拆分音频
#偶尔会出现输出文件数少于输入文件数，造成输出文件数量少于输入文件的原因，通常是部分输入音频在识别后未获得有效文本，因此未被输出。
```

05.检查数据集

```cmd
Miniconda3\python.exe subfix_webui_zh.py
```

06.生成标注文本

```cmd
Miniconda3\python.exe list2txt.py
```

07.整合输出数据集

```cmd
Miniconda3\python.exe copy_to_final_output.py
```
