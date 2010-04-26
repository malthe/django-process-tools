import os
import sys

SOCKETS = sys.stdin.fileno(), sys.stdout.fileno(), sys.stderr.fileno()

def redefine_sockets(stdin, stdout, stderr):
    sys.stdin = os.fdopen(stdin, 'r')
    sys.stdout = os.fdopen(stdout, 'w')
    sys.stderr = os.fdopen(stderr, 'w')
