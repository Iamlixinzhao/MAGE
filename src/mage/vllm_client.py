from pydantic import BaseModel
import requests
import json
from typing import List, Dict, Any, Optional
from llama_index.core.llms.llm import LLM
from llama_index.core.llms import ChatMessage, CompletionResponse, CompletionResponseGen, ChatResponse
from llama_index.core.base.llms.types import LLMMetadata

class CustomVllmClient(LLM, BaseModel):
    """Custom vLLM client that connects to a running vLLM server via HTTP"""
    model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    api_url: str = "http://localhost:8000"
    max_new_tokens: int = 1500  # 降低默认值，避免token超限
    temperature: float = 0.3  # 降低温度，提高Verilog代码生成的准确性
    top_p: float = 0.95

    def _estimate_complexity(self, prompt: str) -> int:
        """根据提示词复杂度估算所需的token数"""
        # 简单的启发式方法
        lines = prompt.count('\n')
        words = len(prompt.split())
        
        # 基础token数
        base_tokens = 1000
        
        # 根据复杂度调整
        if lines > 50 or words > 500:
            return min(4000, base_tokens + (lines * 20) + (words * 2))
        elif lines > 20 or words > 200:
            return min(3000, base_tokens + (lines * 15) + (words * 1.5))
        else:
            return min(2000, base_tokens + (lines * 10) + (words * 1))

    def _get_dynamic_max_tokens(self, prompt: str) -> int:
        """动态计算max_tokens"""
        estimated_tokens = self._estimate_complexity(prompt)
        return min(estimated_tokens, 4000)  # 设置上限为4000

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            model_name=self.model,
            max_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
        )
    
    def complete(
        self, prompt: str, **kwargs: Any
    ) -> CompletionResponse:
        try:
            # 动态调整max_tokens
            dynamic_max_tokens = self._get_dynamic_max_tokens(prompt)
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": dynamic_max_tokens,  # 使用动态计算的token数
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
            }
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120  # 2 minutes should be enough for optimized vLLM
            )
            if response.status_code == 200:
                result = response.json()
                # Handle both OpenAI format (choices) and simple format (response)
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    return CompletionResponse(text=content)
                elif "response" in result:
                    content = result["response"]
                    return CompletionResponse(text=content)
                else:
                    raise Exception(f"Unexpected response format: {result}")
            elif response.status_code == 400 and "maximum context length" in response.text:
                # Token超限，尝试减少token数
                print(f"Token limit exceeded, retrying with reduced tokens. Original: {dynamic_max_tokens}")
                payload["max_tokens"] = max(500, dynamic_max_tokens // 2)
                response = requests.post(
                    f"{self.api_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=120
                )
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return CompletionResponse(text=content)
                    elif "response" in result:
                        content = result["response"]
                        return CompletionResponse(text=content)
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"Failed to complete with vLLM: {str(e)}")
    
    def chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        try:
            vllm_messages = []
            for msg in messages:
                vllm_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            # 动态调整max_tokens
            combined_prompt = " ".join([msg["content"] for msg in vllm_messages])
            dynamic_max_tokens = self._get_dynamic_max_tokens(combined_prompt)
            
            payload = {
                "model": self.model,
                "messages": vllm_messages,
                "max_tokens": dynamic_max_tokens,  # 使用动态计算的token数
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
            }
            response = requests.post(
                f"{self.api_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120  # 2 minutes should be enough for optimized vLLM
            )
            if response.status_code == 200:
                result = response.json()
                # Handle both OpenAI format (choices) and simple format (response)
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    return ChatResponse(message=ChatMessage(role="assistant", content=content))
                elif "response" in result:
                    content = result["response"]
                    return ChatResponse(message=ChatMessage(role="assistant", content=content))
                else:
                    raise Exception(f"Unexpected response format: {result}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"Failed to chat with vLLM: {str(e)}")
    
    def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        return self.complete(prompt, **kwargs)
    
    def achat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
        return self.chat(messages, **kwargs)
    
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        response = self.complete(prompt, **kwargs)
        yield response
    
    def stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponseGen:
        response = self.chat(messages, **kwargs)
        yield response
    
    def astream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        response = self.complete(prompt, **kwargs)
        yield response
    
    def astream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> CompletionResponseGen:
        response = self.chat(messages, **kwargs)
        yield response 
