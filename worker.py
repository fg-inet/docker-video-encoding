import os
import sys
import logging
import random
import json
import time
import subprocess
import re
import traceback
import shutil
from functools import partial
from os.path import join as pjoin
from dirjobs import DirJobs

log = logging.getLogger(__name__)

VID_EXTS = ['y4m', 'yuv', 'mov', 'mkv', 'avi']


def sftp_upload_tmp(host, port, username, password, local_dir, target_dir):
    """
    Upload a folder to sftp server.

    :param host:
    :param port:
    :param username:
    :param password:
    :param local_dir:
    :param target_dir:
    :return:
    """

    log.debug("SFTP CPY: %s to %s@%s:%d:%s" %
              (local_dir, username, host, int(port), target_dir))

    import paramiko

    try:
        t = paramiko.Transport((host, int(port)))

        t.connect(username=username, password=password)

        sftp = paramiko.SFTPClient.from_transport(t)
    except:
        log.error("SFTP Connection failed!")
        log.error(traceback.format_exc())
        return False

    # Local directory name
    ldirname = os.path.basename(os.path.normpath(local_dir))

    try:
        sftp.chdir(target_dir)
        sftp.mkdir(ldirname)
        sftp.chdir(ldirname)
    except:
        log.error("Could not create %s !" % (target_dir + "/" + ldirname))
        log.error(traceback.format_exc())
        sftp.close()
        return False

    try:
        for item in os.listdir(local_dir):
            itemabs = os.path.join(local_dir, item)
            if os.path.isfile(itemabs):
                log.debug("SFTP PUT: %s" % item)
                sftp.put(itemabs, item)
    except:
        log.error("Failed to put items on the sftp server!")
        log.error(traceback.format_exc())
        sftp.close()
        return False

    sftp.close()

    return True


def process_job(job, wargs, dryrun=False):
    """
    Processes a job with the docker container.

    @param job: The job to process
    @param wargs: Arguments for the worker (container)
    """

    ts = int(time.time())

    stats = {'ts': ts,
             'job': job.name(),
             'job.path': job.path()}

    stats.update({k: v for k, v in wargs.items() if k != 'sftp_password'})

    log.info("Processing %s" % job)

    try:
        with open(job.path()) as f:
            j = json.load(f)

        stats['job_dict'] = j

        log.debug("Job: %s" % j)

        d = "%d.%s.%s" % (ts, wargs['id'], job.name_woext())
        rdir = pjoin(wargs['resultdir'], d)
        tdir = pjoin(wargs['tmpdir'], d)

        os.makedirs(rdir, exist_ok=True)
        os.makedirs(tdir, exist_ok=True)

        t = time.perf_counter()

        if "timestamps" in j:
            timestamps = j["timestamps"]
        else:
            timestamps = None
        if "cst_bitrate" in j:
            cst_bitrate = j["cst_bitrate"]
            log.info("CST BITRATE GIVEN!")
        else:
            cst_bitrate = None
            log.info("NO CST BITRATE GIVEN!")
        ret = _docker_run(stats, tdir, wargs['viddir'], rdir, wargs['container'],
                          j["video"], j["reference_video"], j["crf"], j["min_length"],
                          j["max_length"], j["target_seg_length"],
                          j["encoder"], timestamps, cst_bitrate,
                          dryrun=dryrun, processor=wargs['processor'])

        dur = time.perf_counter() - t
        stats['container_runtime'] = dur

        log.info("Container runtime: %.1fs" % dur)

    except:
        log.critical(traceback.format_exc())
        log.critical("Failed to process job!")
        return False

    stats['tmpsize'] = sum(os.path.getsize(pjoin(tdir, f)) for f in os.listdir(tdir) if os.path.isfile(pjoin(tdir, f)))

    with open(pjoin(rdir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=4, sort_keys=True)

    # If SFTP upload is specified.
    if wargs['sftp_host'] and not dryrun:

        t = time.perf_counter()

        sftp_ret = sftp_upload_tmp(wargs['sftp_host'], wargs['sftp_port'],
                                   wargs['sftp_user'], wargs['sftp_password'],
                                   tdir, wargs['sftp_target_dir'])

        dur = time.perf_counter() - t

        log.debug("Upload took %.1fs." % dur)

        if sftp_ret and not wargs['keep_tmp']:
            log.debug("SFTP upload completed. Deleting local %s." % tdir)
            shutil.rmtree(tdir)
        elif not sftp_ret:
            log.error("SFTP Upload of %s failed ! Keeping it locally.")

    # If sshfs folder is specified.
    if wargs['sshfs_dir'] and not dryrun:
        log.debug("SFTP upload completed. Deleting local %s." % tdir)
        shutil.move(tdir, wargs['sshfs_dir'])

    if not wargs['sshfs_dir'] and not wargs['sftp_host'] and not wargs['keep_tmp'] and not dryrun:
        log.debug("Deleting %s." % tdir)
        shutil.rmtree(tdir)

    return ret


def _docker_pull(resultdir, container, dryrun=False):

    log.info("Checking for newer version of %s" % container)

    cmd = ["docker", "pull", container]

    log.debug("RUN: %s" % " ".join(cmd))

    if not dryrun:

        try:
            with open(pjoin(resultdir, "docker_pull_stdout.txt"), "wt") as fout, \
                 open(pjoin(resultdir, "docker_pull_stderr.txt"), "wt") as ferr:

                subprocess.check_call(cmd, stderr=ferr, stdout=fout)

        except subprocess.CalledProcessError:
            log.error("Docker pull failed !!")
            log.error("Check the logs in %s for details." % resultdir)
            return False
    else:
        log.warning("Dryrun selected. Not pulling docker container!")

    return True


def _docker_run(stats, tmpdir, viddir, resultdir, container,
                video_id, reference_video, crf_value, key_int_min, key_int_max, target_seg_length, encoder, timestamps=None, cst_bitrate=None,
                dryrun=False, processor=None, skip_pull=False):

    if not skip_pull:

        ret = _docker_pull(resultdir, container, dryrun=dryrun)

        if not ret:
            return False

    docker_opts = ["--rm",
                   "--user", "%d:%d" % (os.geteuid(), os.getegid()),
                   "-v", "%s:/videos" % os.path.abspath(viddir),
                   "-v", "%s:/tmpdir" % os.path.abspath(tmpdir),
                   "-v", "%s:/results" % os.path.abspath(resultdir)]

    if processor:
        docker_opts += ["--cpuset-cpus=%s" % processor]

    docker_opts += [container]

    if not os.path.exists(pjoin(viddir, video_id)):
        raise Exception("Could not find video %s !!" % video_id)

    cmd = ["docker", "run"] + docker_opts + \
          [video_id, reference_video,str(crf_value), str(key_int_min), str(key_int_max), str(target_seg_length), encoder]
    
    if timestamps != None:
        cmd.append(timestamps)
    
    if cst_bitrate != None:
        cmd.append(str(cst_bitrate))

    log.debug("RUN: %s" % " ".join(cmd))

    if not dryrun:

        try:
            with open(pjoin(resultdir, "docker_run_stdout.txt"), "wt") as fout, \
                 open(pjoin(resultdir, "docker_run_stderr.txt"), "wt") as ferr:

                subprocess.check_call(cmd, stderr=ferr, stdout=fout)

        except subprocess.CalledProcessError:
            log.error("Docker run failed !!")
            log.error("Check the logs in %s for details." % resultdir)
            return False

    else:
        log.warning("Dryrun selected. Not starting docker container!")

    stats['docker_cmd'] = " ".join(cmd)

    return True


def worker_loop(args):

    videos = [os.path.splitext(v)[0] for v in os.listdir(args.viddir) if not v.startswith(".")]
    log.info("Currently available videos: %s" % videos)

    # Select only jobs where we have the video locally available
    def video_filter(viddir, path, name):

        # Get video name from job name
        vid = name.split('_')[0]

        # Check if it exists
        return any([os.path.exists(pjoin(viddir, vid + "." + e)) for e in VID_EXTS])

    dj = DirJobs(args.jobdir,
                 wid=args.id,
                 worker_sync=not args.dry_run,
                 sync_time=70,
                 job_filter=partial(video_filter, args.viddir))

    running = True

    # Worker arguments
    fields = ['tmpdir', 'viddir', 'resultdir', 'container', 'id', 'processor', 'keep_tmp',
              'sftp_host', 'sftp_user', 'sftp_port', 'sftp_password', 'sftp_target_dir', 'sshfs_dir']
    wargs = {k: getattr(args, k) for k in fields}

    if wargs['sftp_host'] and not args.dry_run:

        log.info("Using SFTP upload to %s." % wargs['sftp_host'])

        try:
            import paramiko
        except ImportError:
            log.critical("Python module paramiko not installed !!!")
            return

    while running:

        if os.path.exists("STOP_WORKERS"):
            log.warning("File STOP_WORKERS exists in working directory. Quitting..")
            break

        try:
            job = dj.next_and_lock(no_wait=args.one_job)

            if job:
                ret = process_job(job, wargs, dryrun=args.dry_run)

                if ret:
                    job.done()
                else:
                    log.error("Encoding job failed !!")
                    job.failed()
            else:
                pt = random.randint(30, 90)
                log.debug("No job found. Pausing for %d seconds." % pt)
                time.sleep(pt)

        except KeyboardInterrupt:

            log.warning("Received keyboard interrupt. Quitting after current job.")
            running = False

        if args.one_job or args.dry_run:
            log.warning("One job only option is set. Exiting loop.")
            running = False


if __name__ == "__main__":

    logconf = {'format': '[%(asctime)s.%(msecs)-3d: %(name)-16s - %(levelname)-5s] %(message)s', 'datefmt': "%H:%M:%S"}
    logging.basicConfig(level=logging.DEBUG, **logconf)

    import argparse
    parser = argparse.ArgumentParser(description="Encoding worker.")
    parser.add_argument('-j', '--jobdir', help="Jobs folder.", default="samples/jobs/")
    parser.add_argument('-v', '--viddir', help="Video folder.", default="samples/videos")
    parser.add_argument('-t', '--tmpdir', help="Temporary folder.", default="samples/tmpdir")
    parser.add_argument('-r', '--resultdir', help="Results folder.", default="samples/results")
    parser.add_argument('-c', '--container', help="Container to use.", default="fginet/docker-video-encoding:latest")
    parser.add_argument('--sftp-target-dir', help="Target directory on the SFTP host.", default=".")
    parser.add_argument('--sftp-host', help="SFTP Host to upload encoded videos to.")
    parser.add_argument('--sftp-port', help="Port of SFTP host.", default=22)
    parser.add_argument('--sftp-user', help="User of SFTP host.")
    parser.add_argument('--sftp-password', help="Password of the SFTP host.")
    parser.add_argument('--sshfs-dir', help="Target directory on ssh host.", default=".")
    parser.add_argument('--one-job', help="Run only one job and quit.", action="store_true")
    parser.add_argument('--dry-run', help="Dry-run. Do not run docker.", action="store_true")
    parser.add_argument('--keep-tmp', help="Keep encoded files in tmp folder.", action="store_true")
    parser.add_argument('--log', help="Create a worker log in the home folder.", action="store_true")
    parser.add_argument('-i', '--id', help="Worker identifier.", default="w1")
    parser.add_argument('-p', '--processor', help="Which CPU to use.", default=None)

    args = parser.parse_args()

    log.info("Starting worker %s." % args.id)

    # Sanity check for video filename
    if any(["_" in v for v in os.listdir(args.viddir)]):
        log.error("Sanity check failed: A video contains '_' in the filename! This is not allowed!")
        sys.exit(-1)

    # Sanity check for worker ID
    if not re.match('^[a-zA-Z0-9]+$', args.id):
        log.error("Worker ID is only allowed to contain numbers and letters.")
        sys.exit(-1)

    # Make sure the directories exist
    for d in [args.tmpdir, args.viddir, args.resultdir]:
        os.makedirs(d, exist_ok=True)

    jpath = pjoin(args.jobdir, "00_waiting")
    if not os.path.exists(jpath):
        log.critical("Path with the waiting jobs %s has to exist!" % jpath)
        sys.exit(-1)

    # Create a log file for the worker in the current directory.
    if args.log:
        fh = logging.FileHandler("worker_%s.log" % args.id)
        fh.setFormatter(logging.Formatter(logconf['format']))
        logging.getLogger().addHandler(fh)

    if args.dry_run:
        log.warning("This is a DRY-RUN. I am not running docker.")

    worker_loop(args)

    log.info("Quitting worker %s." % args.id)

