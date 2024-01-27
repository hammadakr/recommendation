#this is a script for launching server automatically through supervisor
. venv/bin/activate
if test -e '/var/run/gunicorn.pid'
then
	echo restarting with hangup signal
	cat /var/run/gunicorn.pid | xargs kill -HUP
else
	echo server was down, relaunching!
	gunicorn -c config/gunicorn_config.py main:app
fi

if test -e '/var/run/gunicorn.pid'
then
	echo successfully launched!
else
	echo launch was unsucessful!
fi
exit 0
