# دليل الإعداد والتكوين

## المفاهيم الأساسية

| المفهوم | معناه |
|---|---|
| Provider | خدمة خارجية تستقبل الطلب |
| Model | نموذج داخل provider |
| Key pool | keys مرتبة لمزود واحد |
| Chain | ترتيب provider/model للـfallback |
| Output route | ترتيب مخصص لـtext/image/audio وغيرها |
| Policy | max attempts وtimeouts وbackoff/cooldown |
| State | SQLite metadata عن calls والفشل والـcursor |

## الخطوة 1: إنشاء بيئة محلية

من terminal نظيف:

```bash
cd /home/ubuntu/work/ai-provider-router
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Expected result: وجود `.venv` ونجاح تثبيت dependencies ووجود `.env`. إذا فشل `venv`، ثبّت حزمة Python المناسبة لنظامك أو استخدم Python 3.11+؛ لا تثبت الأسرار في shell history.

## الخطوة 2: إضافة أول credential

اختر provider واحدًا فقط لأول تجربة. أسماء الحصول والتخزين في [`../docs/credentials.md`](../docs/credentials.md). ضع القيمة في `.env`، مثلًا:

```bash
# placeholders only; replace locally, never commit
NVIDIA_API_KEY=nvapi-<key>
```

أو:

```bash
OPENROUTER_API_KEY=sk-or-<key>
```

Expected result: `summary` يعمل دون طباعة القيمة. إذا ظهر `No keys configured` فهذا يعني أن الاسم أو JSON format غير صحيح.

## خريطة `.env`

| المتغير | النوع | default/format | consumer | الأثر |
|---|---|---|---|---|
| `CHATGPT_API_BASE_URL` | non-secret URL | replica-04 URL في example | ChatGPT provider | base URL للـprovider العام |
| `CHATGPT_API_REPLICA_01_BASE_URL` | non-secret URL | replica-01 URL | replica-01 | override |
| `CHATGPT_API_REPLICA_02_BASE_URL` | non-secret URL | replica-02 URL | replica-02 | override |
| `CHATGPT_API_SECRET_KEY` | secret | empty | ChatGPT key pool fallback | single ChatGPT key |
| `AI_ROUTER_CHATGPT_KEYS_JSON` | secret array | `[]` | ChatGPT pool | ordered keys |
| `AI_ROUTER_GEMINI_KEYS_JSON` | secret array | `[]` | Gemini pool | ordered keys |
| `AI_ROUTER_HF_KEYS_JSON` | secret array | `[]` | HF pool | ordered keys |
| `HF_TOKEN` | secret fallback | empty | HF pool | single token fallback |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` | secret array | `[]` | OpenRouter pool | ordered keys |
| `OPENROUTER_API_KEY` | secret fallback | empty | OpenRouter pool | single key fallback |
| `NVIDIA_API_KEYS_JSON` | secret array | `[]` | NVIDIA pool | ordered keys |
| `NVIDIA_API_KEY` | secret fallback | empty | NVIDIA pool | single key fallback |
| `AI_ROUTER_CONFIG_DIR` | path | `config` | `RouterConfig` | config directory |
| `AI_ROUTER_STATE_DB` | path | `data/ai_router.db` | `RouterStore` | SQLite state location |

GitHub Actions **Secrets** تحفظ القيم الحساسة، أما **Variables** فتحفظ base URLs والمسارات غير الحساسة إن احتجت override. لا تجعل key متغيرًا عاديًا.

## الخطوة 3: افحص config دون live API

```bash
export PYTHONPATH=src
python3 -m ai_router.cli.main \
  --config-dir "${AI_ROUTER_CONFIG_DIR:-config}" \
  --state-db /tmp/router-config.db summary
```

Expected result: JSON summary منقح، providers enabled، routes/model counts، وstate stats. إذا فشل load، تحقق من JSON syntax ووجود الملفات الأربعة.

## اختيار بين `call-json` و`call-auto`

`call-auto` يكتشف intent ويختار output route. `call-json` يناسب chain صريحًا وبنية system/user prompts. `route-plan` لا يرسل network request؛ هو مناسب للتأكد من اختيار model/tool قبل استهلاك quota.

```bash
python3 -m ai_router.cli.main --config-dir config route-plan \
  --output-type text --grounding search \
  --user 'ابحث في الويب عن آخر تحديثات النموذج'
```

Expected result: JSON فيه `output_type`, `grounding`, `route`, وقائمة models/tools. إذا كانت القائمة فارغة، أضف capability إلى config فقط بعد اختبار adapter.

## تعديل ترتيب provider/model

الترتيب يعيش في `config/models.json`، وليس في `.env`. لتغيير أولوية model موجود:

1. افتح chain أو output route المطلوب.
2. انقل entry دون تغيير `provider`/`model`/`method` إلا لسبب موثق.
3. شغّل `tests/test_model_catalog.py` أو suite كاملة.
4. شغّل route-plan وlive smoke واحدًا إن تغيرت أولوية live.
5. وثق سبب التغيير في release notes.

`config/providers.json` يحدد provider/base URL/timeout. `config/key_pools.json` يحدد أسماء env vars وسياسة rotation. `config/policies.json` يحدد حدود المحاولات وcooldowns؛ لا تضع policy values داخل secret pool.

## إضافة key ثانية

استخدم JSON array صالحة:

```bash
AI_ROUTER_OPENROUTER_KEYS_JSON=["<key-1>","<key-2>"]
```

بعد ذلك شغّل `summary` ثم test صغير. `RouterStore` يدير cursor وcooldown لكل key؛ لا تتوقع أن key الثانية تعوض quota مرتبطة بالحساب نفسه أو model نفسه.

## state DB

`AI_ROUTER_STATE_DB` default دائم. للتجربة النظيفة:

```bash
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/fresh-router.db summary
```

لا تمسح `data/ai_router.db` أثناء requests. عند backup، احفظه خارج Git وطبّق retention مناسبًا؛ يحتوي metadata تشغيلية وقد يساعد التحقيق في fallback.

## route capability matrix

| route/output | config source | تنفيذ أم plan |
|---|---|---|
| text | `output_routes.text` أو `default` | تنفيذ |
| translation | `output_routes.translation` | تنفيذ NVIDIA Riva بعقد raw text |
| grounded search/maps | `tools` في model spec | تنفيذ إن وُجد adapter |
| image | `output_routes.image` | تنفيذ ChatGPT/Gemini |
| audio | `output_routes.audio` | تنفيذ Gemini |
| embedding | `output_routes.embedding` | تنفيذ Gemini |
| live | `prepare_live_session()` | plan/WebSocket لاحقًا |
| video_generation | `complete_auto()` | unsupported asynchronous job |

## التحقق بعد أي تغيير

```bash
python3 -m compileall -q src tests
python3 -m unittest discover -s tests -v
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m json.tool config/key_pools.json >/dev/null
python3 -m json.tool config/policies.json >/dev/null
git diff --check
```

Expected result: exit code صفر لكل الأوامر. إذا نجحت هذه الأوامر وفشل live call، لا تتراجع عن config تلقائيًا؛ راجع provider error class وquota وcredential card.

## التضمين في مشروع Python آخر

ثبت source من tag/commit محدد داخل host، ثم استخدم import:

```python
from ai_router.router import AIRouter, AllProvidersFailed

router = AIRouter(config_dir="/opt/ai-provider-router/config", state_db="data/router.db")
try:
    output = router.complete_auto(user_prompt="Return exactly: ok", output_type="text", operation="host_call")
    assert isinstance(output, dict) and output["intent"] == "text"
except AllProvidersFailed as exc:
    # redact the exception before writing logs
    raise RuntimeError("all configured providers failed") from exc
finally:
    router.close()
```

الـhost يملك timeout الأعلى وlogging policy؛ router يملك per-attempt timeout وSQLite state. لا تشارك secrets بين host وrouter إلا عبر environment/secret manager.
