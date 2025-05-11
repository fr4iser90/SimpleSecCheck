class LLMClientBase:
    """Base interface for LLM client implementations (local or API)."""
    def __init__(self, config):
        self.config = config

    def query(self, prompt, context=None):
        """Send a prompt to the LLM and return the response."""
        raise NotImplementedError("LLMClientBase.query must be implemented by subclasses")

    def get_provider_name(self):
        """Return the name of the LLM provider (e.g., 'OpenAI', 'HuggingFace', 'Local')."""
        raise NotImplementedError("LLMClientBase.get_provider_name must be implemented by subclasses") 