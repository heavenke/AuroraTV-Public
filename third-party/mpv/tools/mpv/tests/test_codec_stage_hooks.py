"""Local codec-stage contracts. Fixtures and all generated outputs stay outside the source cache.

Run with --fixture-dir containing original-mediacodecdec.c and
original-mediacodecdec_common.c. --cc enables host tests (Linux cc, -pthread).
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import codec_stage_hooks as hooks

INPUTS = None
NAMES = ('mediacodecdec.c','mediacodecdec_common.c')

class StageContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if INPUTS is None: raise unittest.SkipTest('Supply read-only pre-stage fixture snapshots')
        cls.original = {n:(INPUTS.fixture_dir/('original-'+n)).read_text(encoding='utf-8') for n in NAMES}
        cls.patched = {n:hooks.patch_source(n,s) for n,s in cls.original.items()}

    def assert_rejected_without_either_write(self, sources):
        with tempfile.TemporaryDirectory(prefix='stage-negative-',dir=INPUTS.work_dir) as folder:
            root=Path(folder);(root/'libavcodec').mkdir()
            targets={n:root/'libavcodec'/n for n in NAMES}
            for n,p in targets.items():p.write_bytes(sources[n].encode('utf-8'))
            before={n:(p.read_bytes(),p.stat().st_mtime_ns) for n,p in targets.items()}
            with self.assertRaises(RuntimeError):hooks.apply_codec_stage_hooks(root)
            for n,p in targets.items():self.assertEqual((p.read_bytes(),p.stat().st_mtime_ns),before[n])

    def test_real_fixture_idempotence_and_exact_reversibility(self):
        for name in NAMES:
            s=self.patched[name]
            self.assertEqual(hooks.patch_source(name,s),s)
            for label,before,after in reversed(hooks._edits(name)):
                self.assertEqual(s.count(after),1,label)
                s=s.replace(after,before,1)
            self.assertEqual(s,self.original[name],'Original calls, return branches or cleanup changed')
        for name in NAMES:
            for call in ('ff_AMediaCodec_dequeueInputBuffer(', 'ff_AMediaCodec_dequeueOutputBuffer(',
                         'ff_AMediaCodec_queueInputBuffer('):
                self.assertEqual(self.original[name].count(call),self.patched[name].count(call))
        receive=self.patched['mediacodecdec.c']
        self.assertIn('int result = aurora_mediacodec_receive_frame_internal(avctx, frame);',receive)
        self.assertIn('return result;',receive)

    def test_apply_and_reapply_do_not_rewrite(self):
        with tempfile.TemporaryDirectory(prefix='stage-valid-',dir=INPUTS.work_dir) as folder:
            root=Path(folder);(root/'libavcodec').mkdir()
            for n in NAMES:(root/'libavcodec'/n).write_bytes(self.original[n].encode())
            self.assertTrue(hooks.apply_codec_stage_hooks(root))
            old={n:((root/'libavcodec'/n).read_bytes(),(root/'libavcodec'/n).stat().st_mtime_ns) for n in NAMES}
            self.assertFalse(hooks.apply_codec_stage_hooks(root))
            for n in NAMES:self.assertEqual(((root/'libavcodec'/n).read_bytes(),(root/'libavcodec'/n).stat().st_mtime_ns),old[n])

    def test_every_missing_duplicate_and_partial_anchor_is_no_write(self):
        for name in NAMES:
            for label,before,after in hooks._edits(name):
                self.assertEqual(self.original[name].count(before),1,label)
                for kind in ('missing','duplicate','partial'):
                    with self.subTest(file=name,anchor=label,kind=kind):
                        data=dict(self.original)
                        if kind=='partial':
                            data[name]=self.patched[name].replace(after,'/* incomplete stage patch */\n',1)
                        else:data[name]=data[name].replace(before,'/* lost anchor */\n' if kind=='missing' else before+before,1)
                        self.assert_rejected_without_either_write(data)

    def test_one_already_patched_file_does_not_mask_a_second_file_failure(self):
        for valid,bad in ((NAMES[0],NAMES[1]),(NAMES[1],NAMES[0])):
            data=dict(self.original);data[valid]=self.patched[valid]
            data[bad]=data[bad].replace(hooks._edits(bad)[0][1],'/* invalid second file */\n',1)
            self.assert_rejected_without_either_write(data)

    def test_host_single_calls_video_only_immutable_owner_and_blocking_visibility(self):
        if not INPUTS.cc:self.skipTest('Supply --cc for local host compilation')
        template=Path(__file__).with_name('codec_stage_host.c').read_text(encoding='utf-8')
        template=template.replace('/* AURORA_INCLUDE */','#include "'+str(Path(hooks.__file__).with_suffix('.inc'))+'"')
        labels={label:after for name in NAMES for label,_,after in hooks._edits(name)}
        for marker,label in [('OUTER_DEQUEUE','outer input dequeue'),('INNER_DEQUEUE','inner input dequeue'),
                             ('OUTPUT_DEQUEUE','output dequeue'),('QUEUE_EOS','EOS input queue'),('QUEUE_DATA','data input queue')]:
            template=template.replace('/* AURORA_'+marker+' */',labels[label])
        for suffix,defines in [('present',[]),('absent',['AURORA_TEST_NO_BEGIN','AURORA_TEST_NO_END']),
                               ('begin-only',['AURORA_TEST_NO_END']),('end-only',['AURORA_TEST_NO_BEGIN'])]:
            with self.subTest(observer=suffix), tempfile.TemporaryDirectory(prefix='stage-host-',dir=INPUTS.work_dir) as folder:
                root=Path(folder);(root/'libavutil').mkdir()
                (root/'libavutil/mathematics.h').write_text('#pragma once\nstatic inline int64_t av_rescale_q(int64_t n, AVRational a, AVRational b) { return n*a.num*b.den/(a.den*b.num); }\n')
                source=root/'host.c';source.write_text(template);binary=root/'host'
                args=[INPUTS.cc,'-std=c11','-Wall','-Wextra','-Werror','-pthread','-I'+str(root),
                      *('-D'+d for d in defines),str(source),'-o',str(binary)]
                if INPUTS.sanitize:args[1:1]=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
                compiled=subprocess.run(args,capture_output=True,text=True)
                self.assertEqual(compiled.returncode,0,compiled.stdout+compiled.stderr)
                run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=15)
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                print(suffix+': '+run.stdout.strip())

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-dir',required=True,type=Path)
    parser.add_argument('--work-dir',required=True,type=Path)
    parser.add_argument('--cc')
    parser.add_argument('--sanitize',action='store_true')
    INPUTS=parser.parse_args();INPUTS.work_dir.mkdir(parents=True,exist_ok=True)
    originals={n:(INPUTS.fixture_dir/('original-'+n)).read_bytes() for n in NAMES}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StageContracts))
    for n,before in originals.items():
        if (INPUTS.fixture_dir/('original-'+n)).read_bytes()!=before:raise AssertionError('Input fixture changed: '+n)
        print(n+' sha256='+hashlib.sha256(before).hexdigest())
    sys.exit(0 if result.wasSuccessful() else 1)
