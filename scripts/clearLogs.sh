truncate -s 5M cronJobRefresh.log
truncate -s 5M ../my_logfile.log 
truncate -s 5M /var/log/cron.log
truncate -s 5M /var/log/gunicorn/access.log
truncate -s 5M /var/log/gunicorn/error.log
truncate -s 5M /var/log/httpbot.log
