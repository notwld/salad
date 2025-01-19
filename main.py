from flask import Flask, render_template

app = Flask(__name__)
@app.route('/')
def file_explorer():
    return render_template('index.html')

# curl -o agent.py https://raw.githubusercontent.com/yourusername/yourrepo/main/agent.py
#
if __name__ == '__main__':
    app.run(debug=True, port=5001)