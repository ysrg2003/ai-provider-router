# AI_CONTEXT.md — ai-provider-router

## 1. الهوية والحدود

`ai-provider-router` مكتبة وCLI بلغة Python 3.11+ لتوحيد استدعاء عدة مزودي نماذج خلف إعدادات JSON واحدة. يختار router نوع المخرج، route أو chain، model، provider، وkey من الإعدادات، وينفذ fallback محدودًا عند أخطاء قابلة للإعادة. يحتفظ SQLite بحالة cooldown وcursor وإحصاءات التشغيل، ولا يحتفظ بقيم الأسرار.

المشروع لا يستضيف النماذج، ولا ينشئ API keys، ولا يضمن توفر نموذج خارجي أو بقاء quota. كما أن مستودعات أو Spaces خارج هذا المستودع ليست جزءًا من نطاقه، ولا يجوز إدخال ملفاتها أو جلساتها إلى هذه الشجرة.

المرجع المبتدئ هو [`project-documentation/README.md`](project-documentation/README.md). مرجع عقد الاستجابة هو [`project-documentation/response-contract.md`](project-documentation/response-contract.md). لا تنقل أي مفتاح أو Cookie أو Storage State إلى هذا الملف.

## 2. القاعدة الذهبية قبل التعديل

ابدأ من `README.md` ثم `project-documentation/README.md` و`project-documentation/configuration-guide.md`. اقرأ `config/*.json` قبل تعديل route، و`src/ai_router/router.py` قبل تعديل orchestration، وadapter المناسب قبل تعديل payload. اربط كل تغيير باختبار offline وlive smoke محدود إذا كان التغيير يخص provider خارجي.

عند غياب `providers` و`exclude_providers` يستخدم router جميع providers ذات models وcredentials المتاحة في route، بالترتيب الموجود في `config/models.json`. لا تستنتج capability من اسم model أو من ظهوره في catalog؛ يجب أن يطابق method والـpayload والاختبار العقد المطلوب.

## 3. أول تشغيل مثبت

من جذر المستودع:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp .env.example .env
ai-router --config-dir config --state-db /tmp/router.db summary
ai-router --config-dir config --state-db /tmp/router.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

`summary` يثبت تحميل config مع redaction، و`route-plan` لا يرسل network request. بعد وضع Secret مزود واحد، تكون أول مكالمة:

```bash
ai-router --config-dir config --state-db /tmp/router.db \
  call-auto --output-type text --operation first_smoke \
  --user "Return JSON with exactly one field ok set to true."
```

## 4. خريطة الطبقات والملفات

| الطبقة | الملفات | المسؤولية والعلاقة |
|---|---|---|
| Entrypoint | `pyproject.toml`, `src/ai_router/__init__.py` | تعريف الحزمة وconsole script باسم `ai-router` |
| CLI | `src/ai_router/cli/main.py` | أوامر `summary`, `route-plan`, `call-auto`, و`call-json`; يطبع JSON إلى stdout |
| Intent | `src/ai_router/intent.py` | اكتشاف `output_type` و`grounding` عند عدم التصريح بهما |
| Tools | `src/ai_router/tools.py` | تحويل `search` و`maps` إلى descriptors داخلية |
| Orchestration | `src/ai_router/router.py` | route resolution، provider filters، key/model fallback، retries، envelope |
| Config | `src/ai_router/config.py`, `config/providers.json`, `config/models.json`, `config/key_pools.json`, `config/policies.json` | providers، routes، models، secrets mapping، policy |
| Provider contracts | `src/ai_router/providers/base.py`, `src/ai_router/response_contract.py` | `ProviderResponse`, `ProviderError`, citation normalization، protocol، وvalidator للـresponse envelope |
| Gemini adapter | `src/ai_router/providers/gemini.py` | GenerateContent وInteractions وimage/TTS/embedding/video payloads |
| OpenAI-compatible adapter | `src/ai_router/providers/openai_compatible.py` | chat completions لـGroq وHF وOpenRouter وNVIDIA |
| Persistence | `src/ai_router/store.py` | SQLite calls، failures، cooldown، cursor، stats |
| Live scripts | `scripts/live_smoke.py`, `scripts/capability_audit.py`, `scripts/unified_contract_smoke.py`, `scripts/groq_models.py`, `scripts/groq_functional.py` | اختبارات live منقحة، contract smoke عبر models، واكتشاف catalogs |
| Tests | `tests/*.py` | route، adapter، key pool، citation، response contract، model catalog، regression |
| Workflows | `.github/workflows/*.yml` | offline CI وlive jobs اليدوية، ومنها capability audit وunified response smoke عبر GitHub Secrets |
| Documentation | `README.md`, `docs/`, `project-documentation/` | beginner setup، credentials، contracts، operations، decisions |

## 5. دورة التنفيذ

```text
CLI أو Python input
  -> detect_intent أو output_type صريح
  -> resolve output route أو explicit chain
  -> provider allowlist/denylist
  -> enabled model/capability filtering
  -> key pool ordering + SQLite cooldown/cursor
  -> adapter bounded outbound call
  -> ProviderResponse أو ProviderError
  -> success payload + response envelope
  -> JSON أو media artifact
```

في `_complete_route()` يسجل router النجاح في SQLite، يطبع أو يعيد payload، يطبع `url_citations` موحدة، ويضيف `output_type`, `intent`, `route`, `provider`, و`model`. عند grounded text لا يقبل نجاحًا بلا citation. عند `ProviderError` يسجل النوع والحالة ويطبق cooldown/backoff ثم ينتقل إلى المرشح التالي حتى `max_attempts`.

## 6. العقود وresponse envelope

الواجهة الموصى بها للمستهلك هي `AIRouter.complete_auto()`. بعد نجاح route تنفيذي، الحقول المشتركة هي:

| الحقل | النوع | الدلالة |
|---|---|---|
| `output_type` | string | نوع المخرج الفعلي |
| `intent` | string | intent الذي استخدمه router |
| `route` | string | route أو chain الذي نجح |
| `provider` | string | المزود الذي أعاد النتيجة فعليًا |
| `model` | string | model الذي أعاد النتيجة فعليًا |
| `url_citations` | list[string] | روابط موحدة، فارغة لغير grounded عادةً |

الحقول الدلالية ليست موحدة بالاسم بين الأنواع. النص العام يعيد JSON الذي طلبه prompt، الترجمة تعيد عادةً `translation` و`text`، الصورة والصوت يعيدان `data_base64` و`mime_type`، التضمين يعيد `embeddings`، والبحث يعيد `text` و`grounding_sources` و`url_citations`. التفاصيل والأمثلة في [`response-contract.md`](project-documentation/response-contract.md).

`complete_json()` واجهة منخفضة المستوى تعيد JSON النموذج ولا تضيف envelope router الكامل. `route_plan()` يعيد خطة models/tools دون network request. `summary()` يعيد config/state منقحين. عند الفشل ترفع الواجهة `AllProvidersFailed` أو `UnsupportedOutputType` بدل نتيجة نجاح زائفة.

## 7. providers وroutes الحالية

| الترتيب العام في routes النصية | Provider | التنفيذ |
|---:|---|---|
| 1 | Gemini | adapter خاص؛ text، grounded search، image، audio، embedding، video analysis |
| 2 | Groq | OpenAI-compatible؛ text وtranslation فقط |
| 3 | Hugging Face | OpenAI-compatible؛ models النصية وبعض multimodal حسب spec |
| 4 | OpenRouter | OpenAI-compatible؛ catalog مجاني وroutes متخصصة حسب spec |
| 5 | NVIDIA | OpenAI-compatible؛ text وRiva translation |

يأتي Groq بعد Gemini مباشرة وقبل Hugging Face في `default`, `creative`, `cheap`, و`text`. ترتيب نماذج Groq النصية الحالي من الأعلى تشغيليًا إلى الأقل هو `openai/gpt-oss-120b`, ثم `groq/compound`, ثم `qwen/qwen3.6-27b`, ثم `groq/compound-mini`, ثم `openai/gpt-oss-20b`, ثم `allam-2-7b`. هذا ترتيب heuristic وليس benchmark عالميًا.

`text_grounded_search` هو Gemini-only. يستخدم `method: grounded_text` وREST `generateContent` مع `tools: [{"google_search": {}}]`، وهو المكافئ العملي لـ`GenerateContentConfig(tools=[Tool(google_search=GoogleSearch())])`. يستخرج النص من `candidates[].content.parts[].text` والمصادر من `candidates[].groundingMetadata.groundingChunks[].web.uri`، ويرفض النتيجة بلا `url_citations`. لا تُرسل Google Search إلى Groq أو HF أو OpenRouter لمجرد أن لديها chat completions.

الصور والصوت والتضمين مفعلة عبر Gemini methods المتخصصة. `live` خطة WebSocket فقط، و`video_generation` route مؤجل بلا async adapter. نجاح text لا يثبت image/audio/video capability.

## 8. الأسرار والمتغيرات

| الاسم | النوع | المستهلك | الملاحظة |
|---|---|---|---|
| `AI_ROUTER_GEMINI_KEYS_JSON` | Secret JSON | `gemini_default` | Gemini key pool المرتب |
| `GROQ_API_KEYS_JSON` | Secret JSON | `groq_default` | Groq key pool المرتب |
| `GROQ_API_KEY` | Secret fallback | `groq_default` | مفتاح Groq المفرد |
| `AI_ROUTER_HF_KEYS_JSON` / `HF_TOKEN` | Secret | `huggingface_default` | HF pool أو fallback |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` / `OPENROUTER_API_KEY` | Secret | `openrouter_default` | OpenRouter pool أو fallback |
| `NVIDIA_API_KEYS_JSON` / `NVIDIA_API_KEY` | Secret | `nvidia_default` | NVIDIA pool أو fallback |
| `GROQ_BASE_URL` | Variable | Groq provider | override اختياري، default `https://api.groq.com/openai/v1` |
| `AI_ROUTER_CONFIG_DIR` | Variable | `RouterConfig` وCLI | default `config` |
| `AI_ROUTER_STATE_DB` | Variable | `RouterStore` وCLI | default `data/ai_router.db` |

`RouterConfig.keys_for()` يقبل JSON arrays وwrapper objects وfield aliases، ثم يستخدم fallback المفرد. لا تُكتب القيم الحقيقية في Git أو logs أو artifacts. توجد بطاقات الحصول والتخزين والتدوير في [`docs/credentials.md`](docs/credentials.md).

## 9. state وfailure behavior

يستخدم `RouterStore` SQLite لتسجيل calls وsuccess/failure وusage وcooldown وmodel cursor. تدوير keys لا يلغي quota المرتبطة بالحساب نفسه. الأخطاء `401/403` غالبًا credential أو permission، و`400/404` schema أو model، و`429` quota/rate limit، و`503/timeout` availability أو transport. لا تستخدم retries غير محدودة، خصوصًا لتوليد الصور.

الـexception message يجب أن يبقى منقحًا. لا تسجل Authorization header أو Base64 أو prompts الحساسة. استخدم DB مؤقتة أثناء التشخيص، ولا تحذف DB أثناء request نشط.

## 10. الاختبارات والأدلة الحالية

بوابة التحقق المحلية:

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m json.tool config/key_pools.json >/dev/null
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -q
git diff --check
```

آخر تشغيل موثق في هذه النقطة نجح في **60 اختبارًا محليًا**. ويثبت التدقيق الحي المقارن المنقح [`unified-response-contract-cross-provider-live-2026-08-22.json`](project-documentation/unified-response-contract-cross-provider-live-2026-08-22.json) ما يلي:

| الفئة | passed | failed | deferred | الدليل |
|---|---:|---:|---:|---|
| Gemini text | 7 | 1 | 0 | سبعة models أعادت envelope صالحًا؛ `gemini-3-flash` أعاد 404 |
| Hugging Face text | 4 | 0 | 0 | أربعة models أعادت envelope صالحًا |
| OpenRouter text | 13 | 3 | 0 | 13 models نجحت؛ ثلاث حالات 429/404 |
| NVIDIA text + translation | 8 | 5 | 0 | ثمانية نجحت؛ خمس حالات model EOL أو payload غير متوافق |
| Groq text + translation | 0 | 0 | 12 | مؤجل لغياب Groq Secret في GitHub Actions |
| Gemini Search | 1 | 0 | 0 | نص grounded مع 4 `url_citations` |
| **الإجمالي** | **33** | **9** | **12** | **54 نتيجة/سيناريو** |

التقرير لا يحفظ الأسرار ولا body الكامل. هذه النتيجة تثبت أن envelope المشترك قابل للاستهلاك في الحالات `passed` عبر أربعة providers، لكنها لا تثبت توفر كل model أو جودة موحدة أو صلاحية Groq قبل توفير Secret. لا تعتبر النتيجة الحية دليلًا على صلاحية كل مفتاح داخل pool؛ تثبت فقط نجاح أحد المفاتيح في تنفيذ السيناريو.

للمقارنة عبر providers وmodels، يستخدم `scripts/unified_contract_smoke.py` validator نفسه. ينفذ طلبًا واحدًا لكل model نصي مفعّل، ويختبر الترجمة حيث يوجد route، ثم Gemini Search. الحالة `passed` تثبت contract لهذا provider/model/method، و`deferred_no_key` تعني أن الاختبار لم يُنفذ لغياب Secret، و`failed` تعني أن Secret موجود لكن الاستجابة أو الطلب خالف العقد. لا تُعامل الحالات المؤجلة كنجاح.

## 11. بروتوكول إضافة قدرة أو provider

عند إضافة model موجود في adapter، حدّث `config/models.json`، افحص capability، أضف test للترتيب والعقد، ثم شغّل live smoke محدودًا. عند إضافة provider جديد، حدّث provider registry وkey pool وadapter وerror mapping و`.env.example` وcredential docs وworkflow إن لزم.

عند تعديل output contract، حدّث `project-documentation/response-contract.md`، اختبارات adapter وrouter، و`live_smoke.py` إذا تغيرت حقول التقرير. لا تعدل ترتيب models في `.env`. لا تضف provider إلى grounded search أو image route دون adapter وpayload واختبار يثبت capability.

## 12. التشغيل من GitHub أو Docker

في GitHub Actions، ضع الأسرار في **Settings → Secrets and variables → Actions → Secrets**، وثبت router على tag أو commit. ضع Base URLs والمسارات غير الحساسة في Variables فقط عند الحاجة. ابدأ بـroute plan ثم live smoke واحد، وارفع artifact منقحًا.

في Docker، مرر `.env` وقت التشغيل ولا تنسخه إلى image layers:

```bash
docker build -t ai-provider-router:local .
docker run --rm --env-file .env -v "$PWD/data:/app/data" \
  ai-provider-router:local --config-dir config \
  --state-db /app/data/ai_router.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

HTTP service boundary غير مضمن في المستودع؛ إضافة API server مقترح منفصل، وليست capability حالية.

## 13. المراجع

[1]: [`project-documentation/README.md`](project-documentation/README.md) — فهرس المشروع ودليل البدء.

[2]: [`project-documentation/response-contract.md`](project-documentation/response-contract.md) — عقد الاستجابة الموحد والأمثلة.

[3]: [`config/models.json`](config/models.json) و[`config/providers.json`](config/providers.json) — routes وproviders الفعلية.

[4]: [`src/ai_router/router.py`](src/ai_router/router.py) و[`src/ai_router/providers/base.py`](src/ai_router/providers/base.py) — orchestration والعقود.

[5]: [`tests/test_multiroute.py`](tests/test_multiroute.py) و[`tests/test_router.py`](tests/test_router.py) و[`tests/test_groq.py`](tests/test_groq.py) — اختبارات response envelope وproviders.

[6]: https://ai.google.dev/gemini-api/docs/google-search — Google Search grounding وcitations في Gemini.

[7]: https://ai.google.dev/api/generate-content — مرجع GenerateContent.

[8]: https://console.groq.com/docs/models — Supported Models في GroqDocs.
