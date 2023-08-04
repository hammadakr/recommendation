echo pulling from git
git pull origin
#rm -r venv
#python3 -m venv venv
. venv/bin/activate
echo installing dependencies
pip install -r requirements.txt
echo killing already running server
echo launching server
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
