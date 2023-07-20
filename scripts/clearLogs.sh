echo `tail -c 1000 cronJobRefresh.log` > cronJobRefresh.log
echo `tail -c 1000 ../my_logfile.log` > ../my_logfile.log 
echo `tail -c 1000 /var/log/cron.log` > /var/log/cron.log
echo `tail -c 1000 /var/log/gunicorn/access.log` > /var/log/gunicorn/access.log 
echo `tail -c 1000 /var/log/gunicorn/error.log` > /var/log/gunicorn/error.log
