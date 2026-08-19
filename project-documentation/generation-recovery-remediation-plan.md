# Generation Recovery Remediation Plan — 2026-08-19

## الهدف

إزالة حالات 503 التي ظهرت بعد نشر recovery، مع الحفاظ على عقد JSON الحالي وعدم تكرار طلبات الصور بلا حد. الإصلاح يبدأ من `chatgpt-api` المصدر، ثم ينسخ إلى vendor وSpaces.

## الحقائق المثبتة

| failure signature | الدليل | التصنيف الحالي |
|---|---|---|
| assistant فارغ، `generation_active=True`، stop control ظاهر، ثم 503 | Logs replica-04 | stale in-flight generation؛ recovery مطلوب قبل الطلب التالي وبعد timeout |
| `generation_active=False`، assistant lengths غير فارغة، `main article=0`، ثم 503 | Logs replica-01 | DOM stabilization failure؛ يجب قبول assistant message المستقرة دون اشتراط `main article` |
| text/search passed، image 503 أو invalid/unknown | workflow 32240146321 | image extraction/response contract أو upstream image failure؛ لا يوجد دليل 429 في التقرير |
| replica-04 فشل في الأنواع الثلاثة | workflow وLogs | session/upstream أو browser state failure، ويجب منع تتابع state العالق |

## حدود الأمان

لا تُسجّل Cookies أو Storage State أو API secrets أو base64 images. كل retry يجب أن يكون محدودًا، متسلسلًا، وآمنًا للطلب الحالي. لا تُعاد اختبارات الصور إلا بعد إصلاح payload/extraction، وبحد أقصى طلب تحقق واحد لكل Space في الجولة النهائية.

## الإصلاح المقترح

أولًا، تعديل `_wait_for_response()` ليستخدم assistant message الحديثة كمرشح أساسي، ويقبل النص غير الفارغ عندما تتوقف generation حتى لو لم توجد `main article`. يجب استبعاد النص القديم عبر `previous_count` و`previous_text`، وعدم اعتبار assistant فارغًا نجاحًا.

ثانيًا، بعد timeout أو قبل طلب جديد، تنفيذ recovery محدود: محاولة stop، ثم reload عند بقاء generation، ثم انتظار composer. إذا فشل الطلب الجاري، لا يُعاد تلقائيًا بلا حد؛ أما الطلب التالي فيبدأ من صفحة نظيفة.

ثالثًا، تحسين image extraction ليقبل روابط الصور المدعومة التي يعيدها ChatGPT حتى إن لم تحتوي alt على عبارة `generated image`، مع استبعاد favicon وavatar وواجهة الموقع، والتحقق من MIME/base64 قبل إرجاع النجاح. يجب إبقاء quota errors كـ429 وعدم تحويلها إلى invalid.

رابعًا، إضافة regression tests لكل signature، ثم تشغيل unit tests وcompileall وworkflow محدود. نجاح health وحده لا يُعد قبولًا.

## معايير القبول

1. اختبار gateway يمر عندما تكون آخر assistant message غير فارغة ومستقرة مع `main article=0` و`generation_active=False`.
2. اختبار recovery يثبت reload عند stop failure ويثبت عدم إرسال prompt جديد قبل عودة composer.
3. اختبار image يقبل data URL وblob screenshot وbackend image URL المدعوم، ويرفض favicon/صور الواجهة، ويرفض malformed data.
4. لا يفشل text/search بسبب image DOM عندما يكون `capture_images=False`.
5. بعد النشر: health/root `ready=true` لكل Space، ثم text/search لكل Space، ثم image مرة واحدة فقط لكل Space إذا لم تظهر quota.
6. release لا يعلن نجاحًا كاملًا إلا إذا نجحت المصفوفة أو يذكر صراحة ما بقي deferred.
