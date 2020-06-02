
from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import time
import serial


ser = serial.Serial('/dev/ttyACM0')
ser.flushInput()

async_mode = None

app = Flask(__name__)


app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 


def background_thread(args):
    count = 0
    argument = 0
    dataCounter = 0 
    dataList = []
    fo = open("test.txt","a+")
    
    while True:
        startstop1 = dict(args).get('startstop')
        openclose1 = dict(args).get('openclose')
        
        if openclose1 == "open" and not ser.is_open:
            ser.open()
        elif openclose1 == "close" and ser.is_open:
            ser.close()
            continue
        elif not ser.is_open:
            socketio.sleep(5)
            socketio.emit('my_response',
                          {'data': 0,'data2': 0,'count': 0},
                          namespace='/test')
            continue
        
            

        ser_bytes = ser.readline()
        decoded_bytes = ser_bytes.decode("utf-8")  
        x = decoded_bytes.split(",")
        zoznam = [float(y) for y in decoded_bytes.split(',')]
        print(zoznam[0])
        print(zoznam[1])

        socketio.sleep(5)
        count += 1
        

        if(startstop1 == 'start'):
            
            dataDict = {
            "t": time.time(),
            "x": argument,
            "vlhkost": float(zoznam[1]),
            "teplota": float(zoznam[0])}
            dataList.append(dataDict)
            
            
            socketio.emit('my_response',
                          {'data': float(zoznam[1]),'data2': float(zoznam[0]),'count': count},
                          namespace='/test')
        else:
            socketio.emit('my_response',
                          {'data': 0,'data2': 0,'count': 0},
                          namespace='/test')
            if len(dataList)>0:
                print (str(dataList))
                fuj = str(dataList).replace("'", "\"")
                print fuj
                str2 = "\r\n"
                str1 = str(fuj)
                str3 = str1 + str2
                fo = open("test.txt","a+")
                fo.write(str3)
                fo.close
            dataList = []
            dataCounter = 0
        argument = argument+5
            
            

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)
  
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    emit('my_response',
         {'data': 0, 'data2': 0,'count': session['receive_count']})

@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html', async_mode=socketio.async_mode)  


@app.route('/read/<string:num>')
def readmyfile(num):
    fo = open("test.txt","r")
    rows = fo.readlines()
    return rows[int(num)-1]


@socketio.on('db_event', namespace='/test')
def db_message(message):   

    print(message)
    session['startstop'] = message['value']
   

@socketio.on('openclose_event', namespace='/test')
def db_message(message):   

    print(message)
    session['openclose'] = message['value']



@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    emit('my_response', {'data': 'Connected','data2': 0, 'count': 0})

@app.route('/gauge', methods=['GET', 'POST'])
def gauge():
    return render_template('gauge.html', async_mode=socketio.async_mode)

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


@app.route('/graphlive', methods=['GET', 'POST'])
def graphlive():
    return render_template('graphlive.html', async_mode=socketio.async_mode)



if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)