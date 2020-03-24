#!/usr/bin/env python

"""
This script allows to calculate the stats per segment from a m3u8 file.
"""

import os, sys, re, time, json
import subprocess
import numpy as np

def calc_stats(framelist,fps, durations):
    bitrates_segs_avg = []
    bitrates_segs = []
    sizes = []
    framecount = 0
    for frames in framelist:
        framecount += len(frames)
        bitrate_seg_avg, bitrates_seg, size = calc_avg_bitrate_filesize(frames,fps)
        bitrates_segs_avg.append(bitrate_seg_avg)
        bitrates_segs.append(bitrates_seg.tolist())
        sizes.append(size)
    # get bitrates per frame
    bitrates = np.concatenate(bitrates_segs, axis=0)

    # get avg bitrates per segment
    bitrates_segs_avg = np.array(bitrates_segs_avg)
    
    sizes = np.array(sizes)
    durations = np.array(durations)
    ret_data = {
        # on segment basis
        'bitrates_segs_avg_mean': bitrates_segs_avg.mean(),
        'bitrates_segs_avg_std' : bitrates_segs_avg.std(),
        'bitrates_segs_avg_min' : min(bitrates_segs_avg),
        'bitrates_segs_avg_max' : max(bitrates_segs_avg),
        'bitrates_segs_avg' : bitrates_segs_avg.tolist(),

        # on frame basis
        'bitrate_mean': bitrates.mean(),
        'bitrate_std' : bitrates.std(),
        'bitrate_min' : min(bitrates),
        'bitrate_max' : max(bitrates),
        'bitrates' : bitrates.tolist(),

        'bitrates_segs' : bitrates_segs,
        'size_total' : np.sum(sizes),
        'size_seg_mean' : sizes.mean(),
        'size_seg_std' : sizes.std(),
        'size_seg_min' : min(sizes),
        'size_seg_max' : max(sizes),
        'sizes' : sizes.tolist(),
        'durations_mean' : durations.mean(),
        'durations_std' : durations.std(),
        'durations_min' : min(durations),
        'durations_max' : max(durations),
        'durations' : durations.tolist()
    }
    #print('Framecount: ', framecount)
    return ret_data

def calc_avg_bitrate_filesize(frames,fps):
    bitrates = []
    pkt_sizes = []
    for frame in frames:
        size = float(frame['pkt_size'])*8 # now b
        pkt_sizes.append(float(frame['pkt_size'])*8)
        bitrates.append(size*fps)
    # avg bitrate, segment size
    bitrates = np.array(bitrates)
    pkt_sizes = np.array(pkt_sizes)
    return bitrates.mean(), bitrates, np.sum(pkt_sizes)

def get_vid_stream_stats(file_name):
    command = 'ffprobe -show_entries frame -show_streams ' \
            '-print_format json -show_entries frame ' \
            '-i {file_name}'.format(file_name=file_name)
    proc = subprocess.Popen(command.split(), \
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr = proc.communicate()
    json_dump = json.loads(stderr[0].decode('utf-8'))
    times = []
    #print('Frame first: ', len(json_dump['frames']))
    frames = json_dump['frames']
    for frame in frames:
        frame_type = frame['pict_type']
        if frame_type == 'I':
            times.append(float(frame['best_effort_timestamp_time']))
    return times, frames

def get_segment_by_stamps(frames, begin, end):
    begin_ = 0
    end_ = 0
    for i in range(len(frames)):
        if begin == float(frames[i]['best_effort_timestamp_time']):
            begin_ = i
        if end == float(frames[i]['best_effort_timestamp_time']):
            end_ = i
    if begin_ == end_:
        return frames[begin_:] 
    return frames[begin_:end_]

def get_segments(input_file):
    timeline_I,frames = get_vid_stream_stats(input_file)
    timeline = [0]
    timeline_test = [0]
    count = 1
    segments = []
    idxs = [0]
    durations = []
    with open(input_file,'r') as m3u8:
        for line in m3u8:
            if line .startswith('#EXTINF:'):
                duration = float(line.replace('#EXTINF:','').split(',')[0])
                durations.append(duration)
                stamp = timeline[count-1] + duration
                
                # get exact I-Frame position
                idx = (np.abs(np.array(timeline_I) - stamp)).argmin()
                idxs.append(idx)

                timestamp_I = timeline_I[idx]
                timeline.append(timeline_I[idx])

                #print(timeline)
                #print(timeline[count-1],timeline[count])
                segments.append(get_segment_by_stamps(frames,timeline[count-1],timeline[count]))

                count += 1
    return segments, durations

def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

if __name__== "__main__":
    if len(sys.argv) < 3:
        print('Usage: python getTimeStamps.py [input m3u8] [framerate]')
        exit()
    input_file=str(sys.argv[1])
    framerate=float(sys.argv[2])
    segments, durations = get_segments(input_file)
    stats = calc_stats(segments,framerate, durations)
    stats_clean = calc_stats(segments[:-1],framerate, durations)
    with open('result.json', 'w') as fp:
        json.dump(stats, fp)
    with open('result_clean.json', 'w') as fp:
        json.dump(stats_clean, fp)