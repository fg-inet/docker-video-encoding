#!/usr/bin/env bash

HOST=`echo mmsys`
CORES=`grep -c ^processor /proc/cpuinfo`

VIDEOS="$PWD/videos/"
TMP="$PWD/tmp/"
IMAGE="fginet/docker-video-encoding:latest"

SSHFS_DIR="$PWD/sshfs_dir/"

CORES=2
RESULTS="$PWD/results/"
JOBS="$PWD/jobs/"

echo Host: $HOST
echo Cores: $CORES

# Update docker image
docker pull $IMAGE

for (( c=1; c<${CORES}; c++ ))
do
        WID="${HOST}x${c}"

		#if encoded video files should be put into a sshfs_dir (not necessary sshfs required!)
		WORKER_CMD="python3 worker.py -v \"$VIDEOS\" -t \"$TMP\" -r \"$RESULTS\" -j \"$JOBS\" \
		   -c \"$IMAGE\" -i \"$WID\" --log \
		 --sshfs-dir=\"$SSHFS_DIR\""

	echo "Running worker $WID"
        screen -dm -S "$WID" bash -c "${WORKER_CMD}; exec bash"
done

