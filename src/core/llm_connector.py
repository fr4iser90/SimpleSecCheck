#!/usr/bin/env python3
import os
import sys

# Ensure the scripts directory is in the path for llm client imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

llm_provider = os.environ.get('LLM_PROVIDER', 'openai').lower()
llm_config = {
    'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY', ''),
    'OPENAI_MODEL': os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
    'OPENAI_ENDPOINT': os.environ.get('OPENAI_ENDPOINT', 'https://api.openai.com/v1/chat/completions'),
    'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY', ''),
    'GEMINI_MODEL': os.environ.get('GEMINI_MODEL', 'gemini-pro'),
    'GEMINI_ENDPOINT': os.environ.get('GEMINI_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/models'),
    'HF_API_KEY': os.environ.get('HF_API_KEY', ''),
    'HF_MODEL': os.environ.get('HF_MODEL', 'bigcode/starcoder2-15b'),
    'HF_ENDPOINT': os.environ.get('HF_ENDPOINT', 'https://api-inference.huggingface.co/models'),
    'GROQ_API_KEY': os.environ.get('GROQ_API_KEY', ''),
    'GROQ_MODEL': os.environ.get('GROQ_MODEL', 'llama3-70b-8192'),
    'GROQ_ENDPOINT': os.environ.get('GROQ_ENDPOINT', 'https://api.groq.com/openai/v1/chat/completions'),
    'MISTRAL_API_KEY': os.environ.get('MISTRAL_API_KEY', ''),
    'MISTRAL_MODEL': os.environ.get('MISTRAL_MODEL', 'mistral-medium'),
    'MISTRAL_ENDPOINT': os.environ.get('MISTRAL_ENDPOINT', 'https://api.mistral.ai/v1/chat/completions'),
    'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),
    'ANTHROPIC_MODEL': os.environ.get('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
    'ANTHROPIC_ENDPOINT': os.environ.get('ANTHROPIC_ENDPOINT', 'https://api.anthropic.com/v1/messages'),
}

llm_client = None

def get_llm_client():
    global llm_client
    if llm_client is not None:
        return llm_client

    if llm_provider == 'openai':
        from scripts.llm.llm_client_openai import OpenAILLMClient
        llm_client = OpenAILLMClient(llm_config)
    elif llm_provider == 'gemini':
        from scripts.llm.llm_client_gemini import GeminiLLMClient
        llm_client = GeminiLLMClient(llm_config)
    elif llm_provider == 'huggingface':
        from scripts.llm.llm_client_huggingface import HuggingFaceLLMClient
        llm_client = HuggingFaceLLMClient(llm_config)
    elif llm_provider == 'groq':
        from scripts.llm.llm_client_groq import GroqLLMClient
        llm_client = GroqLLMClient(llm_config)
    elif llm_provider == 'mistral':
        from scripts.llm.llm_client_mistral import MistralLLMClient
        llm_client = MistralLLMClient(llm_config)
    elif llm_provider == 'anthropic':
        from scripts.llm.llm_client_anthropic import AnthropicLLMClient
        llm_client = AnthropicLLMClient(llm_config)
    else:
        print(f"[llm_connector] Warning: Unknown LLM provider '{llm_provider}'. Defaulting to OpenAI.", file=sys.stderr)
        from scripts.llm.llm_client_openai import OpenAILLMClient
        llm_client = OpenAILLMClient(llm_config)
    return llm_client

# Initialize client on import so other modules can directly import llm_client
llm_client = get_llm_client()

if __name__ == '__main__':
    # Example usage/test
    client = get_llm_client()
    if client:
        print(f"Successfully initialized LLM client for provider: {llm_provider}")
        # try:
        #     response = client.query("Hello! Who are you?")
        #     print(f"LLM Response: {response}")
        # except Exception as e:
        #     print(f"Error querying LLM: {e}")
    else:
        print("Failed to initialize LLM client.") 