# نقطة الاستعادة الحالية — 2026-08-19

## هوية النقطة

هذه النقطة تحفظ الحالة بعد نشر إصلاح generation recovery إلى Spaces الثلاثة، وفحص Logs الحية، وتشغيل workflow post-fix واحد متسلسل للنص والبحث والصورة. المشروع في لحظة الحفظ على commit `34d0590`، مع تغييرات التوثيق ونسخة vendor التي ستدخل commit التوثيق التالي.

| العنصر | القيمة |
|---|---|
| المستودع | `ysrg2003/ai-provider-router` |
| الفرع | `main` |
| commit الأساس | `34d0590` — `docs: preserve ChatGPT Spaces checkpoint` |
| workflow post-fix | [32240146321](https://github.com/ysrg2003/ai-provider-router/actions/runs/32240146321) |
| artifact المنقح | [`chatgpt-spaces-functional-32240146321.json`](chatgpt-spaces-functional-32240146321.json) |
| حالة working tree | تغييرات موثقة مقصودة غير ملتزمة بعد: vendor gateway، AI_CONTEXT، browser evidence، chatgpt-spaces، generation-recovery، artifact JSON |

## نشر HF

| Space | HF commit | post-deploy observation |
|---|---|---|
| `chatgpt-api-replica-01` | `85e43bebd060e937e977c9508616e1f59362d66a` | `Running`; gateway ready; loaded 90 cookies |
| `chatgpt-api-replica-02` | `590fc82202d3a07db0878e2806f3706c59c78176` | `Running`; gateway ready; loaded 92 cookies |
| `chatgpt-api-replica-04` | `0d139e4fd9d269c2df99a1c392dc2b31ac126f5a` | `Running`; gateway ready; loaded 71 cookies |

القيم أعلاه هي cookie counts فقط؛ لم تُحفظ Cookie values أو Storage State أو API secrets. ملف token المؤقت حُذف فور انتهاء النشر.

## النتيجة المثبتة بعد الإصلاح

| Space | النص | البحث الحي | الصور |
|---|---|---|---|
| `chatgpt_space_replica_01` | passed | passed | failed: `503 transient` |
| `chatgpt_space_replica_02` | passed | passed | failed: `invalid_or_unknown` |
| `chatgpt_space` / replica-04 | failed: `503 transient` | failed: `503 transient` | failed: `503 transient` |

التقرير الإجمالي هو **4 passed و5 failed**. في Logs الحية ظهر أن replica-04 نفّذ `reloading the browser page` عند بقاء generation نشطًا، ثم انتهى الطلب الجاري بـ503؛ وهذا يثبت نشر وتنفيذ recovery، لا نجاح الطلب الجاري. كما ظهر في replica-01 timeout مختلف مع `generation_active=False` و`main article:count=0`، وهو DOM stabilization failure خارج الحالة الأصلية.

لا توجد في التقرير رسالة `Free plan limit` أو HTTP 429. لذلك لا تُنسب إخفاقات الصور إلى quota دون دليل، ولا تُكرر طلبات الصور قبل تشخيص logs أو انتظار reset خارجي.

## ما لا يجب تغييره عند الاستعادة

لا تغيّر ترتيب providers أو مفاتيح ChatGPT أو Cookies/Storage State استنادًا إلى هذه الجولة وحدها. لا تُسجّل أي API secret أو Cookie أو Storage State في Git. لا تحذف أو تستبدل نتائج الاختبار المنقحة. إذا احتجت العودة إلى commit الأساس فقط:

```bash
git fetch origin
git checkout main
git reset --hard 34d0590
git clean -fd
```

الأمر الأخير يحذف الملفات غير المتعقبة؛ نفذه فقط بعد التأكد من عدم وجود ملفات محلية مهمة. للاستعادة الآمنة بعد commit التوثيق، استخدم tag الإصدار بدل reset.

## الأدلة والملفات

التقرير الأحمر المنقح محفوظ في [`chatgpt-spaces-functional-32240146321.json`](chatgpt-spaces-functional-32240146321.json). أدلة المتصفح الحية في [`browser-evidence-2026-08-19.md`](browser-evidence-2026-08-19.md)، وتحليل الإصلاح في [`chatgpt-generation-recovery.md`](chatgpt-generation-recovery.md)، وملخص كل Space في [`chatgpt-spaces.md`](chatgpt-spaces.md). لا تعد هذه النقطة الإصلاح حلًا كاملًا لكل 503؛ بل تحدد بدقة ما تم نشره وما بقي للتحقيق.
