import re

import anthropic
from llama_index.llms.anthropic import Anthropic


def add_lineno(file_content: str) -> str:
    lines = file_content.split("\n")
    ret = ""
    for i, line in enumerate(lines):
        ret += f"{i+1}: {line}\n"
    return ret


def reformat_json_string(output: str) -> str:
    # 1. Extract JSON from <output_format>...</output_format> tags if present
    pattern = r"<output_format>(.*?)</output_format>"
    match = re.search(pattern, output, re.DOTALL)
    if match:
        output = match.group(1).strip()

    # 2. Remove markdown code blocks (existing logic)
    pattern = r"```json(.*?)```"
    match = re.search(pattern, output, re.DOTALL)
    if match:
        output = match.group(1).strip()

    pattern = r"```xml(.*?)```"
    match = re.search(pattern, output, re.DOTALL)
    if match:
        output = match.group(1).strip()

    # 3. If the JSON has a 'module' field, clean it
    try:
        import json

        json_obj = json.loads(output)
        if "module" in json_obj:
            module_text = json_obj["module"]
            # Strip XML/HTML-like tags from the module field
            module_text_clean = re.sub(r"<[^>]+>", "", module_text).strip()
            # Extract Verilog code between 'module TopModule' and 'endmodule'
            pattern = r"(module TopModule.*?endmodule)"
            match = re.search(pattern, module_text_clean, re.DOTALL)
            if match:
                json_obj["module"] = match.group(1).strip()
            else:
                json_obj["module"] = module_text_clean
            return json.dumps(json_obj, ensure_ascii=False)
    except Exception:
        pass  # If not JSON, just return cleaned output

    return output.strip()


class VertexAnthropicWithCredentials(Anthropic):
    def __init__(self, credentials, **kwargs):
        """
        In addition to all parameters accepted by Anthropic, this class accepts a
        new parameter `credentials` that will be passed to the underlying clients.
        """
        # Pop parameters that determine client type so we can reuse them in our branch.
        region = kwargs.get("region")
        project_id = kwargs.get("project_id")
        aws_region = kwargs.get("aws_region")

        # Call the parent initializer; this sets up a default _client and _aclient.
        super().__init__(**kwargs)

        # If using AnthropicVertex (i.e., region and project_id are provided and aws_region is None),
        # override the _client and _aclient with the additional credentials parameter.
        if region and project_id and not aws_region:
            self._client = anthropic.AnthropicVertex(
                region=region,
                project_id=project_id,
                credentials=credentials,  # extra argument
                timeout=self.timeout,
                max_retries=self.max_retries,
                default_headers=kwargs.get("default_headers"),
            )
            self._aclient = anthropic.AsyncAnthropicVertex(
                region=region,
                project_id=project_id,
                credentials=credentials,  # extra argument
                timeout=self.timeout,
                max_retries=self.max_retries,
                default_headers=kwargs.get("default_headers"),
            )
        # Optionally, you could add similar overrides for the aws_region branch if needed.
