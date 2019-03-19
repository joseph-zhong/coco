#!/usr/bin/env python

# Python wrapper for METEOR implementation, by Xinlei Chen
# Acknowledge Michael Denkowski for the generous discussion and help 

import os
import sys
import subprocess
import threading

from tqdm import tqdm

import src.utils.utility as _util

# Assumes meteor-1.5.jar is in the same directory as meteor.py.  Change as needed.
METEOR_JAR = 'meteor-1.5.jar'
# print METEOR_JAR

class Meteor:

    def __init__(self):
        self.meteor_cmd = ['java', '-jar', '-Xmx2G', METEOR_JAR, \
                '-', '-', '-stdio', '-l', 'en', '-norm']
        jar_dir = os.path.join(_util.get_workspace(), "extern", "coco_caption", "pycocoevalcap", "meteor")
        assert os.path.exists(os.path.join(jar_dir, METEOR_JAR)), \
            "jar not found {}".format(os.path.join(jar_dir, METEOR_JAR))
        self.meteor_p = subprocess.Popen(self.meteor_cmd, \
                cwd=jar_dir, \
                stdin=subprocess.PIPE, \
                stdout=subprocess.PIPE, \
                stderr=subprocess.PIPE)
        # Used to guarantee thread safety
        self.lock = threading.Lock()

    def compute_score(self, gts, res):
        assert(gts.keys() == res.keys())
        imgIds = gts.keys()
        scores = []

        eval_line = b'EVAL'
        self.lock.acquire()
        for i in imgIds:
            assert(len(res[i]) == 1)
            stat = self._stat(res[i][0], gts[i])
            eval_line += bytes(' ||| {}'.format(stat), encoding="ascii")

        self.meteor_p.stdin.write(bytes('{}\n'.format(eval_line), encoding="ascii"))
        for i in range(0,len(imgIds)):
            scores.append(float(self.meteor_p.stdout.readline().strip()))
        score = float(self.meteor_p.stdout.readline().strip())
        self.lock.release()
        self.meteor_p.kill()

        return score, scores

    def method(self):
        return "METEOR"

    def _stat(self, hypothesis_str, reference_list):
        # SCORE ||| reference 1 words ||| reference n words ||| hypothesis words
        hypothesis_str = hypothesis_str.replace(b'|||',b'').replace(b'  ',  b' ')
        score_line = b' ||| '.join((b'SCORE', b' ||| '.join(reference_list), hypothesis_str))
        with open("/tmp/fuck", "w") as f:
            # self.meteor_p.stdin.write(score_line + b'\n')
            f.write(score_line + b'\n')
        return self.meteor_p.stdout.readline().strip()

    def _score(self, hypothesis_str, reference_list):
        self.lock.acquire()
        # SCORE ||| reference 1 words ||| reference n words ||| hypothesis words
        hypothesis_str = hypothesis_str.replace(b'|||',b'').replace(b'  ',b' ')
        score_line = b' ||| '.join((b'SCORE', b' ||| '.join(reference_list), hypothesis_str))
        self.meteor_p.stdin.write('{}\n'.format(score_line.decode("utf-8")))
        stats = self.meteor_p.stdout.readline().strip()
        eval_line = bytes('EVAL ||| {}'.format(stats), encoding="ascii")
        # EVAL ||| stats 
        self.meteor_p.stdin.write('{}\n'.format(eval_line.decode("utf-8")))
        score = float(self.meteor_p.stdout.readline().strip())
        # bug fix: there are two values returned by the jar file, one average, and one all, so do it twice
        # thanks for Andrej for pointing this out
        score = float(self.meteor_p.stdout.readline().strip())
        self.lock.release()
        return score
 
    def __del__(self):
        self.lock.acquire()
        self.meteor_p.stdin.close()
        self.meteor_p.kill()
        self.meteor_p.wait()
        self.lock.release()
