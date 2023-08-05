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
	echo successfully launched after refresh!
else
	echo launch was unsucessful after refresh!
fi
