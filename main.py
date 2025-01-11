from flask import Flask, render_template, request, jsonify
import pyttsx3
import speech_recognition as sr
import emoji
from openai import OpenAI
import time
import json

app = Flask(__name__)

client = OpenAI(
    api_key='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'
)

assistant_id = "asst_48CwO5jrTxs84NJm8XTA2Yzt"


class Assistant:
    functions = {"functions": []}
    registered_functions = {}

    def __init__(self):
        self.thread_id = "thread_id"
        self.active_run_id = None
        self.engine = pyttsx3.init()

        # Настройки для pyttsx3
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'russian' in voice.languages:
                self.engine.setProperty('voice', voice.id)
        self.engine.setProperty('rate', 150)  # Скорость речи
        self.engine.setProperty('volume', 1)  # Громкость

    def create_assistant(self):
        assistant = client.beta.assistants.create(name="Alpha", instructions="You are Alpha my personal assistant",
                                                  model="gpt-4o-mini")
        assistant_id = assistant.id
        print(assistant_id)

    def retrieve_assistant(self):
        my_assistant = client.beta.assistants.retrieve(assistant_id)
        print(my_assistant)

    def modify_assistant(self):
        my_updated_assistant = client.beta.assistants.update(assistant_id=assistant_id, model="gpt-4o-mini",
                                                             instructions="You are Alpha my personal Assistant",
                                                             name="Alpha", tools=self.functions["functions"])

    def create_thread(self):
        thread = client.beta.threads.create()
        self.thread_id = thread.id

    def delete_thread(self):
        response = client.beta.threads.delete(self.thread_id)
        print('Thread Deleted Successfully')

    def add_message(self, user_input):
        message = client.beta.threads.messages.create(thread_id=self.thread_id, role='user', content=user_input)

    def get_message(self):
        messages = client.beta.threads.messages.list(self.thread_id)
        output = messages.data[0].content[0].text.value
        return output

    def run_assistant(self):
        if self.active_run_id:
            # Check if the active run is completed
            run = self.retrieve_run(self.active_run_id)
            if run.status == "completed":
                self.active_run_id = None
            else:
                return self.active_run_id

        run = client.beta.threads.runs.create(thread_id=self.thread_id, assistant_id=assistant_id,
                                              instructions="Reply in Brief")
        self.active_run_id = run.id
        return run.id

    def retrieve_run(self, run_id):
        run = client.beta.threads.runs.retrieve(thread_id=self.thread_id, run_id=run_id)
        return run

    def run_require_action(self, run, run_id):
        tool_outputs = []
        if run.required_action:
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = self.registered_functions.get(function_name)
                if function_to_call:
                    function_args = json.loads(tool_call.function.arguments)
                    function_response = function_to_call(**function_args)
                    tool_outputs.append({"tool_call_id": tool_call.id, "output": function_response})
            run = client.beta.threads.runs.submit_tool_outputs(thread_id=self.thread_id, run_id=run_id,
                                                               tool_outputs=tool_outputs)

    def assistant_api(self):
        self.modify_assistant()
        run_id = self.run_assistant()
        run = self.retrieve_run(run_id)
        while run.status == "requires_action" or "queued":
            run = self.retrieve_run(run_id)
            if run.status == "completed":
                self.active_run_id = None
                break
            self.run_require_action(run, run_id)
        outputs = self.get_message()
        tokens = run.usage.total_tokens
        return outputs, tokens

    @classmethod
    def add_func(cls, func):
        cls.registered_functions[func.__name__] = func
        doc_lines = func.__doc__.strip().split('\n')
        func_info = {
            'type': 'function',
            'function': {
                'name': func.__name__,
                'description': doc_lines[0].strip(),
                'parameters': {
                    'type': 'object',
                    'properties': {k.strip(): {'type': v.strip().split(':')[0].strip(),
                                               'description': v.strip().split(':')[1].strip()}
                                   for k, v in (line.split(':', 1) for line in doc_lines[1:])},
                    'required': [k.strip() for k, v in (line.split(':', 1) for line in doc_lines[1:])]}}}

        cls.functions["functions"].append(func_info)

    def speak(self, output, tokens):
        print("\nAlpha: ", end='')
        for char in output:
            print(char, end='', flush=True)
            time.sleep(0.08)
        print(f"\nTokens Used: {tokens}")
        print()

        # Озвучка сообщения
        self.engine.say(output)
        self.engine.runAndWait()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    user_input = request.json['message']
    ai.add_message(emoji.emojize(user_input))
    output, tokens = ai.assistant_api()
    ai.speak(output, tokens)
    return jsonify({"response": emoji.emojize(output)})

@app.route('/listen_voice_input', methods=['POST'])
def listen_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Скажите что-нибудь...")
        audio_data = recognizer.listen(source)
        print("Распознаю...")
        try:
            voice_input = recognizer.recognize_google(audio_data, language="ru-RU")
            return jsonify({"message": voice_input})
        except sr.UnknownValueError:
            return jsonify({"message": "Не удалось распознать голос"}), 400
        except sr.RequestError as e:
            return jsonify({"message": f"Ошибка при запросе к сервису распознавания: {e}"}), 400


if __name__ == '__main__':
    ai = Assistant()
    ai.create_thread()
    app.run(debug=True)
