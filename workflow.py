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

    email = request.json['email']
    isOnboarding = request.json['isOnboarding']
    date = datetime.now()
    company = request.json['company']

    ckquery = f"INSERT INTO checklist (email, isonboarding, company, date)\
        VALUES ('{email}', '{isOnboarding}', '{company}', '{date}') RETURNING cid"
    cursor.execute(ckquery)
    cid = cursor.fetchone()[0]
    connection.commit()
    # return_checklist = {
    #     "cid":cid, 
    #     "email":request.json['email'],
    #     "isOnboarding":request.json['isOnboarding'],
    #     "company":request.json['company'],
    #     "date": date
    #     }


    Task = request.json['tasks']
    tidList = []
    for x in range(len(Task)):
        description = Task[x]['description']
        reminder = Task[x]['reminder']
        
        taskquery = f"INSERT INTO task (description,reminder) VALUES ('{description}', '{reminder}') RETURNING tid"
        cursor.execute(taskquery)
        tid = cursor.fetchone()[0]
        #tidList.append({"tid":tid, "description":Task[x]['description'], "reminder":Task[x]['reminder']})
        tidList.append({"tid":tid, "description":description})
        joinquery = f"INSERT INTO c_t (cid, tid) VALUES ({cid},{tid})"
        cursor.execute(joinquery)
        connection.commit()
    #return_checklist['tasks'] = tidList
    cursor.close()
    connection.close()
    # print(return_checklist)
    # return jsonify(return_checklist)


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
        task_string += f"<br>-{tidList[index]['description']} <a href='http://127.0.0.1:5000/progress/{tidList[index]['tid']}'>Mark As Complete</a>"
    print(task_string)

    try:
        msg = Message(f"{company} {transition} Checklist for {first_name} {last_name}", sender="donotreply.daughertytransitions@gmail.com", recipients=[f"{email}"])
        msg.html = f"<h2>{company} {transition} Checklist for {first_name} {last_name}</h2>{task_string}"
        mail.send(msg)
        return json.dumps({"Status Code":200})
    except:
        return("error") 

@app.route('/progress/<int:tid>', methods = ["GET"])
def progressUpdate(tid):
    connection = connectPG()
    cursor = connection.cursor()
    update = f"UPDATE task SET iscomplete = true WHERE tid = {tid}"
    cursor.execute(update)
    connection.commit()

    
    return "Task has been marked complete"



if __name__ == "__main__":

    app.run(debug=True)