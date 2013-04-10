# -*- coding: utf-8 -*-
# Started by François-Xavier Bourlet <fx@dotcloud.com>, Oct 2011.

import unittest2

from udotcloud.sandbox.buildfile import load_build_file, SchemaError

class TestBuildFile(unittest2.TestCase):


    def test_simple(self):
        build_file = '''
www:
    type: python
    instances: 1
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': '.',
            'config': {},
            'environment': {},
            'instances': 1,
            'postinstall': '',
            'requirements': [],
            'type': 'python'}})


    def test_empty(self):
        build_file = '''
    '''
        with self.assertRaises(ValueError):
            load_build_file(build_file)


    def test_empty2(self):
        build_file = '''
{}
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'service(s) dict cannot be empty in "dotcloud.yml", line 2, column 1')
                raise


    def test_empty_service(self):
        build_file = '''
www: {}
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Missing mandatory entry: "type" in "dotcloud.yml", line 2, column 6')
                raise


    def test_top_error(self):
        build_file = '''
www
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Expected a type dictionary but got a type string in "dotcloud.yml", line 2, column 1')
                raise


    def test_top_error2(self):
        build_file = '''
- www
- lolita
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Expected a type dictionary but got a type list in "dotcloud.yml", line 2, column 1')
                raise


    def test_more(self):
        build_file = '''
www:
    type: python
    approot: 42
    environment:
        caca: lol
    customshit:
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': '42',
            'config': {},
            'customshit': None,
            'environment': {'caca': 'lol'},
            'instances': 1,
            'postinstall': '',
            'requirements': [],
            'type': 'python'}})


    def test_even_more(self):
        build_file = '''
www:
    type: python
    approot: 42
    environment:
        caca: lol
    customshit:
db:
    type: python
    environment:
       MYVAR: "my lovely var"
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'db': {'approot': '.',
            'config': {},
            'environment': {'MYVAR': 'my lovely var'},
            'instances': 1,
            'postinstall': '',
            'requirements': [],
            'type': 'python'},
            'www': {'approot': '42',
                'config': {},
                'customshit': None,
                'environment': {'caca': 'lol'},
                'instances': 1,
                'postinstall': '',
                'requirements': [],
                'type': 'python'}})


    def test_type_error(self):
        build_file = '''
www:
    type: lolita
    instances: 1
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Unrecognized service "lolita" in "dotcloud.yml", line 3, column 11')
                raise


    def test_process_and_processes(self):
        build_file = '''
www:
    type: python
    process: string
    processes:
        a: 1
        b: 2
'''
        with self.assertRaises(ValueError):
            try:
                load_build_file(build_file)
            except ValueError as e:
                self.assertEqual(str(e), 'You can\'t have both "process" and "processes" at the same time in service "www"')
                raise

    def test_custom_build_simple(self):
        build_file = '''
www:
    type: custom
    approot: ./web
    buildscript: builder
    process: ~/myapp.py
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': './web',
            'buildscript': 'builder',
            'config': {},
            'environment': {},
            'instances': 1,
            'postinstall': '',
            'process': '~/myapp.py',
            'requirements': [],
            'type': 'custom'}})


    def test_custom_build_port(self):
        build_file = '''
worker:
    type: custom
    buildscript: builder
    process: ~/myapp.py
    ports:
        www: http
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'worker': {'approot': '.',
                'buildscript': 'builder',
                'config': {},
                'environment': {},
                'instances': 1,
                'ports': {'www': 'http'},
                'postinstall': '',
                'process': '~/myapp.py',
                'requirements': [],
                'type': 'custom'}})


    def test_custom_invalid_build_port(self):
        build_file = '''
worker:
    type: custom
    buildscript: builder
    process: ~/myapp.py
    ports:
        www: prout
'''
        with self.assertRaises(SchemaError):
            try:
                load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Unrecognized port "prout" in "dotcloud.yml", line 7, column 14')
                raise


    def test_custom_build_port_empty(self):
        build_file = '''
worker:
    type: custom
    buildscript: builder
    process: ~/myapp.py
    ports: {}
'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'worker': {'approot': '.',
            'buildscript': 'builder',
            'config': {},
            'environment': {},
            'instances': 1,
            'ports': {},
            'postinstall': '',
            'process': '~/myapp.py',
            'requirements': [],
            'type': 'custom'}})


    def test_custom_build_complexe(self):
        build_file = '''
www:
    type: custom
    approot: ./web
    ports:
        www: http
        control: tcp
        collectd: tcp
    ruby_version: 1.9

'''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'www': {'approot': './web',
            'config': {},
            'environment': {},
            'instances': 1,
            'ports': {
                'www': 'http',
                'control': 'tcp',
                'collectd': 'tcp',
                },
            'postinstall': '',
            'requirements': [],
            'ruby_version': '1.9',
            'type': 'custom'}})


    def test_service_name_validation(self):
        build_file = '''
    2:
        type: python
    '''
        desc = load_build_file(build_file)
        self.assertDictEqual(desc, {'2': {'approot': '.',
            'config': {},
            'environment': {},
            'instances': 1,
            'postinstall': '',
            'requirements': [],
            'type': 'python'}})

        build_file = '''
www:sdf:
    type: python
'''
        with self.assertRaises(SchemaError):
            try:
                desc = load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Invalid characters (lowercase alphanum only) for service "www:sdf" in "dotcloud.yml", line 3, column 5')
                raise

        build_file = '''
123456789abceswseefsdfsdf:
    type: python
'''
        with self.assertRaises(SchemaError):
            try:
                desc = load_build_file(build_file)
            except SchemaError as e:
                self.assertEqual(str(e), 'Invalid service name (must be <= 16 characters) "123456789abceswseefsdfsdf" in "dotcloud.yml", line 3, column 5')
                raise
