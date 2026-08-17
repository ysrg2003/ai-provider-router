# التحقق من توليد الصور عبر ChatGPT conversation

## النتيجة الحالية

أعيد بناء خدمة `chatgpt-api` من ملف ZIP الأصلي `chatgpt-without-api-main_2.zip`، الذي يفتح المحادثة العادية في `https://chatgpt.com/`. أضيفت cookies بصيغة Netscape من خلال Secret، وأصبحت آلية `/v1/jobs` مع polling هي النقل الموحد للنص والبحث والصور؛ الاختلاف فقط في استخراج النص أو `image_url` من النتيجة المكتملة.

| الاختبار | النتيجة | الدليل |
|---|---|---|
| نص مباشر على نسخة ZIP | نجح | أعاد النص الاختباري المحدد |
| نص عبر `/v1/jobs` | نجح | دورة `queued → done` أعادت النص المحدد |
| البحث الحي اليومي | نجح | [GitHub Actions run 31959469256](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959469256)؛ التقرير المنقح أثبت `transport: queued_job` و`http_status: 200` و`text_chars: 884` |
| route الصورة العام | نجح | [GitHub Actions run 31959554678](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959554678)؛ أعاد PNG بحجم Base64 غير فارغ |
| ChatGPT conversation عبر نفس `/v1/jobs`، بلا fallback | لم ينجح | [run 31983568049](https://github.com/ysrg2003/ai-provider-router/actions/runs/31983568049)؛ أنشأ المسار الطلب وانتظر النتيجة، لكن النتيجة لم تحتوي `image_url` وأعادت `chatgpt conversation returned no image` |

## تفسير النتيجة

نجاح route الصورة العام لا يثبت أن ChatGPT ولّد الصورة؛ فهذا route يسمح بالانتقال التسلسلي إلى fallback. كما أن direct `chatgpt_image` القديم يعيد `404` لأن `/v1/visual-assets/jobs` غير موجود في نسخة ZIP الحالية. لذلك يستدعي الاختبار المباشر `chatgpt_conversation_image` الآن **نفس `/v1/jobs` المستخدم للبحث الحي**، ثم يختلف فقط في فحص `image_url`. نتيجة التشغيل الجديد تثبت أن النقل الموحد يعمل، لكن ChatGPT في الجلسة المنشورة لم يُعد عنصر `image_url`.

لم يُنشأ Release لأن شرط الإصدار كان التحقق أولًا من توليد الصورة بواسطة ChatGPT نفسه. لا ينبغي تسجيل إصدار على أنه ناجح اعتمادًا على fallback أو على HTTP `200` فقط.

## طريقة التحقق الصحيحة لاحقًا

بعد تجدد قدرة إنشاء الصور أو تحديث جلسة cookies، شغّل **Actions → Live smoke → Run workflow → `chatgpt_conversation_image`**. هذا الاختبار يستخدم نفس `/v1/jobs` الذي أثبت نجاح البحث الحي. لا تستخدم `image` وحده لإثبات ChatGPT، لأنه يسمح بالـfallback. يعتبر التحقق ناجحًا فقط عندما يعيد التقرير `status: passed` و`provider: chatgpt_conversation` و`mime_type` للصورة و`bytes_base64` أكبر من صفر.

## الأمن والنسخ الاحتياطية

لا تحتوي التقارير أو النسخ الاحتياطية على cookies أو مفاتيح API أو `data_base64`. حُفظت النسخة المحلية في `backups/2026-08-16-original-zip-rebuild` على شكل Git bundles وأرشيفات للملفات المتعقبة فقط.
