# AI_CONTEXT.md — ai-provider-router

## 1. الهوية والحدود

`ai-provider-router` مشروع Python 3.11+ يقدم مكتبة وCLI لتوجيه طلبات JSON إلى عدة مزودي ذكاء اصطناعي. يختار route أو chain، يمر على model/provider/key بالترتيب، يطبق fallback محدودًا، ويسجل cooldown وcursor وحالة النجاح أو الفشل في SQLite.

المشروع لا يستضيف النماذج ولا ينشئ API keys ولا يضمن توفر كل model خارجي. `route-plan` تخطيط محلي لا يثبت صحة provider؛ البرهان الخارجي هو response أو artifact حقيقي. يستخدم المشروع حاليًا ChatGPT replica-01 وreplica-02 وGemini وHugging Face وOpenRouter وNVIDIA.

المرجع المنشور الأخير هو `v1.2.27-default-all-providers`، وآخر commit موثق في router هو `c5e5a28`. لا توجد Secrets أو Cookies أو Storage State في المستودع.

## 2. القاعدة الذهبية وطريقة القراءة

ابدأ دائمًا بـ`project-documentation/README.md` للمسار المبتدئ، ثم [`docs/credentials.md`](docs/credentials.md) للأسرار، ثم `config/` للعقود، ثم `src/ai_router/router.py` للتنفيذ، ثم `tests/` لإثبات السلوك.

> إذا لم يحدد المستخدم `providers` أو `exclude_providers`، فالوضع الافتراضي هو استخدام **كل providers المتاحة** وفق ترتيب route الحالي.

قبل أي تعديل:

1. اقرأ `pyproject.toml` و`.env.example` و`config/*.json`.
2. افحص entrypoint `src/ai_router/cli/main.py` وorchestration في `src/ai_router/router.py`.
3. حدّد provider/model/method والعقد المطلوب.
4. أضف regression test قبل تغيير route أو adapter.
5. لا تعدّل Secret أو Cookie أو Storage State داخل Git.
6. شغّل JSON validation و`compileall` وunit tests و`git diff --check`.

## 3. النتيجة الأولى القابلة للتشغيل

من جذر clone:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp .env.example .env
ai-router --config-dir config --state-db /tmp/router.db summary
ai-router --config-dir config --state-db /tmp/router.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

`summary` يثبت تحميل config مع redaction. `route-plan` لا يرسل network request. بعد وضع Secret مزود واحد، يكون أول live call:

```bash
ai-router --config-dir config --state-db /tmp/router.db \
  call-auto --output-type text --operation first_smoke \
  --user "Return exactly: router works"
```

## 4. طرق الاستخدام والتكامل

### GitHub Actions

المسار الموصى به للتشغيل المتكرر هو checkout router في workflow مستهلك وتثبيت tag محدد، ثم وضع Secrets في **Settings → Secrets and variables → Actions → Secrets**. توجد workflows جاهزة:

| workflow | الغرض |
|---|---|
| `.github/workflows/test.yml` | compileall و52 unit tests وsummary offline |
| `.github/workflows/live-smoke.yml` | bounded live smoke يدوي |
| `.github/workflows/capability-audit.yml` | تدقيق model/provider/method |
| `.github/workflows/nvidia-functional.yml` | فحص NVIDIA models |
| `.github/workflows/chatgpt-spaces-functional.yml` | اختبار ChatGPT replica-01 وreplica-02 |

لا تطبع Secrets أو Authorization headers أو base64 في artifacts. ابدأ بسيناريو واحد، ولا تستخدم `all` قبل مراجعة quota.

### التشغيل المحلي

استخدم `.venv` و`.env` غير المتعقب. SQLite default هو `data/ai_router.db`، وللتجارب استخدم `/tmp/router.db`. لا تشارك DB بين workers متوازية بلا locking أو state contract.

### Docker

`Dockerfile` الجذري يبني CLI فقط. `.dockerignore` يمنع `.env` وDB وartifacts من الصورة. استخدم:

```bash
docker build -t ai-provider-router:local .
docker run --rm --env-file .env -v "$PWD/data:/app/data" \
  ai-provider-router:local --config-dir config \
  --state-db /app/data/ai_router.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

لا يوجد Docker daemon مثبت في بيئة التوثيق الحالية؛ تحقق من build في CI أو جهاز Docker فعلي.

### Python API

الواجهة العامة الأساسية هي `AIRouter` من `ai_router`. أهم methods هي `summary` و`route_plan` و`complete_auto` و`complete_json` و`complete_video_json` و`translate_text`. أغلق router في `finally` لحفظ SQLite checkpoint.

```python
from ai_router import AIRouter

router = AIRouter(config_dir="config", state_db="/tmp/host-router.db")
try:
    payload = router.complete_auto(
        user_prompt="اكتب إجابة قصيرة",
        output_type="text",
        providers=["huggingface", "openrouter", "nvidia"],
        operation="host_smoke",
    )
finally:
    router.close()
```

إذا كان host بلغة أخرى، استخدم CLI subprocess واحترم exit code وJSON stdout. HTTP service boundary غير مضمن في هذا المستودع؛ إضافته proposal منفصل.

## 5. الأسرار والمتغيرات

المصدر التفصيلي لكل قيمة هو [`docs/credentials.md`](docs/credentials.md). لا تنقل قيمة حقيقية إلى AI_CONTEXT.

| الاسم | النوع | يقرأه | الوظيفة |
|---|---|---|---|
| `CHATGPT_API_SECRET_KEY` | Secret | `chatgpt_space_default` fallback | مصادقة HTTP مع ChatGPT Space |
| `AI_ROUTER_CHATGPT_KEYS_JSON` | Secret JSON | `chatgpt_space_default` | key pool مرتب |
| `AI_ROUTER_GEMINI_KEYS_JSON` | Secret JSON | `gemini_default` | Gemini API keys |
| `AI_ROUTER_HF_KEYS_JSON` / `HF_TOKEN` | Secret | `huggingface_default` | Hugging Face keys/fallback |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` / `OPENROUTER_API_KEY` | Secret | `openrouter_default` | OpenRouter keys/fallback |
| `NVIDIA_API_KEYS_JSON` / `NVIDIA_API_KEY` | Secret | `nvidia_default` | NVIDIA keys/fallback |
| `CHATGPT_API_REPLICA_01_BASE_URL` | Variable | `providers.json` | override Space-01 URL |
| `CHATGPT_API_REPLICA_02_BASE_URL` | Variable | `providers.json` | override Space-02 URL |
| `AI_ROUTER_CONFIG_DIR` | Variable | CLI/environment | config directory، default `config` |
| `AI_ROUTER_STATE_DB` | Variable | CLI/environment | SQLite path، default `data/ai_router.db` |

`RouterConfig.keys_for()` يقبل JSON arrays وwrapper objects وfield aliases، ويطبق fallback المفرد حسب `config/key_pools.json`. `public_summary()` يعرض counts وnames فقط، لا values.

## 6. خريطة الملفات والطبقات

| الطبقة | الملفات | المسؤولية |
|---|---|---|
| Package/entrypoint | `pyproject.toml`, `src/ai_router/__init__.py` | metadata و`ai-router` executable |
| CLI | `src/ai_router/cli/main.py` | parse args وتشغيل summary/route/call |
| Orchestration | `src/ai_router/router.py` | intent، route، filters، fallback، retries |
| Rules | `src/ai_router/intent.py`, `tools.py` | output type وgrounding tools |
| Config | `src/ai_router/config.py`, `config/*.json` | providers/models/keys/policies |
| Contracts | `src/ai_router/providers/base.py` | ProviderResponse وProviderError وadapter interface |
| Adapters | `src/ai_router/providers/gemini.py`, `openai_compatible.py`, `chatgpt_space.py` | outbound API methods |
| Persistence | `src/ai_router/store.py` | SQLite cursor/cooldown/stats |
| Scripts | `scripts/*.py` | live smoke، capability audit، functional tests |
| Tests | `tests/*.py` | regression والعقود والـcatalog |
| Automation | `.github/workflows/*.yml` | offline CI وmanual live jobs |
| Documentation | `README.md`, `docs/`, `project-documentation/` | beginner/ops/engineering docs |
| Vendor | `vendors/chatgpt-api/` | source snapshot مضمن، دون Secrets |

## 7. config والعقود

`config/providers.json` يعرّف provider ID وkind وbase URL وkey pool وtimeout. providers الحالية هي ChatGPT replica-01/02 و`google_gemini` و`huggingface` و`openrouter` و`nvidia`.

`config/models.json` يضم `model_chains` و`output_routes`. كل `ModelSpec` يملك provider/model/method/input_types/output_types وtools وresponse-format flags. `config/key_pools.json` يربط pool بمتغيرات البيئة وfallback وrotation. `config/policies.json` يحدد max attempts وbackoff وcooldowns.

لا تعدّل `.env` لتغيير ترتيب models؛ عدّل `config/models.json` ثم أضف test وrelease note. Base URL override غير سري، أما API keys فهي Secrets.

## 8. دورة البيانات

```text
CLI أو Python input
  -> detect_intent أو output_type صريح
  -> resolve route/chain
  -> providers allowlist/denylist
  -> capability/model filtering
  -> key ordering + SQLite cooldown/cursor
  -> adapter bounded outbound call
  -> ProviderResponse أو ProviderError
  -> success payload + route/intent metadata
  -> JSON أو media artifact
```

عند `ProviderError` يسجل store الخطأ ويطبّق cooldown حسب error class، ثم ينتقل إلى المرشح التالي إذا سمحت retry policy. `AllProvidersFailed` terminal بعد استهلاك المحاولات. لا ينبغي retry عملية image generation بلا حدود بسبب quota.

## 9. provider selection

يقبل CLI `--providers` كـallowlist و`--exclude-providers` كـdenylist. aliases: `gemini`/`google_gemini`، `hf`/`huggingface`، `openrouter`، `nvidia`، و`chatgpt`.

عند غياب الخيارين يستخدم جميع providers. يرفض router unknown alias، overlap بين القائمتين، أو عدم بقاء model مناسب. الاختبار الأساسي في `tests/test_router.py`.

## 10. المسارات والقدرات

| output | التنفيذ الحالي |
|---|---|
| `text` | route عام متعدد providers |
| `text_grounded_search` / maps | عندما يملك spec tool المناسب |
| `image` | Gemini وChatGPT routes؛ quota خارجية |
| `audio` | Gemini TTS |
| `embedding` | Gemini embedding |
| `translation` | NVIDIA Riva raw-text |
| `video_analysis` | يحتاج `video_uri` وadapter |
| `video_generation` | route/plan مؤجل؛ لا async Veo adapter |
| `live` | WebSocket plan فقط |

Capability audit الحالي يفرّق بين live passed وfailed وroute-only. لا تعمم نجاح provider على كل model أو method.

## 11. الاختبارات والفشل والاستعادة

بوابة الإصدار المحلية:

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m compileall -q src scripts tests vendors/chatgpt-api
python3 -m unittest discover -s tests -v
git diff --check
```

الأخطاء المهمة: `401/403` credential أو permissions؛ `400/404` model أو method؛ `429` quota/rate limit؛ `503/timeout` availability أو session؛ `AllProvidersFailed` انتهاء candidates. استخدم SQLite DB مؤقتة أثناء التشخيص، وسجل provider/model/status/error class دون Secret.

## 12. بروتوكول التعديل والإصدار

عند إضافة provider: عدّل config، أضف adapter إن كان contract مختلفًا، أضف model metadata، اكتب offline mock tests، ثم bounded live smoke. عند تعديل route: حدّث `config/models.json` وtests وdocs. عند تعديل Secret semantics: حدّث `.env.example` و`docs/credentials.md` وGitHub workflow.

قبل release، افحص الأسرار والروابط، شغّل suite كاملة، افصل live deferred عن passed، ثم اكتب release notes تذكر ما اختُبر وما لم يُختبر.

## 13. الحالة الحالية والمراجع

آخر release موثق هو `v1.2.27-default-all-providers`. أحدث قرار: عدم تمرير provider filters يعني كل providers، مع إمكانية allowlist/denylist لكل طلب. آخر live ChatGPT text/search مثبت في replica-01 وreplica-02؛ image قد يتوقف بسبب ChatGPT Free-plan quota.

القراءة التالية: [`project-documentation/README.md`](project-documentation/README.md)، ثم [`docs/credentials.md`](docs/credentials.md)، ثم [`project-documentation/troubleshooting.md`](project-documentation/troubleshooting.md)، ثم الكود والاختبارات.

## References

[1]: [project-documentation/README.md](project-documentation/README.md) — دليل البدء المرتب.
[2]: [docs/credentials.md](docs/credentials.md) — بطاقات الأسرار والمتغيرات.
[3]: [config/providers.json](config/providers.json) و[config/models.json](config/models.json) — سجل providers وroutes.
[4]: [src/ai_router/router.py](src/ai_router/router.py) و[src/ai_router/config.py](src/ai_router/config.py) — orchestration وconfig semantics.
[5]: [tests/test_router.py](tests/test_router.py) و[tests/test_model_catalog.py](tests/test_model_catalog.py) — بوابات regression.
[6]: [GitHub Actions secrets documentation](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) — تخزين Secrets في GitHub.
[7]: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) — بناء الصورة وتشغيلها.
