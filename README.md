# ai-provider-router

`ai-provider-router` مكتبة وCLI بلغة Python لتوجيه طلبات الذكاء الاصطناعي إلى عدة providers وmodels وkeys خلف عقد JSON واحد. يحدد route حسب نوع المخرج، يطبق ترتيبًا قابلًا للتهيئة وfallback محدودًا، ويحفظ cooldown وcursor في SQLite.

> المشروع لا يستضيف النماذج ولا ينشئ API keys ولا يضمن أن كل model خارجي متاح لحسابك. نجاح route plan ليس دليلًا على نجاح network provider.

## 1. ما هو المشروع؟

يستقبل router طلبًا من CLI أو Python، يحدد intent أو يستخدم output type صريحًا، يختار model specs المناسبة، يطبق allowlist/denylist اختيارية للproviders، ثم يرسل الطلب إلى adapter المناسب. عند خطأ قابل للانتقال، يسجل الحالة ويتقدم إلى المرشح التالي وفق policy.

الـproviders المهيأة حاليًا هي ChatGPT replica-01 وreplica-02، Gemini، Hugging Face، OpenRouter، وNVIDIA. عند عدم تحديد provider filter يستخدم router كل providers الموجودة في route وفق ترتيب `config/models.json`.

## 2. ما استخداماته؟

يصلح المشروع لتوحيد النص والبحث الحي والصور والصوت والتضمين والترجمة وتحليل الفيديو عندما يكون adapter وmodel contract موجودين. ومن أمثلته استخدام Gemini فقط، استبعاد Gemini والاعتماد على Hugging Face ثم OpenRouter ثم NVIDIA، استخدام NVIDIA Riva للترجمة، أو دمج router في تطبيق Python أو workflow GitHub.

القدرات الخارجية ليست متساوية: catalog النموذج لا يثبت capability، وquota وpermissions وavailability مستقلة لكل provider/model/method. راجع [capability audit](project-documentation/capability-audit.md).

## 3. الاستخدام من GitHub أولًا

### 3.1 تثبيت router من tag داخل مشروعك

في workflow لمشروعك، ثبّت tag معروفًا بدل الاعتماد على branch متغير:

```yaml
- uses: actions/checkout@v4
  with:
    repository: ysrg2003/ai-provider-router
    ref: v1.2.27-default-all-providers
    path: ai-provider-router
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
- run: python -m pip install ./ai-provider-router
```

### 3.2 إضافة Secrets وBase URLs لـChatGPT

من مستودعك: **Settings → Secrets and variables → Actions → Secrets**، أضف Secret باسم `CHATGPT_API_SECRET_KEY`. يجب أن تكون قيمته مطابقة لقيمة `API_SECRET_KEY` الموجودة في Space-01 وSpace-02 إذا كنت تستخدم key pool المشترك الحالي. لا تضع هذا المفتاح في Variables أو YAML أو logs.

عناوين Spaces عامة وليست Secrets. يمكنك ترك القيم الافتراضية في `config/providers.json`، أو تسجيلها كـGitHub Variables من **Settings → Secrets and variables → Actions → Variables**:

```text
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
```

واستخدمها في workflow المستهلك هكذا:

```yaml
env:
  CHATGPT_API_SECRET_KEY: ${{ secrets.CHATGPT_API_SECRET_KEY }}
  CHATGPT_API_REPLICA_01_BASE_URL: ${{ vars.CHATGPT_API_REPLICA_01_BASE_URL }}
  CHATGPT_API_REPLICA_02_BASE_URL: ${{ vars.CHATGPT_API_REPLICA_02_BASE_URL }}
```

إذا لم تنشئ Variables، سيستخدم router العناوين الافتراضية من config. أما Cookies وStorage State الخاصة بـChatGPT فتبقى داخل Space ولا تُضاف إلى GitHub Secrets الخاصة بالrouter.

### 3.3 تشغيل أول تحقق

```yaml
- name: Plan route without network request
  run: |
    ai-router --config-dir ai-provider-router/config \
      --state-db /tmp/router.db \
      route-plan --output-type text --user "اكتب إجابة قصيرة"
```

بعد نجاح التخطيط، استخدم `call-auto` في smoke محدود. `test.yml` هو CI offline، بينما `live-smoke.yml` و`capability-audit.yml` و`nvidia-functional.yml` و`chatgpt-spaces-functional.yml` workflows يدوية أو live وتستهلك quota حسب السيناريو.

## 4. التشغيل المحلي

المتطلبات: Python 3.11+، `requests`، `python-dotenv`، SQLite قابل للكتابة، وcredential لمزود واحد على الأقل لأول live call.

للاستخدام الأبسط مع ChatGPT Spaces، ضع في `.env`:

```dotenv
CHATGPT_API_SECRET_KEY=<نفس API_SECRET_KEY في Space-01 وSpace-02>
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
```

الـBase URLs اختيارية لأن لها defaults في `config/providers.json`. لا تضع `CHATGPT_COOKIES_NETSCAPE` أو `CHATGPT_STORAGE_STATE_JSON` في `.env` الخاص بالrouter؛ هاتان القيمتان تخصان Space نفسها.

```bash
git clone https://github.com/ysrg2003/ai-provider-router.git
cd ai-provider-router
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
cp .env.example .env
```

ضع Secret في `.env` غير المتعقب، ثم:

```bash
ai-router --config-dir config --state-db /tmp/router.db summary
ai-router --config-dir config --state-db /tmp/router.db route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
ai-router --config-dir config --state-db /tmp/router.db \
  call-auto --output-type text --operation local_smoke \
  --user "Return exactly: local router works"
```

النجاح هو JSON غير فارغ يحتوي `route` و`intent`. عند الفشل، استخدم [troubleshooting](project-documentation/troubleshooting.md).

## 5. التشغيل عبر Docker

يوجد `Dockerfile` جذري لـCLI و`.dockerignore` يمنع `.env` وDB وartifacts من الصورة. نفّذ build في جهاز أو CI يحتوي Docker. أنشئ `.env` كما في القسم المحلي، وبالنسبة إلى ChatGPT تأكد من وجود:

```dotenv
CHATGPT_API_SECRET_KEY=<نفس API_SECRET_KEY في Space-01 وSpace-02>
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
```

مرّر `.env` وقت التشغيل فقط؛ لا تنسخه إلى image layers:

```bash
docker build -t ai-provider-router:local .
docker run --rm --env-file .env -v "$PWD/data:/app/data" \
  ai-provider-router:local --config-dir config \
  --state-db /app/data/ai_router.db \
  route-plan --output-type text --user "اكتب إجابة قصيرة"
```

لا تستخدم `ARG` لتمرير API keys ولا تضع secrets في Dockerfile أو image layers. الـDocker daemon غير متاح في بيئة التوثيق الحالية؛ build الفعلي يحتاج Docker host.

## 6. الاستخدام البرمجي

ثبّت tag ثم استورد `AIRouter`:

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
        operation="host_smoke",
        providers=["huggingface", "openrouter", "nvidia"],
    )
    print(result)
finally:
    router.close()
```

المعاملان `providers` و`exclude_providers` اختياريان. من لغة أخرى استخدم CLI subprocess واستهلك JSON stdout وexit code؛ لا تفترض أن Python import يعمل داخل runtime آخر.

## 7. اختيار providers

### كل providers افتراضيًا

عدم تمرير أي filter يستخدم جميع providers المتاحة في route:

```bash
ai-router --config-dir config route-plan \
  --output-type text --user "اكتب إجابة قصيرة"
```

### Allowlist

```bash
# Gemini فقط
ai-router --config-dir config route-plan \
  --output-type text --providers gemini --user "اكتب إجابة قصيرة"

# HF ثم OpenRouter ثم NVIDIA فقط
ai-router --config-dir config call-auto \
  --output-type text --providers huggingface,openrouter,nvidia \
  --user "أجب بإيجاز عن الذكاء الاصطناعي"
```

### Denylist

```bash
# كل providers المتاحة باستثناء Gemini
ai-router --config-dir config call-auto \
  --output-type text --exclude-providers gemini \
  --user "أجب بإيجاز عن آخر التطورات"
```

aliases هي `gemini`/`google_gemini`، `hf`/`huggingface`، `openrouter`، `nvidia`، و`chatgpt`. لا يستخدم router network request في `route-plan`. يرفض alias غير معروف، تقاطع allowlist وdenylist، أو عدم بقاء model مناسب.

## 8. الأسرار والمتغيرات

| الاسم | التصنيف | الوظيفة |
|---|---|---|
| `CHATGPT_API_SECRET_KEY` | Secret | مصادقة ChatGPT Space |
| `AI_ROUTER_CHATGPT_KEYS_JSON` | Secret JSON | key pool لـChatGPT |
| `AI_ROUTER_GEMINI_KEYS_JSON` | Secret JSON | Gemini |
| `AI_ROUTER_HF_KEYS_JSON` / `HF_TOKEN` | Secret | Hugging Face |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` / `OPENROUTER_API_KEY` | Secret | OpenRouter |
| `NVIDIA_API_KEYS_JSON` / `NVIDIA_API_KEY` | Secret | NVIDIA |
| `CHATGPT_API_REPLICA_01_BASE_URL` و`CHATGPT_API_REPLICA_02_BASE_URL` | Variable | override Base URL |
| `AI_ROUTER_CONFIG_DIR` | Variable | مجلد config |
| `AI_ROUTER_STATE_DB` | Variable | مسار SQLite |

راجع [دليل الاعتمادات الكامل](docs/credentials.md)، فهو يشرح لكل قيمة: لماذا نحتاجها، كيف نحصل عليها، الصلاحيات، placeholder، التخزين المحلي/GitHub، health check، expiry، rotation وrevocation. لا تضع `.env` أو tokens أو Cookies أو Storage State في Git.

## 9. بنية المشروع

| المسار | الوظيفة |
|---|---|
| `src/ai_router/router.py` | orchestration وroutes وfallback وprovider filters |
| `src/ai_router/config.py` | تحميل config وenv وkeys والسياسات |
| `src/ai_router/providers/` | adapters |
| `src/ai_router/store.py` | SQLite state |
| `config/providers.json` | provider IDs وURLs وtimeouts |
| `config/models.json` | chains وroutes وcapabilities |
| `config/key_pools.json` | Secret names وrotation |
| `config/policies.json` | attempts/backoff/cooldown |
| `scripts/` | live smoke وaudit |
| `tests/` | unit/regression tests |
| `.github/workflows/` | CI وmanual live workflows |
| `docs/` | credentials وprovider guides |
| `project-documentation/` | الدليل الشامل والتقارير |
| `Dockerfile` | CLI image |
| `pyproject.toml` | package وentrypoint |

## 10. الاختبار

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m compileall -q src scripts tests vendors/chatgpt-api
python3 -m unittest discover -s tests -v
git diff --check
```

الاختبارات offline لا تثبت quota أو session الخارجية. للـlive استخدم workflow محدودًا وسجّل status/provider/model/error class فقط.

## 11. الاستكشاف والأمان

| العرض | الإجراء الأول |
|---|---|
| `401/403` | طابق Secret والpermissions مع provider |
| `400/404` | راجع model ID وmethod وpayload contract |
| `429` | انتظر quota أو استخدم provider/key آخر |
| `503/timeout` | افحص health وavailability وcooldown |
| `AllProvidersFailed` | اقرأ آخر errors المنقحة وتحقق من credentials والroute |
| صورة بلا bytes | لا تعتبر HTTP 200 نجاحًا؛ افحص `images[]` وMIME والأبعاد |

لا تعيد image generation بلا حدود. بعد exposure، revoke/rotate من المصدر ثم حدّث Secret store وافحص Git history.

## 12. خريطة التوثيق

ابدأ بـ[فهرس project-documentation](project-documentation/README.md)، ثم [AI_CONTEXT](AI_CONTEXT.md)، ثم [credentials](docs/credentials.md)، ثم [configuration guide](project-documentation/configuration-guide.md)، ثم [troubleshooting](project-documentation/troubleshooting.md).

## References

[1]: https://github.com/ysrg2003/ai-provider-router "المستودع الرسمي"
[2]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "Using secrets in GitHub Actions"
[3]: https://docs.docker.com/reference/dockerfile/ "Dockerfile reference"
