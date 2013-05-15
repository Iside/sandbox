# -*- coding: utf-8 -*-

import jinja2
import os

class TemplatesRepository(object):

    def __init__(self):
        self._jinja_env = jinja2.Environment(
            loader=jinja2.PackageLoader(__package__, "templates"),
            auto_reload=False
        )

    def render(self, service, name, **kwargs):
        tpl = self._jinja_env.get_template(os.path.join(service, name))
        return tpl.render(**kwargs)
