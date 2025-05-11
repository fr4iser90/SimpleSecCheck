from scripts.llm.llm_client_base import LLMClientBase
import os

class HuggingFaceLLMClient(LLMClientBase):
    def __init__(self, config=None):
        if config is None:
            config = {}
        self.api_key = config.get('HF_API_KEY') or os.environ.get('HF_API_KEY')
        self.model = config.get('HF_MODEL', 'bigcode/starcoder2-15b') or os.environ.get('HF_MODEL', 'bigcode/starcoder2-15b')
        self.endpoint = config.get('HF_ENDPOINT', 'https://api-inference.huggingface.co/models') or os.environ.get('HF_ENDPOINT', 'https://api-inference.huggingface.co/models')

    def query(self, prompt):
        # Placeholder for HuggingFace API call
        # Should POST to f"{self.endpoint}/{self.model}" with API key in header
        return f"[HuggingFace AI explanation for: {prompt[:60]}...]"

    def get_provider_name(self):
        return 'huggingface' 