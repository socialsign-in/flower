from __future__ import absolute_import

import sys
import copy
import logging

try:
    from itertools import imap
except ImportError:
    imap = map

from tornado import web

from ..views import BaseHandler
from ..utils.tasks import iter_tasks, get_task_by_id, as_dict


from redis import Redis 
from django.conf import settings
import simplejson


logger = logging.getLogger(__name__)

class FailObject():

    def __init__(self,task): 
        for k in [
            'uuid',
            'name',
            'args',
            'kwargs',
            'state',
            'exception',
            'timestamp',
            'worker',
          ]:
            setattr(self,k,None)
    
 
        for k,v in task.iteritems():
            setattr(self,k,v)

class FailuresView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        capp = self.application.capp

        time = 'natural-time' if app.options.natural_time else 'time'
        if capp.conf.CELERY_TIMEZONE:
            time += '-' + capp.conf.CELERY_TIMEZONE

        
        redis = Redis()
        conn = Redis(settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_GLOBAL_DB)
        all_fails = conn.zrevrange('task-fails-alltasks',0,-1)
        tasks = []
        for fail_json in all_fails:
            dt = simplejson.loads(fail_json)
            desc = dt['desc']
            task = {
                'name': dt['name'],
                'uuid': dt['task_id'],
                'state': 'FAILURE',
                'exception': desc['exception'],
                'kwargs': desc['kwargs'],
                'args': desc['args'],
                'retries': desc['retries'],
            }
            tasks.append((dt['task_id'],FailObject(task)))
        
        logger.debug(tasks)

        self.render(
            "failures.html",
            failures=tasks,
            columns=[],
            time=time,
        )





