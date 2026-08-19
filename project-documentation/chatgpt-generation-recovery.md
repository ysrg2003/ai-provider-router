# إصلاح generation recovery واستخراج الصور في ChatGPT Spaces

## النطاق

يصف هذا الملف الإصلاحات المشتركة في gateway ونتائج التحقق الخاصة بـ`replica-01` و`replica-02` فقط. يعتمد router هاتين النسختين كـChatGPT providers وحيدين داخل configuration.

## الإصلاحات

أضيف bounded fresh-conversation recovery، وفتح محادثة جديدة فعليًا مع fallback إلى root، وقبول assistant text الجديد بعد توقف generation. عند انتهاء الانتظار، لا يعتبر gateway assistant الفارغ نجاحًا، ويعيد خطأً آمنًا بعد recovery محدود بدل retry غير منتهٍ.

في مسار الصورة فقط، يجمع gateway مصادر الصور السابقة ويستبعدها بالمصدر بدل الاعتماد على ترتيب DOM. أضيفت diagnostics redacted لفحص image-like DOM، ثم وُسّع فحص الصور إلى `body` واستخدام أبعاد العنصر المعروضة عندما تكون `naturalWidth` غير متاحة. طلبات النص والبحث لا تستخدم HTML أو image locators.

## عقد الصورة

لا يعتبر HTTP 200 نجاحًا للصورة. يجب أن تكون `images[]` غير فارغة، وأن يحتوي العنصر على `data_url` أو مصدر قابل للتنزيل. بعد ذلك يفك adapter bytes ويفحص MIME والتوقيع والأبعاد، ويرفض favicon وavatar والصور القديمة.

## الاختبارات المحلية

نجحت 14 اختبارات في مصدر `chatgpt-api`، و47 اختبارًا في `ai-provider-router`. كما نجح `compileall` و`git diff --check` وفحص الأسرار، وتطابقت نسخة `vendors/chatgpt-api/browser_gateway.py` مع المصدر.

## التحقق الحي الأخير

بعد readiness check ناجح، نجح النص والبحث الحي في `replica-01` و`replica-02` HTTP 200. أُرسل طلب صورة واحد فقط لكل نسخة؛ أعادت كلتاهما HTTP 200 مع `images=[]` ورسالة ChatGPT Free plan image-generation limit. هذا يصنف الحالة كـquota خارجية، وليس كفشل Base URL أو API secret أو extraction.

يوجد دليل تاريخي سابق على PNG صالح من replica-02 بحجم 831230 bytes وأبعاد 1254×1254. لا يتعارض ذلك مع الاختبار الحالي؛ فالاختبار الحالي لم ينشئ asset جديدًا بسبب quota.

## الأدلة

التقرير الحي في [`live-test-report-2026-08-19.md`](live-test-report-2026-08-19.md)، والـartifacts المنزوعة الحساسية في [`live-verification-2026-08-19/summary.json`](live-verification-2026-08-19/summary.json). لا تحتوي هذه الملفات Cookies أو Storage State أو API secrets أو access tokens أو base64 image data.

## الاستعادة بعد reset

بعد reset الحصة، نفّذ محاولة صورة واحدة لكل نسخة فقط. اعتبرها ناجحة عند وجود `images[].data_url` وفك bytes والتحقق من MIME والأبعاد. إذا ظهرت رسالة quota، انتظر بدل إعادة الطلب. إذا ظهر asset فعلي لكن `images=[]`، راجع image DOM diagnostics وLogs قبل أي تعديل جديد.
