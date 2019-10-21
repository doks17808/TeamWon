from flask import request, Flask, jsonify
from flask_cors import CORS
import psycopg2 as pg
from psycopg2 import Error
from datetime import datetime
import json 
from flask_mail import Message, Mail

app = Flask(__name__)


app.config.update(
	DEBUG=True,
	MAIL_SERVER='smtp.gmail.com',
	MAIL_PORT=465,
	MAIL_USE_SSL=True,
	MAIL_USERNAME = 'donotreply.daughertytransitions@gmail.com',
	MAIL_PASSWORD = 'teamwon1'
	)
mail = Mail(app)
CORS(app)

def connectPG():
    return pg.connect(user = 'postgres',
                    password = "password",
                    dbname = "teamwon",
                    host = 'teamwon.ci1fgenlh3ew.us-east-1.rds.amazonaws.com',
                    port = '5432',
                    connect_timeout = 1)

@app.route('/cklist', methods = ["POST"])
def dbentry():
    connection = connectPG()
    cursor = connection.cursor()

    #Inserting into Checklist Table
    isOnboarding = request.json['isOnboarding']
    company = request.json['company']
    try:
        name = request.json['name']
    except: name = "Un-named"


    checklist_query = f"INSERT INTO checklist (isonboarding, company, name)\
        VALUES ('{isOnboarding}', '{company}', '{name}') RETURNING cid"
    cursor.execute(checklist_query)
    cid = cursor.fetchone()[0]
    connection.commit()


    #Inserting into Consultant Table
    email = request.json['email']
    name = email.split('.')
    name_2 = name[1].split("@")
    first_name = name[0].capitalize()
    last_name = name_2[0].capitalize()

    consultant_query = f"INSERT INTO consultant (first_name, last_name, email)\
        VALUES ('{first_name}', '{last_name}', '{email}') RETURNING coid"
    cursor.execute(consultant_query)
    coid = cursor.fetchone()[0]
    connection.commit()

    #Inserting into Task Table and status table
    Task = request.json['tasks']
    tidList = []
    date = datetime.now()
    for x in range(len(Task)):
        description = Task[x]['description']
        reminder = Task[x]['reminder']
        
        taskquery = f"INSERT INTO task (description,reminder) VALUES ('{description}', '{reminder}') RETURNING tid"
        cursor.execute(taskquery)
        tid = cursor.fetchone()[0]
        tidList.append({"tid":tid, "description":description})
        joinquery = f"INSERT INTO c_t (cid, tid) VALUES ({cid},{tid})"
        progressquery = f"INSERT INTO progress (cid, coid, tid, date) VALUES ({cid}, {coid}, {tid}, '{date}')"
        cursor.execute(joinquery)
        cursor.execute(progressquery)
        connection.commit()
    cursor.close()
    connection.close()


## Sending the email with link to mark as complete
    if isOnboarding == True:
        transition = 'Onboarding'
    else: 
        transition = 'Offboarding'

    name = email.split('.')
    name_2 = name[1].split("@")
    first_name = name[0].capitalize()
    last_name = name_2[0].capitalize()

    task_string = ""
    for index in range(len(tidList)):
        task_string += f"<br>-{tidList[index]['description']} <a href='http://127.0.0.1:5000/progress/{cid}/{coid}/{tidList[index]['tid']}'>Click Here to Mark As Complete</a>"
    print(task_string)

    try:
        msg = Message(f"{company} {transition} Checklist for {first_name} {last_name}", sender="donotreply.daughertytransitions@gmail.com", recipients=[f"{email}"])
        msg.html = f"<h2>{company} {transition} Checklist for {first_name} {last_name}</h2>{task_string}"
        mail.send(msg)
        return json.dumps({"Status Code":200})
    except:
        return("error") 



@app.route('/progress/<int:cid>/<int:coid>/<int:tid>', methods = ["GET"])
def progressUpdate(cid, coid, tid):
    connection = connectPG()
    cursor = connection.cursor()
    update = f"UPDATE progress SET iscomplete = true WHERE cid = {cid} and coid = {coid} and tid = {tid}"
    cursor.execute(update)
    connection.commit()
    return json.dumps({"Status Code 200": "Task has been marked complete"})




@app.route('/details/<int:cid>/<int:coid>', methods = ["GET"])
def details(cid, coid):
    connection = connectPG()
    cursor = connection.cursor()
    detailquery = f"SELECT first_name, last_name, company, isonboarding, date, description, iscomplete\
        from progress p\
        join task t on p.tid = t.tid\
        join checklist c on c.cid = p.cid\
        join consultant co on co.coid = p.coid\
        where p.cid = {cid} and p.coid = {coid}"
    cursor.execute(detailquery)
    record = cursor.fetchall()
    colnames = ['first_name','last_name','company','isOnboarding','date','description','isComplete']
    results = []
    for row in record:
            results.append(dict(zip(colnames, row)))
    cursor.close()
    connection.close()
    return jsonify(results)

@app.route('/home', methods = ["GET"])
def home():
    connection = connectPG()
    cursor = connection.cursor()
    query = "SELECT consultant.coid as consultant_id, concat(first_name, ' ', last_name) Consultant, progress.cid, checklist.company as Client, checklist.isOnboarding as Transition, progress.date as DateSent, COUNT(CASE WHEN isComplete THEN 1 END) * 100 / count(progress.tid) AS progress \
                FROM consultant \
                    JOIN progress ON progress.coid = consultant.coid \
                    JOIN checklist ON checklist.cid = progress.cid \
                    GROUP BY consultant_id, Consultant, progress.cid, Client, Transition, DateSent \
                    order by consultant, consultant_id"
    cursor.execute(query)
    records = cursor.fetchall()
    colnames = ['coid','consultant','cid','company','isOnboarding','date','progress']

    results = []
    for row in records:
            results.append(dict(zip(colnames, row)))
    if(connection):
            cursor.close()
            connection.close()
    try:
        return jsonify(results)
    except:
        return jsonify(0)


if __name__ == "__main__":

    app.run(debug=True)