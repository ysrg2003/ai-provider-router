from __future__ import annotations

import json
from pathlib import Path

config = json.loads((Path(__file__).parents[1] / "config" / "models.json").read_text(encoding="utf-8"))
hf_models = [item["model"] for item in config["model_chains"]["default"] if item["provider"] == "huggingface" and item.get("enabled", True)]
assert len(hf_models) == 10, hf_models
assert hf_models[0] == "openai/gpt-oss-120b:fastest"
assert hf_models[-1] == "openai/gpt-oss-20b:fastest"
print("default Hugging Face chain contains 10 models")
