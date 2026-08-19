# تكامل NVIDIA NIM

## النتيجة المستهدفة

بعد اتباع هذا الدليل، يستطيع المشغّل إضافة مفتاح NVIDIA بأمان، التحقق من `/v1/models`، اختبار completion محدود، وفهم لماذا يحتوي catalog على 57 Free Endpoint بينما تفعّل routes الحالية 15 نموذجًا فقط.

> هذه الميزة تعتمد على حساب NVIDIA وquota وavailability خارجية. لا تعدّل routes بناءً على منشور أو صفحة catalog فقط.

## المتطلبات

| المتطلب | الحالة |
|---|---|
| حساب NVIDIA Build | مطلوب |
| API key جديد غير مكشوف | مطلوب للـlive |
| Python 3.11+ و`requests` | مطلوب |
| router config الحالي | مطلوب |
| quota كافية لاختبار completion محدود | مطلوب |

للحصول على المفتاح، اتبع بطاقة `NVIDIA_API_KEY` في [`../docs/credentials.md`](../docs/credentials.md) والرابط الرسمي [NVIDIA Build](https://build.nvidia.com/). لا تستخدم مفتاحًا ظهر في محادثة أو log.

## Step 1: تخزين المفتاح

نفذ من جذر المشروع بعد نسخ `.env.example` إلى `.env` غير المتعقب:

```bash
NVIDIA_API_KEY=nvapi-<new-key>
```

أو pool مرتب:

```bash
NVIDIA_API_KEYS_JSON=["nvapi-<new-key>"]
```

النتيجة المتوقعة: `summary` يعرض provider `nvidia` دون أن يعرض المفتاح. إذا ظهر token في output، أوقف التشغيل وافحص redaction قبل live call.

## Step 2: تحقق المصادقة والكتالوج

من طرفية محلية، لا تسجل header أو response كاملًا:

```bash
python3 - <<'PY'
import os
import requests

key = os.environ["NVIDIA_API_KEY"]
response = requests.get(
    "https://integrate.api.nvidia.com/v1/models",
    headers={"Authorization": f"Bearer {key}"},
    timeout=30,
)
print({"status": response.status_code, "content_type": response.headers.get("content-type")})
print({"has_data": isinstance(response.json().get("data"), list)} if response.headers.get("content-type", "").startswith("application/json") else {})
PY
```

Expected result هو HTTP 200 و`has_data: True`. `401/403` يعني key/account verification؛ `429` يعني limit؛ `5xx` يعني availability. لا تنتقل إلى اختبار 30 نموذجًا قبل إصلاح هذه النتيجة.

## Step 3: اختبر model واحدًا

استخدم model ID موجودًا في `config/nvidia_free_catalog.json` وفعّالًا في `config/models.json`. المثال التالي يستخدم placeholder بدل model حقيقي كي لا يصبح الدليل stale:

```bash
python3 - <<'PY'
import os
import requests

model = os.environ.get("NVIDIA_TEST_MODEL", "<enabled-nvidia-model>")
key = os.environ["NVIDIA_API_KEY"]
response = requests.post(
    "https://integrate.api.nvidia.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={"model": model, "messages": [{"role": "user", "content": "Return exactly: NVIDIA smoke works"}], "max_tokens": 32},
    timeout=120,
)
print({"status": response.status_code, "json": response.json() if response.status_code < 300 else {"error": "redacted"}})
PY
```

Expected result: HTTP 200 وmessage نصية. إذا كان model لا يقبل chat text، سجله `failed` أو `deferred` ولا تضفه إلى text route.

## Step 4: افهم catalog مقابل routes

`config/nvidia_free_catalog.json` snapshot بحثي يحتوي 57 Free Endpoint. نتائج live السابقة صنفت 30 مرشحًا، ونجح 15 في completion نصي محدود. `config/models.json` يفعّل الناجح فقط ضمن سلسلة `nvidia_free` وبعد OpenRouter في السلاسل المطلوبة.

الترتيب الحالي من الأعلى إلى الأقل موثق في [`../docs/nvidia-ranking.md`](../docs/nvidia-ranking.md). الترتيب **ترتيب capability عام مبني على family/parameter/reasoning/multimodal evidence ضمن الاختبار**، وليس benchmark موحدًا ولا وعدًا بالجودة أو السرعة.

## Step 5: شغّل router

```bash
export PYTHONPATH=src
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/nvidia-router.db \
  call-auto \
  --output-type text \
  --operation nvidia_smoke \
  --user 'Return exactly: NVIDIA router works'
```

Expected success: JSON فيه `route` و`intent`. قد يختار route providerًا أسبق مثل ChatGPT أو Gemini؛ لا تعتبر ذلك فشل NVIDIA. لاختبار NVIDIA تحديدًا استخدم chain الذي يحتوي `nvidia_free` عبر Python API أو عطّل providers الأخرى مؤقتًا في نسخة config خارج Git.

## Step 6: اختبار NVIDIA من GitHub Actions

يحتوي workflow [`../.github/workflows/live-smoke.yml`](../.github/workflows/live-smoke.yml) على scenario باسم `nvidia` ويحقن القيم من GitHub **Secrets**، لا من GitHub Variables. أضف أحد الاسمين التاليين في مستودع `ysrg2003/ai-provider-router` عبر **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | التنسيق | مستهلكه |
|---|---|---|
| `NVIDIA_API_KEY` | `nvapi-<new-key>` | fallback لمفتاح مفرد |
| `NVIDIA_API_KEYS_JSON` | `["nvapi-<new-key>"]` | pool مرتب |

يجب ألا يظهر secret في workflow logs أو artifact. من صفحة GitHub افتح **Actions → Live smoke → Run workflow**، اختر `nvidia`، ثم اضغط **Run workflow**. النجاح يتطلب أن تكون الخطوات خضراء وأن يحتوي artifact `live-smoke-<run-id>/live-smoke.json` على `"status": "completed"` ونتيجة `nvidia` بحالة `passed`؛ لا يكفي ظهور رسالة بدء التشغيل.

إذا كان workflow يفشل في خطوة `test -n`، فالـSecret غير موجود أو فارغ. إذا كانت النتيجة `401/403` فالمفتاح أو حساب NVIDIA غير صالح. إذا كانت `429/503` فهذه quota/availability؛ لا تعِد تشغيل workflow مرات متتابعة. هذا الاختبار يستهلك طلبًا حيًا محدودًا من NVIDIA.

**آخر نتيجة موثقة:** التشغيل [32217577979](https://github.com/ysrg2003/ai-provider-router/actions/runs/32217577979) على `main` اكتمل بنجاح؛ artifact المنقح سجل `scenario_filter=nvidia` و`route=nvidia_free` و`status=passed` و`loaded_key_counts.nvidia=1` وJSON field باسم `ok`. لم تُحفظ قيمة المفتاح أو Authorization header. هذه النتيجة تثبت completion نصيًا عبر السلسلة الحالية، ولا تثبت capabilities غير النصية.

## تحديث model جديد

1. أضف entry إلى catalog مع source/status/evidence، دون key.
2. نفّذ `/v1/models` ثم completion محدودًا.
3. سجّل status وmodel ID وسبب القبول/الرفض في catalog.
4. أضف model spec إلى `config/models.json` فقط إذا كان method وoutput capability مثبتين.
5. أضف regression test للعدد والترتيب والroute placement.
6. حدّث `docs/nvidia-ranking.md` وREADME وrelease notes.
7. شغّل `compileall`, unit tests, `diff --check`, secret scan، ثم live smoke واحدًا.

## استكشاف الأخطاء

| العرض | السبب المرجح | الإجراء |
|---|---|---|
| `401/403` | key غير صالح أو account غير مفعّل | أصدِر key جديدًا من NVIDIA Build، لا تكرر الطلبات |
| `400` | model/method/payload غير مدعوم | افحص model ID و`response_format` وmessages |
| `429` | rate/quota | انتظر cooldown أو استخدم key مصرحًا، ولا تفتح flood |
| `503` | worker/model مؤقتًا غير متاح | سجّل deferred واترك fallback يعمل |
| timeout | endpoint بطيء أو مزدحم | استخدم timeout route، لا ترفع retries بلا حد |
| router يتجاوز NVIDIA | لا يوجد key أو key/model في cooldown | افحص `summary` وSQLite state ثم اختبر key واحدًا |

## الأمن والتدوير

لا تحفظ `Authorization` headers أو response الخام إذا احتوى provider metadata حساسة. عند exposure ألغِ المفتاح فورًا من NVIDIA Build، أنشئ بديلًا، حدّث `.env`/GitHub Secret، واختبر `/v1/models` مرة واحدة. راجع [`../docs/credentials.md`](../docs/credentials.md) بدل نسخ المفتاح في issue أو commit.
