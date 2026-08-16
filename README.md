# ai-provider-router

`ai-provider-router` هو راوتر Python مستقل يستقبل طلبًا واحدًا، يحدد نوع المخرج، ثم يختار provider/model/key بالترتيب الموجود في `config/`. عند نجاح المحاولة يعيد النتيجة فورًا؛ وعند خطأ قابل للتصنيف يسجل الحالة في SQLite وينتقل إلى العنصر التالي وفق سياسة retry وcooldown.

> **قاعدة الأولوية الحالية:** يعتمد route الصور والنصوص والبحث الحي على `chatgpt_conversation` أولًا. هذه الخدمة تستهلك مشروع `chatgpt-api` عبر HTTP وتفتح المحادثة العادية في ChatGPT؛ لا ترسل cookies إلى الراوتر. Gemini و`chatgpt_image` وبقية المزودات تبقى fallback حسب route.

## النتيجة الأولى التي سيحصل عليها المستخدم

بعد الإعداد يستطيع المشروع المستهلك استدعاء `AIRouter.complete_auto(...)` بدل كتابة تكامل منفصل لكل مزود. سيكتشف الراوتر مخرج الطلب، يختار route مناسبًا، ويدير key rotation وfallback. كما يستطيع المستخدم استدعاء `route_plan(...)` لمشاهدة الترتيب دون إرسال طلب حي.

## المتطلبات

| المتطلب | الحالة | الغرض |
|---|---|---|
| Python 3.11 أو أحدث | مطلوب | runtime والاختبارات الحالية |
| `pip` أو بيئة virtualenv | مطلوب محليًا | تثبيت dependencies |
| مفتاح واحد على الأقل | مطلوب للطلبات الحية | Gemini أو HF أو OpenRouter أو ChatGPT |
| خدمة `chatgpt-api` | مطلوبة فقط لمسارات ChatGPT | النص والصورة والبحث الحي الأول |
| SQLite قابل للكتابة | مطلوب | حفظ state وcooldowns وmodel cursors |
| GitHub Secrets | اختياري | تشغيل live smoke من Actions |

## خريطة المشروع

| المسار | الوظيفة |
|---|---|
| `src/ai_router/router.py` | orchestration، route resolution، retries، key/model cursor، والفشل المتتابع |
| `src/ai_router/config.py` | تحميل JSON و`.env` وحل الأسرار من environment |
| `src/ai_router/providers/` | adapters الخاصة بـGemini وOpenAI-compatible وChatGPT image/conversation |
| `config/providers.json` | عنوان ونوع كل provider وkey pool وtimeout |
| `config/models.json` | model chains وoutput routes وترتيب الأولوية |
| `config/key_pools.json` | اسم كل environment variable وصيغة المفاتيح |
| `config/policies.json` | max attempts وtimeout وcooldown وbackoff |
| `scripts/live_smoke.py` | اختبارات حية محدودة ومقارير redacted |
| `.github/workflows/live-smoke.yml` | تشغيل smoke يدويًا مع concurrency وحدود زمنية |
| `tests/` | اختبارات offline باستخدام mocks وfixtures |
| `data/ai_router.db` | SQLite state محلي؛ لا ترفعه إلى Git |

## الإعداد المحلي

### الخطوة 1: تنزيل وتثبيت

نفّذ من Terminal جديدة:

```bash
git clone https://github.com/ysrg2003/ai-provider-router.git
cd ai-provider-router
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

إذا اكتمل التثبيت دون خطأ، شغّل الاختبارات غير المتصلة:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

النجاح هو خروج العملية برمز `0` وظهور `OK`. هذه الاختبارات لا تستهلك حصص المزودات ولا تحتاج secrets حقيقية.

### الخطوة 2: إنشاء الإعدادات السرية

انسخ القالب للمراجعة فقط، ثم ضع القيم في environment أو GitHub Secrets، لا داخل `config/`:

```bash
cp .env.example .env
```

يقرأ الراوتر `.env` محليًا، ثم يقرأ الملفات JSON، ثم يحل كل key pool من environment. لا تضع قيمة فعلية بين علامات اقتباس في Git ولا تطبعها بأمر `env`.

### الخطوة 3: أول فحص route بدون طلب حي

```bash
PYTHONPATH=src python -c "from ai_router import AIRouter; r=AIRouter(); print(r.summary()); r.close()"
```

يجب أن يعرض summary أسماء المزودات والroutes وعدد الأسرار المحملة دون قيم الأسرار. إذا ظهر provider غير مدعوم، راجع `config/providers.json` و`kind` المقابل له.

## المفاهيم الأساسية

| المفهوم | معناه في هذا المشروع |
|---|---|
| Provider | خدمة خارجية تستقبل الطلب، مثل Gemini أو HF أو OpenRouter أو chatgpt-api |
| Model | اسم النموذج أو المسار داخل provider |
| Key pool | قائمة مفاتيح مرتبة لمزود واحد |
| Output route | سلسلة النماذج المناسبة لنوع مخرج مثل `text` أو `image` |
| Chain | سلسلة داخلية مثل `default` أو `openrouter_free` |
| Policy | حدود المحاولات والمهل والـcooldown والـbackoff |
| State | سجل SQLite يحفظ النجاح والفشل وcursor لكل key/model |

## الاستخدام البرمجي

الواجهة العامة الأساسية هي `AIRouter` من `ai_router`:

```python
from ai_router import AIRouter, AllProvidersFailed

router = AIRouter(state_db="data/ai_router.db")
try:
    result = router.complete_auto(
        user_prompt="اكتب فقرة قصيرة عن التحقق من المصادر.",
        output_type="text",
        operation="example_text",
    )
    print(result["text"])
except AllProvidersFailed as exc:
    print(f"all configured attempts failed: {exc}")
finally:
    router.close()
```

لرؤية الترتيب دون استهلاك request:

```python
from ai_router import AIRouter

router = AIRouter()
try:
    print(router.route_plan(
        user_prompt="ابحث في الويب بحث حي عن آخر أخبار الذكاء الاصطناعي.",
        output_type="text",
    ))
finally:
    router.close()
```

`complete_auto` يعيد payload المزود ويضيف `route` و`intent`. المخرج النصي يحتوي عادة `text`، والمخرج الصوري يحتوي `mime_type` و`data_base64`. لا تفترض أن كل provider يعيد نفس الحقول الإضافية؛ تحقق من `output_type` أولًا.

## ترتيب routes الحالي

| نوع الطلب | route | الاختيار الأول | fallback المباشر |
|---|---|---|---|
| نص عادي | `text` | `chatgpt_conversation/chatgpt-conversation` | Gemini ثم Hugging Face حسب القائمة |
| بحث حي | `text_grounded_search` | `chatgpt_conversation/chatgpt-conversation` مع تعليمات live web | Gemini `gemini-2.5-flash` مع `grounded_search` |
| صورة | `image` | `chatgpt_conversation/chatgpt-conversation` عبر المحادثة العادية | `chatgpt_image/chatgpt-api` ثم Gemini image models |
| خرائط | `text_grounded_maps` | Gemini models التي تدعم maps | العنصر التالي داخل route |
| صوت | `audio` | Gemini 3.1 Flash TTS | Gemini 2.5 Flash TTS |
| embedding | `embedding` | Gemini Embedding 2 | Gemini Embedding 001 |
| تحليل فيديو | `video_analysis` | Gemini Flash chain | العنصر التالي |
| live audio/text | `live` | Gemini live models | العنصر التالي |
| OpenRouter المجاني | `openrouter_free` | القائمة المجانية المرتبة في `models.json` | العنصر التالي داخل chain |

### البحث الحي

استخدم عبارة صريحة مثل:

```text
ابحث في الويب بحث حي عن آخر أخبار الذكاء الاصطناعي، واذكر المصادر والروابط.
```

يتعرف `intent.py` على markers مثل `بحث حي` و`ابحث` و`web search` و`live web`. يضع الراوتر ChatGPT أولًا، ويضيف adapter تعليمات تطلب تنفيذ بحث فعلي وذكر المصادر. إذا فشل ChatGPT، ينتقل إلى Gemini search route. لا تنشئ طلبين متوازيين للبحث نفسه.

### الصور

يُرسل prompt الصورة إلى خدمة `chatgpt-api` عبر `POST /v1/chat/completions` في المحادثة العادية. تبقى cookies في الخدمة، ويستخدم الراوتر `CHATGPT_API_KEY` فقط للمصادقة مع endpoint. إذا لم يرجع ChatGPT صورة صالحة، يجرب الراوتر `chatgpt_image` ثم Gemini وفق ترتيب `config/models.json`.

## الإعدادات والأسرار

يجب أن تُقرأ أسماء الأسرار من `config/key_pools.json` لا من ذاكرة المستخدم أو توثيق قديم.

| pool | environment الأساسي | fallback | الصيغة |
|---|---|---|---|
| `gemini_default` | `AI_ROUTER_GEMINI_KEYS_JSON` | لا يوجد | JSON array |
| `huggingface_default` | `AI_ROUTER_HF_KEYS_JSON` | `HF_TOKEN` | JSON array أو token واحد |
| `openrouter_default` | `AI_ROUTER_OPENROUTER_KEYS_JSON` | `OPENROUTER_API_KEY` | JSON array أو token واحد |
| `chatgpt_image_default` | `AI_ROUTER_CHATGPT_IMAGE_KEYS_JSON` | `CHATGPT_API_KEY` | JSON array أو token واحد |
| `chatgpt_conversation_default` | `AI_ROUTER_CHATGPT_CONVERSATION_KEYS_JSON` | `CHATGPT_API_KEY` | JSON array أو token واحد |

يمكن أن تكون JSON array مثل:

```json
[{"id":"key-1","key":"REDACTED","project":"optional-project"}]
```

أو wrapper يحتوي `keys` أو `items` أو `entries` بحسب `config.py`. لا تضع المفتاح الحقيقي في المثال أو commit. في خدمة `chatgpt-api` يجب أن تتطابق قيمة `CHATGPT_API_KEY` مع `API_SECRET_KEY` في الخدمة، بينما `CHATGPT_COOKIES_NETSCAPE` لا يوضع في الراوتر.

### تدوير المفاتيح

عند وجود عدة مفاتيح، يحاول الراوتر المفتاح الحالي ثم يسجل failure ويحدث cursor عند الخطأ المناسب. state محفوظ في SQLite، لذلك قد يستمر الترتيب بعد إعادة التشغيل. احذف `data/ai_router.db` فقط إذا أردت بدء حالة جديدة، وتوقع فقدان سجل cooldown وموضع cursor.

## سياسة retry والطلبات المتتابعة

القيم الحالية في `config/policies.json` هي `max_attempts=64` و`request_timeout_seconds=90`. تصنيف `401/403` هو `auth` مع cooldown يوم كامل، و`429` هو `quota` مع cooldown 15 دقيقة، وأخطاء `408/409/425/5xx` مؤقتة مع cooldown دقيقتين. backoff هو `[1, 2, 4, 8]` ثانية، و`stop_after_all_models=true`.

التنفيذ **تسلسلي**: لا يرسل الراوتر الطلب إلى ChatGPT وGemini في الوقت نفسه. ينتظر المحاولة الحالية، يعيد النجاح فورًا، أو يسجل الخطأ ثم ينتقل إلى key/model التالي. هذا يحفظ الاستهلاك لكنه قد يزيد زمن الفشل إذا كان route طويلًا.

## OpenRouter وHugging Face

`openrouter_free` يستخدم models موجودة في `config/models.json` مع `:free`، ولا يعني ذلك أن كل model يدعم كل نوع إدخال أو response format. `OpenRouter` يحتاج `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY`. أما Hugging Face فيستخدم `HF_TOKEN` كأبسط إعداد.

قبل اختيار model جديد، تحقق من catalog الرسمي ثم أضف entry يتوافق مع adapter ونوع المخرج. لا تضف model صورة أو صوت إلى route النص فقط؛ `input_types` و`output_types` شروط تشغيلية وليست وصفًا تجميليًا.

## التحقق المحلي والحي

للتأكد من الكود دون استهلاك خارجي:

```bash
python3 -m json.tool config/models.json >/dev/null
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/key_pools.json >/dev/null
python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

للتجربة الحية استخدم GitHub Actions يدويًا من تبويب **Actions → Live smoke → Run workflow**. المدخل `scenario` يقبل `routing`, `text`, `normal_search`, `openrouter`, `search`, `maps`, `image`, `chatgpt_image`, `audio`, `embedding`, أو `all`. الـworkflow يستخدم Python 3.11، حدًا أعلى 15 دقيقة، concurrency group واحدًا، ويرفع تقريرًا منقحًا لمدة 7 أيام.

لا تبدأ `all` إذا كان هدفك اختبار provider واحدًا؛ استخدم scenario محدودًا. `chatgpt_image` تشخيص مباشر ولا يعمل fallback إلى Gemini، ويعرض حقولًا منقحة مثل `logged_in`, `chatgpt_cookie_count`, `prompt_selector`, و`error_type` دون cookie value.

## استكشاف الأخطاء

| العرض | التشخيص | الإجراء |
|---|---|---|
| `secrets_loaded` يساوي صفرًا | environment غير مضبوط أو اسم pool خاطئ | قارن الاسم مع `config/key_pools.json` ولا تطبع القيمة |
| `AllProvidersFailed` | كل المفاتيح/models فشلت أو في cooldown | اقرأ آخر attempts، أصلح أول auth/quota، ثم أعد الاختبار المحدود |
| `401/403` | API key غير صالح أو لا يملك الصلاحية | دوّر السر وتحقق من provider dashboard |
| `429` | quota exhausted | انتظر cooldown أو استخدم key pool آخر؛ لا تكرر smoke بلا حاجة |
| ChatGPT بلا صورة | cookies أو API_SECRET أو DOM/جلسة الخدمة | افحص خدمة chatgpt-api مباشرة ثم تحقق من تطابق `CHATGPT_API_KEY` و`API_SECRET_KEY` |
| البحث لا يحتوي مصادر | prompt غير صريح أو ChatGPT لم ينفذ browsing | استخدم عبارة `ابحث في الويب بحث حي` وتحقق من fallback Gemini عند الحاجة |
| OpenRouter لا يظهر | mismatch في secret أو chain غير محدد | استخدم `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY` وتحقق من `openrouter_free` |
| SQLite locked | عمليتان تستخدمان نفس state DB | استخدم state DB منفصلًا لكل smoke/worker أو شغّل الطلبات بشكل متسلسل |

## GitHub Actions والأسرار

يحتاج workflow إلى Secrets المناسبة للسيناريو. لا يمرر secrets إلى pull request من fork. يملك workflow `contents: read` فقط، ويرفع artifact redacted لا يحتوي المفاتيح. يجب عدم إضافة `CHATGPT_COOKIES_NETSCAPE` إلى هذا الراوتر؛ ضعه في Hugging Face Space أو مستودع خدمة chatgpt-api فقط.

## المراجع

[1]: https://github.com/ysrg2003/ai-provider-router "المستودع المنشور"
[2]: https://github.com/ysrg2003/chatgpt-api "خدمة chatgpt-api المستهلكة عبر HTTP"
[3]: https://ai.google.dev/gemini-api/docs "Gemini API Documentation"
[4]: https://huggingface.co/docs/huggingface_hub/en/guides/inference "Hugging Face Inference Documentation"
[5]: https://openrouter.ai/docs/api-reference/overview "OpenRouter API Reference"
[6]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions Secrets"
[7]: https://docs.python.org/3/library/sqlite3.html "Python SQLite Documentation"
