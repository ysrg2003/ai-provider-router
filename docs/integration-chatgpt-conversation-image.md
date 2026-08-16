# تكامل توليد الصور عبر محادثة ChatGPT العادية

هذا التكامل مبني على baseline `v1.0.0` فقط. مصدر الخدمة هو ملفات `chatgpt-without-api-main` المرفقة، وليس مسار Images API أو أي تغييرات لاحقة في مستودع الراوتر.

تفتح الخدمة صفحة `https://chatgpt.com/` العادية، وتضع prompt في `#prompt-textarea`، ثم ترسل الرسالة من زر المحادثة العادي. عندما تظهر صورة كبيرة في رد المساعد، تُنزّل bytes الصورة داخل الخدمة وتعيدها في عقد `POST /v1/chat/completions` كجزء `image_url` من نوع `data:image/...;base64,...`.

## الأولوية والمسار

يحتوي `config/models.json` في هذا الفرع على `chatgpt_conversation/chatgpt-conversation` في أول `output_routes.image`. لذلك يستخدم `complete_auto(..., output_type="image")` هذا المزود أولًا. إذا فشل HTTP أو لم تُرجع المحادثة صورة، يستخدم الراوتر Gemini image models الموجودة في baseline بالترتيب الأصلي.

| الترتيب | المزود | الطريقة | المدخل | المخرج |
|---:|---|---|---|---|
| 1 | `chatgpt_conversation` | `POST /v1/chat/completions` | نص | صورة |
| 2 | `google_gemini` | `generateContent` | نص أو صورة | صورة أو نص |
| 3 وما بعده | Gemini image models | `generateContent` | نص أو صورة | صورة أو نص |

## الأسرار

في المشروع المستدعي يكفي ضبط `CHATGPT_API_KEY` بحيث يساوي قيمة `API_SECRET_KEY` في خدمة Hugging Face. يمكن أيضًا استخدام `AI_ROUTER_CHATGPT_CONVERSATION_KEYS_JSON` إذا كان المطلوب pool مرتب من المفاتيح. لا تُرسل cookies إلى `ai-provider-router` ولا تحفظها في GitHub.

داخل خدمة `chatgpt-api` يجب ضبط `CHATGPT_COOKIES_NETSCAPE` كـSecret في Space. هذا المتغير يبقى داخل الخدمة ويُحقن في BrowserContext عند إنشاء كل محادثة. للاختبار المحلي فقط يمكن تمريره من ملف cookies المرفق في الذاكرة، مع عدم طباعته أو تخزينه في source.

| المتغير | المكان | الوظيفة |
|---|---|---|
| `API_SECRET_KEY` | خدمة chatgpt-api | حماية HTTP API |
| `CHATGPT_COOKIES_NETSCAPE` | خدمة chatgpt-api فقط | جلسة ChatGPT داخل المتصفح |
| `CHATGPT_API_KEY` | ai-provider-router | قيمة Authorization للوصول إلى الخدمة |
| `AI_ROUTER_CHATGPT_CONVERSATION_KEYS_JSON` | ai-provider-router اختياريًا | pool مرتب بديل عن المفتاح المفرد |

## التحقق المحلي

تم اختبار المسار end-to-end محليًا باستخدام cookies المرفقة. نجح health check، ثم أُرسل طلب إلى `/v1/chat/completions` في خدمة الملفات المرفقة، وعاد جزء صورة PNG فعلي. بعد ذلك استخدم الراوتر المعزول route `image`، وأظهر plan أن `chatgpt_conversation` هو أول نموذج، ثم أعاد صورة PNG عبر هذا المزود.

كما نجحت اختبارات fallback المحلية: عند جعل adapter ChatGPT يفشل، انتقل الراوتر إلى Gemini؛ وعند وجود مفتاح ChatGPT صالح، جرى استدعاء ChatGPT أولًا.

## النص والبحث الحي

أصبح `chatgpt_conversation` أيضًا أول عنصر في `output_routes.text` و`output_routes.text_grounded_search`. إذا كان المطلوب بحثًا حيًا، يمكن إرسال طلب صريح مثل:

```text
ابحث في الويب بحث حي عن آخر أخبار الذكاء الاصطناعي، واذكر المصادر والروابط.
```

عند اكتشاف `search`، يمرر الراوتر route `text_grounded_search` ويضيف adapter تعليمات واضحة إلى ChatGPT لتنفيذ بحث حي في الويب وعدم الاعتماد على الذاكرة وحدها وذكر المصادر. هذه التعليمات لا تستخدم Gemini Search API؛ البحث ينفذ داخل جلسة ChatGPT العادية عبر المتصفح.

| نوع الطلب | route | الأول | fallback |
|---|---|---|---|
| نص عادي | `text` | `chatgpt_conversation` عبر `interaction_text` | Gemini النصي ثم بقية السلسلة |
| بحث حي | `text_grounded_search` | `chatgpt_conversation` مع تعليمات البحث | Gemini `gemini-2.5-flash` مع أداة `search` |
| صورة | `image` | `chatgpt_conversation` عبر `generate_image` | Gemini image models |

## هل الطلبات متوازية؟

لا. تنفيذ الراوتر الحالي **تسلسلي**: يمر على provider/model ثم key واحدًا في كل مرة، وينتظر نهاية HTTP request قبل تجربة العنصر التالي. عند النجاح يعيد النتيجة فورًا ولا يرسل الطلب نفسه إلى Gemini. عند الفشل يسجل الحالة، يحدّث cursor، يطبق backoff إذا كان الخطأ قابلًا لإعادة المحاولة، ثم ينتقل إلى التالي. لذلك لا يوجد استهلاك متزامن لمفتاح ChatGPT وGemini في الطلب الواحد.

هذه خاصية مقصودة للحفاظ على الأولوية وتقليل الاستهلاك، لكنها تجعل زمن الاستجابة في حالة الفشل مساويًا تقريبًا لمجموع محاولات الفشل المتتالية. يجب إبقاء timeout والـmax attempts مضبوطين، وعدم تشغيل smoke متوازٍ لنفس الجلسة.

## التحقق المحلي الأخير

نجح التحقق المحلي على الخدمة الجديدة والراوتر المعزول. عاد طلب النص عبر route `text` ومن provider `chatgpt_conversation`. وعاد طلب البحث الحي الحرفي عبر route `text_grounded_search` ومن provider نفسه، وكانت الاستجابة تحمل عبارة تفيد بتنفيذ بحث حي ومصادر. كما نجحت suite الراوتر والadapter وعددها **33 اختبارًا**.

## حدود هذا المسار

هذا ليس OpenAI Images API رسميًا؛ إنه أتمتة لواجهة ChatGPT العادية عبر Playwright. لذلك تعتمد الاستمرارية على صلاحية cookies وتغير DOM في ChatGPT. عند انتهاء الجلسة أو تغير composer، يفشل المزود بأمان ويستمر fallback وفق سياسة الراوتر. لا ينبغي تسجيل cookies أو prompt الكامل أو محتوى data URL في السجلات.
