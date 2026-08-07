from flask import Flask, request, render_template, jsonify
from database import Reed, ReedSession, start_engine, get_new_user
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

#creates a global database engine to create a sqlalchemy session in any app route or function
engine = start_engine()

logged_in = False
user_id = None

def log_in():
    global user_id
    global logged_in
    id_file = Path("user_id.txt")
    #writes to the user_id file if it does not exist, to obtain a user id for the database
    if id_file.exists():
        with open('user_id.txt', 'r') as file:
            user_id = file.readline()
    else:
        with Session(bind=engine) as session:
            new_id = get_new_user(session)
        with open('user_id.txt', 'w') as file:
            file.write(str(new_id))
        user_id = new_id
        logged_in = True


@app.route('/', methods=['GET', 'POST'])
def home():
    if not logged_in:
        log_in()
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
    with Session(bind=engine) as session:
        new_reed = Reed(id=reed_id, reed_type=reed_type, strength=reed_strength, user_id=user_id)
        session.add(new_reed)
        session.commit()
    return ' ', 204

@app.route('/save-session-data', methods=['POST'])
def save_session_data():
    data = request.get_json()
    reed_id = data.get('reed_id')
    rating = data.get('rating')
    minutes = int(data.get('minutes_played'))
    with Session(bind=engine) as session:
        #uses a select statement to get the reed with the correct id and user_id. .all() turns it into a list
        reed = (session.scalars(select(Reed).where(Reed.id == reed_id, Reed.user_id == user_id)).all())[0]
        new_session = ReedSession(date=datetime.now(), rating=rating, minutes=minutes, parent_id=reed_id, reed=reed)
        session.add(new_session)
        #updates non-property elements, like total minutes and step, that don't update on their own
        #step and minutes should only be changed when a session is submitted
        reed.update_daily_info()
        session.commit()
    return ' ', 204

@app.route('/delete-reed', methods=['POST'])
def delete_reed():
    with Session(bind=engine) as session:
        data = request.get_json()
        reed_id = data.get('reed')
        #uses a select statement to get the reed with the correct id and user_id. .all() turns it into a list
        reed = (session.scalars(select(Reed).where(Reed.id == reed_id, Reed.user_id == user_id)).all())[0]
        session.delete(reed)
        session.commit()
    return ' ', 204

@app.route('/get-rec-data', methods=["GET"])
def get_rec_data():
    with Session(bind=engine) as session:
        the_reeds = Reed.recommended_reeds(user_id, session)
        #turned to json_serializable because it can't parse an ORM object from sql_alchemy
        #returns a dictionary and turns the sessions into individual dictionaries to represent the objects
        json_serializable = Reed.to_json_serializable(the_reeds)
    return jsonify({"reeds": json_serializable})

@app.route('/get-breakin-data', methods=["GET"])
def get_breakin_data():
    with Session(bind=engine) as session:
        #turned to json_serializable because it can't parse an ORM object from sql_alchemy
        #returns a dictionary and turns the sessions into individual dictionaries to represent the objects
        breakin_reeds = Reed.rec_breakin_reeds(user_id, session)
        json_serializable = Reed.to_json_serializable(breakin_reeds)
    return jsonify({"reeds": json_serializable})

@app.route('/get-all-data', methods=["GET"])
def get_all_data():
    with Session(bind=engine) as session:
        #turned to json_serializable because it can't parse an ORM object from sql_alchemy
        #returns a dictionary and turns the sessions into individual dictionaries to represent the objects
        rec_reeds = Reed.to_json_serializable(Reed.recommended_reeds(user_id, session))
        breakin_reeds = Reed.to_json_serializable(Reed.rec_breakin_reeds(user_id, session))
        rec_reeds.extend(breakin_reeds)
    return jsonify({"reeds": rec_reeds})

#uses a URL parameter to pass the reed_id using GET, so the session can find it
@app.route('/get-reed/<reed_id>', methods=['GET'])
def get_reed(reed_id):
    with Session(bind=engine) as session:
        #uses a select statement to get the reed with the correct id and user_id. .all() turns it into a list
        reed = (session.scalars(select(Reed).where(Reed.id == reed_id, Reed.user_id == user_id)).all())[0]
        reed_json = Reed.to_json_serializable([reed])
    return jsonify({'reed': reed_json})

#prevents app running when the file is imported
if __name__ == '__main__':
    app.run()