# تشخيص اختبار إعادة المحاولة داخل نفس المحادثة — 2026-08-17

## النتائج

تم نشر `chatgpt-api` بنجاح عبر [deploy run 31989034313](https://github.com/ysrg2003/ai-provider-router/actions/runs/31989034313)، وأصبح Space في حالة `running`.

شغّل اختبار direct ChatGPT image عبر [live smoke run 31989055624](https://github.com/ysrg2003/ai-provider-router/actions/runs/31989055624). انتهى بالفشل خلال 0.16 ثانية، وكانت النتيجة `provider: chatgpt_conversation` و`status_code: 500` و`message: request rejected`. هذه السرعة لا تشبه دورة Playwright أو دورة الطلبين؛ لذلك يجب تشخيص استجابة Space/الراوتر قبل الحكم على منطق إعادة المحاولة.

## سجل Space

بعد النشر ظهر بدء التشغيل الطبيعي:

- `Application startup complete`
- `Uvicorn running on http://0.0.0.0:7860`
- فحوصات GET على `/` أعادت `200 OK`

لم يظهر في واجهة سجل Container طلب POST أو traceback، وظهرت لاحقًا رسالة واجهة السجلات `BodyStreamBuffer was aborted`. لا توجد cookies أو مفاتيح أو data URI في هذه المذكرة.

## الاستنتاج المرحلي

كود إعادة المحاولة تم دفعه إلى `chatgpt-api` في commit `6deff99`، وتوثيقه في `ai-provider-router` في commit `e752687`. رُفعت مهلة smoke إلى 240 ثانية وworkflow commit هو `8a6c3ad`. الاختبار الحي الحالي لا يثبت نجاحًا أو فشلًا في quota؛ بل يثبت وجود رفض HTTP 500 مبكر يحتاج إلى فحص شكل الطلب/الاستجابة أو إعدادات الخدمة.
