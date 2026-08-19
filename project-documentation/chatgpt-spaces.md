# ChatGPT Spaces المعتمدة في ai-provider-router

## النطاق

يعتمد router نسختين مستقلتين فقط من `chatgpt-api` كمصادر ChatGPT مرتبة. تبقى Space قديمة محفوظة على Hugging Face خارج هذا المشروع، لكنها لا تُستخدم ولا تظهر في configuration أو routes أو workflow الاختبار.

| الترتيب | Provider ID | Base URL | الحالة الوظيفية الأخيرة |
|---:|---|---|---|
| 1 | `chatgpt_space_replica_01` | `https://yousefsg-chatgpt-api-replica-01.hf.space` | text/search نجحا؛ image مؤجلة بسبب quota |
| 2 | `chatgpt_space_replica_02` | `https://yousefsg-chatgpt-api-replica-02.hf.space` | text/search نجحا؛ image مؤجلة بسبب quota في آخر جولة |

## الحدود الأمنية

تحتوي كل Space على Chromium وCookies أو Storage State الخاصة بها. لا تدخل Cookies أو Storage State إلى router، ولا تُحفظ في Git. يستخدم router `API_SECRET_KEY` فقط لمصادقة HTTP، ويمكنه قراءة قيمة واحدة من `CHATGPT_API_SECRET_KEY` أو مصفوفة مرتبة من `AI_ROUTER_CHATGPT_KEYS_JSON`.

## الإعداد

تعريف providers موجود في `config/providers.json`، وترتيب المسارات في `config/models.json`. المتغيرات العامة الاختيارية هي:

```dotenv
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
```

أما السر فيُضبط في router عبر:

```dotenv
CHATGPT_API_SECRET_KEY=YOUR_SPACE_API_SECRET
AI_ROUTER_CHATGPT_KEYS_JSON=[]
```

يجب أن تطابق قيمة router Secret قيمة `API_SECRET_KEY` في Space المقابلة. لا تضع `CHATGPT_COOKIES_NETSCAPE` أو `CHATGPT_STORAGE_STATE_JSON` في router.

## ترتيب المسارات

| المسار | ترتيب ChatGPT |
|---|---|
| `text` | replica-01 ثم replica-02 |
| `text_grounded_search` | replica-01 ثم replica-02 |
| `image` | replica-01 ثم replica-02 |
| `image_grounded_search` | replica-01 ثم replica-02 |

تعمل providers الأخرى الموجودة في route كـfallback بعد ChatGPT إذا سمحت capability filtering بذلك. عند نجاح replica-01 لا يُرسل الطلب نفسه إلى replica-02 لتجنب التكرار؛ عند فشلها ينتقل router وفق سياسة retry وcooldown.

## قاعدة الصور

لا يُفعل فحص DOM أو image extraction في text/search. للصورة فقط، ينتظر adapter generation، يرفض الصور القديمة وfavicon وavatar، ويفك `data_url` أو ينزّل `src` عند توفره. HTTP 200 وحده لا يكفي؛ النجاح يتطلب bytes صورة صالحة وفحص MIME والأبعاد.

## آخر live smoke

بعد readiness check ناجح للنسختين، أُجريت الحالات بالتسلسل: نص، بحث حي، ثم طلب صورة واحد فقط لكل نسخة.

| Space | النص | البحث الحي | الصورة |
|---|---|---|---|
| replica-01 | passed، HTTP 200، `LIVE_TEXT_OK` | passed_nonempty، HTTP 200، إجابة مع مصدر | quota، HTTP 200، `images_count=0` |
| replica-02 | passed، HTTP 200، `LIVE_TEXT_OK` | passed، HTTP 200، إجابة مع مصدر | quota، HTTP 200، `images_count=0` |

في حالتي الصورة، احتوى الرد على رسالة ChatGPT Free plan image-generation limit. لم تُرسل retries إضافية. يوجد دليل تاريخي سابق على PNG صالح من replica-02 بحجم 831230 bytes وأبعاد 1254×1254، لكن quota الحالية منعت إعادة التحقق في آخر جولة.

التقرير الكامل في [`live-test-report-2026-08-19.md`](live-test-report-2026-08-19.md)، والـartifacts في [`live-verification-2026-08-19/summary.json`](live-verification-2026-08-19/summary.json).

## الاختبار الوظيفي

يستخدم `.github/workflows/chatgpt-spaces-functional.yml` السكربت `scripts/chatgpt_spaces_functional.py`، وقائمة الاختبار داخله مقيدة بالمعرفين:

```text
chatgpt_space_replica_01
chatgpt_space_replica_02
```

الاختبار متسلسل لتجنب concurrent browser/session load وbursts غير الضرورية في quota. نفّذ text/search أولًا، ثم image مرة واحدة فقط عندما تكون هناك حاجة.

## التشغيل الآمن

```bash
curl -fsS https://yousefsg-chatgpt-api-replica-01.hf.space/health
curl -fsS https://yousefsg-chatgpt-api-replica-02.hf.space/health

PYTHONPATH=src python3 -m compileall -q src tests vendors/chatgpt-api
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

إذا كان `/health` جاهزًا لكن text/search يفشلان، افحص Secret والجلسة داخل Space. إذا ظهرت رسالة Free plan limit للصورة، انتظر reset ولا تغيّر Base URL أو key pool.

## الملفات ذات الصلة

| الملف | الوظيفة |
|---|---|
| `config/providers.json` | تعريف Space-01 وSpace-02 |
| `config/models.json` | ترتيب providers في routes |
| `scripts/chatgpt_spaces_functional.py` | live smoke للنسختين فقط |
| `src/ai_router/providers/chatgpt_space.py` | HTTP adapter |
| `project-documentation/live-test-report-2026-08-19.md` | التقرير الحي الأخير |
| `project-documentation/live-verification-2026-08-19/` | artifacts JSON redacted |
