from flask import Flask ,render_template , request, Blueprint
from flask_cors import CORS
from recommendations import recApp

app = Flask(__name__)
app.register_blueprint(recApp)
CORS(app)

#To run: flask --app main.py --debug run 
if __name__ == "__main__":
    app.run()
