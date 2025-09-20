import requests
from typing import Dict, List, Any
from logger import logger

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def generate(self, model: str, prompt: str, stream: bool = False) -> Dict[str, Any]:
        """Generate response from Ollama model"""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=None)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    def list_models(self) -> List[str]:
        """Get available models from Ollama"""
        try:
            url = f"{self.base_url}/api/tags"
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch models: {e}")
            return []
