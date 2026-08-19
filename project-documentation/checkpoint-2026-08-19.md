# نقطة الاستعادة الحالية — 2026-08-19

## هوية النقطة

هذه النقطة تحفظ الحالة بعد إصلاح generation recovery وDOM stabilization وimage contract، ثم تشخيص session state داخل Spaces الثلاثة، ثم التحقيق النهائي في replica-01. أُجريت محاولة الصورة الأخيرة في replica-01 فقط بعد إصلاح جديد؛ أُوقفت محاولات الصور الأخرى لتجنب quota. آخر commits منشورة في router هي `1a209bd`، وفي المصدر `2ac0d0e`.

| العنصر | القيمة |
|---|---|
| المستودع | `ysrg2003/ai-provider-router` |
| الفرع | `main` |
| آخر router commit منشور | `1a209bd` — `chore: sync broader image extraction fix` |
| آخر source commit منشور | `2ac0d0e` — `fix: capture image assets outside main and use rendered dimensions` |
| آخر commit في HF replica-01 | `d2c5bee` — نفس إصلاح extraction الأوسع، منشور إلى replica-01 فقط |
| workflow الشامل | [32245401088](https://github.com/ysrg2003/ai-provider-router/actions/runs/32245401088) |
| workflow المحدود لـreplica-04 | [32247225620](https://github.com/ysrg2003/ai-provider-router/actions/runs/32247225620) |
| workflow image-only المستقل | [32251162719](https://github.com/ysrg2003/ai-provider-router/actions/runs/32251162719) |
| artifact الشامل | [`chatgpt-spaces-functional-32245401088.json`](chatgpt-spaces-functional-32245401088.json) |
| artifact image-only | [`chatgpt-spaces-functional-32251162719.json`](chatgpt-spaces-functional-32251162719.json) |

## الحالة المثبتة

| Space | النص | البحث الحي | الصورة | التفسير |
|---|---|---|---|---|
| `chatgpt-api-replica-01` | passed | passed | **quota-confirmed / not verified** | بعد نشر الإصلاح الأوسع أعاد HTTP 200، لكن `images=[]` و`choices[0].message.content` احتوى رسالة ChatGPT Free plan image limit؛ لم تُنشأ صورة يمكن فك bytes لها. |
| `chatgpt-api-replica-02` | passed | passed | **verified** | وصلت data_url؛ PNG صالح 831230 bytes، أبعاده 1254×1254، وفُحص بصريًا. |
| `chatgpt-api-replica-04` | re-auth required | re-auth required | لم تُكرر بعد التشخيص | الحساب المقصود هو sg، لكن diagnostics المنقح أثبت زر `log in` مرئيًا فعليًا بحجم 68.2×36 رغم `ready=true` و`input_visible=true`. |

الاختبار السابق الشامل سجل **6 passed و3 failed**، لكن التحقق الحاسم الأخير في replica-01 فصل extraction عن quota: HTTP 200، `images=[]`، ورسالة upstream صريحة `You've hit the Free plan limit for image generations requests...`. لذلك لا تُصنّف replica-01 كفشل DOM في هذه النقطة؛ الصورة **غير قابلة للتحقق حيًا حتى reset الحصة**. اختبار text/search المحدود للنسخة 04 فشل قبل fail-fast بعد نحو 268 ثانية. بعد نشر fail-fast، أعاد طلب نص واحد إلى replica-04 HTTP 503 برسالة `ChatGPT session requires re-authentication; visible auth control detected` خلال `2.881228` ثانية، بدل timeout طويل.

## إصلاحات الكود

في `chatgpt-api` المصدر أضيفت bounded fresh-conversation recovery، فتح رابط `New chat` فعليًا مع fallback، قبول assistant text الجديد عند توقف generation، استخراج الصور من data_url/src/url، وendpoint محمي `GET /diagnostics/session` لا يعيد إلا مؤشرات redacted. أضيف أيضًا fail-fast عند ظهور login control، ثم image DOM diagnostics redacted. وأخيرًا وُسّع استخراج الصور للصورة فقط من `body` بدل `main`، مع استخدام أبعاد العرض عند غياب `naturalWidth`. هذه التغييرات لا تُفعّل فحص HTML في text/search. أظهر التحقق الأخير أن upstream حجب توليد replica-01 بسبب Free plan image quota، لذلك لم يكن هناك asset جديد لاستخراجه.

في router أُرسل `output_type=image` صراحة، وقُبلت أشكال الصور `data_url` و`src` و`url`، وحُدّ retry الصور إلى محاولتين. تمت مزامنة `vendors/chatgpt-api` مع المصدر في `1a209bd`. نجحت **47 اختبارات router** و**14 اختبارًا في المصدر**، مع compileall وgit diff check.

## HF deployment commits الأخيرة

| Space | أحدث gateway commit | حالة التشغيل |
|---|---|---|
| replica-01 | `d2c5bee` / HF current | Running/ready؛ آخر image request حُجب برسالة quota |
| replica-02 | `6ae0e10b74218d469329ac5f71701818d890836e` | Running/ready |
| replica-04 | `cd675aeadb768112475cdba3f16f5d7ad2dc79ab` | Running/ready؛ session يحتاج re-authentication |

تم نشر `main.py` الذي يحتوي diagnostics endpoint إلى النسخ الثلاثة أيضًا. لم تُحفظ Cookie values أو Storage State أو API secrets في Git أو artifacts، وحُذفت الملفات المؤقتة بعد النشر.

## إجراء الاستعادة التالي

لا تنسخ Cookies أو Storage State من replica أخرى. بالنسبة إلى replica-01، لا ترسل طلب صورة جديدًا قبل انتهاء Free plan reset؛ بعد ذلك نفّذ محاولة واحدة فقط وتحقق من `images[].data_url` وbytes الفعلية. بالنسبة إلى replica-04، يجب إعادة تسجيل دخول حساب ChatGPT داخل Space نفسها أو تحديث session state الخاصة بها، ثم إعادة تشغيل Space. بعد ظهور `visible_auth_controls=[]` يمكن تشغيل text/search مرة واحدة، ثم image مرة واحدة فقط إذا نجح المساران النصي والبحثي.

## الملفات والأدلة

الأدلة الحية المنقحة في [`browser-evidence-2026-08-19.md`](browser-evidence-2026-08-19.md)، وملخص النتائج في [`chatgpt-spaces.md`](chatgpt-spaces.md)، والتحليل البرمجي في [`chatgpt-generation-recovery.md`](chatgpt-generation-recovery.md)، وتقرير live smoke الجديد في [`live-test-report-2026-08-19.md`](live-test-report-2026-08-19.md)، وخطة remediation في [`generation-recovery-remediation-plan.md`](generation-recovery-remediation-plan.md). لا تعتبر هذه النقطة replica-04 ناجحة؛ هي تثبت أن مشكلة الكود والـretry storm عولجت، وأن العائق المتبقي هو session authentication داخل Space.

## live smoke الأخير للنسختين 01 و02

في 2026-08-19، وبعد readiness check ناجح، نجح النص والبحث الحي في replica-01 وreplica-02. أُرسل طلب صورة واحد فقط لكل نسخة؛ كلاهما أعاد HTTP 200 مع `images=[]` ورسالة ChatGPT Free plan image-generation limit. لذلك تُصنف الصورة في هذه الجولة `quota`، ولا تُرسل طلبات إضافية قبل reset. هذه النتيجة لا تلغي الدليل التاريخي الذي فك PNG صالحًا من replica-02؛ إنها تصف حالة quota وقت الاختبار الحالي.
