import os
import shutil
import logging
import random
import time
import re
from os.path import join as pjoin

log = logging.getLogger(__name__)


class Job(object):

    def __init__(self, dj, status, job):
        self._dj = dj
        self._status = status
        self._job = job

    def done(self):
        return self._dj.on_job_success(self)

    def failed(self):
        return self._dj.on_job_failed(self)

    def __str__(self):
        return "Job(%s)" % self.path()

    def path(self):
        """
        Returns the current path to the job file.
        """
        return pjoin(self._dj._jobsdir, self._status, self.full_name())
    
    def name(self):
        """
        Returns the filename of the job.
        
        """
        return self._job
    
    def name_woext(self):
        """
        Return the name of the job without file extension.
        """
        return os.path.splitext(self._job)[0]
    
    def full_name(self):
        """
        Returns the full name (wid.name) of the job.
        """
        return "%s.%s" % (self._dj._wid, self._job)


class DirJobs(object):

    def __init__(self, jobsdir, wid="w1", rnd_job=True, job_ext=".txt",
                       worker_sync=False, sync_time=1,
                       job_filter=None):
        """

        @param jobsidr: Directory where the jobs are in the folder 00_waiting/.
        @param rnd_job: Choose the job randomly from the waiting ones.
        @param job_ext: File extension of the jobs (default: .txt)
        @param worker_sync: Sync multiple workers
        @param sync_time: Time until sync to all workers is done (for samba, webdav, etc.)
        @param job_filter: A function with the signature f(path, name) -> boolean to filter jobs
        """

        self._jobsdir = jobsdir
        self._wid = wid
        self._rnd_job = rnd_job
        self._job_ext = ".txt"
        self._worker_sync = worker_sync
        self._sync_time = sync_time
        self._job_filter = job_filter
        self._cur_job = None

        # Sanity check for worker ID
        if not re.match('^[a-zA-Z0-9]+$', self._wid):
                raise Exception("Worker ID is only allowed to contain numbers and letters.")

        # Make sure job directories exist.
        for d in ["00_waiting", "01_running", "02_done", "99_failed"]:
            os.makedirs(pjoin(self._jobsdir, d), exist_ok=True)

    def on_job_failed(self, job):

        log.debug("Job failed: %s" % job)
        
        dst = pjoin(self._jobsdir, "99_failed", job.name())
       
        self._move(job.path(), dst)
        
        self._cur_job = None

    def on_job_success(self, job):

        log.debug("Job finished: %s" % job)

        dst = pjoin(self._jobsdir, "02_done", job.name())

        self._move(job.path(), dst)
        
        self._cur_job = None

    def next_and_lock(self, no_wait=False):
        """
        Get the next job to process and locks it for the worker.
        """

        if self._cur_job:
            log.error("There is already an active job! Please call done() or failed() on the job first.")
            return None

        # Loop until we found a job
        while True:

            jobs = self._ls_waiting_jobs()

            # No more jobs
            if not jobs:
                return None

            if self._rnd_job:
                    job = random.choice(jobs)
            else:
                job = sorted(jobs)[0]

            log.debug("Selected job: %s" % job)

            wjob = "%s.%s" % (self._wid, job)

            src = pjoin(self._jobsdir, "00_waiting", job)
            dst = pjoin(self._jobsdir, "01_running", wjob)

            try:
                self._move(src, dst)
            except FileNotFoundError:
                log.warning("Job %s does not exist anymore. Moving on" % src)
                continue

            if not self._worker_sync:
                return Job(self, "01_running", job)
            else:

                job = self._job_worker_selection(job, no_wait=no_wait)

                if job is not None:
                    return job

    def _ls_waiting_jobs(self):
        """
        Returns a (filtered) list of the waiting jobs.
        """
        
        jobs = [j for j in os.listdir(pjoin(self._jobsdir, "00_waiting")) if j.endswith(self._job_ext)]
        
        if self._job_filter:
            jobs = [j for j in jobs if self._job_filter(pjoin(self._jobsdir, "00_waiting", j), j)]
        
        return jobs

    def _job_worker_selection(self, job, no_wait=False):

        if not no_wait:
            log.debug("Waiting %ds if someone else wants this job.." % self._sync_time)
            time.sleep(self._sync_time)

        job_workers = [j.split(".")[0] for j in os.listdir(pjoin(self._jobsdir, "01_running")) if job in j]

        assert(len(job_workers) > 0 and (self._wid in job_workers))

        if len(job_workers) == 1:
            self._cur_job = Job(self, "01_running", job)
        else:

                log.warning("Conflicting workers for job %s! Workers: %s " % (job, job_workers))

                me_idx = sorted(job_workers).index(self._wid)

                log.debug("me idx:" + me_idx)
                log.debug("job_workers:" + job_workers)

                if me_idx == 0:
                    log.info("I am index %d, taking the job!" % me_idx)

                    self._cur_job = Job(self, "01_running", job)
                else:
                    log.info("I am index %d, giving up on the job" % me_idx)

                    wjob = "%s.%s" % (self._wid, job)
                    self._rm(pjoin(self._jobsdir, "01_running", wjob))

                    self._cur_job = None
                
        return self._cur_job

    def _rm(self, f):
        log.debug("RM: %s" % f)
        os.remove(f)
    
    def _move(self, src, dst):
        log.debug("MOVE: %s to %s" % (src, dst))
        shutil.move(src, dst)
        os.utime(dst)

if __name__ == "__main__":
    
    logconf = {'format': '[%(asctime)s.%(msecs)-3d: %(name)-16s - %(levelname)-5s] %(message)s', 'datefmt': "%H:%M:%S"}
    logging.basicConfig(level=logging.DEBUG, **logconf)

    import argparse
    parser = argparse.ArgumentParser(description="Encoding worker.")
    parser.add_argument('-j', '--jobdir', help="Jobs folder.", default="samples/jobs/")
    parser.add_argument('-i', '--worker-id', help="ID of the worker.", default="w1")

    args = parser.parse_args()

    def job_filter(path, name):
        print(path, ", ", name)
        return True

    dj = DirJobs(args.jobdir, job_filter=job_filter)

    log.info("Starting worker %s" % args.worker_id)

    while True:
        
        job = dj.next_and_lock()
        
        if not job:
            log.info("No more jobs!")
            break
       
        log.info("Processing: %s" % job)
        
        job.done()
       
    log.info("Quitting worker %s." % args.worker_id)

