# تكامل chatgpt-api كمزود Image خارجي

هذا الدليل يشرح استخدام Space الخاص بـ[chatgpt-api](https://github.com/ysrg2003/chatgpt-api) داخل `ai-provider-router`، ويشرح كذلك كيف يكرر مشروع آخر نفس التكامل. الحد الفاصل هو **HTTP API**: الراوتر لا ينسخ Playwright أو ملف cookies أو كود المتصفح من Space.

> خدمة `chatgpt-api` adapter غير رسمية تعتمد على جلسة ChatGPT داخل Hugging Face Space، وليست OpenAI Images API الرسمية. لذلك وضعها المشروع كخيار Image أول اختياري، مع fallback إلى Gemini Image عند غياب المفتاح أو فشل job أو timeout.

## العقد التنفيذي

يستخدم الراوتر المسار prompt-only التالي:

```text
POST /v1/visual-assets/jobs
GET  /v1/visual-assets/jobs/{job_id}
GET  /v1/visual-assets/jobs/{job_id}/download
```

يرسل الإنشاء JSON بالشكل:

```json
{"prompt":"..."}
```

ويستخدم كل طلب:

```http
Authorization: Bearer <CHATGPT_API_KEY>
```

ينتظر adapter انتقال الحالة إلى `done`، ثم ينزل الملف ويتحقق من أن `Content-Type` يبدأ بـ`image/`. أما تعديل صورة مرجعية مع قناع، فيبقى مسارًا منفصلًا تديره Gemini داخل الراوتر؛ لا يحوّل adapter الخارجي `image_data` إلى prompt نصي.

## إعداد Hugging Face Space

في Space، افتح **Settings → Variables and secrets → Secrets** وأضف:

| الاسم | القيمة | مكان الاستخدام |
|---|---|---|
| `API_KEY` | مفتاح قوي عشوائي | مصادقة HTTP في Space؛ لا يخرج منه |
| `CHATGPT_COOKIES_NETSCAPE` | cookies جلسة ChatGPT بصيغة Netscape | Playwright داخل Space فقط |

لا تضع `CHATGPT_COOKIES_NETSCAPE` في `ai-provider-router` أو أي مشروع مستدعٍ. لا تضع أيًا من القيم في Git أو Docker image أو artifact.

اختبر أن Space يعمل من خلال `GET /v1/models` أو واجهة OpenAPI. هذا الاختبار يثبت الوصول إلى الخدمة فقط، ولا يثبت أن جلسة ChatGPT قادرة على إكمال توليد صورة.

## إعداد ai-provider-router محليًا

من جذر المستودع:

```bash
cd /path/to/ai-provider-router
cp .env.example .env
```

أضف إلى `.env`، مع استبدال placeholder بالقيمة نفسها التي ضبطتها في Space تحت اسم `API_KEY`:

```dotenv
CHATGPT_API_BASE=https://yousefsg-chatgpt-api.hf.space
CHATGPT_API_KEY=ضع_هنا_قيمة_API_KEY_الخاصة_بالـSpace
AI_ROUTER_CONFIG_DIR=config
AI_ROUTER_STATE_DB=data/ai_router.db
```

يقرأ `config/key_pools.json` المتغير `CHATGPT_API_KEY` ضمن pool `chatgpt_image_default`. عند وجود مفتاح واحد يجب أن يعرض `summary` عددًا يساوي `chatgpt_image: 1`، من دون عرض القيمة.

لعدة مفاتيح يمكن استخدام pool صريح:

```dotenv
AI_ROUTER_CHATGPT_IMAGE_KEYS_JSON=[
  {"id":"chatgpt-image-1","key":"المفتاح_الأول","project":"chatgpt-api-space"},
  {"id":"chatgpt-image-2","key":"المفتاح_الثاني","project":"chatgpt-api-space"}
]
```

يستخدم الراوتر cursor مستقلًا لكل مفتاح وموديل وroute في SQLite. لا تشارك قاعدة SQLite نفسها بين workers متوازية من دون قفل خارجي.

## إعداد GitHub Actions

في مستودع `ysrg2003/ai-provider-router` افتح [Settings → Secrets and variables → Actions](https://github.com/ysrg2003/ai-provider-router/settings/secrets/actions)، ثم اختر **New repository secret** وأضف:

| الحقل | القيمة |
|---|---|
| Name | `CHATGPT_API_KEY` |
| Secret | القيمة نفسها الموجودة في Space تحت `API_KEY` |

لا تستخدم اسم `API_KEY` في مستودع الراوتر؛ الاسم الذي يقرأه workflow هو `CHATGPT_API_KEY`. ولا يكفي وجود `API_KEY` داخل Space، لأن GitHub Actions لا يستطيع قراءة Secrets الخاصة بـSpace.

إذا كان GitHub يعرض `chatgpt_image: 0` في تقرير smoke، فمعنى ذلك أن Secret لم يصل إلى job. راجع الاسم حرفيًا، وتأكد من أنه **repository secret** وليس Secret في مستودع آخر أو environment غير مربوط بالworkflow، ثم أعد تشغيل workflow. لا تحاول طباعة قيمة Secret للتشخيص؛ يكفي فحص العدد.

## التحقق المحلي دون استهلاك صورة

نفذ:

```bash
cd /path/to/ai-provider-router
python3 -m compileall -q src tests
python3 -m unittest discover -s tests -v
ruff check src tests
PYTHONPATH=src python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/ai-router-image-plan.db \
  route-plan --user "أنشئ صورة لدائرة زرقاء على خلفية بيضاء"
```

النتيجة المتوقعة في route plan هي:

```json
{
  "route": "image",
  "output_type": "image",
  "models": [
    {"provider":"chatgpt_image","model":"chatgpt-api"},
    {"provider":"google_gemini","model":"gemini-3-pro-image"}
  ]
}
```

هذا الفحص لا يرسل طلبًا خارجيًا ولا يستهلك الحصة.

## اختبار Image حي محدود

من واجهة GitHub Actions افتح **Actions → Live smoke tests → Run workflow**، واختر:

```text
scenario: image
```

لا تبدأ بـ`all` عند تشخيص المفتاح؛ سيناريو واحد يقلل الحصة ويجعل artifact أسهل في القراءة. النجاح الحقيقي يتطلب كل الشروط التالية:

| التحقق | الدليل المطلوب |
|---|---|
| تحميل المفتاح | `loaded_key_counts.chatgpt_image` أكبر من صفر |
| اختيار المسار | النتيجة تشير إلى `chatgpt_image/chatgpt-api` |
| اكتمال job | الحالة `done` ثم تنزيل ناجح |
| نوع المخرج | `image/png` أو `image/*` |
| حجم المخرج | `bytes_base64` أو حجم الملف أكبر من صفر |
| سلامة التقرير | لا توجد قيمة API key أو Base64 خام في artifact |

في التشغيل الحي بتاريخ 2026-08-16، كان تقرير run [31942957994](https://github.com/ysrg2003/ai-provider-router/actions/runs/31942957994) يوضح:

```text
loaded_key_counts: google_gemini=6, huggingface=1, openrouter=1, chatgpt_image=0
image: failed
fallback: Gemini Image attempts returned quota/429 RESOURCE_EXHAUSTED
```

هذا التشغيل **لم يختبر chatgpt-api فعليًا**؛ لأن Secret لم يصل إلى workflow، ولذلك قفز الراوتر إلى Gemini الذي كانت حصته مستنفدة. لا تُفسر هذه النتيجة بأن Space فشل أو بأن adapter غير صحيح. بعد إضافة `CHATGPT_API_KEY` في مستودع الراوتر، يجب إعادة تشغيل `scenario: image`، والنتيجة المنتظرة هي ظهور `chatgpt_image` بعدد مفاتيح واحد على الأقل قبل بدء job.

## المسار من مشروع آخر

إذا أراد مشروع آخر استخدام Space مباشرة بدل استدعاء `AIRouter`، فليستخدم عقد HTTP الموثق في [دليل إعادة الاستخدام في chatgpt-api](https://github.com/ysrg2003/chatgpt-api/blob/main/docs/reuse-in-another-project.md). الحد الأدنى هو:

```python
import os
import time
from pathlib import Path
import requests

base = os.environ["CHATGPT_API_BASE"].rstrip("/")
headers = {"Authorization": f"Bearer {os.environ['CHATGPT_API_KEY']}"}
create = requests.post(
    f"{base}/v1/visual-assets/jobs",
    headers={**headers, "Content-Type": "application/json"},
    json={"prompt": "Create a blue circle on a white background. No text."},
    timeout=60,
)
create.raise_for_status()
job_id = create.json()["job_id"]

for _ in range(60):
    state = requests.get(
        f"{base}/v1/visual-assets/jobs/{job_id}",
        headers=headers,
        timeout=30,
    )
    state.raise_for_status()
    payload = state.json()
    if payload.get("status") == "done":
        break
    if payload.get("status") in {"failed", "error", "cancelled"}:
        raise RuntimeError("image job failed")
    time.sleep(3)
else:
    raise TimeoutError("image job polling timed out")

image = requests.get(
    f"{base}/v1/visual-assets/jobs/{job_id}/download",
    headers=headers,
    timeout=60,
)
image.raise_for_status()
if not image.headers.get("content-type", "").startswith("image/"):
    raise RuntimeError("response is not an image")
Path("generated-image.png").write_bytes(image.content)
```

لا يحتاج هذا المشروع الآخر إلى Playwright أو `CHATGPT_COOKIES_NETSCAPE`. يحتاج فقط إلى `requests`، رابط Space، و`CHATGPT_API_KEY` في مدير أسرار آمن. يجب أن يضيف اختبارات mock للحالات `queued → done` و`401` و`failed` وtimeout، ثم يشغل smoke حيًا بصورة واحدة.

## fallback وسياسة الأخطاء

| الحالة | التصرف في الراوتر |
|---|---|
| Secret غير موجود أو عدد المفاتيح صفر | تخطي `chatgpt_image` والانتقال إلى Gemini Image |
| `401` أو `403` | تبريد المفتاح وتصنيف خطأ المصادقة ثم تجربة البديل |
| `429` أو `RESOURCE_EXHAUSTED` | تسجيل quota/rate limit ثم تجربة المفتاح أو النموذج التالي |
| `502` أو `503` أو `504` | retry محدود مع backoff ثم fallback |
| `status=failed` | عدم نشر صورة ناقصة والانتقال إلى البديل |
| timeout في polling | اعتبار نتيجة job غير مؤكدة وعدم استبدال المخرج المرجعي |
| response لا يبدأ بـ`image/` | رفض المخرج وعدم حفظه كصورة |

لا تطبع prompt حساسًا أو response body الخام أو header Authorization. التقرير الآمن يطبع provider، model، status، error type، HTTP status، MIME type، وحجم المخرج فقط.

## تدوير السر والتراجع

عند تدوير `API_KEY` داخل Space، حدّث `CHATGPT_API_KEY` في كل مشروع مستدعٍ ثم نفذ smoke محدودًا. إذا ظهرت قيمة المفتاح في log أو commit، ألغِ القيمة القديمة فورًا من مكان إصدارها، وأنشئ قيمة جديدة، ثم حدّث Secrets. إذا تعطلت Space أو انتهت جلسة ChatGPT، لا تحذف fallback؛ عطّل route الخارجي مؤقتًا في `config/models.json` أو اترك policy تنتقل تلقائيًا إلى Gemini.

## المراجع

1. [chatgpt-api: دليل visual-assets](https://github.com/ysrg2003/chatgpt-api/blob/main/docs_visual_assets.md).
2. [chatgpt-api: إعادة الاستخدام من مشروع آخر](https://github.com/ysrg2003/chatgpt-api/blob/main/docs/reuse-in-another-project.md).
3. [GitHub Actions encrypted secrets](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions).
4. [Hugging Face Spaces documentation](https://huggingface.co/docs/hub/spaces).
5. [Requests documentation](https://requests.readthedocs.io/en/latest/).
