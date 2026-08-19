# نقطة الاستعادة الحالية — 2026-08-19

## القرار التشغيلي

يعتمد `ai-provider-router` الآن **replica-01 وreplica-02 فقط** من ChatGPT Spaces. توجد Space قديمة محفوظة على Hugging Face خارج router، ولم تُحذف، لكنها أُزيلت من config وroutes وworkflow والتوثيق التشغيلي.

| العنصر | القيمة |
|---|---|
| المستودع | `ysrg2003/ai-provider-router` |
| الفرع | `main` |
| ChatGPT providers المعتمدة | `chatgpt_space_replica_01`, `chatgpt_space_replica_02` |
| Base URL 01 | `https://yousefsg-chatgpt-api-replica-01.hf.space` |
| Base URL 02 | `https://yousefsg-chatgpt-api-replica-02.hf.space` |
| source commit | `2ac0d0e` |
| router/vendor commit السابق | `1a209bd` |
| latest live-documentation commit قبل هذا التغيير | `a57c0b2` |

## الحالة المثبتة

| Space | النص | البحث الحي | الصورة |
|---|---|---|---|
| replica-01 | passed، HTTP 200 | passed، HTTP 200 | quota، HTTP 200 مع `images=[]` |
| replica-02 | passed، HTTP 200 | passed، HTTP 200 | quota، HTTP 200 مع `images=[]` في آخر جولة |

أُرسل طلب صورة واحد فقط لكل نسخة في آخر live smoke. أعادت ChatGPT رسالة Free plan image-generation limit، لذلك لم تُنشأ bytes صورة جديدة ولم تُرسل retries إضافية. يوجد دليل تاريخي سابق على PNG صالح من replica-02 بحجم 831230 bytes وأبعاد 1254×1254؛ لا يتعارض ذلك مع quota الحالية.

## التغييرات البرمجية

أزيل provider legacy من `config/providers.json`، وأزيل من `config/models.json` في routes `text` و`text_grounded_search` و`image` و`image_grounded_search`. أزيلت أيضًا قائمة الاختبار الثالثة من `scripts/chatgpt_spaces_functional.py`، وتحدثت route-plan assertions في `tests/test_multiroute.py` لتتوقع 01 ثم02 فقط.

تبقى تحسينات ChatGPT السابقة فعالة: bounded recovery، فتح محادثة جديدة، diagnostics redacted، image DOM diagnostics، واستخراج الصور للصورة فقط من `body` مع دعم أبعاد العرض عند غياب `naturalWidth`. لا يستخدم text/search فحص HTML.

## الاختبارات والقدرات

نجحت اختبارات router المحلية وعددها 47، واختبارات source وعددها 14، إضافة إلى `compileall` و`git diff --check` وفحص الأسرار. live smoke أثبت text/search في النسختين، لكنه لا يثبت image bytes في آخر جولة بسبب quota.

لا يصح القول إن **كل نماذج المشروع** مثبتة حيًا لمجرد نجاح ChatGPT text/search. للمشروع providers ونماذج متعددة تشمل Gemini وHugging Face وOpenRouter وNVIDIA، ولكل نموذج capability وpayload وquota مستقلة. يلزم capability audit أو live smoke مخصص لكل نموذج قبل تصنيف جميعها `verified`.

## الملفات والأدلة

| الملف | المحتوى |
|---|---|
| [`docs/chatgpt-space.md`](../docs/chatgpt-space.md) | دليل تشغيل Space-01 وSpace-02 |
| [`docs/chatgpt-integration-guide.md`](../docs/chatgpt-integration-guide.md) | مسار الإعداد المبتدئ |
| [`project-documentation/chatgpt-spaces.md`](chatgpt-spaces.md) | الحالة التشغيلية والاختبار الحي |
| [`project-documentation/live-test-report-2026-08-19.md`](live-test-report-2026-08-19.md) | تقرير live smoke الأخير |
| [`project-documentation/live-verification-2026-08-19/summary.json`](live-verification-2026-08-19/summary.json) | artifact redacted |
| [`project-documentation/verified-replica-02-image-32251162719.png`](verified-replica-02-image-32251162719.png) | PNG التاريخي المتحقق |

## الاستعادة الآمنة

لا تنسخ Cookies أو Storage State بين Spaces. إذا ظهر 401، طابق `CHATGPT_API_SECRET_KEY` مع `API_SECRET_KEY`. إذا ظهر `session expired`، حدّث جلسة الحساب داخل Space المقابلة فقط. إذا ظهرت رسالة Free plan image quota، انتظر reset ولا تغيّر Base URLs أو key pool.
