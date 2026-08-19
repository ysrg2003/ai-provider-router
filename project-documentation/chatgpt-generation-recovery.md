# إصلاح 503 الناتج عن generation عالق في ChatGPT Spaces

## الدليل الحي

أظهر فحص المتصفح الحي لصفحة Hugging Face Logs في replica-04 أن الـSpace نفسها كانت `Running`، وأن التطبيق بدأ بنجاح وكتب `ChatGPT browser gateway is ready; loaded 71 cookies`. لكن طلب ChatGPT لم يُنتج رسالة assistant مستقرة. النمط المنقح في السجل كان:

```text
ChatGPT prompt submitted with explicit send button fallback
TimeoutError: ChatGPT response did not stabilize before timeout
assistant count=1, lengths=0
main article count=0
main count=1
generation_active=True
send_button_count=1, send_states=True/True
POST /v1/chat/completions 503 Service Unavailable
```

ظهر النمط نفسه بعد الإرسال عبر Enter. لذلك فالـ503 لم يكن ناتجًا عن `/health` أو Swagger أو API secret مرفوض، ولم تظهر `429` أو رسالة `Free plan limit`. المشكلة المثبتة هي أن browser gateway بقي في حالة generation نشطة مع assistant فارغ، ثم حوّل timeout إلى 503.

## الإصلاح

تم إصلاح المصدر في [`ysrg2003/chatgpt-api`](https://github.com/ysrg2003/chatgpt-api) في commit [`c42cc05`](https://github.com/ysrg2003/chatgpt-api/commit/c42cc05)، ثم مزامنة `vendors/chatgpt-api/browser_gateway.py` في هذا المشروع.

قبل إرسال طلب جديد، يفحص gateway وجود generation نشطة. إذا وُجدت، يحاول الضغط على stop control ثم يعيد تحميل صفحة ChatGPT عندما تبقى الحالة نشطة، ولا يسمح بإرسال الطلب التالي إلا بعد عودة composer/input. وعند انتهاء `_wait_for_response()` بtimeout، يُنفّذ recovery نفسه قبل إعادة الخطأ. لا يعتبر الإصلاح assistant فارغًا نجاحًا، ولا يسجل Cookies أو Storage State.

## الاختبارات

أضيف regression باسم `test_generation_recovery_reloads_when_stop_control_fails` في المصدر. اجتازت اختبارات المصدر و`compileall`، كما اجتازت نسخة vendor compilation. يلزم بعد نشر الإصلاح في كل Space تشغيل رحلة حية منفصلة للنص والبحث والصورة؛ نجاح `/health` أو `/docs` وحده لا يكفي.

## التحقق بعد النشر

نُشر الإصلاح إلى Spaces الثلاثة بهذه commits المنقحة:

| Space | HF commit | post-deploy state |
|---|---|---|
| replica-01 | `85e43bebd060e937e977c9508616e1f59362d66a` | `Running`, gateway ready, 90 cookies loaded |
| replica-02 | `590fc82202d3a07db0878e2806f3706c59c78176` | `Running`, gateway ready, 92 cookies loaded |
| replica-04 | `0d139e4fd9d269c2df99a1c392dc2b31ac126f5a` | `Running`, gateway ready, 71 cookies loaded |

في [workflow 32240146321](https://github.com/ysrg2003/ai-provider-router/actions/runs/32240146321)، نجح text/search في replica-01 وreplica-02، وفشلت image في النسختين. فشلت السيناريوهات الثلاثة في replica-04 بـ503 transient. التقرير التفصيلي المنقح محفوظ في [`chatgpt-spaces-functional-32240146321.json`](chatgpt-spaces-functional-32240146321.json).

## النتيجة الدقيقة وحدود الإصلاح

Logs الحية لـreplica-04 أثبتت أن الإصلاح يعمل فعليًا: ظهر `WARNING ChatGPT generation remained active; reloading the browser page` قبل إعادة الخطأ. لكن recovery يُطبّق بعد timeout للطلب الجاري ثم يعيد الخطأ؛ لذلك لا يضمن نجاح الطلب نفسه، بل يهيئ الصفحة للطلب التالي. كما ظهر في replica-01 timeout مختلف مع `generation_active=False` وassistant lengths غير فارغة لكن `main article:count=0`، وهو stabilization/DOM failure لا يغطيه هذا الإصلاح.

بالتالي، الإصلاح **متحقق من حيث النشر والتنفيذ في الحالة المستهدفة، لكنه ليس حلًا كاملًا لكل 503**. لا توجد في التقرير رسالة `Free plan limit` أو HTTP 429، لذلك لا يجوز تفسير image failures الحالية كنفاد quota دون دليل إضافي. يجب فصل التحقيق اللاحق إلى: session/upstream failure في replica-04، وimage payload/contract أو upstream failure في replica-01/02، وDOM stabilization fallback في replica-01.

لا توجد في هذا الملف API secrets أو Cookies أو Storage State أو Authorization headers. لأدلة المتصفح المنقحة، راجع [`browser-evidence-2026-08-19.md`](browser-evidence-2026-08-19.md)، ولنتائج كل Space راجع [`chatgpt-spaces.md`](chatgpt-spaces.md).
