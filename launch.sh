echo pulling from git
git pull origin
#rm -r venv
#python3 -m venv venv
. venv/bin/activate
echo installing dependencies
pip install -r requirements.txt
echo killing already running server
pkill gunicorn
echo launching server
gunicorn --bind 127.0.0.1:5000 --daemon main:app
echo successfully launched!
