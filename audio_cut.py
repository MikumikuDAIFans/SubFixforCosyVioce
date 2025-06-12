import os
import argparse
import librosa
import numpy as np
import soundfile as sf

# 查找音频能量低谷，返回低谷的起止帧和持续时间
def find_valleys(y, sr, frame_length=2048, hop_length=512, energy_threshold=0.1, min_valley_duration=0.3):
    """
    查找音频能量低谷，返回低谷的起止帧和持续时间
    :param y: 音频波形
    :param sr: 采样率
    :param frame_length: 帧长
    :param hop_length: 帧移
    :param energy_threshold: 能量低于最大能量的百分比视为低谷
    :param min_valley_duration: 低谷最小持续时间（秒）
    :return: [(start_sample, end_sample, duration_sec), ...]
    """
    energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    max_energy = np.max(energy)
    threshold = max_energy * energy_threshold
    valleys = []
    in_valley = False
    start = 0
    for i, e in enumerate(energy):
        if e < threshold:
            if not in_valley:
                in_valley = True
                start = i
        else:
            if in_valley:
                in_valley = False
                end = i
                duration = (end - start) * hop_length / sr
                if duration >= min_valley_duration:
                    valleys.append((start * hop_length, end * hop_length, duration))
    # 处理结尾处的低谷
    if in_valley:
        end = len(energy)
        duration = (end - start) * hop_length / sr
        if duration >= min_valley_duration:
            valleys.append((start * hop_length, end * hop_length, duration))
    return valleys

# 根据低谷持续时间判断一句话是否结束，优先在长低谷处分割
def segment_audio_by_valley_duration(y, sr, valleys, max_len=28.0):
    """
    根据低谷持续时间判断一句话是否结束，优先在长低谷处分割
    :param y: 音频波形
    :param sr: 采样率
    :param valleys: 低谷列表 (start_sample, end_sample, duration_sec)
    :param max_len: 最大片段长度（秒）
    :return: [(start_sample, end_sample), ...]
    """
    segments = []
    start_sample = 0
    audio_len = len(y)
    max_samples = int(max_len * sr)
    valley_idx = 0
    while start_sample < audio_len:
        # 查找下一个低谷，且该低谷距离start_sample不超过max_len
        best_valley = None
        best_duration = 0
        while valley_idx < len(valleys):
            v_start, v_end, v_dur = valleys[valley_idx]
            if v_end - start_sample > max_samples:
                break
            if v_dur > best_duration and v_end > start_sample:
                best_valley = (v_start, v_end, v_dur)
                best_duration = v_dur
            valley_idx += 1
        if best_valley:
            # 在最长低谷处分割
            cut_point = best_valley[1]
            segments.append((start_sample, cut_point))
            start_sample = cut_point
        else:
            # 没有合适低谷，强制按最大长度裁剪
            end_sample = min(start_sample + max_samples, audio_len)
            segments.append((start_sample, end_sample))
            start_sample = end_sample
    return segments

# 合并短片段，合并后不超过最大时长，并确保所有片段大于3秒
def merge_short_segments(segments, sr, merge_thresh=10.0, max_len=28.0, min_final_len=3.0):
    """
    合并时长低于merge_thresh的片段，合并后不超过max_len，最终所有片段大于min_final_len
    :param segments: [(start_sample, end_sample), ...]
    :param sr: 采样率
    :param merge_thresh: 合并阈值（秒），最大14秒
    :param max_len: 合并后最大时长（秒）
    :param min_final_len: 合并后最小时长（秒）
    :return: 合并后的片段列表
    """
    merge_thresh = min(merge_thresh, 14.0)
    merged = []
    i = 0
    while i < len(segments):
        start, end = segments[i]
        seg_len = (end - start) / sr
        if seg_len >= merge_thresh:
            merged.append((start, end))
            i += 1
        else:
            # 尝试向后合并
            j = i + 1
            total_end = end
            while j < len(segments) and (total_end - start) / sr < merge_thresh and (total_end - start) / sr < max_len:
                next_start, next_end = segments[j]
                if (next_end - start) / sr > max_len:
                    break
                total_end = next_end
                j += 1
            # 合并后不能超过max_len
            if (total_end - start) / sr > max_len:
                total_end = end
                j = i + 1
            merged.append((start, total_end))
            i = j
    # 再次遍历，合并小于min_final_len的片段到相邻片段
    final_segments = []
    i = 0
    while i < len(merged):
        start, end = merged[i]
        seg_len = (end - start) / sr
        if seg_len >= min_final_len or len(merged) == 1:
            final_segments.append((start, end))
            i += 1
        else:
            # 优先尝试与前一个合并
            if i > 0:
                prev_start, prev_end = final_segments[-1]
                if (end - prev_start) / sr <= max_len:
                    final_segments[-1] = (prev_start, end)
                    i += 1
                    continue
            # 否则尝试与后一个合并
            if i + 1 < len(merged):
                next_start, next_end = merged[i+1]
                if (next_end - start) / sr <= max_len:
                    final_segments.append((start, next_end))
                    i += 2
                    continue
            # 无法合并则保留
            final_segments.append((start, end))
            i += 1
    return final_segments

# 批量处理文件夹下的音频文件
def process_audio_files(input_path, out_dir, max_len=28.0, sr=16000, merge_thresh=10.0):
    """
    批量处理文件夹下的音频文件
    :param input_path: 输入音频文件夹或单个文件
    :param out_dir: 输出文件夹
    :param max_len: 最大片段长度（秒）
    :param sr: 采样率
    :param merge_thresh: 合并阈值（秒）
    """
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    audio_files = []
    if os.path.isdir(input_path):
        for file in os.listdir(input_path):
            if file.lower().endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a")):
                audio_files.append(os.path.join(input_path, file))
    else:
        audio_files.append(input_path)
    input_file_count = len(audio_files)
    split_file_count = 0
    total_split_segments = 0
    output_file_count = 0
    for audio_file in audio_files:
        # 若未指定采样率，则与输入音频一致
        y, file_sr = librosa.load(audio_file, sr=args.sr)
        sr_to_use = file_sr
        duration_sec = len(y) / sr_to_use
        if duration_sec <= 30.0:
            # 不超过30秒，直接复制到输出文件夹
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            out_file = os.path.join(out_dir, f"{base_name}.wav")
            sf.write(out_file, y, sr_to_use)
            print(f"音频未超过30秒，直接复制: {out_file} ({duration_sec:.2f}秒)")
            output_file_count += 1
            continue
        valleys = find_valleys(y, sr_to_use)
        segments = segment_audio_by_valley_duration(y, sr_to_use, valleys, max_len=args.max_len)
        segments = merge_short_segments(segments, sr_to_use, merge_thresh=args.merge_thresh, max_len=args.max_len, min_final_len=3.0)
        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        if len(segments) > 1:
            split_file_count += 1
        total_split_segments += len(segments)
        for idx, (start, end) in enumerate(segments):
            segment = y[start:end]
            # 读取音频
            duration = len(segment) / sr_to_use
            # 判断是否需要分割
            if duration <= args.min_split_len:
                # 直接复制到输出目录
                out_file = os.path.join(out_dir, f"{base_name}{idx+1:02d}.wav")
                sf.write(out_file, segment, sr_to_use)
                print(f"音频片段时长 {duration:.2f}s <= {args.min_split_len}s，已直接复制到 {out_file}")
                output_file_count += 1
                continue
            out_file = os.path.join(out_dir, f"{base_name}{idx+1:02d}.wav")
            sf.write(out_file, segment, sr_to_use)
            print(f"保存片段: {out_file} ({(end-start)/sr_to_use:.2f}秒)")
            output_file_count += 1
    print(f"\n输入{input_file_count}个文件，其中{split_file_count}个文件共被拆分为{total_split_segments}个片段，输出{output_file_count}个文件。\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据波形低谷长度裁剪音频，优先在长低谷处分割，支持短片段合并，合并阈值最大14秒，最终片段大于3秒。")
    parser.add_argument('--audio', type=str, required=False, default='./origin', help='输入音频文件夹或单个音频文件路径，默认./origin')
    parser.add_argument('--out_dir', type=str, required=False, default=None, help='输出音频片段文件夹，若未指定则为 ./fragment/{fragment_name}')
    parser.add_argument('--max_len', type=float, default=28.0, help='最大片段长度（秒）')
    parser.add_argument('--sr', type=int, default=None, help='采样率，默认与输入音频一致')
    parser.add_argument('--merge_thresh', type=float, default=10.0, help='合并阈值（秒），最大14秒')
    parser.add_argument('--min_split_len', type=float, default=30.0, help='音频分割阈值（单位：秒），小于等于该时长的音频将直接复制而不分割，默认30秒')
    parser.add_argument('--fragment_name', type=str, required=False, default='displace', help='fragment子文件夹名称，默认displace')
    args = parser.parse_args()
    if args.out_dir:
        out_dir = args.out_dir
    else:
        out_dir = os.path.join('./fragment', args.fragment_name)
    process_audio_files(args.audio, out_dir, max_len=args.max_len, sr=args.sr, merge_thresh=args.merge_thresh)