import os
import time

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
    # First refresh a harmless public revision marker. This is useful when the
    # restart endpoint has a transient 500 and also records the deployed source.
    api.add_space_variable(repo_id=repo_id, key="SPACE_DEPLOY_REV", value=deploy_rev)
    time.sleep(3)
    try:
        api.pause_space(repo_id=repo_id)
        time.sleep(3)
        api.restart_space(repo_id=repo_id)
        print(f"Triggered pause/restart recovery for {repo_id}")
    except Exception:
        # Do not claim success if the Space could not be restarted.
        raise
