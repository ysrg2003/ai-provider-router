# بطاقات الاعتمادات ومتغيرات البيئة

هذا الملف يشرح **أسماء** الاعتمادات ومكان تخزينها وطريقة التحقق منها. لا يحتوي على أي قيمة حقيقية. محليًا استخدم `.env` غير المتعقب أو export مؤقتًا؛ في GitHub Actions استخدم **Settings → Secrets and variables → Actions → Secrets**. لا تضع أي key أو token أو cookie أو Storage State في `config/*.json` أو Git أو logs.

## خريطة سريعة

> **قاعدة الربط:** أسماء المتغيرات لا تُقرأ عشوائيًا من كل الملفات؛ `config/key_pools.json` يحدد pool واسم البيئة، `src/ai_router/config.py` يحمّل القيمة ويفك JSON، `src/ai_router/router.py` يمررها إلى adapter، و`.github/workflows/*.yml` يحقن Secrets في live jobs. ابحث عن الاسم في هذه الملفات عند التشخيص، ولا تعدّل القيمة داخل JSON config.

| المجموعة | تعريف الاسم | القراءة البرمجية | الاستخدام الخارجي |
|---|---|---|---|
| Gemini | `config/key_pools.json` → `gemini_default` | `RouterConfig.keys_for()` → `GeminiAdapter` | `live-smoke.yml` أو `.env` |
| Hugging Face | `config/key_pools.json` → `huggingface_default` | `RouterConfig.keys_for()` → `OpenAICompatibleAdapter` | `live-smoke.yml` أو `.env` |
| OpenRouter | `config/key_pools.json` → `openrouter_default` | `RouterConfig.keys_for()` → `OpenAICompatibleAdapter` | `live-smoke.yml` أو `.env` |
| NVIDIA | `config/key_pools.json` → `nvidia_default` | `RouterConfig.keys_for()` → `OpenAICompatibleAdapter` | `live-smoke.yml` و`nvidia-functional.yml` |
| Base URLs/state | `.env.example` و`config/providers.json` | `RouterConfig.load()` و`RouterStore` | CLI، Docker، GitHub Variables |

| الاسم | التصنيف | مطلوب؟ | يقرأه | مكانه الآمن |
|---|---|---|---|---|
| `AI_ROUTER_GEMINI_KEYS_JSON` | secret pool | اختياري | `gemini_default` | local `.env` أو GitHub Secret |
| `AI_ROUTER_HF_KEYS_JSON` / `HF_TOKEN` | secret pool/single fallback | اختياري | `huggingface_default` | local `.env` أو GitHub Secret |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` / `OPENROUTER_API_KEY` | secret pool/single fallback | اختياري | `openrouter_default` | local `.env` أو GitHub Secret |
| `NVIDIA_API_KEYS_JSON` / `NVIDIA_API_KEY` | secret pool/single fallback | اختياري | `nvidia_default` | local `.env` أو GitHub Secret |



| بطاقة Secret | Space المقابلة | Base URL | Provider ID | مصدر الإنشاء |
|---|---|---|---|---|









**Account and permissions:** تحتاج صلاحية إدارة Space المقابل في Hugging Face. لا تحتاج هذه القيمة إلى صلاحيات GitHub.

**Step-by-step acquisition:**

1. افتح Space المطلوب في Hugging Face.
2. ادخل إلى **Settings → Variables and secrets**.
3. أنشئ أو راجع Secret باسم `API_SECRET_KEY`.
5. كرر الخطوات لكل Space فقط إذا كانت Spaces لا تشترك في القيمة؛ لا تنسخ Storage State بين الحسابات.



**How the code reads it:** `config/key_pools.json` يحدد `fallback_env`; `src/ai_router/config.py` يقرأ single token إذا لم توجد array صالحة.

**Minimal health check:** شغّل `summary` وتأكد أن provider موجود دون أن يظهر secret، ثم نفّذ text smoke محدودًا. لا تطبع قيمة المتغير.

**Expected success:** استجابة JSON من route text/search مع `route` و`intent`، أو health HTTP صالح من Space.

**Common failure and fix:** `401/403` يعني اختلاف القيمة عن `API_SECRET_KEY` في Space؛ صحح Secret ثم أعد تشغيل Space/router. `503` أو timeout يعني runtime/Space غير جاهز؛ افحص health ولا تغيّر secret بلا دليل.

**Expiry:** لا يوجد expiry مضمون؛ قد تُدوّر القيمة عند تغيير Secret في Space.

**Rotation:** أنشئ قيمة جديدة في Space، حدّث GitHub Secret أو `.env`، اختبر، ثم احذف القيمة القديمة.

**Revocation:** احذف أو غيّر `API_SECRET_KEY` في Space، ثم حدّث كل بيئة تستخدم القيمة القديمة.

**What to do after accidental exposure:** غيّر Secret فورًا في كل Space متأثرة، حدّث router، افحص Git history، ولا تكتفِ بحذف الرسالة أو الملف المحلي.



**Classification:** secret key pool.

**Required or optional:** اختياري؛ يتيح keys مرتبة بدل single fallback.


**Where to obtain it:** استخدم قيم `API_SECRET_KEY` الصحيحة التي أنشأتها في Spaces، أو pool داخلي منفصل لكل مشروع حسب سياسة الأمان.

**Account and permissions:** صلاحية إدارة Spaces أو معرفة API secrets المطلوبة؛ لا تضع Storage State أو Cookies في هذا المتغير.

**Step-by-step acquisition:**

1. جهّز JSON array من secrets دون طباعتها.
2. خزّنها في local `.env` أو GitHub Secret.
3. شغّل `summary`؛ يجب أن يظهر عدد keys منقحًا دون values.
4. نفّذ اختبارًا محدودًا للنص، ثم راقب cooldown/rotation في SQLite.


**Exact storage location:** `.env` غير المتعقب أو GitHub Secret. لا تضع array في `config/key_pools.json`؛ الملف يضم اسم المتغير فقط.

**How the code reads it:** `RouterConfig.keys_for()` يقبل array وwrapper aliases ويحوّلها إلى `KeySpec`، ثم `AIRouter._ordered_keys()` يطبق ordered rotation.

**Minimal health check:** `summary` ثم test text واحد مع state DB مؤقت.

**Expected success:** router يختار key صالحًا ويسجل success في SQLite دون كشف key.


**Expiry:** حسب secret المصدر.

**Rotation:** بدّل key pool تدريجيًا، اختبر، ثم أزل القديم.

**Revocation:** ألغِ كل source key في Space أو مزودها.

**What to do after accidental exposure:** rotate كل العناصر التي ظهرت، ثم امسح أي artifacts/logs تحتوي values.

## بطاقة `AI_ROUTER_GEMINI_KEYS_JSON`

**Exact name:** `AI_ROUTER_GEMINI_KEYS_JSON`.

**Classification:** Google Gemini API key pool.

**Required or optional:** اختياري؛ مطلوب فقط إذا أردت Gemini fallback أو image/audio/embedding/video paths التي يعتمدها config.

**Used by:** `gemini_default` و`google_gemini`.

**Where to obtain it:** [Google AI Studio](https://aistudio.google.com/app/apikey) أو Google Cloud حسب API المنتج المستخدم؛ فعّل API المناسبة للحساب.

**Account and permissions:** Google account ومشروع/صلاحيات تسمح باستخدام Gemini API. اتبع quota وسياسة Google الحالية.

**Step-by-step acquisition:**

1. افتح Google AI Studio أو Cloud Console.
2. أنشئ/اختر project.
3. فعّل API المطلوبة وأنشئ API key.
4. خزّنها في GitHub Secret باسم `AI_ROUTER_GEMINI_KEYS_JSON` كـJSON array.
5. اختبر route المناسب، مع الانتباه إلى quota.

**Safe placeholder and format:** `AI_ROUTER_GEMINI_KEYS_JSON=["<gemini-key>"]`.

**Exact storage location:** `.env` أو GitHub Secret فقط.

**How the code reads it:** `config/key_pools.json` و`RouterConfig.keys_for()`.

**Minimal health check:** `summary` ثم route-plan أو live smoke scenario غير مولد للصور إن كانت quota محدودة.

**Expected success:** HTTP/JSON response صالح أو output artifact مناسب للمسار.

**Common failure and fix:** `401/403` راجع project/API enablement؛ `429` quota، انتظر أو استخدم key آخر؛ `400` راجع model/method payload.

**Expiry:** حسب إعدادات Google key والسياسة.

**Rotation:** أنشئ key جديدًا، اختبر، ثم احذف القديم من Google وGitHub.

**Revocation:** احذف key من Google project.

**What to do after accidental exposure:** revoke من Google فورًا، ثم استبدل GitHub Secret وافحص logs.

## بطاقة `AI_ROUTER_HF_KEYS_JSON` و`HF_TOKEN`

**Exact name:** `AI_ROUTER_HF_KEYS_JSON`، مع fallback مفرد باسم `HF_TOKEN`.

**Classification:** Hugging Face access token.

**Required or optional:** اختياري؛ مطلوب عند استخدام Hugging Face provider أو inference route.

**Used by:** `huggingface_default` وprovider `huggingface`.

**Where to obtain it:** [Hugging Face Settings → Access Tokens](https://huggingface.co/settings/tokens). استخدم fine-grained token بأقل صلاحية لازمة، مثل Inference Providers عند الحاجة.

**Account and permissions:** حساب Hugging Face وصلاحية inference المطلوبة؛ لا تستخدم token إداريًا إذا كان token inference كافيًا.

**Step-by-step acquisition:**

1. افتح صفحة Access Tokens.
2. اختر **Create new token**.
3. اختر أقل scope مناسب.
4. خزّن token كـ`HF_TOKEN` أو JSON array في `AI_ROUTER_HF_KEYS_JSON`.
5. اختبر provider بطلب محدود.

**Safe placeholder and format:** `HF_TOKEN=hf_<token>` أو `AI_ROUTER_HF_KEYS_JSON=["hf_<token>"]`، حيث `<token>` placeholder لا قيمة حقيقية.

**Exact storage location:** `.env` أو GitHub Secret.

**How the code reads it:** key pool `huggingface_default` يقرأ array ثم fallback `HF_TOKEN`.

**Minimal health check:** route-plan لا يكفي؛ نفّذ text smoke محدودًا إذا كانت quota تسمح.

**Expected success:** response صالح من Hugging Face router.

**Common failure and fix:** `401` scope/token؛ `429` provider quota؛ `503` model unavailable؛ راجع model ID وpermissions.

**Expiry:** fine-grained token قد يملك expiration.

**Rotation:** أنشئ token جديدًا، استبدله، اختبر، ثم احذف القديم.

**Revocation:** احذف token من Hugging Face.

**What to do after accidental exposure:** revoke فورًا ولا تعتمد على إخفائه في Git history.

## بطاقة `AI_ROUTER_OPENROUTER_KEYS_JSON` و`OPENROUTER_API_KEY`

**Exact name:** `AI_ROUTER_OPENROUTER_KEYS_JSON`، مع fallback مفرد `OPENROUTER_API_KEY`.

**Classification:** OpenRouter API key.

**Required or optional:** اختياري؛ مطلوب عند تفعيل OpenRouter fallback.

**Used by:** `openrouter_default` وprovider `openrouter` على `https://openrouter.ai/api/v1`.

**Where to obtain it:** [OpenRouter Keys](https://openrouter.ai/keys). راجع model availability وfree/paid policy قبل الاستخدام.

**Account and permissions:** OpenRouter account والـlimits المطبقة على key.

**Step-by-step acquisition:**

1. سجّل الدخول إلى OpenRouter.
2. افتح صفحة Keys وأنشئ key محدودًا.
3. خزّنه كـ`OPENROUTER_API_KEY` أو JSON array في `AI_ROUTER_OPENROUTER_KEYS_JSON`.
4. شغّل text smoke محدودًا وتحقق من route.

**Safe placeholder and format:** `OPENROUTER_API_KEY=sk-or-<key>`.

**Exact storage location:** `.env` أو GitHub Secret.

**How the code reads it:** `openrouter_default` عبر `RouterConfig.keys_for()`.

**Minimal health check:** text request صغير مع state DB مؤقت.

**Expected success:** response JSON والـroute يشير إلى OpenRouter عند اختياره.

**Common failure and fix:** `401` key؛ `429` quota/rate; `404` model unavailable؛ لا تخلط OpenRouter model IDs مع NVIDIA IDs.

**Expiry:** حسب key settings.

**Rotation:** create new key → replace secret → smoke test → revoke old key.

**Revocation:** احذف key من OpenRouter.

**What to do after accidental exposure:** revoke فورًا وتحقق من usage/billing في الحساب.

## بطاقة `NVIDIA_API_KEY` و`NVIDIA_API_KEYS_JSON`

**Exact name:** `NVIDIA_API_KEY`، مع pool باسم `NVIDIA_API_KEYS_JSON`.

**Classification:** NVIDIA NIM API key.

**Required or optional:** اختياري في router؛ مطلوب لتجربة NVIDIA live. عند غيابه يتجاوز router NVIDIA ويستمر إلى provider التالي.

**Used by:** `nvidia_default` وprovider `nvidia` على `https://integrate.api.nvidia.com/v1`.

**Where to obtain it:** [NVIDIA Build](https://build.nvidia.com/) ثم account verification و**Get API Key** من صفحة نموذج متاح.

**Account and permissions:** NVIDIA account مع متطلبات التحقق التي تفرضها NVIDIA، وقد يختلف `/v1/models` والـFree Endpoint حسب الحساب والوقت.

**Step-by-step acquisition:**

1. افتح NVIDIA Build وسجّل الدخول.
2. أكمل التحقق المطلوب للحساب.
3. افتح صفحة نموذج أو صفحة API Catalog.
4. اختر **Get API Key**.
5. خزّنه في `NVIDIA_API_KEY` أو JSON array في `NVIDIA_API_KEYS_JSON`.
6. اختبر model ID واحدًا ثم سلسلة `nvidia_free`، ولا ترسل عشرات الطلبات بلا حد.

**Safe placeholder and format:** `NVIDIA_API_KEY=nvapi-<key>` أو `NVIDIA_API_KEYS_JSON=["nvapi-<key>"]`.

**Exact storage location:** local `.env` أو GitHub Secret باسم `NVIDIA_API_KEY`/`NVIDIA_API_KEYS_JSON`.

**How the code reads it:** `nvidia_default` يقرأ JSON pool ثم fallback single key؛ adapter هو `OpenAICompatibleAdapter`.

**Minimal health check:** GET `/v1/models` لاختبار المصادقة وقائمة النماذج، ثم completion محدود؛ لا تسجل Authorization header.

**Expected success:** HTTP 200 من `/v1/models` وresponse من `/v1/chat/completions`. في الإصدار الحالي مفعّل 12 نموذجًا NVIDIA في النص العام، مع Riva في `output_routes.translation` بعد اختبار وظيفي مستقل؛ catalog العام 57 ليس ضمانًا أن كل نموذج مكشوف أو صالح لكل capability في حسابك.

**Common failure and fix:** `401/403` key/account verification؛ `400` model/payload؛ `429/503` quota أو worker limit؛ timeout availability. لا تضف نموذجًا إلى routes لمجرد وجوده في public catalog؛ اختبره أولًا.

**Expiry:** حسب NVIDIA account/key policy وFree Endpoint quota.

**Rotation:** أنشئ key جديدًا من NVIDIA Build، حدّث secret، اختبر `/v1/models` وcompletion، ثم احذف القديم.

**Revocation:** ألغِ key من NVIDIA Build أو احذفه من حسابك.

**What to do after accidental exposure:** ألغِ المفتاح فورًا وأنشئ بديلًا. لا تعيد استخدام مفتاح ظهر في chat أو log حتى لو لم تكن هناك مؤشرات استخدام.

## بطاقات متغيرات غير سرية


هذه base URLs ليست secrets بحد ذاتها، ويستخدمها `providers.json` عبر `base_url_env`. يجب أن تكون HTTPS URLs لـSpace الصحيحة. القيمة الافتراضية موجودة في `.env.example`، ويمكن override محليًا أو عبر GitHub Variables. تحقق من `/health` أو أول response قبل تغييرها. الخطأ الشائع هو وضع key داخل URL أو خلط replica مع Storage State؛ Storage State لا يوضع في router config.

### `AI_ROUTER_CONFIG_DIR`

المتغير غير السري الذي يحدد مجلد `config`; default هو `config`. يجب أن يحتوي `providers.json` و`models.json` و`key_pools.json` و`policies.json` وcatalogs. إذا كان المسار خاطئًا يظهر config/load error؛ صححه قبل أي live call.

### `AI_ROUTER_STATE_DB`

المتغير غير السري الذي يحدد SQLite state DB؛ default هو `data/ai_router.db`. استخدم مسارًا قابلًا للكتابة. لتجربة نظيفة استخدم DB جديدًا؛ لا تحذف DB إنتاجي أثناء تشغيل requests.

## اختبار آمن بعد إضافة secret

```bash
cd /path/to/ai-provider-router
export PYTHONPATH=src
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/router-smoke.db summary
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/router-smoke.db call-auto --output-type text --operation credential_smoke --user 'Return exactly: credential works'
```

نجاح `summary` يثبت تحميل config فقط. النجاح الحقيقي هو JSON response من `call-auto`. عند الفشل، سجّل provider/model/status/error class فقط؛ لا تسجل key أو Authorization header أو base64 أو Cookies.

## بطاقة `GROQ_API_KEY` و`GROQ_API_KEYS_JSON`

**الاسم الدقيق:** `GROQ_API_KEY` لمفتاح واحد، أو `GROQ_API_KEYS_JSON` كمصفوفة مرتبة من المفاتيح. يقرأ `config/key_pools.json` المصفوفة أولًا، ثم يستخدم `GROQ_API_KEY` كـfallback إذا لم توجد مصفوفة.

**الوظيفة:** مصادقة طلبات Groq إلى `https://api.groq.com/openai/v1`. لا تضع المفتاح في `config/providers.json`؛ الملف يحتوي Base URL واسم key pool فقط.

**الحصول عليه خطوة بخطوة:**

1. افتح [GroqCloud Console](https://console.groq.com/).
2. أنشئ حسابًا أو سجّل الدخول.
3. افتح قسم **API Keys**.
4. أنشئ مفتاحًا جديدًا باسم يوضح المشروع.
5. انسخ المفتاح مرة واحدة إلى مدير أسرار آمن؛ لا تضعه في README أو Issue أو Git.
6. للتشغيل المحلي خزّنه في ملف `.env` غير متعقب بصيغة `GROQ_API_KEY=gsk_<token>`.
7. في GitHub Actions خزّنه من **Settings → Secrets and variables → Actions → Secrets** باسم `GROQ_API_KEY`.
8. عند استخدام أكثر من مفتاح، خزّن JSON مثل `GROQ_API_KEYS_JSON=["<groq-key-1>","<groq-key-2>"]` في Secret واحد.

**اختبار آمن:** بعد ضبط المفتاح، نفّذ `python scripts/groq_models.py --write config/groq_catalog.json` لاكتشاف القائمة، ثم `python scripts/groq_functional.py` لإرسال smoke واحد لكل نموذج نصي مفعّل. تظهر أسماء النماذج والحالات فقط ولا يظهر المفتاح أو محتوى الرد.

**التدوير والإلغاء:** أنشئ مفتاحًا جديدًا، اختبره، استبدل Secret، ثم احذف المفتاح القديم من GroqCloud. إذا ظهر المفتاح في سجل أو ملف، ألغِه فورًا وأنشئ بديلًا؛ حذف الملف وحده لا يلغي المفتاح.
