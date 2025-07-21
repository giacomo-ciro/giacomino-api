import os

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

from giacomino import Giacomino
from utils import MyLogger
import traceback

# Init logger
logger = MyLogger()

# Load environment variables
if not os.path.exists(".env"):
    logger.error("Missing .env")
load_dotenv()

# set port env
os.environ["PORT"]="5001"

# Init app
app = Flask(__name__)
CORS(app)

# Initialize Giacomino model
TEXT_MODEL_PATH = "meta-llama/Llama-3.2-3B-Instruct-Turbo"
EMB_MODEL_PATH = "BAAI/bge-large-en-v1.5"
try:
    giacomino = Giacomino(
        model_text=TEXT_MODEL_PATH,
        model_embeddings=EMB_MODEL_PATH,
        logger=logger
    )
    logger.info(f"Giacomino model initialized with {TEXT_MODEL_PATH} and {EMB_MODEL_PATH}.")
except Exception as e:
    logger.error(f"Failed to initialize Giacomino: {e}")
    giacomino = None


@app.route('/')
def hello_world():
    """
    Returns the API documentation.
    """
    return {
        "message": "Giacomo Ciro's Personal Chatbot API",
        "version": giacomino.version if giacomino else "N/A",
        "endpoints": {
            "/chat": "POST - Chat with Giacomino",
            "/health": "GET - Check API health",
            "/docs": "GET - Get documentation about Giacomo"
        }
    }


@app.route('/status', methods=['GET'])
def status_check():
    """
    Status check endpoint.
    """
    return jsonify({
        "status": "healthy" if giacomino else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": giacomino is not None,
        "version": giacomino.version if giacomino else "N/A",
        "docs_available": giacomino.get_available_docs() if giacomino else "N/A",
        "logger_status": logger.get_stats(),
        "logs_dump": logger.dumps(),
        "models":{
            "model_text": giacomino.model_text if giacomino else "N/A",
            "model_embeddings": giacomino.model_embeddings if giacomino else "N/A"
        }
    })


@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint for the personal chatbot.
    """
    if not giacomino:
        return jsonify({'error': 'Model not available'}), 503
    
    try:
        data = request.get_json()
        if not data or 'messages' not in data:
            return jsonify({'error': 'Missing message in request body'}), 400
        
        messages = data['messages']
        if not messages:
            return jsonify({'error': 'Empty message'}), 400
        
        # Generate response using Giacomino
        response = giacomino.generate_response(messages)
        
        return jsonify({
            'text': response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500
    

@app.route('/history', methods=["GET"])
def get_history():
    """
    Returns the chat history in JSON format. Auth using a HISTORY_KEY stored in .env
    Send requests as url/history?key=yourkey
    """
    try:
        # Check for authorization key
        auth_key = request.headers.get('Authorization') or request.args.get('key')
        logger.info(f"Auth access attempt with key: {auth_key}")
        expected_key = os.environ.get('HISTORY_KEY')
        
        if not expected_key:
            logger.error("HISTORY_KEY not configured in environment")
            return jsonify({'error': 'Service not configured'}), 500
            
        if not auth_key or auth_key != expected_key:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Read and return history.json
        if not os.path.exists('saved_messages.jsonl'):
            return jsonify({'history': [], 'message': 'No history file found'})
        
        with open('saved_messages.jsonl', 'r') as file:
            history_data = file.read()
            
        return jsonify({'history': history_data})
        
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return jsonify({'error': 'Failed to retrieve history'}), 500
    

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port} with debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)