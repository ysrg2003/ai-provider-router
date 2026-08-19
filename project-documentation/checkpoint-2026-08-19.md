# نقطة الاستعادة الحالية — 2026-08-19

## هوية النقطة

هذه النقطة تحفظ الحالة بعد اختبار ChatGPT Spaces الثلاثة مباشرة في النص والبحث والصور، وبعد دفع توثيق النتائج إلى GitHub وقبل إنشاء release الخاص بهذه الجولة.

| العنصر | القيمة |
|---|---|
| المستودع | `ysrg2003/ai-provider-router` |
| الفرع | `main` |
| commit الحالي | `b21c9cf` — `docs: record direct ChatGPT Spaces test results` |
| آخر release قبل هذه الجولة | [`v1.2.17-translation-capability-audit`](https://github.com/ysrg2003/ai-provider-router/releases/tag/v1.2.17-translation-capability-audit) |
| release المطلوب لهذه النقطة | `v1.2.18-chatgpt-spaces-verified` |
| حالة working tree عند الحفظ | نظيف ومتزامن مع `origin/main` |

## النتيجة المثبتة

| Space | النص | البحث الحي | الصور |
|---|---|---|---|
| `chatgpt_space_replica_01` | نجح | نجح | `503 transient` |
| `chatgpt_space_replica_02` | نجح | نجح | `503 transient` |
| `chatgpt_space` / replica-04 | `503 transient` | `503 transient` | `503 transient` |

الجولة الكاملة هي [32222693459](https://github.com/ysrg2003/ai-provider-router/actions/runs/32222693459)، وسجلت 4 نجاحات و5 إخفاقات. إعادة اختبار replica-04 منفردًا في النص والبحث هي [32224351325](https://github.com/ysrg2003/ai-provider-router/actions/runs/32224351325)، وبقيت النتيجة `503` بعد نحو 223 ثانية لكل طلب.

لم تظهر `429` أو رسالة `Free plan limit` في هذه الجولة، ولذلك لا يوجد دليل على أن فشل الصور سببه quota. فحص endpoints العامة أعاد `/` و`/health` و`/docs` بقيمة `200` للـSpaces، بينما أعاد `/v1/models` قيمة `401` دون secret كما هو متوقع. هذا يثبت أن runtime HTTP متاح، لكنه لا يثبت صلاحية ChatGPT browser/session أو upstream داخل Space.

## ما لا يجب تغييره عند الاستعادة

لا تغيّر ترتيب providers أو مفاتيح ChatGPT أو Cookies/Storage State استنادًا إلى هذه الجولة وحدها. لا تُسجّل أي API secret أو Cookie أو Storage State في Git. لا تكرر اختبارات الصور قبل فحص logs وsession/challenge داخل Spaces، لأن `503` الحالي ليس `quota` مثبتًا.

## الاستعادة

لإعادة المشروع إلى هذه النقطة:

```bash
git fetch origin
git checkout main
git reset --hard b21c9cf
git clean -fd
```

الأمر الأخير يحذف الملفات غير المتعقبة؛ نفذه فقط بعد التأكد من عدم وجود ملفات محلية مهمة. للاستعادة الآمنة دون تغيير working tree، استخدم tag الإصدار بعد إنشائه بدل `reset`.

## الأدلة والملفات

التقرير المنقح محفوظ في artifact الخاص بـ[32222693459](https://github.com/ysrg2003/ai-provider-router/actions/runs/32222693459). تفاصيل التشغيل والتشخيص موجودة في [`chatgpt-spaces.md`](chatgpt-spaces.md)، وworkflow الاختبار في [`../.github/workflows/chatgpt-spaces-functional.yml`](../.github/workflows/chatgpt-spaces-functional.yml).
