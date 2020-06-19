web: gunicorn gridgaming.wsgi --workers 4
worker: python manage.py rqworker high low default --worker-class rq.SimpleWorker


# DONT USE PRELOAD
#web: gunicorn gridgaming.wsgi --preload --workers 3
#worker: python manage.py rqworker high low default --with-scheduler
#worker: python run-worker.py


#worker: python manage.py rqworker high low default --with-scheduler

#worker: python manage.py rqworker high low default --worker-class rq.SimpleWorker
#worker: python manage.py rqworker high low default --worker-class rq.HerokuWorker
