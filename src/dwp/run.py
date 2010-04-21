import os
import imp
import sys
import threading
import traceback

from multiprocessing import Process
from multiprocessing import Pipe
from multiprocessing import JoinableQueue
from mmap import mmap
from array import array

from django.core.handlers.wsgi import WSGIHandler
from django import conf
from django import utils

from .utils import redefine_sockets
from .utils import SOCKETS

BUFFER_SIZE = 65535

SAFE_ENVIRON = 'HTTP_ACCEPT', \
               'HTTP_ACCEPT_CHARSET', \
               'HTTP_ACCEPT_ENCODING', \
               'HTTP_ACCEPT_LANGUAGE', \
               'HTTP_CONNECTION', \
               'HTTP_HOST', \
               'HTTP_KEEP_ALIVE', \
               'HTTP_USER_AGENT', \
               'CONTENT_LENGTH', \
               'CONTENT_TYPE', \
               'PATH_INFO', \
               'QUERY_STRING', \
               'REMOTE_ADDR', \
               'REMOTE_HOST', \
               'REQUEST_METHOD', \
               'SCRIPT_NAME', \
               'SERVER_NAME', \
               'SERVER_PORT', \
               'SERVER_PROTOCOL', \
               'SERVER_SOFTWARE', \

def make_app(config, **kwargs):
    return WSGIApplication(**kwargs)

def run_loop(stdin, stdout, stderr, pipe, shared, queue, settings):
    redefine_sockets(stdin, stdout, stderr)

    # set up django environment
    imp.load_source("settings", settings)
    settings = conf.Settings("settings")
    conf.settings.configure(settings)

    # activate language
    utils.translation.activate(conf.settings.LANGUAGE_CODE)

    handler = WSGIHandler()
    output = mmap(shared, BUFFER_SIZE)

    while True:
        environ = pipe.recv()
        response = ["500 Internal Server Error", [], None]

        def start_response(*args):
            response[:] = args

        try:
            chunks = handler(environ, start_response)
        except:
            exc_info = sys.exc_info()
            chunks = traceback.format_exception(*exc_info)

        pipe.send(response)

        for chunk in chunks:
            size = len(chunk)
            if size > BUFFER_SIZE:
                raise ValueError("Chunk too large: %d." % size)

            position = output.tell()

            if position + size < BUFFER_SIZE:
                output.write(chunk)
            else:
                queue.join()
                position = 0
                output.seek(position)

            queue.put_nowait((position, size))
        queue.put(None)

    os.fdclose(shared)

class WSGIApplication(object):
    def __init__(self, settings=None):
        tmpfile = os.tmpfile()
        (array('c', [' ']) * BUFFER_SIZE).tofile(tmpfile)
        tmpfile.seek(0)
        fd = tmpfile.fileno()
        self.input = mmap(fd, BUFFER_SIZE)
        pipe, self.pipe = Pipe()
        self.queue = JoinableQueue()
        self.process = Process(target=run_loop, args=SOCKETS + (
            pipe, fd, self.queue, settings))
        self.process.daemon = True
        self.process.start()
        self.lock = threading.Lock()

    def __call__(self, environ, start_response):
        safe_environ = dict(
            (name, environ.get(name, '')) for name in SAFE_ENVIRON)

        # send request
        self.pipe.send(safe_environ)

        # single-threaded
        self.lock.acquire()
        try:
            # wait for response
            args = self.pipe.recv()

            # start response
            start_response(*args)

            # process queue
            while True:
                item = self.queue.get(True, 1.0)

                try:
                    if item is None:
                        break
                    position, size = item
                    self.input.seek(position)
                    if size > 0:
                        chunk = self.input.read(size)
                    else:
                        chunk = None
                finally:
                    self.queue.task_done()

                if chunk is not None:
                    yield chunk

        finally:
            self.lock.release()
