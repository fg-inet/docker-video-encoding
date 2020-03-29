# Docker Video Encoding

Docker container for DASH video encoding using FFMPEG.
The following parameters can be specified:

* **video:** input video
* **reference_video:** reference video for quality calculation
* **crf:** target output quality
* **min_length:** minimum duration of a segment in seconds (relevant in case of variable segment duration encoding)
* **max_length:** maximum duration of a segment in seconds (relevant in case of variable segment duration encoding)
* **target_seg_length:** fix duration in seconds of all video segments (in case of variable set seglen="var")
* **encoder:** encoder. supported: x264. planned to be supported: x265, vp9
* **timestamps:** I-frame positions from reference encoding
* **cst_bitrate:** target bitrate for constant bitrate encoding (cbr)

If the source video shall be splitted into segments of fixed duration, set maxdur=0 and mindur=0; If the source video shall be splitted into segments of variable duration, please set seglen="var".


## Requirements

- Docker
- Python

## QUICKSTART (MMSYS)

Additional Requirements:

  - Linux OS
  - rename (from util-linux)
  - wget
  - screen

Steps 2, 3 and 4 are optional and can be skipped, if only example files should be used.

  1. Run `init_mmsys.sh`
  2. Create Job Files as described [here](https://github.com/fg-inet/video-scripts).
  3. Copy them into `jobs/`.
  4. Copy the source videos into `videos/`.
  5. Run `run_workers_mmsys.sh`.
  6. Video statistics file are located at `results/` and encoded videos at `sshfs_dir/`.