# فهرس توثيق ai-provider-router

هذا هو **المسار التنفيذي للمبتدئ** في المستودع الأصلي `ai-provider-router`. ابدأ بتعريف المشروع، ثم اختر طريقة الاستخدام، ثم اقرأ بطاقات الأسرار والعقود قبل إجراء live call. أما [`AI_CONTEXT.md`](../AI_CONTEXT.md) فهو المرجع الهندسي لتعديل الكود.

## 1. ما هو المشروع؟

`ai-provider-router` مكتبة وCLI وخادم محلي Python يوجه الطلبات إلى عدة providers وmodels وkeys خلف عقد موحد. يحدد route حسب output type، ويطبق `invocation_profile` عندما يختلف request/response contract بين النماذج، ويسجل cooldown وcursor في SQLite.

يدعم المشروع text وGoogle Search grounding في Gemini وimage وaudio وtranslation وembeddings وvideo analysis وlive preparation، إضافةً إلى OpenAI-compatible `complete_chat()` وخادم `serve` المحلي. لا يستضيف المشروع النماذج، ولا يضمن quota أو availability خارجية، ولا يحتوي تكامل Cline.

## 2. ما استخداماته؟

يصلح كـPython library، أو CLI subprocess من مشروع آخر، أو خطوة GitHub Actions، أو Docker CLI، أو خادم محلي تتصل به أداة VS Code. default هو **كل providers المتاحة في route**. تستطيع استخدام allowlist أو denylist، أو اختيار provider/model صريحين عند الحاجة.

## 3. VS Code على Windows — يراه المستخدم مبكرًا

### النتيجة المتوقعة

بعد إعداد واحد، تبدأ إضافة VS Code العالمية خادم router عند `onStartupFinished` بغض النظر عن Workspace المفتوح. لا تحتاج إلى كتابة `ai-router serve` عند كل فتح.

### الإعداد خطوة بخطوة

1. في PowerShell ثبّت المشروع داخل مجلد ثابت:

```powershell
cd $env:USERPROFILE
git clone https://github.com/ysrg2003/ai-provider-router.git
cd .\ai-provider-router
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

2. ضع أسرار providers في `.env` فقط، كما في [`docs/credentials.md`](../docs/credentials.md).

3. ابنِ VSIX من مجلد الإضافة:

```powershell
cd $env:USERPROFILE\ai-provider-router\vscode-global-autostart
npx @vscode/vsce package --no-dependencies
```

4. في VS Code افتح **Extensions: Install from VSIX...** واختر الملف الناتج.

5. افتح **Ctrl+Shift+P → AI Router: Configure Project Path** واختر مجلد `ai-provider-router`. يجب أن يحتوي على:

```text
scripts\start_router_windows.ps1
.venv\Scripts\ai-router.exe
```

6. أعد تشغيل VS Code، ثم تحقق من PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
```

المتوقع `status: ok` و`service: ai-provider-router`. الأوامر الأخرى هي **AI Router: Start Now** و**AI Router: Show Status** و**AI Router: Stop Managed Server**. الخادم loopback افتراضيًا، والـmutex يمنع النسخ المكررة.

### إعداد Cline أو عميل OpenAI-compatible

| الحقل | القيمة |
|---|---|
| API Provider | `OpenAI Compatible` |
| Base URL | `http://127.0.0.1:8787/v1` |
| Model ID | `ai-provider-router` |
| API Key | فارغ مع loopback anonymous، أو قيمة `AI_ROUTER_LOCAL_API_KEY` |

Cline هنا عميل يدوي فقط؛ لا يضيفه router إلى fallback ولا يقرأ نماذجه أو رصيده.

## 4. GitHub Actions — أول boundary موصى به

أنشئ `.github/workflows/ai-router.yml` في مشروعك المضيف:

```yaml
name: AI Router smoke

on:
  workflow_dispatch:
    inputs:
      prompt:
        required: true
        default: "Return a short greeting"

permissions:
  contents: read

jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: ysrg2003/ai-provider-router
          ref: main
          path: ai-provider-router
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install ./ai-provider-router
      - name: Plan route
        run: |
          ai-router --config-dir ai-provider-router/config \
            --state-db /tmp/router.db route-plan \
            --output-type text --user "${{ inputs.prompt }}"
      - name: Bounded live call
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: |
          ai-router --config-dir ai-provider-router/config \
            --state-db /tmp/router.db call-auto --output-type text \
            --operation github_smoke --user "${{ inputs.prompt }}" > response.json
          python -c "import json; d=json.load(open('response.json')); assert d.get('provider') and d.get('model') and d.get('route')"
      - uses: actions/upload-artifact@v4
        with:
          name: ai-router-response
          path: response.json
          retention-days: 3
```

أضف `GROQ_API_KEY` من **Settings → Secrets and variables → Actions → Secrets → New repository secret**. route plan لا يستهلك quota، أما live call فيستهلك quota للمزود. استخدم [بطاقات الاعتمادات](../docs/credentials.md) لباقي providers ولا تطبع الأسرار.

## 5. التشغيل المحلي

من terminal نظيف:

```bash
git clone https://github.com/ysrg2003/ai-provider-router.git
cd ai-provider-router
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp .env.example .env
```

على Windows PowerShell استخدم `py -3` و`Copy-Item`. ابدأ بلا network:

```bash
ai-router --config-dir config --state-db data/ai_router.db summary
ai-router --config-dir config --state-db data/ai_router.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

ثم live call محدود:

```bash
ai-router --config-dir config --state-db data/ai_router.db call-auto \
  --output-type text --operation first_local_smoke \
  --user "Return exactly: local router works"
```

## 6. Docker

```bash
docker build -t ai-provider-router:local .
docker run --rm --env-file .env -v "$PWD/data:/app/data" \
  ai-provider-router:local --config-dir config \
  --state-db /app/data/ai_router.db \
  call-auto --output-type text --user "اكتب إجابة قصيرة"
```

استخدم `--env-file` أو secret manager وقت التشغيل. لا تستخدم `ARG` للمفاتيح ولا تضع `.env` في image layer.

## 7. الاستخدام البرمجي وHTTP

```python
from ai_router import AIRouter

router = AIRouter(config_dir="/path/to/ai-provider-router/config", state_db="data/router.db")
try:
    result = router.complete_auto(
        user_prompt="اكتب إجابة قصيرة",
        output_type="text",
        providers=["gemini", "groq", "huggingface"],
    )
    print(result["provider"], result["model"], result["route"])
finally:
    router.close()
```

لعميل غير Python استخدم CLI أو شغّل:

```bash
ai-router --config-dir config --state-db data/ai_router.db serve \
  --host 127.0.0.1 --port 8787
```

يقدم الخادم `GET /health` و`GET /v1/models` و`POST /v1/chat/completions`. يقبل `messages` و`tools` و`tool_choice` و`parallel_tool_calls`، ويمرر `router_provider` و`router_model` عند الاختيار الصريح. يعيد metadata آمنة في body وheaders. chat يقتصر على OpenAI-compatible providers؛ لا يحوّل Gemini raw tools قسرًا.

## 8. الاختيار والعقد الموحد

عدم تمرير `provider/model` يعني auto وكل providers في route. للاختيار الصريح مرر الاثنين:

```bash
ai-router --config-dir config call-auto --output-type text \
  --provider groq --model openai/gpt-oss-120b \
  --user "اكتب إجابة قصيرة"
```

`providers`/`--providers` allowlist و`exclude_providers`/`--exclude-providers` denylist. يرفض router provider/model الناقص أو غير الموجود في route. عند النجاح تظهر `provider` و`model` و`route`، ويظهر آخر اختيار المنقح في `summary.last_selection`.

لا يكتب المستهلك parser خاصًا لكل provider. في `config/models.json` يربط model بـ`invocation_profile`، وفي `config/invocation_profiles.json` توجد قواعد token field وresponse format وJSON/text envelope وreasoning. Gemini methods المتخصصة تبقى في `gemini.py`.

## 9. providers وroutes

| provider | الاستخدام الأساسي | القيد المهم |
|---|---|---|
| Gemini | text/search/image/audio/embedding/video | البحث الفعلي عبر GenerateContent Google Search |
| Groq | text/translation/chat | OpenAI-compatible profile و`max_completion_tokens` |
| Hugging Face | text وبعض النماذج المرنة | availability وpermissions تتغير |
| OpenRouter | text وfree routes | limits/model availability حسب الحساب |
| NVIDIA | text وroutes المهيأة | وجود model في catalog لا يثبت access أو quota |

لا يعني HTTP 200 نجاح صورة أو بحث؛ يجب فحص artifact أو `url_citations`.

## 10. الأسرار والمتغيرات

المرجع التفصيلي هو [`docs/credentials.md`](../docs/credentials.md). الأسماء الحالية هي `AI_ROUTER_GEMINI_KEYS_JSON`، و`GROQ_API_KEY`/`GROQ_API_KEYS_JSON`، و`AI_ROUTER_HF_KEYS_JSON`/`HF_TOKEN`، و`AI_ROUTER_OPENROUTER_KEYS_JSON`/`OPENROUTER_API_KEY`، و`NVIDIA_API_KEY`/`NVIDIA_API_KEYS_JSON`، و`AI_ROUTER_LOCAL_API_KEY` الاختياري. `GROQ_BASE_URL` و`AI_ROUTER_CONFIG_DIR` و`AI_ROUTER_STATE_DB` غير سرية.

## 11. خريطة الملفات

| المسار | المسؤولية |
|---|---|
| `src/ai_router/router.py` | routes وfallback وselection وmetadata |
| `src/ai_router/config.py` | JSON/env/keys/profiles/policy |
| `src/ai_router/providers/gemini.py` | Gemini specialized methods |
| `src/ai_router/providers/openai_compatible.py` | JSON/text/chat/tool calls |
| `src/ai_router/openai_server.py` | HTTP boundary المحلي |
| `src/ai_router/cli/main.py` | CLI و`serve` |
| `src/ai_router/store.py` | SQLite cursor/cooldown |
| `config/models.json` | chains وoutput routes وprofiles |
| `config/invocation_profiles.json` | request/response behavior |
| `scripts/start_router_windows.ps1` | Windows loopback starter |
| `vscode-global-autostart/` | مصدر الإضافة العالمية |
| `tests/` | regression وserver/provider tests |

## 12. الاختبارات واستكشاف الأعطال

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m json.tool config/invocation_profiles.json >/dev/null
python3 -m compileall -q src scripts tests
PYTHONPATH="$PWD/src" python3 -m unittest discover -s tests -q
node --check vscode-global-autostart/extension.js
git diff --check
```

`401/403` تعني secret أو permission، و`402` قد تعني plan/credits، و`404` تعني model أو endpoint، و`429` quota/rate، و`503/timeout` availability. افحص `summary` وroute plan وhealth، ولا تطبع الأسرار أو Authorization headers أو base64.

## 13. بقية الوثائق

| الهدف | الملف |
|---|---|
| أسرار ومتغيرات | [`docs/credentials.md`](../docs/credentials.md) |
| إعداد config | [`configuration-guide.md`](configuration-guide.md) |
| عقد الاستجابة | [`response-contract.md`](response-contract.md) |
| troubleshooting | [`troubleshooting.md`](troubleshooting.md) |
| تشغيل workflows | [`../docs/operations.md`](../docs/operations.md) |
| السياق الهندسي | [`../AI_CONTEXT.md`](../AI_CONTEXT.md) |
| المشروع الأم | [`../README.md`](../README.md) |

## مراجع

[1]: https://github.com/ysrg2003/ai-provider-router "المستودع الأصلي"
[2]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions Secrets"
[3]: https://docs.docker.com/reference/dockerfile/ "Dockerfile reference"
[4]: https://code.visualstudio.com/api/references/extension-manifest "VS Code extension manifest"
