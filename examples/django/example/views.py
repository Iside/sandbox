import os

from django.http import HttpResponse
from django.views.generic import View

class HomeView(View):
    
    def get(self, request, *args, **kwargs):
        return HttpResponse("</br>\n".join([
            "{0}={1}".format(k, v) for k, v in os.environ.iteritems()
        ]))
