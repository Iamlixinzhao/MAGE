import os

import config
from google.oauth2 import service_account
from llama_index.core.llms.llm import LLM
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.ollama import Ollama  # Add this import for Ollama support
from llama_index.llms.openai import OpenAI
from llama_index.llms.vertex import Vertex
from llama_index.llms.vllm import Vllm  # Add this import for Vllm support
from pydantic import BaseModel

from .log_utils import get_logger
from .utils import VertexAnthropicWithCredentials

logger = get_logger(__name__)


class Config:
    def __init__(self, file_path=None):
        self.file_path = file_path
        self.file_config = {}
        if self.file_path and os.path.isfile(self.file_path):
            self.file_config = config.Config(self.file_path)
        self.fallback_config = {}
        self.fallback_config["OPENAI_API_BASE_URL"] = ""

    def __getitem__(self, index):
        # Values in key.cfg has priority over env variables
        if index in self.file_config:
            return self.file_config[index]
        if index in os.environ:
            return os.environ[index]
        if index in self.fallback_config:
            return self.fallback_config[index]
        raise KeyError(
            f"Cannot find {index} in either cfg file '{self.file_path}' or env variables"
        )


def get_llm(**kwargs) -> LLM:
    print("DEBUG: get_llm called with provider =", kwargs["provider"])
    cfg = Config(kwargs["cfg_path"])
    provider: str = kwargs["provider"].lower()
    if provider == "anthropic":
        try:
            llm: LLM = Anthropic(
                model=kwargs["model"],
                api_key=cfg["ANTHROPIC_API_KEY"],
                max_tokens=kwargs["max_token"],
            )
        except Exception as e:
            raise Exception(f"gen_config: Failed to get {provider} LLM") from e
    elif provider == "openai":
        try:
            llm: LLM = OpenAI(
                model=kwargs["model"],
                api_key=cfg["OPENAI_API_KEY"],
                max_tokens=kwargs["max_token"],
            )
        except Exception as e:
            raise Exception(f"gen_config: Failed to get {provider} LLM") from e
    elif provider == "ollama":
        try:
            # Accept model_info and host from kwargs, with defaults
            model_info = kwargs.get("model_info", {})
            host = kwargs.get(
                "host",
                cfg.file_config.get("OLLAMA_BASE_URL", "http://192.168.1.201:11434"),
            )
            llm: LLM = Ollama(
                model=kwargs["model"],
                base_url=host,
                model_info=model_info,
                max_tokens=kwargs["max_token"],
            )
        except Exception as e:
            raise Exception(f"gen_config: Failed to get {provider} LLM") from e
    elif provider == "vllm":
        try:
            # Accept vllm specific parameters from kwargs
            base_url = kwargs.get(
                "base_url",
                cfg.file_config.get("VLLM_BASE_URL", "http://localhost:8000"),
            )
            llm: LLM = Vllm(
                model=kwargs["model"],
                base_url=base_url,
                max_tokens=kwargs["max_token"],
            )
        except Exception as e:
            raise Exception(f"gen_config: Failed to get {provider} LLM") from e
    elif provider == "vertex":
        logger.warning(
            "Support of Vertex Gemini LLMs is still in experimental stage, use with caution"
        )
        service_account_path = os.path.expanduser(cfg["VERTEX_SERVICE_ACCOUNT_PATH"])
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(
                f"Google Cloud Service Account file not found: {service_account_path}"
            )
        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path
            )
            llm: LLM = Vertex(
                model=kwargs["model"],
                project=credentials.project_id,
                credentials=credentials,
                max_tokens=kwargs["max_token"],
            )

        except Exception as e:
            raise Exception(f"gen_config: Failed to get {provider} LLM") from e
    elif provider == "vertexanthropic":
        service_account_path = os.path.expanduser(cfg["VERTEX_SERVICE_ACCOUNT_PATH"])
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(
                f"Google Cloud Service Account file not found: {service_account_path}"
            )
        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            llm: LLM = VertexAnthropicWithCredentials(
                model=kwargs["model"],
                project_id=credentials.project_id,
                credentials=credentials,
                region=cfg["VERTEX_REGION"],
                max_tokens=kwargs["max_token"],
            )

        except Exception as e:
            raise Exception(f"gen_config: Failed to get {provider} LLM") from e
    else:
        raise ValueError(f"gen_config: Invalid provider: {provider}")

    try:
        _ = llm.complete("Say 'Hi'")
    except Exception as e:
        raise Exception(
            f"gen_config: Failed to complete LLM chat for {provider}"
        ) from e

    return llm


class ExperimentSetting(BaseModel):
    """
    Global setting for experiment
    """

    temperature: float = 0.85  # Chat temperature
    top_p: float = 0.95  # Chat top_p


global_exp_setting = ExperimentSetting()


def get_exp_setting() -> ExperimentSetting:
    return global_exp_setting


def set_exp_setting(temperature: float | None = None, top_p: float | None = None):
    if temperature is not None:
        global_exp_setting.temperature = temperature
    if top_p is not None:
        global_exp_setting.top_p = top_p
    return global_exp_setting
