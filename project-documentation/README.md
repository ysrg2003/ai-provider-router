# دليل ai-provider-router

هذا هو **الفهرس التنفيذي الرئيسي** لمشروع `ai-provider-router`. اقرأ الأقسام بالترتيب التالي؛ كل قسم يقود إلى الدليل التفصيلي المناسب، بينما يبقى [`AI_CONTEXT.md`](../AI_CONTEXT.md) مرجعًا هندسيًا للوكيل أو المطور الذي سيعدّل الكود.

## 1. ما هو هذا المشروع؟

`ai-provider-router` مكتبة وCLI بلغة Python لتوجيه طلبات الذكاء الاصطناعي JSON إلى عدة providers وفق route وmodel وkey pool مرتبة. يكتشف نوع المخرج مثل text أو image أو audio أو embedding أو translation، يختار النماذج القابلة للتنفيذ، يرسل الطلب إلى أول مرشح مناسب، ثم يستخدم fallback محدودًا عند الفشل القابل للانتقال. يحفظ SQLite حالة cooldown وcursor وتاريخ النجاح أو الفشل دون حفظ قيم الأسرار.

المشروع **لا يستضيف النماذج** ولا ينشئ مفاتيح المزودين ولا يضمن إتاحة كل نموذج في الكتالوج الخارجي. نجاح `route-plan` يثبت صحة التخطيط فقط؛ أما نجاح التكامل فيثبت باستجابة حقيقية أو artifact قابل للفحص.

> أول مبدأ تشغيلي: ابدأ بـ`summary` ثم `route-plan`، وبعدها نفّذ live smoke صغيرًا بمفتاح مزود واحد فقط.

## 2. ما استخدامات المشروع؟


يدعم المشروع أيضًا key rotation مرتبة، cooldown بعد أخطاء quota أو transient، search/maps grounding عند وجود capability مناسبة، وprovider selection لكل طلب عبر `--providers` و`--exclude-providers`. عند غياب الفلترين يستخدم **كل providers المتاحة افتراضيًا** وفق ترتيب route في `config/models.json`.

لحدود القدرات الحالية، راجع [كتالوج القدرات والتدقيق](capability-audit.md) و[دليل المزودين](providers.md). لا تصف model بأنه verified إلا إذا كان له اختبار payload وmethod مناسب.

## 3. كيفية استخدامه في مشروعك

### 3.1 GitHub Actions — المسار الموصى به أولًا

#### الخطوة 1: إنشاء مستودع مستهلك

أنشئ مستودعًا خاصًا أو عامًا لتطبيقك، ثم أضف router كـcheckout مستقل أو كاعتماد مثبت على tag. المسار الأبسط والأكثر قابلية للتدقيق هو checkout المشروعين:

```yaml
name: provider-smoke
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: ysrg2003/ai-provider-router
          ref: v1.2.27-default-all-providers
          path: ai-provider-router
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install router
        run: python -m pip install ./ai-provider-router
      - name: Run bounded route plan
        env:
          AI_ROUTER_GEMINI_KEYS_JSON: ${{ secrets.AI_ROUTER_GEMINI_KEYS_JSON }}
          AI_ROUTER_HF_KEYS_JSON: ${{ secrets.AI_ROUTER_HF_KEYS_JSON }}
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
          AI_ROUTER_OPENROUTER_KEYS_JSON: ${{ secrets.AI_ROUTER_OPENROUTER_KEYS_JSON }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          NVIDIA_API_KEYS_JSON: ${{ secrets.NVIDIA_API_KEYS_JSON }}
          NVIDIA_API_KEY: ${{ secrets.NVIDIA_API_KEY }}
        run: |
          set -euo pipefail
          ai-router --config-dir ai-provider-router/config \
            --state-db /tmp/provider-smoke.db \
            route-plan --output-type text --user "اكتب إجابة قصيرة"
```

نجاح هذه الخطوة يعني أن route plan والـconfig صالحان، ولا يعني أن كل provider يملك credential صالحًا. لإجراء live call، أضف خطوة `call-auto` بعد اختيار Secret واحد، واحتفظ بالـartifact منقحًا فقط.

#### الخطوة 2: إضافة Secrets وVariables


```text
```

يمكن ترك Variables فارغة لأن `config/providers.json` يحتوي defaults. لا تضع Cookies أو Storage State الخاصة بالـSpace في Secrets الخاصة بالrouter. استخدم أسماء المتغيرات الأخرى من [دليل الأسرار والمتغيرات](../docs/credentials.md). لا تطبع Environment أو Authorization headers في logs.

#### الخطوة 3: تشغيل workflow الموجود

في مستودع router، افتح **Actions** واختر أحد workflows اليدوية، ثم اضغط **Run workflow**:

| Workflow | الاستخدام |
|---|---|
| `live-smoke.yml` | smoke محدود لسيناريو text/search/image/audio/embedding وغيرها |
| `capability-audit.yml` | تدقيق نماذج متعددة مع التمييز بين passed وfailed وroute-only |
| `nvidia-functional.yml` | فحص نماذج NVIDIA النشطة أو قائمة محددة |
| `test.yml` | اختبارات offline على push وpull request |

ابدأ بسيناريو واحد. لا تستخدم `all` قبل معرفة quota ومدة كل provider.

### 3.2 تشغيل محليًا


```dotenv
```


من terminal نظيف:

```bash
git clone https://github.com/ysrg2003/ai-provider-router.git
cd ai-provider-router
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
```

افتح `.env` وضع Secret مزود واحد على الأقل. لا تحفظ `.env` في Git؛ هو موجود ضمن `.gitignore`. اختبر config دون network:

```bash
ai-router --config-dir config --state-db /tmp/router-summary.db summary
ai-router --config-dir config --state-db /tmp/router-summary.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

بعد ظهور summary منقح وroute صالح، نفّذ أول live call:

```bash
ai-router --config-dir config --state-db /tmp/router-text.db \
  call-auto --output-type text \
  --operation first_local_smoke \
  --user "Return exactly: local router works"
```

النجاح هو JSON غير فارغ يحتوي `route` و`intent`. إذا فشل، راجع [troubleshooting](troubleshooting.md) ولا تغيّر ترتيب models عشوائيًا.

### 3.3 Docker


```bash
docker build -t ai-provider-router:local .
docker run --rm --env-file .env -v "$PWD/data:/app/data" \
  ai-provider-router:local --config-dir config \
  --state-db /app/data/ai_router.db route-plan \
```

لا تضع المفتاح في Dockerfile أو build args أو image layers. لا يوجد Docker daemon مثبت في بيئة التطوير الحالية، لذلك يجب تنفيذ build في جهاز أو CI يحتوي Docker.

لا تضع Secret في `Dockerfile` أو `docker build --build-arg`. استخدم `--env-file` محليًا أو secret store في orchestrator. افحص الصورة والـlogs قبل نشرها.

### 3.4 الاستخدام البرمجي من Python

ثبّت tag محددًا ثم استورد public API:

```bash
python -m pip install "git+https://github.com/ysrg2003/ai-provider-router.git@v1.2.27-default-all-providers"
```

```python
from ai_router import AIRouter

router = AIRouter(config_dir="/path/to/ai-provider-router/config", state_db="data/router.db")
try:
    result = router.complete_auto(
        user_prompt="اكتب إجابة قصيرة",
        output_type="text",
        operation="host_python_smoke",
        providers=["huggingface", "openrouter", "nvidia"],
    )
    assert result["route"] and result["intent"] == "text"
finally:
    router.close()
```

المعاملان `providers` و`exclude_providers` اختياريان. عدم تمريرهما يعني كل providers؛ تمرير allowlist يعني providers المحددة فقط.

### 3.5 الاستهلاك من لغة أخرى أو خدمة أخرى

إذا كان مشروعك غير Python، استخدم CLI subprocess. ثبّت router في نفس worker، مرر JSON إلى stdout، واستخدم exit code للتحقق:

```text
host application -> process ai-router -> JSON stdout
                                      -> SQLite state DB
```

اجعل كل worker يملك State DB مستقلة أو استخدم storage contract واضحًا؛ لا تشارك SQLite file بين عمليات متوازية بلا locking strategy. يمكن أيضًا وضع router خلف HTTP service، لكن هذا boundary **مقترح يحتاج adapter/service host منفصلًا** وليس serverًا مضمنًا في هذا المستودع.

## 4. الأسرار والمتغيرات

يوجد مرجع تفصيلي مستقل في [docs/credentials.md](../docs/credentials.md). هذا القسم يشرح الخريطة فقط:

| الاسم | النوع | الوظيفة |
|---|---|---|
| `AI_ROUTER_GEMINI_KEYS_JSON` | Secret JSON array | مفاتيح Gemini |
| `AI_ROUTER_HF_KEYS_JSON` / `HF_TOKEN` | Secret | مفاتيح Hugging Face وfallback المفرد |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` / `OPENROUTER_API_KEY` | Secret | مفاتيح OpenRouter وfallback المفرد |
| `NVIDIA_API_KEYS_JSON` / `NVIDIA_API_KEY` | Secret | مفاتيح NVIDIA وfallback المفرد |
| `AI_ROUTER_CONFIG_DIR` | Variable | مجلد `config`، default=`config` |
| `AI_ROUTER_STATE_DB` | Variable | مسار SQLite، default=`data/ai_router.db` |

لكل بطاقة في docs/credentials: الاسم الدقيق، سبب الحاجة، الحساب والصلاحيات، رابط الحصول، الخطوات، safe placeholder، مكان التخزين، طريقة قراءة الكود، health check، الفشل، expiry، rotation وrevocation. لا توجد قيم حقيقية في الوثائق.

## 5. بنية المشروع والمجلدات والملفات

| المسار | المسؤولية |
|---|---|
| `src/ai_router/router.py` | intent، route/chain resolution، provider filters، fallback، retries، state recording |
| `src/ai_router/config.py` | تحميل JSON و`.env`، override Base URL، key parsing، policies، public summary |
| `src/ai_router/intent.py` | اكتشاف output type وgrounding من prompt أو الخيارات الصريحة |
| `src/ai_router/providers/base.py` | عقود adapter وProviderResponse وProviderError |
| `src/ai_router/providers/gemini.py` | Gemini REST/interactions وimage/TTS/embedding/video methods |
| `src/ai_router/providers/openai_compatible.py` | Hugging Face وOpenRouter وNVIDIA عبر OpenAI-compatible contract |
| `src/ai_router/store.py` | SQLite state، cursor، cooldown، success/failure metadata |
| `src/ai_router/tools.py` | بناء search/maps tools حسب intent وroute |
| `src/ai_router/cli/main.py` | أوامر `summary` و`route-plan` و`call-json` و`call-auto` |
| `config/providers.json` | provider IDs وkind وbase URL وkey pool وtimeout |
| `config/models.json` | model chains وoutput routes وmethods وcapabilities |
| `config/key_pools.json` | أسماء Secrets وfallback وrotation |
| `config/policies.json` | max attempts وtimeouts وbackoff وcooldowns |
| `config/nvidia_free_catalog.json` | snapshot كتالوج NVIDIA العام |
| `scripts/` | live smoke وcapability audit وfunctional tests |
| `tests/` | regression tests للعقود والـstate والـroutes والـproviders |
| `.github/workflows/` | offline CI وmanual live workflows |
| `docs/` | أدلة credentials وproviders والتشغيل والتكاملات |
| `project-documentation/` | التقارير، الأدلة، checkpoint، artifacts المنقحة |
| `Dockerfile` | صورة CLI اختيارية للـrouter |
| `pyproject.toml` | package metadata وentrypoint `ai-router` |

## 6. دورة البيانات والعقود

```text
CLI أو Python input
  -> detect_intent / explicit output_type
  -> resolve route أو chain
  -> provider allowlist/denylist
  -> model capability filtering
  -> key pool وSQLite cooldown/cursor
  -> provider adapter وbounded timeout
  -> ProviderResponse payload
  -> route/intent metadata
  -> JSON أو image/audio/embedding artifact
```

`ProviderError` يحمل error class وstatus code وretryability. الأخطاء transient أو quota قد تؤدي إلى fallback محدود؛ الأخطاء terminal أو عدم وجود model مناسب توقف الطلب. لا يعيد router الأسرار في exception أو summary.

## 7. المزودون والقدرات

| provider | المسارات الأساسية | ملاحظات |
|---|---|---|
| Gemini | text/search/image/audio/embedding/video analysis | payload خاص بـGemini، capability حسب model |
| Hugging Face | text وبعض multimodal حسب model | OpenAI-compatible، availability تتغير |
| OpenRouter | text/free وبعض input modalities | model availability وquota حسب الحساب |
| NVIDIA | text وRiva translation | 12 نموذجًا عامًا مفعلة من catalog 57؛ ليس كل catalog route تنفيذياً |

الاختيار الافتراضي هو كل providers الموجودة في route. استخدم [capability-audit](capability-audit.md) لتمييز passed وfailed وroute-only.

## 8. الاختبارات والتشغيل والإصدارات

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m unittest discover -s tests -v
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/router.db summary
```

الاختبارات offline لا تثبت quota أو صحة session الخارجية. للـlive استخدم workflow محدودًا، ولا تسجل headers أو base64 أو prompts الحساسة. آخر capability audit موثق في [capability-audit.md](capability-audit.md)، وآخر live evidence في [live-test-report-2026-08-19.md](live-test-report-2026-08-19.md).

## 9. الاستكشاف والأمان

ابدأ بـ`summary` ثم `route-plan`. عند 401/403 افحص Secret وpermissions. عند 400/404 افحص model/method. عند 429 انتظر quota أو استخدم provider آخر. عند 503/timeout افحص health وavailability وSQLite cooldown، ولا تكرر image generation بلا حاجة.

لا تضع `.env` أو Cookies أو Storage State أو API tokens أو Authorization headers في Git أو Docker image أو artifacts. بعد التعرض، revoke/rotate من المصدر، حدّث Secret store، ثم نفّذ smoke محدودًا.

## 10. مراجع القراءة

| الهدف | الوثيقة |
|---|---|
| البدء من الصفر | هذا الملف |
| أسرار router والمتغيرات | [`docs/credentials.md`](../docs/credentials.md) |
| config وroutes | [`configuration-guide.md`](configuration-guide.md) و[`../config/README.md`](../config/README.md) |
| providers | [`providers.md`](providers.md) |
| GitHub/live operations | [`../docs/operations.md`](../docs/operations.md) |
| troubleshooting | [`troubleshooting.md`](troubleshooting.md) |
| AI agent context | [`../AI_CONTEXT.md`](../AI_CONTEXT.md) |
| artifact/file inventory | [`artifact-inventory.md`](artifact-inventory.md) |
| release history | [GitHub releases](https://github.com/ysrg2003/ai-provider-router/releases) |

## المراجع

[1]: https://github.com/ysrg2003/ai-provider-router "المستودع الرسمي"
[2]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions Secrets"
[3]: https://docs.docker.com/engine/reference/builder/ "Dockerfile reference"
[4]: https://huggingface.co/docs/hub/spaces-overview "Hugging Face Spaces"

## 14. تقارير تحقق حديثة

- [إصلاح النصوص الطويلة في replica-02](replica-02-long-prompt-fix-2026-08-21.md): السبب الجذري، stack trace المنقح، الإصلاح، ونتيجة اختبار 1,500 حرف.
