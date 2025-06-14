import argparse
import os
import re
import subprocess

import librosa
import numpy as np
import soundfile

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks


def get_sub_dirs(source_dir):
    sub_dir = [f for f in os.listdir(source_dir) if not f.startswith('.')]
    sub_dir = [f for f in sub_dir if os.path.isdir(os.path.join(source_dir, f))]
    return sub_dir


def is_sentence_ending(sentence):
    if re.search(r'[。？！……]$', sentence):
        return True
    return False


def resample_audios(origin_dir, resample_dir, sample_rate):
    print("start resample audios")
    os.makedirs(resample_dir, exist_ok=True)
    dirs = get_sub_dirs(origin_dir)

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        ffmpeg_installed = True
        print("ffmpeg installed. use ffmpeg.")
    except Exception as e:
        ffmpeg_installed = False
        print("ERROR! ffmpeg is not installed. use librosa.")

    for dir in dirs:
        source_dir = os.path.join(origin_dir, dir)
        target_dir = os.path.join(resample_dir, dir)
        os.makedirs(target_dir, exist_ok=True)
        listdir = list(os.listdir(source_dir))
        listdir_len = len(listdir)
        for index, f in enumerate(listdir, start=1):
            if f.endswith(".wav") or f.endswith(".mp3"):
                file_path = os.path.join(source_dir, f)
                target_path = os.path.join(target_dir, f)
                target_path = os.path.splitext(target_path)[0] + '.wav'
                if os.path.exists(target_path):
                    continue
                if ffmpeg_installed:
                    process = subprocess.run(["ffmpeg", "-y", "-i", file_path, "-ar", f"{sample_rate}", "-ac", "1", "-v", "quiet", target_path])
                else:
                    try:
                        print(f"{index}/{listdir_len} file")
                        data, sample_rate = librosa.load(file_path, sr=sample_rate, mono=True)
                        soundfile.write(target_path, data, sample_rate)
                    except Exception as e:
                        print(f"\n{file_path} convert fail.")
                    finally:
                        pass
                    


def create_dataset(source_dir, target_dir, sample_rate, language, inference_pipeline, max_seconds, multi_split=True):
    # source_dir, target_dir, sample_rate=44100, language = "ZH", inference_pipeline = None
    
    roles = get_sub_dirs(source_dir)
    count = 0
    result = []

    for speaker_name in roles:

        source_audios = [f for f in os.listdir(os.path.join(source_dir, speaker_name)) if f.endswith(".wav")]
        source_audios = [os.path.join(source_dir, speaker_name, filename) for filename in source_audios]
        slice_dir = os.path.join(target_dir, speaker_name)
        os.makedirs(slice_dir, exist_ok=True)

        for audio_path in source_audios:
            rec_result = inference_pipeline(audio_in=audio_path) # dict_keys(['text', 'text_postprocessed', 'time_stamp', 'sentences'])
            if 'sentences' not in rec_result:
                print(f"Warning: 推理结果缺少 'sentences' 字段，文件：{audio_path}，rec_result keys: {list(rec_result.keys())}")
                continue
            data, sample_rate = librosa.load(audio_path, sr=sample_rate, mono=True)

            sentence_list = []
            audio_list = []
            time_length = 0
            if multi_split:
                for sentence in rec_result['sentences']:
                    text = sentence['text'].strip()
                    if (text == ""):
                        continue
                    start = int((sentence['start'] / 1000) * sample_rate)
                    end = int((sentence['end'] / 1000) * sample_rate)

                    if time_length > 0 and time_length + ((sentence['end'] - sentence['start']) / 1000) > max_seconds:
                        sliced_audio_name = f"{str(count).zfill(6)}"
                        sliced_audio_path = os.path.join(slice_dir, sliced_audio_name+".wav")
                        s_sentence = "".join(sentence_list)
                        if not re.search(r"[。！？]$", s_sentence):
                            sentence_end = s_sentence[-1]
                            s_sentence = s_sentence[:-1] + '。' if sentence_end != '。' else s_sentence
                        audio_concat = np.concatenate(audio_list)
                        if time_length > max_seconds:
                            print(f"[too long voice]:{sliced_audio_path}, voice_length:{time_length} seconds")
                        soundfile.write(sliced_audio_path, audio_concat, sample_rate)
                        result.append(
                            f"{sliced_audio_path}|{speaker_name}|{language}|{s_sentence}"
                        )
                        sentence_list = []
                        audio_list = []
                        time_length = 0
                        count = count + 1

                    sentence_list.append(text)
                    audio_list.append(data[start:end])
                    time_length = time_length + ((sentence['end'] - sentence['start']) / 1000)
                    
                    if ( is_sentence_ending(text) ):
                        sliced_audio_name = f"{str(count).zfill(6)}"
                        sliced_audio_path = os.path.join(slice_dir, sliced_audio_name+".wav")
                        s_sentence = "".join(sentence_list)
                        audio_concat = np.concatenate(audio_list)
                        soundfile.write(sliced_audio_path, audio_concat, sample_rate)
                        result.append(
                            f"{sliced_audio_path}|{speaker_name}|{language}|{s_sentence}"
                        )
                        sentence_list = []
                        audio_list = []
                        time_length = 0
                        count = count + 1
            else:
                # 不进行多段切分，整段输出
                full_text = "".join([s['text'].strip() for s in rec_result['sentences'] if s['text'].strip() != ""])
                if len(full_text) > 0:
                    sliced_audio_name = f"{str(count).zfill(6)}"
                    sliced_audio_path = os.path.join(slice_dir, sliced_audio_name+".wav")
                    soundfile.write(sliced_audio_path, data, sample_rate)
                    result.append(
                        f"{sliced_audio_path}|{speaker_name}|{language}|{full_text}"
                    )
                    count = count + 1
                else:
                    print(f"[Warning] full_text 为空，未输出音频：{audio_path}")
    return result


def create_list(source_dir, target_dir, resample_dir, sample_rate, language, output_list, max_seconds, multi_split=True):
    resample_audios(source_dir, resample_dir, sample_rate)
    inference_pipeline = pipeline(
        task=Tasks.auto_speech_recognition,
        model='damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
        model_revision="v1.2.4")
    result =  create_dataset(resample_dir, target_dir, sample_rate = sample_rate, language = language, inference_pipeline = inference_pipeline, max_seconds = max_seconds, multi_split=multi_split)
    # 输出统计信息
    input_count = 0
    for root, dirs, files in os.walk(resample_dir):
        input_count += len([f for f in files if f.lower().endswith('.wav')])
    output_count = 0
    for root, dirs, files in os.walk(target_dir):
        output_count += len([f for f in files if f.lower().endswith('.wav')])
    print(f"从{resample_dir}输入{input_count}个文件，输出到{target_dir}{output_count}个文件")
    with open(output_list, "w", encoding="utf-8") as file:
        for line in result:
            try:
                file.write(line.strip() + '\n')
            except UnicodeEncodeError as e:
                print("UnicodeEncodeError: Can't encode to ASCII:", e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_dir", type=str, default="fragment", help="Source directory path, Default: fragment")
    parser.add_argument("--target_dir", type=str, default="dataset", help="Target directory path, Default: dataset")
    parser.add_argument("--resample_dir", type=str, default="fragment_resample", help="Resample directory path, Default: origin_resample")
    parser.add_argument("--sample_rate", type=int, default=48000, help="Sample rate, Default: 44100")
    parser.add_argument("--language", type=str, default="ZH", help="Language, Default: ZH")
    parser.add_argument("--output", type=str, default="demo.list", help="List file, Default: demo.list")
    parser.add_argument("--max_seconds", type=int, default=15, help="Max sliced voice length(seconds), Default: 15")
    parser.add_argument("--multi_split", action="store_true", help="是否进行多段切分，添加该参数则多段切分，否则整段输出")
    args = parser.parse_args()
    create_list(args.source_dir, args.target_dir, args.resample_dir, args.sample_rate, args.language, args.output, args.max_seconds, args.multi_split)
    
