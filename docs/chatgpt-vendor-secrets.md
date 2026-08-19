# أسرار ومتغيرات خدمة chatgpt-api المضمنة

هذا الملف يخص `vendors/chatgpt-api/` وSpace التي تشغل gateway للمتصفح. هذه القيم **ليست** كلها مطلوبة لتشغيل `ai-provider-router` نفسه. router يرسل HTTP إلى Space ويحتاج عادةً `CHATGPT_API_SECRET_KEY` أو `AI_ROUTER_CHATGPT_KEYS_JSON` فقط؛ أما cookies/session فتظل داخل Space ولا تُوضع في router.

المصدر الفعلي للأسماء هو [`vendors/chatgpt-api/.env.example`](../vendors/chatgpt-api/.env.example)، والمصدر التشغيلي للـvendor هو [`vendors/chatgpt-api/README.md`](../vendors/chatgpt-api/README.md).

## خريطة الفصل

| القيمة | المالك | مكان التخزين | هل يحتاجها router؟ |
|---|---|---|---|
| `API_SECRET_KEY` | chatgpt-api Space | Hugging Face Space Secret | نعم، تُنسخ قيمتها إلى router باسم `CHATGPT_API_SECRET_KEY` أو pool |
| `CHATGPT_COOKIES_NETSCAPE` | chatgpt-api browser gateway | Hugging Face Space Secret | لا؛ لا تُنقل إلى router |
| `PORT` | Space runtime | Space Variable | لا |
| `CHATGPT_HEADLESS` | Space runtime | Space Variable | لا |
| `CHATGPT_READY_TIMEOUT` | Space runtime | Space Variable | لا |
| `CHATGPT_REQUEST_TIMEOUT` | Space runtime | Space Variable | لا |
| `MAX_PROMPT_CHARS` | Space runtime | Space Variable | لا |
| `RATE_LIMIT_REQUESTS` | Space runtime | Space Variable | لا |
| `RATE_LIMIT_WINDOW_SECONDS` | Space runtime | Space Variable | لا |
| `LOG_LEVEL` | Space runtime | Space Variable | لا |
| `ALLOWED_ORIGINS` | Space runtime | Space Variable | لا |

## بطاقة `API_SECRET_KEY`

**التصنيف:** Secret مطلوب لحماية HTTP endpoint في Space.

**الحصول عليه:** أنشئ قيمة عشوائية طويلة من مدير أسرار موثوق أو مولد عشوائي محلي. افتح Hugging Face Space → **Settings → Variables and secrets** → **New secret**، وأدخل الاسم `API_SECRET_KEY` والقيمة. لا تضع القيمة في Git أو Dockerfile.

**ربطه بالrouter:** في بيئة router استخدم القيمة نفسها باسم `CHATGPT_API_SECRET_KEY`، أو داخل `AI_ROUTER_CHATGPT_KEYS_JSON` كـJSON array. لا يلزم أن تكون أسماء Secret متطابقة بين Space وrouter؛ المهم أن القيمة نفسها هي التي يتحقق منها endpoint.

**التحقق:** شغّل `summary`، ثم text smoke صغير. لا تطبع header أو value. `401/403` يعني غالبًا اختلاف القيمة أو عدم تحديث Space.

**التدوير والإلغاء:** أنشئ قيمة جديدة في Space، حدّث Secret في Space وrouter، اختبر، ثم غيّر أو احذف القيمة القديمة. إذا تسربت، اعتبرها مكشوفة فورًا.

## بطاقة `CHATGPT_COOKIES_NETSCAPE`

**التصنيف:** session credential حساس للغاية، وليس API key.

**الحصول عليه:** استخدم حساب ChatGPT المصرح به في متصفحك، وسجّل الدخول يدويًا، ثم صدّر cookies بصيغة Netscape باستخدام أداة موثوقة تعمل محليًا. راجع الملف محليًا دون مشاركته، وتأكد من أنه يحتوي الجلسة المطلوبة فقط. لا ترفع الملف إلى GitHub ولا ترسله إلى router.

**التخزين:** Hugging Face Space Secret باسم `CHATGPT_COOKIES_NETSCAPE`. لا تضعه في `.env` الخاص بـai-provider-router، ولا في `AI_ROUTER_CHATGPT_KEYS_JSON`، ولا في issue أو artifact أو screenshot.

**التحقق:** أعد بناء Space أو أعد تشغيلها، ثم نفّذ text smoke محدودًا من Space. إذا ظهر `re-auth required` أو challenge، أعد تصدير session يدويًا من الحساب الصحيح بدل تدوير router key.

**التدوير والإلغاء:** سجّل الخروج من الجلسات المتأثرة أو ألغِها من ChatGPT، استبدل Secret، ثم أعد تشغيل Space. تعامل مع أي تسريب كاختراق session.

## بطاقات runtime غير السرية

| الاسم | القيمة الآمنة | الوظيفة | الخطأ الشائع |
|---|---|---|---|
| `PORT` | `7860` | منفذ خدمة FastAPI داخل Space | محاولة تغيير منفذ دون إعداد deployment |
| `CHATGPT_HEADLESS` | `true` | تشغيل Chromium headless | تعطيله في بيئة بلا VNC |
| `CHATGPT_READY_TIMEOUT` | `180` | انتظار جاهزية الصفحة بالثواني | تقليله مع بطء startup |
| `CHATGPT_REQUEST_TIMEOUT` | `210` | مهلة طلب ChatGPT | اعتباره quota timeout |
| `MAX_PROMPT_CHARS` | `50000` | حد حجم prompt | إرسال prompt أكبر من الحد |
| `RATE_LIMIT_REQUESTS` | `20` | عدد الطلبات في window | رفعه دون حساب الحمل |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | نافذة rate limit | تفسير 429 المحلي كـprovider quota |
| `LOG_LEVEL` | `INFO` | مستوى logs | تفعيل DEBUG مع بيانات حساسة |
| `ALLOWED_ORIGINS` | فارغ أو origins مفصولة بفواصل | CORS للواجهة | فتح origins عامة بلا حاجة |

## مسار تشغيل vendor منفصل

من مجلد `vendors/chatgpt-api`:

```bash
cp .env.example .env
# ضع API_SECRET_KEY وCHATGPT_COOKIES_NETSCAPE في secret manager المحلي فقط
python3 -m pip install -r requirements.txt
python3 main.py
```

هذا المسار منفصل عن تثبيت router. لا تشغله live إلا بحساب وsession مصرح بهما، ولا تخلط SQLite أو Secrets بين المشروعين.

## مراجع

[1]: [vendors/chatgpt-api/.env.example](../vendors/chatgpt-api/.env.example)
[2]: [vendors/chatgpt-api/README.md](../vendors/chatgpt-api/README.md)
[3]: [docs/credentials.md](credentials.md)
