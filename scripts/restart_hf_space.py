import os

from huggingface_hub import HfApi


token = os.environ.get("HF_TOKEN", "").strip()
repo_id = os.environ.get("HF_SPACE_REPO", "Yousefsg/chatgpt-api").strip()
if not token:
    raise SystemExit("HF_TOKEN is required")
if not repo_id:
    raise SystemExit("HF_SPACE_REPO is required")

HfApi(token=token).restart_space(repo_id=repo_id)
print(f"Requested restart for {repo_id}")
