# نقطة الاستعادة الحالية — 2026-08-19

## القرار التشغيلي


| العنصر | القيمة |
|---|---|
| المستودع | `ysrg2003/ai-provider-router` |
| الفرع | `main` |
| source commit | `2ac0d0e` |
| router/vendor commit السابق | `1a209bd` |
| latest live-documentation commit قبل هذا التغيير | `a57c0b2` |

## الحالة المثبتة

| Space | النص | البحث الحي | الصورة |
|---|---|---|---|
| replica-01 | passed، HTTP 200 | passed، HTTP 200 | quota، HTTP 200 مع `images=[]` |
| replica-02 | passed، HTTP 200 | passed، HTTP 200 | quota، HTTP 200 مع `images=[]` في آخر جولة |


## التغييرات البرمجية



## الاختبارات والقدرات

نجحت اختبارات router المحلية وعددها 47، واختبارات source وعددها 14، إضافة إلى `compileall` و`git diff --check` وفحص الأسرار. live smoke أثبت text/search في النسختين، لكنه لا يثبت image bytes في آخر جولة بسبب quota.


## الملفات والأدلة

| الملف | المحتوى |
|---|---|
| [`project-documentation/live-test-report-2026-08-19.md`](live-test-report-2026-08-19.md) | تقرير live smoke الأخير |
| [`project-documentation/live-verification-2026-08-19/summary.json`](live-verification-2026-08-19/summary.json) | artifact redacted |
| [`project-documentation/verified-replica-02-image-32251162719.png`](verified-replica-02-image-32251162719.png) | PNG التاريخي المتحقق |

## الاستعادة الآمنة
