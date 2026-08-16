# التحقق من توليد الصور عبر ChatGPT conversation

## النتيجة الحالية

أعيد بناء خدمة `chatgpt-api` من ملف ZIP الأصلي `chatgpt-without-api-main_2.zip`، الذي يستخدم `POST /v1/chat/completions` ويفتح المحادثة العادية في `https://chatgpt.com/`. أضيفت cookies بصيغة Netscape من خلال Secret، وأضيفت آلية `/v1/jobs` مع polling للنص والبحث الحي، مع إبقاء مسار الصورة في نفس endpoint المحادثة.

| الاختبار | النتيجة | الدليل |
|---|---|---|
| نص مباشر على نسخة ZIP | نجح | أعاد النص الاختباري المحدد |
| نص عبر `/v1/jobs` | نجح | دورة `queued → done` أعادت النص المحدد |
| البحث الحي اليومي | نجح | [GitHub Actions run 31959469256](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959469256)؛ التقرير المنقح أثبت `transport: queued_job` و`http_status: 200` و`text_chars: 884` |
| route الصورة العام | نجح | [GitHub Actions run 31959554678](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959554678)؛ أعاد PNG بحجم Base64 غير فارغ |
| ChatGPT conversation وحده، بلا fallback | لم ينجح | [run 31959694292](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959694292) و[إعادة prompt المطابق run 31959757627](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959757627)؛ كلاهما أعاد `chatgpt conversation returned no image` |

## تفسير النتيجة

نجاح route الصورة العام لا يثبت أن ChatGPT ولّد الصورة؛ فهذا route يسمح بالانتقال التسلسلي إلى fallback. أما الاختبار المباشر `chatgpt_conversation_image` فيستدعي adapter ChatGPT conversation وحده، ولذلك فهو الاختبار الحاسم. نتيجة الاختبار الحالي تعني أن ChatGPT في الجلسة المنشورة لم يُعد عنصر `image_url`، حتى بعد استعمال prompt يبدأ بعبارة `Generate an image`.

لم يُنشأ Release لأن شرط الإصدار كان التحقق أولًا من توليد الصورة بواسطة ChatGPT نفسه. لا ينبغي تسجيل إصدار على أنه ناجح اعتمادًا على fallback أو على HTTP `200` فقط.

## طريقة التحقق الصحيحة لاحقًا

بعد تجدد قدرة إنشاء الصور أو تحديث جلسة cookies، شغّل **Actions → Live smoke → Run workflow → `chatgpt_conversation_image`**. لا تستخدم `image` وحده لإثبات ChatGPT، لأنه يسمح بالـfallback. يعتبر التحقق ناجحًا فقط عندما يعيد التقرير `status: passed` و`provider: chatgpt_conversation` و`mime_type` للصورة و`bytes_base64` أكبر من صفر.

## الأمن والنسخ الاحتياطية

لا تحتوي التقارير أو النسخ الاحتياطية على cookies أو مفاتيح API أو `data_base64`. حُفظت النسخة المحلية في `backups/2026-08-16-original-zip-rebuild` على شكل Git bundles وأرشيفات للملفات المتعقبة فقط.
