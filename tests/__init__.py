# -*- coding: utf-8 -*-

def run_all():
    import os, unittest
    loader = unittest.TestLoader()
    return loader.discover(os.path.dirname(__file__))
