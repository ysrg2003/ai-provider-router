# تقرير الاختبار الحي للـreplica-01 والـreplica-02 — 2026-08-19

## النطاق والقيود

اختُبرت **replica-01 وreplica-02 فقط** عبر HTTP API المباشر. نُفذت الحالات بالتسلسل لكل نسخة: طلب نص واحد، طلب بحث حي واحد، ثم **طلب صورة واحد فقط** لتقليل استهلاك حصة ChatGPT. بدأ الفحص بعد تأكيد أن `/health` أعاد HTTP 200 و`ready=true` للنسختين.

## النتائج

| النسخة | النص | البحث الحي | الصورة | التفسير |
|---|---|---|---|---|
| replica-01 | **passed** — HTTP 200، المحتوى `LIVE_TEXT_OK` | **passed_nonempty** — HTTP 200، إجابة عربية مع مصدر Anthropic | **quota** — HTTP 200، `images_count=0` | ChatGPT أعاد رسالة Free plan image-generation limit؛ لم تُنشأ bytes صورة في هذه المحاولة. |
| replica-02 | **passed** — HTTP 200، المحتوى `LIVE_TEXT_OK` | **passed** — HTTP 200، إجابة عربية مع مصدر Anthropic | **quota** — HTTP 200، `images_count=0` | ChatGPT أعاد رسالة Free plan image-generation limit؛ لم تُنشأ bytes صورة في هذه المحاولة. |

> **HTTP 200 ليس نجاحًا للصورة.** معيار نجاح الصورة هو وجود `images[]` غير فارغة، ثم فك `data_url` أو تنزيل المصدر والتحقق من MIME والتوقيع والأبعاد. في الاختبار الحالي أعادت النسختان رسالة quota صريحة بدل asset قابل للفك.

## تفسير النتيجة

المساران النصي والبحثي يعملان في النسختين، ولذلك لا توجد إشارة في هذا الاختبار إلى خلل في Base URL أو API secret أو router text/search adapter. أما الصورة فالعائق المشترك الحالي هو quota الخاص بتوليد الصور في ChatGPT Free plan. هذا يختلف عن التحقق التاريخي السابق الذي ثبت PNG فعليًا من replica-02؛ النتيجة الحالية تعكس حالة الحصة وقت الاختبار ولا تلغي ذلك الدليل السابق.

لا يجوز إرسال طلبات صورة إضافية الآن. بعد reset الحصة، يكفي طلب صورة واحد لكل نسخة، ثم يجب تسجيل `images_count` وbytes وMIME والأبعاد. إذا ظهرت رسالة quota مرة أخرى، تُسجل الحالة كـquota ولا يُجرى retry.

## الأدلة والـartifacts

الملخص المنظم موجود في [`live-verification-2026-08-19/summary.json`](live-verification-2026-08-19/summary.json). توجد ملفات JSON منفصلة لكل حالة داخل المجلد نفسه:

| artifact | الغرض |
|---|---|
| `replica-01-text.json` و`replica-02-text.json` | إثبات النص الحي |
| `replica-01-search.json` و`replica-02-search.json` | إثبات البحث الحي |
| `replica-01-image.json` و`replica-02-image.json` | إثبات HTTP 200 ورسالة quota و`images_count=0` |

لا تحتوي هذه artifacts على Authorization headers أو cookies أو Storage State أو API secrets أو base64 image data.

## المراجع

[1]: https://yousefsg-chatgpt-api-replica-01.hf.space/health "replica-01 health endpoint"
[2]: https://yousefsg-chatgpt-api-replica-02.hf.space/health "replica-02 health endpoint"
[3]: https://github.com/ysrg2003/ai-provider-router/tree/main/project-documentation/live-verification-2026-08-19 "Live verification artifacts"
