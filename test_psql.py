from recommendations import app
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import pandas as pd



app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:your_password@localhost/template1'
db = SQLAlchemy(app)
with app.app_context():
    engine = db.engine




query = "SELECT * FROM popular_cities"
df = pd.read_sql_query(query, engine)
@app.route('/data', methods=['GET'])
def get_data():
    with app.app_context():
        # Use pd.read_sql instead of pd.read_sql_query
        query = "SELECT * FROM popular_cities"
        df = pd.read_sql(query, engine)

    # Convert DataFrame to JSON
    data_json = df.to_json(orient='records')

    # Parse JSON string to a Python dictionary
    data_dict = pd.read_json(data_json, orient='records')

    # Return the JSON response
    return jsonify(data_dict.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True)
