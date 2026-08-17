# التشغيل والعمليات

هذا الملف يشرح ما يحدث بعد أول تشغيل محلي: كيف تضبط الأسرار، كيف تشغل smoke محدودًا، كيف تقرأ التقرير، وكيف تتراجع بأمان.

## تشغيل محلي متكرر

استخدم state DB منفصلًا لكل تجربة طويلة أو worker. لا تجعل عمليتين تكتبان إلى نفس SQLite إذا لم تكن بحاجة إلى state مشترك.

```bash
cd ai-provider-router
. .venv/bin/activate
export AI_ROUTER_CONFIG_DIR=config
export AI_ROUTER_STATE_DB=data/ai_router.db
PYTHONPATH=src python -m unittest discover -s tests -v
```

قبل طلب حي، اطبع route plan لا summary الأسرار:

```bash
PYTHONPATH=src python - <<'PY'
from ai_router import AIRouter
router = AIRouter()
try:
    print(router.route_plan(user_prompt="ابحث في الويب بحث حي عن خبر حديث", output_type="text"))
finally:
    router.close()
PY
```

## GitHub Secrets

أضف Secrets في المستودع من **Settings → Secrets and variables → Actions → New repository secret**. استخدم الأسماء التالية كما يقرأها workflow والـkey pools:

| Secret | تستخدمه |
|---|---|
| `AI_ROUTER_GEMINI_KEYS_JSON` | Gemini key pool |
| `AI_ROUTER_HF_KEYS_JSON` | Hugging Face key pool الاختياري |
| `HF_TOKEN` | fallback token لـHugging Face |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` | OpenRouter key pool |
| `OPENROUTER_API_KEY` | fallback token لـOpenRouter |
| `AI_ROUTER_CHATGPT_IMAGE_KEYS_JSON` | direct `chatgpt_image` diagnostic/fallback |
| `CHATGPT_API_KEY` | fallback لـChatGPT conversation وchatgpt_image |

لا تضف `CHATGPT_COOKIES_NETSCAPE` إلى الراوتر. هذه cookie session تخص خدمة chatgpt-api أو Space فقط.

## Daily live-search keepalive

يوجد workflow مستقل في `.github/workflows/daily-live-search.yml` يعمل مرة كل 24 ساعة عند `03:17 UTC`. يرسل طلبًا واحدًا فقط إلى `CHATGPT_API_BASE_URL/jobs` بعبارة صريحة `ابحث في الويب بحث حي`، ثم يستطلع `jobs/{job_id}` حتى `done` أو `error`. هذا هو نفس نمط الطابور الذي تستخدمه نسخة ZIP الأصلية فوق `process_request`، ويمنع قطع اتصال Hugging Face أثناء البحث. يحفظ workflow تقريرًا منقحًا في artifact لمدة 7 أيام. يحتاج إلى `CHATGPT_API_KEY` فقط؛ لا تُرسل `CHATGPT_COOKIES_NETSCAPE` إلى الراوتر، لأنها تبقى في خدمة `chatgpt-api`.

لتشغيله يدويًا افتح **Actions → Daily live search keepalive → Run workflow**. النجاح يتطلب إنشاء `job_id`، ثم حالة `done` ونصًا فعليًا، ثم ملف `daily-live-search.json` بحالة `passed`. إذا ظهر `error` أو انتهت مهلة polling، افحص تطابق `CHATGPT_API_KEY` مع `API_SECRET_KEY` في الخدمة وصحة Space، ثم أعد التشغيل يدويًا مرة واحدة فقط.

## Live smoke

من GitHub افتح **Actions → Live smoke → Run workflow** واختر scenario واحدًا. الخيارات الحالية هي `routing`, `text`, `normal_search`, `openrouter`, `search`, `maps`, `image`, `chatgpt_image`, `chatgpt_conversation_image`, `audio`, `embedding`, و`all`. سيناريو `chatgpt_conversation_image` يستدعي adapter المحادثة العادية مباشرةً بلا fallback، وهو الاختبار الصحيح لإثبات أن ChatGPT conversation نفسه ولّد الصورة.

يستخدم workflow Python 3.11 وtimeout إجمالي 20 دقيقة وconcurrency group واحدًا مع `cancel-in-progress: false`. لذلك لا يقتل تشغيلًا سابقًا تلقائيًا، ولا تشغل عدة smoke لنفس ChatGPT session بلا حاجة. سيناريو `chatgpt_conversation_image` يستخدم jobs مع polling حتى 240 ثانية؛ أما `chatgpt_image` القديم فله timeout داخلي 120 ثانية وهو diagnostic مباشر لا fallback له.

الـworkflow ينشئ `artifacts/live-smoke.json` ويرفعه لمدة 7 أيام. النجاح يتطلب status `completed` وكل النتائج `passed` أو `route_plan_only`، وليس مجرد ظهور سطر progress.

## معنى التقرير

يحتوي التقرير على `scenario_filter` و`loaded_key_counts` و`passed_or_planned` و`total` ثم `results`. في النص تظهر `text_chars` و`annotations`. في الصورة تظهر `mime_type` و`bytes_base64`. في embedding تظهر `embedding_count` و`dimensions`. في `chatgpt_image` تظهر session diagnostics منقحة مثل `logged_in`, `prompt_selector`, `chatgpt_cookie_count`, و`error_type`.

لا تحفظ أو ترفق prompt كاملًا أو Authorization أو cookies أو `data_base64`. التقرير المنقح دليل على نتيجة smoke فقط، وليس مخزنًا للبيانات الناتجة.

## تشغيل سيناريو مناسب

| الهدف | scenario | الاستهلاك المتوقع |
|---|---|---|
| فحص route plan فقط | `routing` | لا يرسل generation request |
| اختبار النص | `text` | طلب نص واحد إلى أول provider المتاح |
| اختبار بحث Gemini | `search` | طلب grounded search عند توفر Gemini |
| اختبار ChatGPT conversation search | `text` مع prompt `بحث حي` عبر `/v1/jobs` | إنشاء job واحد ثم polling حتى `done`؛ قد ينفذ browsing داخل الجلسة |
| اختبار image route | `image` | قد يستهلك أول ChatGPT conversation ثم fallback عند الفشل |
| تشخيص direct chatgpt_image | `chatgpt_image` | لا fallback؛ فحص session ثم طلب صورة عبر adapter القديم |
| إثبات ChatGPT conversation للصورة | `chatgpt_conversation_image` | لا fallback؛ `/v1/jobs` ثم polling، والخدمة تنفذ direct conversation داخل job |
| فحص جميع الفئات | `all` | عدة طلبات وحصص؛ استخدمه فقط عند الحاجة |

## الفشل والتعافي

عند `401` أو `403` أصلح secret أولًا. عند `429` انتظر cooldown أو استخدم key pool آخر، ولا تكرر نفس الطلب سريعًا. عند timeout ChatGPT، افحص `/` و`/v1/models` في Space ثم افحص صلاحية `CHATGPT_COOKIES_NETSCAPE` داخل الخدمة. عند فشل provider الأول، اترك الراوتر ينتقل تلقائيًا إلى fallback بدل تشغيل duplicate request يدويًا.

## تحديث config وrollback

أنشئ commit صغيرًا لكل تغيير في ترتيب route أو secret naming. قبل الدفع شغّل JSON validation وsuite الاختبارات. للتراجع، أعد branch إلى commit السابق عبر revert عادي، ولا تستخدم force-push على `main`. لإعادة cursor وcooldowns إلى الصفر، أوقف الطلبات وانقل `data/ai_router.db` إلى backup ثم أنشئ DB جديدة.

## النشر

خدمة chatgpt-api هي boundary منفصل. workflow `_deploy-chatgpt-space.yml` الموجود في الراوتر workflow مؤقت ومحدود؛ لا يفترض أنه ينشر كل Docker/requirements/README إلى Space. عند نشر خدمة كاملة، ادفع ملفات خدمة chatgpt-api إلى Space واضبط secrets هناك، ثم اختبر health و`/v1/models` قبل توصيل الراوتر.

## المراجع

[1]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch "GitHub workflow_dispatch"
[2]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions Secrets"
[3]: https://github.com/ysrg2003/chatgpt-api "خدمة chatgpt-api"
