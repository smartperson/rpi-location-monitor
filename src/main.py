from flask import Flask
import threading
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

def server():
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    serverThread = threading.Thread(target=server)
    serverThread.start()
