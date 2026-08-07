from flask import Flask, request, render_template, jsonify, session
from database import Reed, ReedSession, start_engine
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import secrets
import os

app = Flask(__name__)
#gets secret key for changing user data, otherwise uses the local key for development
app.secret_key = os.environ.get("SECRET_KEY", "local_dev_key")
#creates a global database engine to create a sqlalchemy session in any app route or function
engine = start_engine()

logged_in = False
user_id = None

def get_user_id():
    if not app.secret_key == "local_dev_key":
        if "user_id" not in session:
            #generates a user_id
            session["user_id"] = secrets.token_hex(16)
        return session["user_id"]
    return "dev_key"


@app.route('/', methods=['GET', 'POST'])
def home():
    global logged_in
    global user_id
    if not logged_in:
        user_id = get_user_id()
        logged_in = True
    return render_template('home.html')

@app.route('/save-reed-data', methods=['POST'])
def save_reed_data():
    #data is sent from javascript through json, so get_json is needed to parse
    data = request.get_json()
    reed_id = data.get('reed_id')
    reed_type = data.get('reed_type')
    #float type already verified in js file, no need to catch or use try/except
    reed_strength = float(data.get('reed_strength'))

    #activates a session and commits the changes to update the database
    with Session(bind=engine) as db_session:
        new_reed = Reed(id=reed_id, reed_type=reed_type, strength=reed_strength, user_id=user_id)
        db_session.add(new_reed)
        db_session.commit()
    return ' ', 204

@app.route('/save-session-data', methods=['POST'])
def save_session_data():
    data = request.get_json()
    reed_id = data.get('reed_id')
    rating = data.get('rating')
    minutes = int(data.get('minutes_played'))
    with Session(bind=engine) as db_session:
        #uses a select statement to get the reed with the correct id and user_id. .all() turns it into a list
        reed = (db_session.scalars(select(Reed).where(Reed.id == reed_id, Reed.user_id == user_id)).all())[0]
        new_session = ReedSession(date=datetime.now(), rating=rating, minutes=minutes, parent_id=reed_id, reed=reed)
        db_session.add(new_session)
        #updates non-property elements, like total minutes and step, that don't update on their own
        #step and minutes should only be changed when a session is submitted
        reed.update_daily_info()
        db_session.commit()
    return ' ', 204

@app.route('/delete-reed', methods=['POST'])
def delete_reed():
    with Session(bind=engine) as db_session:
        data = request.get_json()
        reed_id = data.get('reed')
        #uses a select statement to get the reed with the correct id and user_id. .all() turns it into a list
        reed = (db_session.scalars(select(Reed).where(Reed.id == reed_id, Reed.user_id == user_id)).all())[0]
        db_session.delete(reed)
        db_session.commit()
    return ' ', 204

@app.route('/get-rec-data', methods=["GET"])
def get_rec_data():
    with Session(bind=engine) as db_session:
        the_reeds = Reed.recommended_reeds(user_id, db_session)
        #turned to json_serializable because it can't parse an ORM object from sql_alchemy
        #returns a dictionary and turns the sessions into individual dictionaries to represent the objects
        json_serializable = Reed.to_json_serializable(the_reeds)
    return jsonify({"reeds": json_serializable})

@app.route('/get-breakin-data', methods=["GET"])
def get_breakin_data():
    with Session(bind=engine) as db_session:
        #turned to json_serializable because it can't parse an ORM object from sql_alchemy
        #returns a dictionary and turns the sessions into individual dictionaries to represent the objects
        breakin_reeds = Reed.rec_breakin_reeds(user_id, db_session)
        json_serializable = Reed.to_json_serializable(breakin_reeds)
    return jsonify({"reeds": json_serializable})

@app.route('/get-all-data', methods=["GET"])
def get_all_data():
    with Session(bind=engine) as db_session:
        #turned to json_serializable because it can't parse an ORM object from sql_alchemy
        #returns a dictionary and turns the sessions into individual dictionaries to represent the objects
        rec_reeds = Reed.to_json_serializable(Reed.recommended_reeds(user_id, db_session))
        breakin_reeds = Reed.to_json_serializable(Reed.rec_breakin_reeds(user_id, db_session))
        rec_reeds.extend(breakin_reeds)
    return jsonify({"reeds": rec_reeds})

#uses a URL parameter to pass the reed_id using GET, so the session can find it
@app.route('/get-reed/<reed_id>', methods=['GET'])
def get_reed(reed_id):
    with Session(bind=engine) as db_session:
        #uses a select statement to get the reed with the correct id and user_id. .all() turns it into a list
        reed = (db_session.scalars(select(Reed).where(Reed.id == reed_id, Reed.user_id == user_id)).all())[0]
        reed_json = Reed.to_json_serializable([reed])
    return jsonify({'reed': reed_json})

#prevents app running when the file is imported
if __name__ == '__main__':
    app.run()