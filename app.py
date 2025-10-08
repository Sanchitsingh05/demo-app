from flask import Flask
app = Flask(__name__)

@app.get("/")
def index():
    return "Hello, Sanchit! CI/CD via Jenkins → Docker → Helm → Minikube."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
