from unittest import TestCase

from .utils import redefine_sockets
from .utils import SOCKETS

def run_test(stdin, stdout, stderr, pipe, cls, name):
    redefine_sockets(stdin, stdout, stderr)

    try:
        # configure django
        from django.conf import settings
        settings.configure()

        # initialize test case
        inst = TestCase.__new__(cls)
        inst.__init__(name)

        # run test and store result
        result = inst.defaultTestResult()
        inst.run(result)

        # clear test instances dictionary, because it may contain
        # values which are local to this process and won't pickle
        inst.__dict__.clear()

        # reinitialize test case
        inst.__init__(name)

        try:
            pipe.send(result)
        except Exception, e:
            pipe.send(e)
    finally:
        redefine_sockets(*SOCKETS)

class FunctionalTestCase(TestCase):
    def __new__(cls, name=None):
        if name is None:
            return TestCase.__new__(cls)
        from multiprocessing import Process
        from multiprocessing import Pipe
        parent, child = Pipe()
        process = Process(target=run_test, args=SOCKETS + (child, cls, name))

        def run(self, result):
            process.start()
            try:
                result.startTest(self)
                r = parent.recv()
                result.stopTest(self)
                if isinstance(r, Exception):
                    result.addFailure(self, (r.__class__, r, None))
                else:
                    result.failures.extend(r.failures)
                    result.errors.extend(r.errors)
            finally:
                process.join()

        case = type(cls.__name__, (TestCase,), {
            'run': run, '__module__': cls.__module__, name: getattr(cls, name)})
        inst = TestCase.__new__(case)
        inst.__init__(name)
        return inst
