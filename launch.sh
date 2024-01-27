#this is a script for pulling changes from git, installing all libs and restarting/launching the server
echo pulling from git
git pull origin
. venv/bin/activate
echo installing dependencies
sudo pip install -r requirements.txt
echo killing already running server
echo launching server
if test -e '/var/run/gunicorn.pid'
then
	echo restarting with hangup signal
	sudo cat /var/run/gunicorn.pid | xargs kill -HUP
else
	echo server was down, relaunching!
	sudo gunicorn -c config/gunicorn_config.py main:app
fi

if test -e '/var/run/gunicorn.pid'
then
	echo successfully launched!
else
	echo launch was unsucessful!
fi
