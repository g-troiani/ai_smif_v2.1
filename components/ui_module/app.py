# components/ui_module/app.py
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_socketio import SocketIO

app = Flask(__name__)
app.config.from_object('config')
Bootstrap(app)
socketio = SocketIO(app)

from routes import *

if __name__ == '__main__':
    socketio.run(app, debug=True)
