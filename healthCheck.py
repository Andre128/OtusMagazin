from flask import Flask, jsonify

healthCheck = Flask(__name__)

@healthCheck.route('/health/', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"})

if __name__ == '__main__':
    healthCheck.run(host='0.0.0.0', port=8000)
    #1