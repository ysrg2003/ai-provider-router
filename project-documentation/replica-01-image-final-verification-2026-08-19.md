# التحقق النهائي من صورة replica-01 — 2026-08-19

## الخلاصة

أُعيد اختبار **replica-01 فقط** بعد نشر إصلاحين متتابعين في gateway: إصلاح استخراج الصور المستقل عن ترتيب DOM، ثم توسيع فحص الصور إلى `document.body` ودعم أبعاد العرض عندما تكون `naturalWidth` غير متاحة. أعاد endpoint الصورة HTTP 200، لكن الاستجابة نفسها احتوت رسالة ChatGPT التالية:

> You've hit the Free plan limit for image generations requests. You can create more images when the limit resets in 17 hours and 3 minutes.

لذلك فإن **السبب الجذري المؤكد في محاولة التحقق الأخيرة هو quota الخاص بتوليد الصور في حساب ChatGPT المجاني**. لم تُثبت هذه الجولة نجاح استخراج bytes لأن upstream لم يُنشئ صورة جديدة أصلًا؛ وهذا ليس دليلًا على فشل Base URL أو API secret أو router.

## نطاق التغيير

| النطاق | ما تم تغييره | الحالة |
|---|---|---|
| `chatgpt-api` المصدر | إضافة `image_dom` redacted إلى diagnostics، ثم استخراج الصور من `body` بدل `main` للصورة فقط، وقبول أبعاد العنصر المعروضة عند غياب `naturalWidth` | منشور في `2ac0d0e` |
| `ai-provider-router` | مزامنة vendor gateway نفسه | منشور في `1a209bd` |
| HF `replica-01` | نشر gateway نفسه فقط | منشور في commit `d2c5bee` |
| replica-02 | لم تُلمس | لا تغيير |
| replica-04 | لم تُلمس | لا تغيير؛ ما زالت تحتاج re-authentication |

## الأدلة التشغيلية

| الفحص | النتيجة |
|---|---|
| `GET https://yousefsg-chatgpt-api-replica-01.hf.space/health` بعد كل build | HTTP 200؛ headers أظهرت `server: uvicorn` وSpace proxy جديدًا، وready endpoint متاح |
| `GET /diagnostics/session` بعد نشر diagnostics | `ready=true`، الصفحة `https://chatgpt.com/`، لا توجد markers لتسجيل الدخول أو challenge؛ بعد restart لا توجد محادثة مفتوحة (`assistant_count=0`) |
| اختبار image الأول بعد إصلاح DOM-order | HTTP 200، `images_count=0`، دون image bytes |
| فحص DOM التشخيصي بعد ذلك | `img_count=0`, `picture_count=0`, `canvas_count=0` في الصفحة الرئيسية؛ لم يُرسل prompt جديد أثناء هذا الفحص |
| اختبار image الأخير بعد التوسيع | HTTP 200، `images_count=0`، و`choices[0].message.content` احتوى رسالة Free plan limit أعلاه |

## الاستدلال

لا يجوز تفسير HTTP 200 وحده على أنه نجاح صورة. عقد النجاح يتطلب وجود `images[]` وعنصر `data_url` أو مصدر قابل للتنزيل، ثم فك bytes والتحقق من MIME والتوقيع والأبعاد. في المحاولة الأخيرة كان لدينا نص upstream صريح يحدد quota، ولذلك تُصنّف النتيجة `quota` لا `extraction_failure`.

الإصلاحات البرمجية المضافة تظل مفيدة عندما تعود الحصة؛ فهي لا تفحص HTML في طلبات النص أو البحث، وتعمل فقط عندما يقرر `should_capture_images` أن الطلب صورة. لكن **لا يمكن إثبات نجاحها الحي قبل انتهاء quota**، ولا ينبغي استهلاك محاولة إضافية الآن.

## ما لم يُفعل

لم تُرسل أي طلبات صورة إلى replica-02 أو replica-04 في هذه الجولة. لم تُنسخ Cookies أو Storage State، ولم تُحفظ API secrets أو HF token أو بيانات اعتماد مؤقتة في Git أو artifact. حُذفت ملفات المصادقة المؤقتة بعد النشر والاختبارات.

## إجراء الاستئناف بعد reset

بعد أن يسمح ChatGPT بتوليد الصور مجددًا، نفّذ طلب صورة واحدًا إلى replica-01. اعتبره ناجحًا فقط إذا كان HTTP 200، وكانت `images[]` غير فارغة، واحتوى العنصر على `data_url` صالح، ثم نجح فك base64 وأثبتت أداة `file` أو فحص PNG/JPEG MIME والأبعاد. إذا عادت رسالة quota، انتظر reset ولا تغيّر router keys؛ وإذا عاد upstream بصورة لكن `images=[]`، فحينها فقط راجع `image_dom.details` وLogs لاستخراج مصدر الصورة الفعلي.

## المراجع

[1]: https://github.com/ysrg2003/chatgpt-api/commit/2ac0d0e "chatgpt-api image extraction fix"
[2]: https://github.com/ysrg2003/ai-provider-router/commit/1a209bd "ai-provider-router vendor synchronization"
[3]: https://huggingface.co/spaces/Yousefsg/chatgpt-api-replica-01 "replica-01 Hugging Face Space"
[4]: https://help.openai.com/en/articles/8932459-dall-e-in-chatgpt "OpenAI Help — image generation limits in ChatGPT"
