# نقطة الاستعادة الحالية — 2026-08-19

## هوية النقطة

هذه النقطة تحفظ الحالة بعد إصلاح generation recovery وDOM stabilization وimage contract، ثم تشخيص session state داخل Spaces الثلاثة. أُجريت اختبارات حية محدودة دون تكرار الصور بلا داعٍ. آخر commit منشور في router هو `63e6b33`، وتوجد تغييرات التوثيق الأخيرة محليًا تمهيدًا لcommit/release التالي.

| العنصر | القيمة |
|---|---|
| المستودع | `ysrg2003/ai-provider-router` |
| الفرع | `main` |
| آخر router commit منشور | `63e6b33` — `fix: fail fast on ChatGPT reauthentication state` |
| آخر source commit منشور | `5c34094` — `fix: fail fast when ChatGPT session needs reauthentication` |
| workflow الشامل | [32245401088](https://github.com/ysrg2003/ai-provider-router/actions/runs/32245401088) |
| workflow المحدود لـreplica-04 | [32247225620](https://github.com/ysrg2003/ai-provider-router/actions/runs/32247225620) |
| artifact الشامل | [`chatgpt-spaces-functional-32245401088.json`](chatgpt-spaces-functional-32245401088.json) |

## الحالة المثبتة

| Space | النص | البحث الحي | الصورة | التفسير |
|---|---|---|---|---|
| `chatgpt-api-replica-01` | passed | passed | passed | المسارات الثلاثة نجحت بعد إصلاح output_type/image extraction. |
| `chatgpt-api-replica-02` | passed | passed | passed | المسارات الثلاثة نجحت بعد إصلاح output_type/image extraction. |
| `chatgpt-api-replica-04` | re-auth required | re-auth required | لم تُكرر بعد التشخيص | تظهر `visible_auth_controls=["log in"]` رغم `ready=true` و`input_visible=true`. |

النتيجة الإجمالية في workflow الشامل: **6 passed و3 failed**. اختبار text/search المحدود للنسخة 04 فشل قبل fail-fast بعد نحو 268 ثانية. بعد نشر fail-fast، أعاد طلب نص واحد إلى replica-04 HTTP 503 برسالة `ChatGPT session requires re-authentication; visible auth control detected` خلال `2.881228` ثانية، بدل timeout طويل.

## إصلاحات الكود

في `chatgpt-api` المصدر أضيفت bounded fresh-conversation recovery، فتح رابط `New chat` فعليًا مع fallback، قبول assistant text الجديد عند توقف generation، استخراج الصور من data_url/src/url، وendpoint محمي `GET /diagnostics/session` لا يعيد إلا مؤشرات redacted. أضيف أيضًا fail-fast عند ظهور login control.

في router أُرسل `output_type=image` صراحة، وقُبلت أشكال الصور `data_url` و`src` و`url`، وحُدّ retry الصور إلى محاولتين. تمت مزامنة `vendors/chatgpt-api` مع المصدر، ونجحت **47 اختبارات router** و**13 اختبارًا في المصدر**، مع compileall وgit diff check.

## HF deployment commits الأخيرة

| Space | أحدث gateway commit | حالة التشغيل |
|---|---|---|
| replica-01 | `f6a5db5fd6b2961bc2d18d05c2cf93c5c84a6e02` | Running/ready |
| replica-02 | `6ae0e10b74218d469329ac5f71701818d890836e` | Running/ready |
| replica-04 | `cd675aeadb768112475cdba3f16f5d7ad2dc79ab` | Running/ready؛ session يحتاج re-authentication |

تم نشر `main.py` الذي يحتوي diagnostics endpoint إلى النسخ الثلاثة أيضًا. لم تُحفظ Cookie values أو Storage State أو API secrets في Git أو artifacts، وحُذفت الملفات المؤقتة بعد النشر.

## إجراء الاستعادة التالي

لا تنسخ Cookies أو Storage State من replica أخرى. يجب إعادة تسجيل دخول حساب ChatGPT الخاص بـreplica-04 داخل Space نفسها أو تحديث session state الخاصة بها، ثم إعادة تشغيل Space. بعد ظهور `visible_auth_controls=[]` في `/diagnostics/session` يمكن تشغيل text/search مرة واحدة، ثم image مرة واحدة فقط إذا نجح المساران النصي والبحثي.

## الملفات والأدلة

الأدلة الحية المنقحة في [`browser-evidence-2026-08-19.md`](browser-evidence-2026-08-19.md)، وملخص النتائج في [`chatgpt-spaces.md`](chatgpt-spaces.md)، والتحليل البرمجي في [`chatgpt-generation-recovery.md`](chatgpt-generation-recovery.md)، وخطة remediation في [`generation-recovery-remediation-plan.md`](generation-recovery-remediation-plan.md). لا تعتبر هذه النقطة replica-04 ناجحة؛ هي تثبت أن مشكلة الكود والـretry storm عولجت، وأن العائق المتبقي هو session authentication داخل Space.
