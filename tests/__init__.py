# -*- coding: utf-8 -*-

def run_all():
    import os, unittest2
    loader = unittest2.TestLoader()
    return loader.discover(os.path.dirname(__file__))
