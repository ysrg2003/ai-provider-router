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


## إصلاح تشخيص HTTP 500

أضيف في الخدمة سجل آمن يطبع نوع الاستثناء فقط، وأصبح adapter الراوتر يحافظ على `error` النصية القادمة من الخدمة بدل إخفائها برسالة `request rejected`. أضيف اختبار regression لهذه الصيغة.

## تشخيص cookies و502 اللاحق

أظهر فحص Netscape المحلي أربع cookies بقيمة `expires=0`، وظهر أن إحدى cookies هي `__Host-next-auth.csrf-token`. أضيفت ثلاث حمايات في `chatgpt-api`: إسقاط `expires=0`، تحويل `__Host-` إلى cookie host-only باستخدام `url` فقط، ثم حقن cookies واحدة واحدة وتجاوز الحقول غير الصالحة مع تسجيل عدد الرفض فقط.

بعد نشر commits `31bc4ff` ثم `106a6fb` ثم `cb1e679` ثم `6bc2b3b`، اختفت أخطاء `Storage.setCookies: Invalid cookie fields` و`Cookie should have either url or path`. لكن [run 31989512379](https://github.com/ysrg2003/ai-provider-router/actions/runs/31989512379) عاد بـHTTP `502` ورسالة عامة `request rejected` بعد `16.86` ثانية، ولم يعد خطأ cookie. هذه النتيجة ترجح أن direct synchronous image request يتجاوز حد gateway/Space أو أن Space يعيد 502 أثناء انتظار Playwright، ويجب تأكيدها قبل تسجيل نجاح الصورة.

لم تُسجّل أي قيمة cookie أو token أو data URI في هذه المذكرة.


## queued image smoke و404 المؤقت

بعد تحويل adapter إلى `/v1/jobs`، بدأ [run 31989710774](https://github.com/ysrg2003/ai-provider-router/actions/runs/31989710774) دورة Playwright ووصل إلى `Timeout 120000ms exceeded` بعد نحو 129 ثانية؛ وهذا أزال 502 المتزامن. بعد fallback screenshot السريع ظهر [run 31989892050](https://github.com/ysrg2003/ai-provider-router/actions/runs/31989892050) بـ`Job not found` بعد 23 ثانية، ثم تكرر بعد استقرار Space في [run 31990244227](https://github.com/ysrg2003/ai-provider-router/actions/runs/31990244227) بعد 45 ثانية. أضيف في adapter تجاهل 404 المؤقت ضمن deadline، مع اختبار offline لذلك.
