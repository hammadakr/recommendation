echo pulling from git
git pull origin
#rm -r venv
#python3 -m venv venv
. venv/bin/activate
echo installing dependencies
pip install -r requirements.txt
echo killing already running server
echo launching server
cat /var/run/gunicorn.pid | xargs kill -HUP
# gunicorn --bind 127.0.0.1:5000 --daemon main:app
# gunicorn -c config/gunicorn_config.py main:app
echo successfully launched!
