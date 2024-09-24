from flask import Flask, request, jsonify
from langchain_community.llms import Ollama
import time
from datetime import datetime
# from flask_cors import CORS

app = Flask(__name__)

# Initialize Ollama with the gemma2:2b model
llm = Ollama(model="gemma2:2b")

@app.route('/generate1', methods=['POST'])
def generate_sample():
    start_time = time.time()  # Record the start time in seconds
    formatted_start_time = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')  # Convert to readable format
    print("API call started at:", formatted_start_time)

    user_prompt = request.form.get('data')
    print(f"user_prompt-==== {user_prompt}")
    if not user_prompt:
        return jsonify({"error": "No input provided"}), 400
    try:
        result = llm.invoke(user_prompt)
        print(f"result-=== {result}")

        end_time = time.time()  # Record the end time in seconds
        formatted_end_time = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')  # Convert to readable format
        duration = end_time - start_time  # Calculate the duration
        print("API call ended at:", formatted_end_time)
        print(f"API call duration: {duration:.4f} seconds")
        return jsonify({"output": result})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
