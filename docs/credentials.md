# بطاقات الأسرار والمتغيرات

هذا الملف هو المرجع الأمني لمشروع `ai-provider-router`. القاعدة الأساسية هي أن **القيمة السرية تُحفظ خارج Git**: محليًا في `.env` المتجاهل، أو في GitHub **Secrets**، أو في secret manager الخاص ببيئة التشغيل. لا تنسخ مفتاحًا حقيقيًا إلى README أو Issue أو سجل workflow.

## خريطة القراءة

| الفئة | الأسماء | مكان التخزين | يستخدمها |
|---|---|---|---|
| Gemini | `AI_ROUTER_GEMINI_KEYS_JSON` | `.env` أو GitHub Secret | `google_gemini` وGenerateContent والبحث والصورة والصوت وembeddings والفيديو |
| Groq | `GROQ_API_KEYS_JSON` أو `GROQ_API_KEY` | `.env` أو GitHub Secret | `groq` وOpenAI-compatible JSON/text/chat |
| Hugging Face | `AI_ROUTER_HF_KEYS_JSON` أو `HF_TOKEN` | `.env` أو GitHub Secret | `huggingface` وInference Providers |
| OpenRouter | `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY` | `.env` أو GitHub Secret | `openrouter` وOpenAI-compatible routes |
| NVIDIA | `NVIDIA_API_KEYS_JSON` أو `NVIDIA_API_KEY` | `.env` أو GitHub Secret | `nvidia` وOpenAI-compatible routes |
| الخادم المحلي | `AI_ROUTER_LOCAL_API_KEY` | `.env` أو مدير أسرار النظام | Bearer اختياري لـ`/v1/chat/completions` |
| runtime | `GROQ_BASE_URL`, `AI_ROUTER_CONFIG_DIR`, `AI_ROUTER_STATE_DB` | `.env` أو Variables | عناوين ومسارات غير سرية |

> `config/key_pools.json` هو المصدر الحاسم لأسماء متغيرات المفاتيح. عند وجود JSON pool، يحاول الكود الاسم الأساسي أولًا، ثم `fallback_env` إذا كان pool فارغًا.

## إعداد التخزين المحلي

### الخطوة 1: إنشاء `.env`

من جذر المشروع في Linux أو Git Bash:

```bash
cp .env.example .env
```

في PowerShell:

```powershell
Copy-Item .env.example .env
```

افتح `.env` بمحرر نصي، واستبدل placeholders بقيمك. افحص أن `git status --short` لا يعرض `.env`. إذا ظهر، لا تعمل commit؛ راجع `.gitignore` وأزل الملف من staging قبل أي push.

### الخطوة 2: اختيار صيغة المفتاح

يمكن استخدام token واحد عند provider الذي يدعم fallback، أو JSON array مرتبة عندما تريد أكثر من مفتاح. الشكل الآمن التالي مثال شكلي فقط:

```json
[
  {"id": "provider-primary", "key": "REPLACE_WITH_SECRET", "project": "descriptive-label"}
]
```

لا تشغّل أمرًا يطبع `.env` أو قيمة المفتاح. للتحقق استخدم `summary`: الناتج يعرض عدد الأسرار المقروءة في `secrets_loaded` ولا يعرض القيم.

## `AI_ROUTER_GEMINI_KEYS_JSON` — مفتاح Gemini

**Purpose.** يتيح calls إلى Google Gemini، بما فيها `generateContent` وGoogle Search grounding والصور والصوت وembeddings وتحليل الفيديو حسب route. بدونه تبقى route plan ممكنة، لكن live call إلى Gemini يفشل.

**Classification.** Secret JSON array. **Required or optional.** اختياري للمشروع ككل، ومطلوب فقط إذا أردت استخدام Gemini route.

**Where to obtain it.** افتح [Google AI Studio API keys](https://aistudio.google.com/app/apikey) وراجع [Gemini API documentation](https://ai.google.dev/gemini-api/docs). سجّل الدخول بالحساب الذي يملك المشروع، أنشئ API key، وانسخه مرة واحدة.

**Where to add it.** محليًا:

```dotenv
AI_ROUTER_GEMINI_KEYS_JSON=[{"id":"gemini-primary","key":"REPLACE_WITH_GEMINI_KEY","project":"my-project"}]
```

في GitHub: افتح المستودع → **Settings → Secrets and variables → Actions → New repository secret**، واستخدم الاسم `AI_ROUTER_GEMINI_KEYS_JSON` والصق JSON بعد استبدال placeholder بمفتاحك في واجهة GitHub فقط. لا تستخدم Variables العامة.

**Minimal verification.** شغّل `ai-router --config-dir config summary`، وتحقق من أن `secrets_loaded.google_gemini` أكبر من صفر من غير طباعة السر. ثم أجرِ live call قصيرًا في route مناسبة.

**Failure and recovery.** `401/403` يعني غالبًا مفتاحًا خاطئًا أو API غير مفعّل أو حسابًا مختلفًا؛ تحقق من AI Studio والمشروع. `429` يعني rate/quota؛ انتظر أو استخدم key pool آخر. أخطاء الصورة أو الفيديو التي تعيد HTTP 200 بلا artifact ليست نجاحًا؛ افحص `data_base64` وroute.

**Rotation and revocation.** من صفحة إدارة المفاتيح عطّل أو احذف المفتاح المكشوف، أنشئ بديلًا، حدّث `.env` أو GitHub Secret، ثم أعد health check. اعتبر المفتاح مكشوفًا بالكامل إذا دخل Git أو log.

## `GROQ_API_KEY` و`GROQ_API_KEYS_JSON` — مفاتيح Groq

**Purpose.** يستخدمها adapter المتوافق مع OpenAI عبر `https://api.groq.com/openai/v1`. profile `groq_json` يضبط `max_completion_tokens` وJSON parsing عند الحاجة.

**Classification.** Secret أو Secret JSON array. **Required or optional.** اختياري، ومطلوب لمسارات Groq الحية.

**Where to obtain it.** افتح [Groq API reference](https://console.groq.com/docs/api-reference) ثم [Groq API keys](https://console.groq.com/keys). سجّل الدخول، أنشئ key، وانسخه.

**Safe formats.**

```dotenv
GROQ_API_KEY=REPLACE_WITH_GROQ_KEY
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

أو:

```dotenv
GROQ_API_KEYS_JSON=[{"id":"groq-primary","key":"REPLACE_WITH_GROQ_KEY","project":"default"}]
```

**Minimal verification.** شغّل `route-plan` أولًا، ثم `call-auto --output-type text --providers groq` بمطالبة قصيرة. تحقق من `provider: groq` و`model` في النتيجة.

**Failure and recovery.** `401/403` يعني key أو صلاحية غير صحيحة. `429` يعني rate limit. `402` يصنفه adapter كـ`plan_or_credit` عندما يعيد المزود هذه الحالة. افحص Base URL ولا تستخدم `/v1` مرتين.

**Rotation and revocation.** احذف key من Groq Console عند exposure، أنشئ بديلًا، حدّث الاسم نفسه في GitHub Secret أو `.env`، ثم اختبر call واحدًا.

## `AI_ROUTER_HF_KEYS_JSON` و`HF_TOKEN` — Hugging Face

**Purpose.** يتيح Hugging Face Inference Providers للنماذج الموجودة في routes. يقرأ الكود `AI_ROUTER_HF_KEYS_JSON` أولًا، ويستخدم `HF_TOKEN` كـfallback عند عدم وجود pool.

**Classification.** Secret أو Secret JSON array. **Required or optional.** اختياري.

**Where to obtain it.** افتح [Hugging Face access tokens](https://huggingface.co/settings/tokens) واقرأ [Inference Providers documentation](https://huggingface.co/docs/inference-providers/en/index). أنشئ fine-grained token بأقل صلاحية لازمة.

**Safe formats.**

```dotenv
HF_TOKEN=REPLACE_WITH_HF_TOKEN
```

أو:

```dotenv
AI_ROUTER_HF_KEYS_JSON=[{"id":"hf-primary","key":"REPLACE_WITH_HF_TOKEN","project":"default"}]
```

**Minimal verification.** شغّل `summary` وافحص `secrets_loaded.huggingface`، ثم استخدم route plan قبل live call. لا تعتبر ظهور model في catalog دليلًا على أن token يستطيع تشغيله.

**Failure and recovery.** راجع token permissions، وحالة provider/model، وquota للحساب. profiles `hf_flexible` و`hf_reasoning_json` تعالج اختلافات JSON/text، لكنها لا تصلح model ID غير موجود أو نموذجًا غير متاح للحساب.

**Rotation and revocation.** من صفحة tokens احذف أو revoke token القديم، أنشئ token جديدًا، حدّث التخزين، ثم اختبر بإجابة قصيرة.

## `AI_ROUTER_OPENROUTER_KEYS_JSON` و`OPENROUTER_API_KEY` — OpenRouter

**Purpose.** يرسل calls إلى OpenRouter، الذي يوفر endpoint متوافقًا مع OpenAI لبعض النماذج. يقرأ pool أولًا ثم fallback token.

**Classification.** Secret أو Secret JSON array. **Required or optional.** اختياري.

**Where to obtain it.** افتح [OpenRouter authentication](https://openrouter.ai/docs/api_reference/authentication) ثم [OpenRouter API keys](https://openrouter.ai/settings/keys). أنشئ key واضبط limits المناسبة لحسابك.

**Safe format.**

```dotenv
OPENROUTER_API_KEY=REPLACE_WITH_OPENROUTER_KEY
```

أو:

```dotenv
AI_ROUTER_OPENROUTER_KEYS_JSON=[{"id":"openrouter-primary","key":"REPLACE_WITH_OPENROUTER_KEY","project":"default"}]
```

**Minimal verification.** استخدم `route-plan` بلا network، ثم call محدودًا مع `--providers openrouter`. تحقق من `provider` و`model` و`route`.

**Failure and recovery.** `401` يعني key غير صحيح. `402` قد يعني limit أو credits أو plan. `429` يعني rate limit. افحص model availability وlimits في لوحة OpenRouter بدل إضافة model ID عشوائيًا.

**Rotation and revocation.** أوقف key من لوحة OpenRouter، أنشئ البديل، حدّث Secret store، ثم نفّذ call واحدًا bounded.

## `NVIDIA_API_KEY` و`NVIDIA_API_KEYS_JSON` — NVIDIA

**Purpose.** يستخدمها provider `nvidia` عبر endpoint الموجود في `config/providers.json`، مع profiles مرنة لبعض استجابات OpenAI-compatible.

**Classification.** Secret أو Secret JSON array. **Required or optional.** اختياري؛ مطلوب لتجربة NVIDIA live. عند غيابه يتجاوز router NVIDIA ويستمر إلى provider التالي.

**Where to obtain it.** افتح [NVIDIA Build](https://build.nvidia.com/) وسجّل الدخول، ثم اتبع صفحة API key أو credentials الخاصة بالحساب. راجع [NVIDIA API documentation](https://docs.api.nvidia.com/) إذا اختلفت شاشة الحساب أو صلاحياته.

**Safe formats.**

```dotenv
NVIDIA_API_KEY=REPLACE_WITH_NVIDIA_KEY
```

أو:

```dotenv
NVIDIA_API_KEYS_JSON=[{"id":"nvidia-primary","key":"REPLACE_WITH_NVIDIA_KEY","project":"default"}]
```

**Minimal verification.** ابدأ بـ`route-plan`، ثم اختر model موجودًا فعلًا في `config/models.json` وأجرِ call نصي محدودًا. تحقق من metadata الفعلية في الرد.

**Failure and recovery.** `403` قد يعني model access أو permission. `404` غالبًا model ID أو endpoint قديم. `429/503` quota أو worker limit. لا تضف نموذجًا إلى catalog لمجرد وجوده في public catalog؛ اختبره أولًا.

**Rotation and revocation.** أنشئ key جديدًا من NVIDIA Build، حدّث secret، اختبر `/v1/models` وcompletion، ثم احذف القديم.

## `AI_ROUTER_LOCAL_API_KEY` — مصادقة الخادم المحلي

**Purpose.** Bearer secret اختياري للخادم `serve`. عند عدم ضبطه، يسمح الخادم بالوصول من loopback فقط. عند binding إلى عنوان غير loopback، يطلب الكود هذا المفتاح.

**Classification.** Secret runtime value. **Required or optional.** اختياري مع `127.0.0.1`، ومطلوب عند `--host` غير loopback.

**How to create it.** أنشئ قيمة عشوائية محليًا باستخدام مدير أسرار أو مولد النظام. لا تستخدم قيمة من هذا الملف ولا تطبعها في terminal history.

```dotenv
AI_ROUTER_LOCAL_API_KEY=REPLACE_WITH_A_LONG_LOCAL_SECRET
```

**Minimal verification.** شغّل الخادم، ثم استخدم:

```bash
curl -H "Authorization: Bearer REPLACE_WITH_LOCAL_SECRET" http://127.0.0.1:8787/health
```

المتوقع JSON يحتوي `status: ok`. إذا لم تستخدم المفتاح، احذف header بدل إرسال placeholder.

**Failure and recovery.** `401` يعني header غير مطابق. تأكد من وجود `Bearer ` ومن نفس القيمة الموجودة في البيئة. لا ترسل المفتاح إلى GitHub logs إلا عبر Secret store.

**Rotation and revocation.** أوقف الخادم، غيّر القيمة، أعد تشغيله، وحدّث إعداد عميل VS Code إن كان يستخدمها. عند exposure أوقف الخادم واعتبر القيمة ملغاة.

## بطاقات المتغيرات غير السرية

### `GROQ_BASE_URL`

| الحقل | القيمة |
|---|---|
| Type | string URL |
| Default | `https://api.groq.com/openai/v1` |
| Valid values | Base URL متوافق مع Groq؛ لا تضف `/chat/completions` |
| Set location | `.env` أو GitHub Variables |
| Effect | يحدد endpoint الذي يستعمله Groq adapter |
| Verification | راجع `route-plan` ثم استخدم call محدودًا |
| Common mistake | وضع `/v1` مرتين أو وضع endpoint غير متوافق |

### `AI_ROUTER_CONFIG_DIR`

| الحقل | القيمة |
|---|---|
| Type | path |
| Default | `config` عند CLI الموثق |
| Valid values | مجلد يحتوي `providers.json` و`models.json` وملفات config الأخرى |
| Set location | `.env` أو global CLI flag `--config-dir` |
| Effect | يحدد catalog وprofiles وkey pools والسياسات |
| Verification | `ai-router --config-dir config summary` |
| Common mistake | تمريره بعد subcommand؛ يجب أن يأتي قبل `serve` أو `call-auto` |

### `AI_ROUTER_STATE_DB`

| الحقل | القيمة |
|---|---|
| Type | writable SQLite path |
| Default | `data/ai_router.db` |
| Valid values | مسار قابل للكتابة؛ استخدم volume في Docker |
| Set location | `.env` أو global CLI flag `--state-db` |
| Effect | يحفظ calls وcooldowns وmodel/key cursors |
| Verification | راقب `summary.state` بعد call |
| Common mistake | وضع DB داخل Git أو جعل volume غير قابل للكتابة |

## GitHub Secrets مقابل GitHub Variables

استخدم **Secrets** لكل API key و`AI_ROUTER_LOCAL_API_KEY`. استخدم **Variables** فقط للمسارات أو Base URL أو flags غير الحساسة. المسار العام هو: افتح المستودع → **Settings → Secrets and variables → Actions** → اختر **Secrets** أو **Variables** → **New repository secret/variable** → اكتب الاسم الحرفي → احفظ. سيظهر الاسم دون القيمة السرية.

## اختبار آمن بعد إضافة secret

```bash
cd /path/to/ai-provider-router
export PYTHONPATH=src
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/router-smoke.db summary
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/router-smoke.db call-auto --output-type text --operation credential_smoke --user 'Return exactly: credential works'
```

نجاح `summary` يثبت تحميل config فقط. النجاح الحقيقي هو JSON response من `call-auto`. عند الفشل، سجّل provider/model/status/error class فقط؛ لا تسجل key أو Authorization header أو base64.

## بعد التعرض العرضي

أوقف live calls، ثم revoke المفتاح من لوحة المزود، وأنشئ بديلًا، واستبدل Secret في كل بيئة. ابحث في Git history وCI artifacts، واحذف artifacts الحساسة وفق سياسة المستودع، ثم أعد health check. لا تعتمد على حذف الملف الحالي فقط؛ Git history قد يحتفظ بالقيمة.

## مراجع رسمية

[1]: https://ai.google.dev/gemini-api/docs "Gemini API documentation"
[2]: https://aistudio.google.com/app/apikey "Google AI Studio API keys"
[3]: https://console.groq.com/docs/api-reference "Groq API reference"
[4]: https://console.groq.com/keys "Groq API keys"
[5]: https://huggingface.co/docs/inference-providers/en/index "Hugging Face Inference Providers"
[6]: https://huggingface.co/settings/tokens "Hugging Face access tokens"
[7]: https://openrouter.ai/docs/api_reference/authentication "OpenRouter authentication"
[8]: https://openrouter.ai/settings/keys "OpenRouter API keys"
[9]: https://build.nvidia.com/ "NVIDIA Build"
[10]: https://docs.api.nvidia.com/ "NVIDIA API documentation"
[11]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions secrets"
