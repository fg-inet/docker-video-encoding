#!/usr/bin/env bash

# directories
VIDEOS="$PWD/videos/"
TMP="$PWD/tmp/"
SSHFS_DIR="$PWD/sshfs_dir/"
RESULTS="$PWD/results/"
JOBS="$PWD/jobs/"

# create directories
mkdir -p $VIDEOS
mkdir -p $TMP
mkdir -p $SSHFS_DIR
mkdir -p $RESULTS
mkdir -p $JOBS/{00_waiting,01_running,02_done,99_failed}

# download example videos
wget https://service.inet.tu-berlin.de/owncloud/index.php/s/8NA7IFNKN9TgXVA/download -O videos/bigbuckbunny480p24x30s.y4m

# copy template files to job directory
cp samples/jobs/00_waiting/*.txt jobs/00_waiting/
