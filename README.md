# ai-provider-router

## 1. ما هو هذا المشروع؟

`ai-provider-router` مكتبة وCLI وخادم محلي صغير بلغة Python يضع عدة مزودي ذكاء اصطناعي ونماذج ومفاتيح خلف واجهة موحدة. يحدد النظام route حسب نوع المخرج، ثم يختار المرشح المناسب ويستعمل **طريقة الاستدعاء الخاصة بالنموذج** عبر `invocation_profile` عندما يحتاج المزود إلى اسم حقل مختلف أو parsing مختلف للاستجابة.

يدعم المشروع routes عامة للنص، والبحث المرتبط بـGoogle Search في Gemini، وتوليد الصور، والصوت، والترجمة، وembeddings، وتحليل الفيديو، وتهيئة جلسة live. كما يوفر `complete_chat()` وخادمًا محليًا متوافقًا مع OpenAI لاستخدامه من VS Code أو أي عميل يدعم Chat Completions.

> هذا المشروع لا يستضيف النماذج، ولا ينشئ مفاتيح API، ولا يضمن توفر نموذج خارجي لحسابك. نجاح `route-plan` يثبت صحة catalog المحلي فقط؛ أما نجاح network call فيتطلب مفتاحًا وصلاحية وحصة متاحة لدى المزود.

## 2. ما استخدامات المشروع؟

يمكن استعماله من برنامج Python، أو من CLI داخل GitHub Actions، أو من Docker، أو كخادم محلي تتصل به أدوات التطوير. في الوضع الافتراضي يستخدم كل providers المسموح بها في route، ويحافظ على ترتيب `config/models.json`. ويمكن للمستخدم تمرير provider/model صريحين، أو allowlist مثل `gemini,groq`, أو denylist مثل `--exclude-providers gemini`.

تظل Cline وأي إضافة VS Code عميلًا يدويًا مستقلًا. لا توجد نماذج Cline أو مفاتيح Cline أو أرصدة Cline داخل هذا المستودع.

## 3. VS Code: تشغيل router تلقائيًا لأي مشروع Windows

هذا هو المسار الأسهل لمستخدم Windows. تحتاج إلى تثبيت Python وVS Code، ثم إعداد المشروع مرة واحدة. بعد ذلك يمكن فتح أي Workspace في VS Code، وستبدأ الإضافة العالمية الخادم من مجلد router المحفوظ، لا من مجلد المشروع المفتوح.

### 3.1 تجهيز المشروع مرة واحدة

افتح **PowerShell** ونفّذ الأوامر التالية. هذه الأوامر تعمل في جهاز Windows، وليست أوامر تكتب داخل Chat في VS Code:

```powershell
cd $env:USERPROFILE
git clone https://github.com/ysrg2003/ai-provider-router.git
cd .\ai-provider-router
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
```

ضع مفاتيح المزود في `.env`، ثم لا تفتح هذا الملف في Git ولا ترفعه. لا تحتاج إلى تشغيل `ai-router serve` يدويًا بعد تثبيت الإضافة العالمية، إلا عند اختبار الخادم مباشرة.

### 3.2 تثبيت إضافة global autostart

من مجلد المشروع، شغّل الأمر التالي إذا كان Node.js مثبتًا:

```powershell
cd $env:USERPROFILE\ai-provider-router\vscode-global-autostart
npx @vscode/vsce package --no-dependencies
```

في VS Code افتح **Extensions: Install from VSIX...**، اختر الملف الناتج `ai-router-global-autostart-0.1.0.vsix`، ثم أعد تشغيل VS Code. الإضافة لا تقرأ أسرار المزود ولا تضعها في إعدادات VS Code؛ هي تشغّل سكربت PowerShell المحلي فقط.

بعد التثبيت افتح **Command Palette** بالضغط على `Ctrl+Shift+P`، ثم نفّذ **AI Router: Configure Project Path** واختر:

```text
C:\Users\YOUR_NAME\ai-provider-router
```

يجب أن يحتوي المسار المختار على الملفين التاليين:

```text
scripts\start_router_windows.ps1
.venv\Scripts\ai-router.exe
```

أغلق VS Code وافتحه من جديد. للتحقق من النجاح افتح PowerShell في أي مكان ونفّذ:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
```

النتيجة المتوقعة هي JSON يحتوي `status: ok` و`service: ai-provider-router`. إذا كان المسار صحيحًا، لا يهم أي مشروع أو Workspace فتحته في VS Code.

الأوامر المتاحة من Command Palette هي **AI Router: Start Now** و**AI Router: Show Status** و**AI Router: Stop Managed Server** و**AI Router: Configure Project Path**. الخادم مربوط افتراضيًا بـ`127.0.0.1`، ويستخدم mutex لمنع بدء نسخ مكررة من نوافذ VS Code المختلفة.

### 3.3 إعداد عميل OpenAI-compatible في VS Code

عند إعداد Cline أو أي عميل يدعم OpenAI Compatible، استخدم القيم الآتية. هذه القيم لا تعني أن Cline أصبح provider داخل router؛ العميل يتصل بالخادم المحلي فقط.

| الحقل | القيمة |
|---|---|
| API Provider | `OpenAI Compatible` |
| Base URL | `http://127.0.0.1:8787/v1` |
| Model ID | `ai-provider-router` |
| API Key | اتركه فارغًا عند loopback بلا مفتاح، أو استخدم قيمة `AI_ROUTER_LOCAL_API_KEY` المحلية |

يختار router تلقائيًا provider/model من routes المناسبة. ويمكن تمرير اختيار صريح عبر طلب HTTP باستخدام `router_provider` و`router_model`، بشرط أن يكون النموذج ضمن chain وقادرًا على Chat Completions. يعيد الخادم أيضًا `router_provider` و`router_model` و`router_route` في الاستجابة، ويضعها في headers باسم `X-AI-Router-Provider` و`X-AI-Router-Model`.

## 4. الاستخدام المباشر من GitHub أولًا

### 4.1 استدعاء CLI من مشروع GitHub آخر

في مستودعك الآخر، أنشئ الملف `.github/workflows/ai-router.yml` وضع فيه المثال التالي. استبدل `main` بcommit معروف عندما تريد تثبيت نسخة لا تتغير.

```yaml
name: AI Router smoke

on:
  workflow_dispatch:
    inputs:
      prompt:
        description: "Prompt"
        required: true
        default: "Return a short greeting"

permissions:
  contents: read

jobs:
  call-router:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout host project
        uses: actions/checkout@v4

      - name: Checkout router
        uses: actions/checkout@v4
        with:
          repository: ysrg2003/ai-provider-router
          ref: main
          path: ai-provider-router

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install router
        run: python -m pip install ./ai-provider-router

      - name: Plan route without network
        run: |
          ai-router --config-dir ai-provider-router/config \
            --state-db /tmp/ai_router.db route-plan \
            --output-type text --user "${{ inputs.prompt }}"

      - name: Call selected route
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: |
          ai-router --config-dir ai-provider-router/config \
            --state-db /tmp/ai_router.db call-auto \
            --output-type text --operation github_smoke \
            --user "${{ inputs.prompt }}" > router-response.json
          python -c "import json; d=json.load(open('router-response.json')); assert d.get('provider') and d.get('model') and d.get('route')"

      - name: Upload redacted response
        uses: actions/upload-artifact@v4
        with:
          name: ai-router-response
          path: router-response.json
          retention-days: 3
```

أضف `GROQ_API_KEY` من **Settings → Secrets and variables → Actions → New repository secret** في المستودع المضيف. لا تستخدم GitHub Variables للمفتاح السري. إذا أردت مزودًا آخر، استخدم اسم السر الموجود في [بطاقات الاعتمادات](docs/credentials.md). لا تطبع `.env` أو headers أو request body في logs.

### 4.2 استدعاء Python من GitHub أو من تطبيق آخر

إذا كان التطبيق المضيف Python، ثبّت tag أو commit ثم استورد `AIRouter`:

```bash
python -m pip install "git+https://github.com/ysrg2003/ai-provider-router.git@main"
```

```python
from ai_router import AIRouter

router = AIRouter(config_dir="/path/to/ai-provider-router/config", state_db="data/router.db")
try:
    result = router.complete_auto(
        user_prompt="اكتب إجابة قصيرة",
        output_type="text",
        operation="host_call",
        providers=["gemini", "groq", "huggingface"],
    )
    print(result["provider"], result["model"], result["text"])
finally:
    router.close()
```

من runtime غير Python استخدم CLI subprocess أو الخادم المحلي HTTP. لا تفترض أن `import ai_router` يعمل في لغة أخرى.

## 5. التشغيل المحلي على Windows أو Linux

المتطلبات هي Python 3.11 أو أحدث، و`requests`، و`python-dotenv`، وSQLite قابل للكتابة، ومفتاح لمزود واحد على الأقل عند إجراء live call. على Windows استخدم `py -3` بدل `python3` إذا لم يكن الأمر الأخير موجودًا.

```bash
git clone https://github.com/ysrg2003/ai-provider-router.git
cd ai-provider-router
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
```

في Windows PowerShell استخدم:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

ابدأ دائمًا بـroute plan، لأنه لا يرسل network request:

```bash
ai-router --config-dir config --state-db data/ai_router.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

ثم جرّب استدعاءً حقيقيًا بمفتاح مضبوط:

```bash
ai-router --config-dir config --state-db data/ai_router.db call-auto \
  --output-type text --operation local_smoke \
  --user "Return exactly: local router works"
```

## 6. التشغيل عبر Docker

يبني `Dockerfile` صورة CLI ولا يضمّن `.env` أو قاعدة SQLite. من جذر المشروع:

```bash
docker build -t ai-provider-router:local .
docker run --rm --env-file .env \
  -v "$PWD/data:/app/data" \
  ai-provider-router:local \
  --config-dir config --state-db /app/data/ai_router.db \
  call-auto --output-type text --user "اكتب إجابة قصيرة"
```

في PowerShell استخدم `${PWD}` بدل `$PWD` داخل المسار عند الحاجة. لا تستخدم `ARG` لتمرير API keys ولا تضع الأسرار في Dockerfile أو image layer. إذا احتجت خادم OpenAI داخل Docker، اربطه داخليًا بشبكة موثوقة واضبط `--local-api-key`؛ لا تعرض loopback server للإنترنت بلا مصادقة.

## 7. الاستجابة الموحدة والاختيار

الواجهة الأعلى مستوى هي `complete_auto()`. يحدد `output_type` أو يستنتج intent، ثم يختار route ويمرر الاستدعاء إلى adapter المتخصص. الاستجابة الناجحة تحتوي عادةً على `output_type` و`route` و`provider` و`model`، إضافةً إلى حقل المخرج مثل `text` أو `data_base64` أو `embeddings`.

| الحالة | الحقول الأساسية |
|---|---|
| نص أو ترجمة | `output_type`, `text`, `provider`, `model`, `route` |
| بحث | الحقول السابقة و`url_citations` وبيانات grounding |
| صورة أو صوت | `output_type`, `mime_type`, `data_base64`, `provider`, `model` |
| embeddings | `output_type`, `embeddings`, `provider`, `model` |
| تحليل فيديو | JSON التحليل و`provider`, `model`, `route` |
| خطة route | `route`, `models[]`، ولا توجد network call |
| Chat HTTP | OpenAI `choices[]` مع `router_provider`, `router_model`, `router_route` |

لا تكتب parser جديدًا لكل provider. اربط النموذج باسم `invocation_profile` في `config/models.json`. profile يحدد transport، وresponse format، وحقل max tokens، و`model_suffix`، و`reasoning_effort`، وparser مثل `json_object` أو `json_or_text_envelope`. Gemini يحتفظ باستدعاءاته الخاصة لـGenerateContent والبحث والصور والصوت والفيديو؛ لا يُستبدل بـOpenAI adapter.

### اختيار تلقائي أو صريح

بدون `--provider` و`--model` يستخدم CLI كل candidates الموجودة في route. للاختيار الصريح يجب تمرير الاثنين معًا:

```bash
ai-router --config-dir config call-auto \
  --output-type text --provider groq \
  --model openai/gpt-oss-120b \
  --user "اكتب إجابة قصيرة"
```

في Python استخدم `provider="groq", model="openai/gpt-oss-120b"`. يرفض router اختيارًا ناقصًا أو model غير موجود في route. أما `providers` و`--providers` فهي allowlist، و`exclude_providers` و`--exclude-providers` فهي denylist. إذا لم تمرر أيًا منهما فالإعداد الافتراضي هو **كل providers المتاحة**.

## 8. البحث والصور وباقي routes العامة

بحث الويب الفعلي يستخدم Gemini `generateContent` مع أداة Google Search عندما يكون route وmodel داعمين لذلك. يدمج router تعليمات البحث مع سؤال المستخدم في prompt واحد، ثم لا يعتبر النجاح مكتملًا إلا إذا وصلت citations قابلة للتطبيع إلى `url_citations`. لا يعني HTTP 200 وحده أن البحث نجح.

توليد الصورة يجب أن يعيد bytes أو Base64 صالحًا؛ استجابة تبدأ generation بلا `data_base64` ليست نجاحًا. الصوت وembeddings وتحليل الفيديو يستخدمون methods منفصلة في Gemini adapter. لذلك يجب إضافة model إلى route المناسب بدل وضعه في chain النصية عشوائيًا.

## 9. الأسرار والمتغيرات

الملف `.env.example` هو المصدر المختصر للأسماء. الشرح التفصيلي لكل قيمة، وطريقة الحصول عليها، ومكان حفظها، والتحقق، والتدوير والإلغاء موجود في [docs/credentials.md](docs/credentials.md).

| الاسم | التصنيف | الوظيفة |
|---|---|---|
| `GROQ_API_KEY` أو `GROQ_API_KEYS_JSON` | Secret | مفاتيح Groq مع دوران اختياري |
| `AI_ROUTER_GEMINI_KEYS_JSON` | Secret JSON | مفاتيح Gemini المرتبة |
| `AI_ROUTER_HF_KEYS_JSON` أو `HF_TOKEN` | Secret | Hugging Face Inference Providers |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY` | Secret | OpenRouter |
| `NVIDIA_API_KEY` أو `NVIDIA_API_KEYS_JSON` | Secret | NVIDIA API |
| `GROQ_BASE_URL` | Variable | الافتراضي `https://api.groq.com/openai/v1` |
| `AI_ROUTER_CONFIG_DIR` | Variable | مسار config عند استخدامه من البيئة |
| `AI_ROUTER_STATE_DB` | Variable | مسار SQLite عند استخدامه من البيئة |
| `AI_ROUTER_LOCAL_API_KEY` | Secret اختياري | Bearer للخادم المحلي عندما لا تريد anonymous loopback |

لا تضع أي قيمة حقيقية في `README.md` أو `config/` أو GitHub Issues أو logs. ملف `.env` وSQLite وVSIX الناتج محليًا غير مخصصة للcommit.

## 10. بنية المشروع

| المسار | الوظيفة |
|---|---|
| `src/ai_router/router.py` | orchestration، routes، fallback، selection، metadata |
| `src/ai_router/config.py` | تحميل providers/chains/profiles/keys/policy |
| `src/ai_router/providers/gemini.py` | GenerateContent، search، image، speech، embeddings، video |
| `src/ai_router/providers/openai_compatible.py` | JSON/text/chat وtools/tool_calls للمزودين المتوافقين |
| `src/ai_router/openai_server.py` | خادم HTTP محلي لعقد OpenAI Chat Completions |
| `src/ai_router/cli/main.py` | أوامر `summary` و`route-plan` و`call-json` و`call-auto` و`serve` |
| `src/ai_router/store.py` | cooldown وkey/model cursor وSQLite state |
| `config/providers.json` | provider IDs وbase URLs وkey pools |
| `config/models.json` | chains وoutput routes وmethods وprofiles |
| `config/invocation_profiles.json` | قواعد request/response الخاصة بالنماذج |
| `config/key_pools.json` | أسماء متغيرات الأسرار ودوران المفاتيح |
| `config/policies.json` | attempts وtimeouts وbackoff وcooldowns |
| `scripts/start_router_windows.ps1` | بدء آمن loopback على Windows مع mutex وhealth check |
| `vscode-global-autostart/` | مصدر إضافة VS Code العالمية، ولا تُدخل VSIX الناتجة إلى Git |
| `tests/` | اختبارات providers وroutes وprofiles وserver |
| `docs/` و`project-documentation/` | أدلة الاعتمادات والتشغيل والتكامل والسياق |

## 11. الخادم المحلي وعقد HTTP

شغّل الخادم يدويًا من جذر المشروع:

```bash
ai-router --config-dir config --state-db data/ai_router.db serve \
  --host 127.0.0.1 --port 8787
```

يعيد `GET /health` حالة الخدمة، ويعيد `GET /v1/models` model ID المحلي `ai-provider-router`. يقبل `POST /v1/chat/completions` مع `messages` و`tools` و`tool_choice` و`parallel_tool_calls`. يستخدم server chain `default`، ويقتصر chat على providers من نوع OpenAI-compatible؛ Gemini routes العامة لا تُحوّل قسرًا إلى raw OpenAI tools.

للمصادقة المحلية:

```bash
AI_ROUTER_LOCAL_API_KEY=replace-with-local-secret \
ai-router --config-dir config --state-db data/ai_router.db serve \
  --host 127.0.0.1 --port 8787
```

وعند ربطه بعنوان غير loopback، يجب تمرير `--local-api-key`. لا يسجل الخادم request bodies أو الأسرار، ويضع حدًا لحجم الطلب.

## 12. الأعطال الشائعة

| العرض | السبب المرجح | الإجراء |
|---|---|---|
| `401` أو `403` | Secret ناقص أو صلاحية غير مفعلة | افحص اسم المتغير وحساب المزود وpermission، ثم دوّر المفتاح إذا تعرض |
| `402` | خطة أو رصيد غير كافٍ لدى مزود OpenAI-compatible | استخدم provider/key متاحًا أو راجع خطة المزود؛ لا يزيل router القيد |
| `404` | model ID أو endpoint قديم | راجع catalog و`config/providers.json` ولا تخمّن اسمًا مشابهًا |
| `429` | quota/rate limit | اترك cooldown يعمل أو استخدم candidate آخر |
| `503` أو timeout | خدمة خارجية بطيئة أو خادم محلي غير مستمع | افحص `/health`، والمنفذ، والـlogs، ثم أعد المحاولة بحدود |
| `AllProvidersFailed` | فشل كل المرشحين أو لا توجد أسرار | افحص route plan و`secrets_loaded` وerror class بدون طباعة المفاتيح |
| صورة بلا `data_base64` | generation بدأ لكن لم تصل bytes | لا تعتبر HTTP 200 نجاحًا؛ تحقق من method/model والـquota |
| VS Code لا يصل إلى الخادم | الإضافة لم تجد project path أو `.venv` | نفّذ Configure Project Path واختر المجلد الذي يحتوي الملفين المطلوبين |
| `unrecognized arguments --config-dir` | وضعت global flags بعد subcommand | ضع `--config-dir` و`--state-db` قبل `serve` أو `call-auto` |

## 13. التحقق

من جذر المشروع نفّذ:

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m json.tool config/invocation_profiles.json >/dev/null
python3 -m compileall -q src scripts tests
PYTHONPATH="$PWD/src" python3 -m unittest discover -s tests -q
node --check vscode-global-autostart/extension.js
git diff --check
```

الاختبارات المحلية تستخدم mocks ولا تثبت quota أو availability الخارجية. للتحقق الحي نفّذ طلبًا واحدًا bounded بمفتاحك، وافحص `provider` و`model` و`route`، ولا تكتفِ بعلامة HTTP أو برسالة `listening`.

## 14. خريطة التوثيق

ابدأ بهذا الملف، ثم [دليل الاعتمادات](docs/credentials.md)، و[دليل الإعداد](project-documentation/configuration-guide.md)، و[عقد الاستجابة](project-documentation/response-contract.md)، و[دليل التشغيل](project-documentation/troubleshooting.md)، و[AI_CONTEXT.md](AI_CONTEXT.md). توثق [project-documentation/README.md](project-documentation/README.md) مسارات GitHub والمحلي وDocker والتكامل البرمجي بالتفصيل.

## References

[1]: https://github.com/ysrg2003/ai-provider-router "المستودع الأصلي"
[2]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "Using secrets in GitHub Actions"
[3]: https://docs.docker.com/reference/dockerfile/ "Dockerfile reference"
[4]: https://code.visualstudio.com/api/references/extension-manifest "VS Code extension manifest"
