# TODO

## External tool subprocesses have no timeout and can be orphaned

`run_command` in `plannotate/_tools/common.py` calls `subprocess.run(...)` without a
`timeout`. In the API container (gunicorn, `PLANNOTATE_TIMEOUT`), a stuck request is
handled by killing the worker. Any BLAST, DIAMOND or Infernal child that worker started
is not killed with it: it is orphaned and keeps running (and using CPU) until it finishes
on its own. `docker run --init` only reaps such processes after they exit; it does not
stop them early.

Possible fixes:

- Pass a `timeout` to `subprocess.run` (configurable, e.g. via an environment variable)
  and raise a clear error when it expires.
- Start the child in its own process group and kill the group on timeout or shutdown.
- On Linux, make the child die with its parent (`PR_SET_PDEATHSIG`).
