# التحقق من توليد الصور عبر ChatGPT conversation

## النتيجة الحالية

أعيد بناء خدمة `chatgpt-api` من ملف ZIP الأصلي `chatgpt-without-api-main_2.zip`، الذي يفتح المحادثة العادية في `https://chatgpt.com/`. أضيفت cookies بصيغة Netscape من خلال Secret، وأصبحت آلية `/v1/jobs` مع polling هي النقل الموحد للنص والبحث والصور؛ الاختلاف فقط في استخراج النص أو `image_url` من النتيجة المكتملة.

| الاختبار | النتيجة | الدليل |
|---|---|---|
| نص مباشر على نسخة ZIP | نجح | أعاد النص الاختباري المحدد |
| نص عبر `/v1/jobs` | نجح | دورة `queued → done` أعادت النص المحدد |
| البحث الحي اليومي | نجح | [GitHub Actions run 31959469256](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959469256)؛ التقرير المنقح أثبت `transport: queued_job` و`http_status: 200` و`text_chars: 884` |
| route الصورة العام قبل توحيد النقل | نجح | [run 31959554678](https://github.com/ysrg2003/ai-provider-router/actions/runs/31959554678)؛ أعاد PNG، لكن التقرير القديم لم يذكر provider وكان يسمح بالـfallback |
| البحث الحي بعد توحيد النقل | نجح | [run 31983527404](https://github.com/ysrg2003/ai-provider-router/actions/runs/31983527404)؛ `transport: queued_job` وHTTP `200` و`text_chars: 641` |
| ChatGPT conversation للصورة عبر نفس `/v1/jobs` | لم ينجح | [run 31983568049](https://github.com/ysrg2003/ai-provider-router/actions/runs/31983568049)؛ أعاد `provider: chatgpt_conversation` ثم `chatgpt conversation returned no image` |
| route الصورة بعد توحيد النقل | لم ينجح | [run 31983645449](https://github.com/ysrg2003/ai-provider-router/actions/runs/31983645449)؛ ChatGPT لم يُعد صورة، والـlegacy endpoint أعاد 404، وGemini كان عنده 429 quota |

## تفسير النتيجة

الآن يستخدم النظام **نفس `/v1/jobs`** للبحث والنص والصور. في الصورة يختلف فقط استخراج النتيجة: يجب أن تكون `message.content` قائمة وبداخلها `image_url`. أثبت التشغيل أن النقل الموحد يعمل للبحث، لكن ChatGPT لم يُعد صورة. كما أثبت direct `chatgpt_image` أن `/v1/visual-assets/jobs` يعيد 404 في نسخة ZIP الحالية؛ لذلك عُطّل هذا المسار القديم من route الصور، وبقي ChatGPT conversation هو المحاولة الأولى ثم Gemini fallback عند الحاجة.

لم يُنشأ Release حتى الآن لأن شرط الإصدار هو نجاح ChatGPT conversation نفسه في إعادة `image_url`. لا ينبغي تسجيل إصدار على أنه ناجح اعتمادًا على fallback أو على HTTP `200` فقط.

## طريقة التحقق الصحيحة لاحقًا

بعد تجدد قدرة إنشاء الصور أو تحديث جلسة cookies، شغّل **Actions → Live smoke → Run workflow → `chatgpt_conversation_image`**. هذا الاختبار يستخدم نفس `/v1/jobs` الذي أثبت نجاح البحث الحي. لا تستخدم `image` وحده لإثبات ChatGPT، لأنه يسمح بالـfallback. يعتبر التحقق ناجحًا فقط عندما يعيد التقرير `status: passed` و`provider: chatgpt_conversation` و`mime_type` للصورة و`bytes_base64` أكبر من صفر.

## الأمن والنسخ الاحتياطية

لا تحتوي التقارير أو النسخ الاحتياطية على cookies أو مفاتيح API أو `data_base64`. حُفظت النسخة المحلية في `backups/2026-08-16-original-zip-rebuild` على شكل Git bundles وأرشيفات للملفات المتعقبة فقط.
