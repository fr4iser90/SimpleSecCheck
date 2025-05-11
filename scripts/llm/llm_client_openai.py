import requests
from .llm_client_base import LLMClientBase

class OpenAILLMClient(LLMClientBase):
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get('OPENAI_API_KEY')
        self.model = config.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.endpoint = config.get('OPENAI_ENDPOINT', 'https://api.openai.com/v1/chat/completions')

    def query(self, prompt, context=None):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': context or ''},
                {'role': 'user', 'content': prompt}
            ]
        }
        # Placeholder for real API call
        # resp = requests.post(self.endpoint, headers=headers, json=data)
        # return resp.json()['choices'][0]['message']['content']
        return "[OpenAI LLM response placeholder]"

    def get_provider_name(self):
        return 'OpenAI' 