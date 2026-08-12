from ai_router import AIRouter

router = AIRouter(config_dir="config", state_db="data/ai_router.db")
try:
    result = router.complete_json(
        chain="default",
        operation="example",
        system_prompt="Return JSON only. You are a concise professional assistant.",
        user_prompt="Create one original idea for a structured video lesson.",
    )
    print(result)
finally:
    router.close()
