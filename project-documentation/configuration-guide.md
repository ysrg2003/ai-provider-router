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

## اختيار providers لكل طلب

يمكن للمستخدم تقييد الطلب إلى providers محددة دون تعديل `config/models.json`. تعمل الفلاتر على مستوى الطلب فقط، وتحافظ على ترتيب models والـfallback داخل providers المسموحة. **إذا لم يحدد المستخدم `--providers` ولا `--exclude-providers`، يستخدم router جميع providers المتاحة افتراضيًا** وفق ترتيب route الحالي.

### Allowlist — السماح بقائمة محددة

استخدم `--providers` مع قائمة مفصولة بفواصل. يمكن استخدام provider IDs أو aliases التالية:

| Alias | Provider المستهدف |
|---|---|
| `gemini` أو `google_gemini` | Gemini |
| `hf` أو `huggingface` | Hugging Face |
| `openrouter` | OpenRouter |
| `nvidia` | NVIDIA |

لجعل الطلب يستخدم Gemini فقط:

```bash
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/gemini-only.db \
  call-auto --output-type text \
  --providers gemini \
  --operation gemini_only \
  --user 'أجب بجملة واحدة: ما عاصمة اليابان؟'
```

وللسماح بمسار من Hugging Face ثم OpenRouter ثم NVIDIA فقط:

```bash
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/non-gemini.db \
  call-auto --output-type text \
  --providers huggingface,openrouter,nvidia \
  --operation non_gemini_fallback \
  --user 'أجب بإيجاز عن مفهوم الاستدلال في النماذج اللغوية'
```

### Denylist — استبعاد provider

استخدم `--exclude-providers` عندما تريد إبقاء بقية route مع استبعاد مزود واحد. مثال: كل providers المتاحة باستثناء Gemini:

```bash
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/no-gemini.db \
  call-auto --output-type text \
  --exclude-providers gemini \
  --operation without_gemini \
  --user 'أجب بإيجاز عن آخر تطورات الذكاء الاصطناعي'
```

يمكن استخدام الفلاتر أيضًا مع `route-plan` لمعاينة النتيجة دون إرسال network request:

```bash
python3 -m ai_router.cli.main --config-dir config route-plan \
  --output-type text \
  --providers huggingface,openrouter,nvidia \
  --user 'اكتب إجابة قصيرة'
```

إذا استُخدم `--providers` و`--exclude-providers` معًا، يجب ألا يتقاطعَا. عند وجود تقاطع أو alias غير معروف أو عدم بقاء أي model مناسب للمسار، يوقف router الطلب بخطأ واضح بدل تنفيذ fallback غير مقصود. **عدم تمرير أي خيار هو الوضع الافتراضي الشامل**: لا تتم إزالة أي provider من route.

### الاستخدام من Python

تقبل `AIRouter.complete_auto` و`route_plan` و`complete_json` و`complete_video_json` و`translate_text` المعاملين `providers` و`exclude_providers`:

```python
from ai_router import AIRouter

router = AIRouter(config_dir="config", state_db="/tmp/provider-filter.db")
try:
    result = router.complete_auto(
        user_prompt="اكتب إجابة قصيرة عن Gemini",
        output_type="text",
        providers=["huggingface", "openrouter", "nvidia"],
        operation="selected_providers",
    )
finally:
    router.close()
```

هذه الميزة لا تنشئ مفاتيح أو providers جديدة؛ يجب أن تكون credentials الخاصة بالمزود المسموح موجودة أصلًا في key pool المناسب. كما أنها لا تتجاوز quota أو capability contract؛ إذا لم يكن للمزود model مناسب للمسار، ستظهر حالة `No configured models remain after provider filters`.

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
