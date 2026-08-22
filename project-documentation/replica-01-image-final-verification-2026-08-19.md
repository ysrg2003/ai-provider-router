# التحقق النهائي من صورة replica-01 — 2026-08-19

## الخلاصة


> You've hit the Free plan limit for image generations requests. You can create more images when the limit resets in 17 hours and 3 minutes.


## نطاق التغيير

| النطاق | ما تم تغييره | الحالة |
|---|---|---|
| `ai-provider-router` | مزامنة vendor gateway نفسه | منشور في `1a209bd` |
| HF `replica-01` | نشر gateway نفسه فقط | منشور في commit `d2c5bee` |
| replica-02 | لم تُلمس | لا تغيير |

## الأدلة التشغيلية

| الفحص | النتيجة |
|---|---|
| اختبار image الأول بعد إصلاح DOM-order | HTTP 200، `images_count=0`، دون image bytes |
| فحص DOM التشخيصي بعد ذلك | `img_count=0`, `picture_count=0`, `canvas_count=0` في الصفحة الرئيسية؛ لم يُرسل prompt جديد أثناء هذا الفحص |
| اختبار image الأخير بعد التوسيع | HTTP 200، `images_count=0`، و`choices[0].message.content` احتوى رسالة Free plan limit أعلاه |

## الاستدلال

لا يجوز تفسير HTTP 200 وحده على أنه نجاح صورة. عقد النجاح يتطلب وجود `images[]` وعنصر `data_url` أو مصدر قابل للتنزيل، ثم فك bytes والتحقق من MIME والتوقيع والأبعاد. في المحاولة الأخيرة كان لدينا نص upstream صريح يحدد quota، ولذلك تُصنّف النتيجة `quota` لا `extraction_failure`.

الإصلاحات البرمجية المضافة تظل مفيدة عندما تعود الحصة؛ فهي لا تفحص HTML في طلبات النص أو البحث، وتعمل فقط عندما يقرر `should_capture_images` أن الطلب صورة. لكن **لا يمكن إثبات نجاحها الحي قبل انتهاء quota**، ولا ينبغي استهلاك محاولة إضافية الآن.

## ما لم يُفعل

لم تُنسخ Cookies أو Storage State، ولم تُحفظ API secrets أو HF token أو بيانات اعتماد مؤقتة في Git أو artifact. حُذفت ملفات المصادقة المؤقتة بعد النشر والاختبارات.

## إجراء الاستئناف بعد reset


## المراجع

[2]: https://github.com/ysrg2003/ai-provider-router/commit/1a209bd "ai-provider-router vendor synchronization"
