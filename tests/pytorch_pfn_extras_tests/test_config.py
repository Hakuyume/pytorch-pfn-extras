import json
import os
import tempfile
import unittest

from pytorch_pfn_extras.config import Config
from pytorch_pfn_extras.config import customize_type


def func_0(a, b, c=10):
    return a + b + c


@customize_type(c='/foo/v0')
def func_1(a, b, c):
    return {'d': a * b, 'e': c}


@customize_type(config='!/')
def func_2(config):
    return json.dumps(config)


class Cls0(object):

    def __init__(self, a, b, c=10):
        self.a = a
        self.b = b
        self.c = c

    def __eq__(self, other):
        return (self.a, self.b, self.c) == (other.a, other.b, other.c)


@customize_type(c='../../foo/v0')
class Cls1(object):

    def __init__(self, a, b, c):
        self.d = a * b
        self.e = c

    def __eq__(self, other):
        return (self.d, self.e) == (other.d, other.e)


class TestConfig(unittest.TestCase):

    types = {
        'func_0': func_0,
        'func_1': func_1,
        'func_2': func_2,
        'cls_0': Cls0,
        'cls_1': Cls1,
    }

    def test_config(self):
        config = Config({
            'foo': {
                'v0': {'type': 'func_0', 'a': 1, 'b': 2},
                'v1': {'type': 'func_0', 'a': 1, 'b': 2, 'c': 3},
                'v2': {'type': 'func_1', 'a': 1, 'b': 2},
                'v3': {'type': 'func_1', 'a': 1, 'b': 2, 'c': 3},
            },
            'bar': [
                {'type': 'cls_0', 'a': 1, 'b': 2},
                {'type': 'cls_0', 'a': 1, 'b': 2, 'c': 3},
                {'type': 'cls_1', 'a': 1, 'b': 2},
                {'type': 'cls_1', 'a': 1, 'b': 2, 'c': 3},
            ],
            'baz': {
                'v0': '@/foo/v2.d',
                'v1': '@../bar/1/c',
                'v2': '@/bar/3.d',
                'v3': '@../foo/v3',
            }
        }, self.types)

        self.assertEqual(config['/'], {
            'foo': {
                'v0': 13,
                'v1': 6,
                'v2': {'d': 2, 'e': 13},
                'v3': {'d': 2, 'e': 3},
            },
            'bar': [
                Cls0(1, 2, 10),
                Cls0(1, 2, 3),
                Cls1(1, 2, 13),
                Cls1(1, 2, 3),
            ],
            'baz': {
                'v0': 2,
                'v1': 3,
                'v2': 2,
                'v3': {'d': 2, 'e': 3},
            },
        })

    def test_config_escape(self):
        pre_eval_config = {
            'foo': {
                'v0': {'type': 'func_0', 'a': 1, 'b': 2},
            },
            'bar': {'type': 'func_2'},
        }
        config = Config(pre_eval_config, self.types)

        self.assertEqual(config['!/foo'], {
            'v0': {'type': 'func_0', 'a': 1, 'b': 2},
        })
        self.assertEqual(json.loads(config['/bar']), pre_eval_config)

    def test_config_load_path(self):
        with tempfile.TemporaryDirectory() as temp0, \
             tempfile.TemporaryDirectory() as temp1:
            with open(os.path.join(temp0, 'foo.json'), mode='w') as f:
                json.dump({
                    'foo': {'v0': {'type': 'func_0', 'a': 1, 'b': 2}},
                    'bar': {'import': os.path.join(temp1, 'bar.json')},
                    'baz': {
                        'import': 'baz.json',
                        '0/b': 3,
                        '1/d': [1, 2],
                    },
                }, f)
            with open(os.path.join(temp1, 'bar.json'), mode='w') as f:
                json.dump({'type': 'func_0', 'a': 3, 'b': 4}, f)
            with open(os.path.join(temp0, 'baz.json'), mode='w') as f:
                json.dump([
                    {'type': 'func_1', 'a': 1, 'b': 2},
                    {'d': 3, 'e': 4},
                ], f)

            config = Config.load_path(
                os.path.join(temp0, 'foo.json'), types=self.types)

        self.assertEqual(config['!/foo'],
                         {'v0': {'type': 'func_0', 'a': 1, 'b': 2}})
        self.assertEqual(config['/foo'], {'v0': 13})
        self.assertEqual(config['!/bar'], {'type': 'func_0', 'a': 3, 'b': 4})
        self.assertEqual(config['/bar'], 17)
        self.assertEqual(config['!/baz'], [
            {'type': 'func_1', 'a': 1, 'b': 3},
            {'d': [1, 2], 'e': 4},
        ])
        self.assertEqual(config['/baz'], [
            {'d': 3, 'e': 13},
            {'d': [1, 2], 'e': 4},
        ])

    def test_config_with_circular_dependency(self):
        config = Config({'foo': '@/bar', 'bar': '@foo.d'})
        with self.assertRaises(RuntimeError):
            config['/']

    def test_config_with_circular_import(self):
        with tempfile.TemporaryDirectory() as temp:
            with open(os.path.join(temp, 'foo.json'), mode='w') as f:
                json.dump({'import': 'bar.json'}, f)
            with open(os.path.join(temp, 'bar.json'), mode='w') as f:
                json.dump([{'import': './foo.json'}], f)

            with self.assertRaises(RuntimeError):
                Config.load_path(os.path.join(temp, 'foo.json'))
