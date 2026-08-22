# تقرير الاختبار الحي للـreplica-01 والـreplica-02 — 2026-08-19

## النطاق والقيود


## النتائج

| النسخة | النص | البحث الحي | الصورة | التفسير |
|---|---|---|---|---|

> **HTTP 200 ليس نجاحًا للصورة.** معيار نجاح الصورة هو وجود `images[]` غير فارغة، ثم فك `data_url` أو تنزيل المصدر والتحقق من MIME والتوقيع والأبعاد. في الاختبار الحالي أعادت النسختان رسالة quota صريحة بدل asset قابل للفك.

## تفسير النتيجة


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

[3]: https://github.com/ysrg2003/ai-provider-router/tree/main/project-documentation/live-verification-2026-08-19 "Live verification artifacts"
