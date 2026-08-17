import os

from huggingface_hub import HfApi


token = os.environ.get("HF_TOKEN", "").strip()
repo_id = os.environ.get("HF_SPACE_REPO", "Yousefsg/chatgpt-api").strip()
deploy_rev = os.environ.get("SPACE_DEPLOY_REV", "").strip()
if not token:
    raise SystemExit("HF_TOKEN is required")
if not repo_id:
    raise SystemExit("HF_SPACE_REPO is required")

api = HfApi(token=token)
try:
    api.restart_space(repo_id=repo_id)
    print(f"Requested restart for {repo_id}")
except Exception:
    if not deploy_rev:
        raise
    # Hugging Face documents that changing Space configuration triggers a restart.
    # This fallback is used when the direct restart endpoint has a transient 500.
    api.add_space_variable(repo_id=repo_id, key="SPACE_DEPLOY_REV", value=deploy_rev)
    print(f"Triggered Space restart through configuration refresh for {repo_id}")
