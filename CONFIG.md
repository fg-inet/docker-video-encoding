## QUICKSTART (encoding only)

First download an example video:

```
mkdir -p samples/videos/ && \
  wget https://service.inet.tu-berlin.de/owncloud/index.php/s/8NA7IFNKN9TgXVA/download -O samples/videos/bigbuckbunny480p24x30s.y4m
```

Encode the example with fixed segment durations:

```
sudo docker run --rm -v "$PWD"/samples/videos/:/videos \
                     -v "$PWD"/samples/results/:/results \
                     fginet/docker-video-encoding:latest bigbuckbunny480p24x30s.y4m bigbuckbunny480p24x30s.y4m 41 0 4 0 x264 1.0,2.0,3.0

```

The command line arguments for *variable length bitrate encoding*:

```
<reference_video> <video_id> <crf_value> <min_length> <max_length> 0.0 <codec> <key_frames_t> [<cst_bitrate>]
```

The command line arguments for *fixed length bitrate encoding*:


```
<reference_video> <video_id> <crf_value> <min_length> <max_length> <target_seg_length> <codec> [<cst_bitrate>]
```

You can find the results in the *samples/results* folder.

## QUICKSTART (with worker and job queue)

**Important**: Make sure that docker is configured to work without root access.

First make sure you downloaded the video as described about (*bigbuckbunny480p24x30s.y4m*).
Afterwards make a copy of the job template:

```
cp samples/jobs/00_waiting/bigbuckbunny480p24x30s_var_vbr_job001.txt.tmpl samples/jobs/00_waiting/bigbuckbunny480p24x30s_var_vbr_job001.txt
```

Start the worker:

```
python3 worker.py --dry-run --one-job
```

The following options are used:

  * **--dry-run**: does not call the container, but prints the docker command.
  * **--one-job**: quit after processing one job.

You can use different templates:

  * *bigbuckbunny480p24x30s_var_vbr_job001.txt.tmpl*: Variable Length VBR encoding
  * *bigbuckbunny480p24x30s_var_cbr_job002.txt.tmpl*: Variable Length CBR encoding
  * *bigbuckbunny480p24x30s_fix_vbr_job003.txt.tmpl*: Fixed Length VBR encoding
  * *bigbuckbunny480p24x30s_fix_cbr_job004.txt.tmpl*: Fixed Length CBR encoding

### run_workers.sh Script

Use the *run_workers.sh* script to start a worker on each available core:

```
cp run_workers_template.sh run_workers.sh
```

Adapt the paths and parameters in the script and remove the *echo* from *echo screen* in the script to activate the workers when you execute the script.

You can stop all running workers after the current job with creating a *STOP_WORKERS* file in the working directory:

```
touch STOP_WORKERS
```

#### Job/Result Files

Job and result files (video statistics) are managed [here](https://github.com/fg-inet/docker-video-encoding/blob/master/run_workers_template.sh#L10-L11).
The directory structure can be combine with other usful services allowing a central managing of all workers on a distributed system:
  * WEBDAV
  * SSHFS
  * NFS
  * ...

#### Video Encoded Files

The docker automatically copies the encoded video files to the [`SSHFS_DIR`](https://github.com/fg-inet/docker-video-encoding/blob/master/run_workers_template.sh#L18) or uploads the results via [`SFTP`](https://github.com/fg-inet/docker-video-encoding/blob/master/run_workers_template.sh#L13-L17).
Further, you have to specify [`SFTP`](https://github.com/fg-inet/docker-video-encoding/blob/master/run_workers_template.sh#L35-L40) or [`SSHFS_DIR`](https://github.com/fg-inet/docker-video-encoding/blob/master/run_workers_template.sh#L42-L45), by comment and uncommenting the metioned lines.


## Local Testing

First build the image:

	sudo docker build -t fginet/docker-video-encoding:latest .

You can start and enter the build image with:

```
sudo docker run --rm -it --entrypoint=bash fginet/docker-video-encoding:latest
```

If you want to test encoding, also add the videos/ and results/ volumes:

```
sudo docker run --rm -v "$PWD"/samples/videos/:/videos \
                     -v "$PWD"/samples/results/:/results \
                     -it --entrypoint=bash fginet/docker-video-encoding:latest
```

