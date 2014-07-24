import resource
import fcntl
import os

def get_open_fds():
    fds = []
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    for fd in range(0, soft):
        try:
            flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        except IOError:
            continue
        fds.append(fd)
    return fds

def get_file_names_from_file_number(fds):
    names = []
    for fd in fds:
        names.append(os.readlink('/proc/self/fd/%d' % fd))
    return names

fds = get_open_fds()
print get_file_names_from_file_number(fds)