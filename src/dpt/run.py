import os
import imp
import sys
import threading
import traceback
import webob

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

BUFFER_SIZE = 2**18

SAFE_ENVIRON = 'HTTP_ACCEPT', \
               'HTTP_ACCEPT_CHARSET', \
               'HTTP_ACCEPT_ENCODING', \
               'HTTP_ACCEPT_LANGUAGE', \
               'HTTP_CONNECTION', \
               'HTTP_COOKIE', \
               'HTTP_HOST', \
               'HTTP_KEEP_ALIVE', \
               'HTTP_REFERER', \
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
               'wsgi.run_once', \
               'wsgi.url_scheme', \
               'wsgi.version'

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
        environ, input_fd, error_fd = pipe.recv()

        try:
            environ['wsgi.input'] = os.fdopen(input_fd, 'r')
        except OSError:
            pass

        try:
            environ['wsgi.errors'] = os.fdopen(error_fd, 'w')
        except OSError:
            pass

        response = ["500 Internal Server Error", [], None]

        def start_response(*args):
            response[:] = args

        try:
            chunks = handler(environ, start_response)
        except:
            exc_info = sys.exc_info()
            chunks = traceback.format_exception(*exc_info)

        headerlist = response[1]
        for header, value in headerlist:
            if header == 'Content-Length':
                pipe.send(response)
                started = True
                break
        else:
            started = False

        length = 0
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
            length += size

        if not started:
            headerlist.append(('Content-Length', str(length)))
            pipe.send(response)
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

        safe_environ['wsgi.multiprocess'] = True
        safe_environ['wsgi.multithread'] = False

        try:
            wsgi_input_fd = os.dup(environ['wsgi.input'].fileno())
        except KeyError, AttributeError:
            wsgi_input_fd = None

        try:
            wsgi_error_fd = os.dup(environ['wsgi.errors'].fileno())
        except AttributeError:
            wsgi_error_fd = None

        # send request
        self.pipe.send((safe_environ, wsgi_input_fd, wsgi_error_fd))

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