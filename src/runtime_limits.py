"""Explicit execution capabilities; portable mode never claims POSIX enforcement.

SPDX-License-Identifier: MIT
"""
import json
import os
import sys
import time
try:
    import resource
except ImportError:
    resource=None

CPU_SECONDS=110
ADDRESS_BYTES=2*1024**3


def configure(portable=False):
    if not portable:
        if resource is None:
            raise RuntimeError('POSIX resource limits unavailable; explicitly select --portable')
        resource.setrlimit(resource.RLIMIT_AS,(ADDRESS_BYTES,ADDRESS_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU,(CPU_SECONDS,CPU_SECONDS))
        if hasattr(os,'sched_setaffinity'):
            os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    return {'mode':'portable' if portable else 'posix','workers':1,
            'requested_cpu_seconds':CPU_SECONDS,'requested_address_space_bytes':ADDRESS_BYTES,
            'os_cpu_limit_enforced':not portable,'os_address_space_limit_enforced':not portable,
            'cooperative_cpu_checks':True,'peak_rss_available':resource is not None,
            'python_optimization':sys.flags.optimize,'site_packages_disabled':bool(sys.flags.no_site),
            'dont_write_bytecode':sys.dont_write_bytecode,'platform':sys.platform}


def check_cpu():
    if time.process_time()>CPU_SECONDS:
        raise RuntimeError('cooperative process CPU ceiling; no scientific verdict')


def peak_rss_kib():
    if resource is None: return None
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value/1024 if sys.platform=='darwin' else value


def scientific_equal(a,b):
    def canonical(x):
        return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return canonical(a)==canonical(b)
