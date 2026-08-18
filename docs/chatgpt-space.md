# تكامل ChatGPT Spaces مع ai-provider-router

للمسار المبتدئ الكامل من إعداد Hugging Face وSecrets وCookies إلى استخدام router، راجع **[دليل تكامل ChatGPT الكامل](chatgpt-integration-guide.md)**. هذا الملف مرجع تشغيلي متخصص للـreplicas والـroutes والاختبارات.

## الغرض

يستخدم `ai-provider-router` ثلاث نسخ مستقلة من خدمة `chatgpt-api` كمصادر أولى مرتبة لمسارات النص والبحث الحي وتوليد الصور. الاتصال بين router وSpaces يتم عبر HTTP فقط؛ لا تُنسخ Cookies أو جلسة Playwright أو `CHATGPT_STORAGE_STATE_JSON` إلى router، وتبقى حالة الجلسة داخل إعدادات Hugging Face لكل Space.

عند فشل Netscape Cookies بسبب Cloudflare أو `session expired`، يمكن لـ`chatgpt-api` استخدام Secret اختياري باسم `CHATGPT_STORAGE_STATE_JSON`. هذا Secret يخص الحساب والجلسة داخل Space بعينها؛ لا يُوضع في `ai-provider-router` ولا في `AI_ROUTER_CHATGPT_KEYS_JSON`. إذا وُجد Storage State صالح، يتغلب على `CHATGPT_COOKIES_NETSCAPE` داخل تلك Space فقط. يجب اختبار كل حساب على حدة، لأن نقل Storage State الخاص بـ`sg` إلى replica أخرى يربطها بحساب sg.

| الترتيب | Provider ID | Space | Base URL |
|---:|---|---|---|
| 1 | `chatgpt_space_replica_01` | `Yousefsg/chatgpt-api-replica-01` | `https://yousefsg-chatgpt-api-replica-01.hf.space` |
| 2 | `chatgpt_space_replica_02` | `Yousefsg/chatgpt-api-replica-02` | `https://yousefsg-chatgpt-api-replica-02.hf.space` |
| 3 | `chatgpt_space` | `Yousefsg/chatgpt-api-replica-04` | `https://yousefsg-chatgpt-api-replica-04.hf.space` |

يُحافظ الاسم `chatgpt_space` على التوافق مع الإعدادات السابقة، لكنه يشير الآن إلى `replica-04`، بينما تبدأ routes الجديدة من `replica-01` ثم `replica-02` ثم `replica-04`.

## التطابق والإصدار

المصدر الحالي في `chatgpt-api` هو commit `0c35f4e`، المبني فوق إصدار `v1.2.0-storage-state`، ويضيف إصلاح image submission ومهلة الصور إلى جانب دعم Playwright Storage State الكامل. تم نشر الكود الموحد إلى replica-01 بعد تحديث Secret الخاص بحساب `ben2003`، بينما بقي كل replica مرتبطًا بحساب ChatGPT الخاص به.

| النسخة | commit أو بصمة التحقق | الملاحظة |
|---|---|---|
| `/home/ubuntu/work/chatgpt-api` | `0c35f4e` | المصدر المرجعي، إصلاح image submission وtimeout |
| `chatgpt-api-replica-01` | `fee9268` | إصلاح image submission وtimeout، مع جلسة ben2003 فقط |
| `chatgpt-api-replica-02` | `aa69567` | إصلاح image submission وtimeout، مع جلسة pn2003 فقط |
| `chatgpt-api-replica-04` | `41c9a55` | إصلاح image submission وtimeout، مع جلسة sg فقط |
| `vendors/chatgpt-api/` | قيد التحقق بعد sync commit `0c35f4e` | نسخة المصدر المضمنة دون Git وcache وملفات الأسرار |

توجد فروقات commit طبيعية بين مستودعات Spaces بسبب نشر كل Space في وقت مختلف؛ معيار التطابق التشغيلي هو وجود كود `browser_gateway.py` الحالي وسر Storage State الخاص بالحساب الصحيح، لا نقل جلسة حساب إلى Space أخرى. لا تُحفظ ملفات Storage State في Git أو في `vendors/chatgpt-api/`.

## قاعدة فصل المسارات

يستخدم `chatgpt-api` فحص DOM/HTML للصور فقط. مسارات `text` و`text_grounded_search` تعتمد على `choices[0].message.content` ولا تستدعي image locators أو image-count. عند طلب الصورة فقط يُفعل `capture_images`، ثم تُقبل الصور التي تحمل marker مثل `Generated image` أو رابط ChatGPT backend الخاص بملف مولد.

يطبق router القاعدة نفسها على adapter. وهو يرفض favicon وavatar والصور القديمة، ولا يعيد `data_base64` إلا عند وجود صورة مولدة قابلة للتنزيل. في البحث الحي، يتعرف adapter على `search` و`google_search` و`web_search_preview` ويضيف تلقائيًا:

```text
ابحث في الويب بحث حي:
```

## الإعدادات

يتم تعريف replicas في `config/providers.json`، وتُقرأ عناوينها من متغيرات بيئة اختيارية:

```dotenv
CHATGPT_API_BASE_URL=https://yousefsg-chatgpt-api-replica-04.hf.space
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا
AI_ROUTER_CHATGPT_KEYS_JSON=[]
```

القيمة الافتراضية موجودة في `config/providers.json`، ولذلك لا يلزم وضع Base URLs في `.env` إلا عند الحاجة إلى تبديلها. لا تحفظ `.env` في Git.

يستخدم كل Provider مجموعة المفاتيح نفسها `chatgpt_space_default`. يستطيع router قراءة Secret واحد من `CHATGPT_API_SECRET_KEY` أو مصفوفة مرتبة من `AI_ROUTER_CHATGPT_KEYS_JSON`. في الإنتاج، يجب أن تكون قيمة كل Secret مساوية لـ`API_SECRET_KEY` في Space الهدف. أما `CHATGPT_STORAGE_STATE_JSON` و`CHATGPT_COOKIES_NETSCAPE` فهما Secrets داخل Space فقط، ولا يعرف router محتواهما.

## ترتيب routes

يظهر ترتيب المصادر في `config/models.json` كما يلي:

| المسار | ترتيب ChatGPT الأول |
|---|---|
| `text` | `replica-01` ثم `replica-02` ثم `replica-04` |
| `text_grounded_search` | `replica-01` ثم `replica-02` ثم `replica-04` |
| `image` | `replica-01` ثم `replica-02` ثم `replica-04` |
| `image_grounded_search` | `replica-01` ثم `replica-02` ثم `replica-04` |

Router يجرب العناصر بالترتيب، وينتقل إلى replica التالي عند خطأ قابل للانتقال أو quota أو عدم وجود صورة. نجاح replica-01 يعني أن replicas اللاحقة لا تُستدعى في ذلك الطلب؛ أما عند تعطلها فتعمل replicas التالية كـfallback مرتب.

## أمثلة التشغيل

### النص

```bash
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا \
ai-router --config-dir config --state-db /tmp/chatgpt-router-text.db \
  call-auto --output-type text \
  --operation replica_text \
  --user "قل فقط: نجح اختبار router مع replicas"
```

### البحث الحي

```bash
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا \
ai-router --config-dir config --state-db /tmp/chatgpt-router-search.db \
  call-auto --output-type text --grounding search \
  --operation replica_search \
  --user "ابحث عن اخر موديل anthropic ai"
```

### الصورة

```bash
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا \
ai-router --config-dir config --state-db /tmp/chatgpt-router-image.db \
  call-auto --output-type image \
  --operation replica_image \
  --user "generate image of wise stikman read book in libary"
```

تستخدم الصورة مهلة لا تقل عن 540 ثانية، وثلاث محاولات محدودة عند غياب `images`. إذا أعادت الخدمة رسالة Free-plan quota، يسجل router `quota` وينتقل إلى replica التالي بدل إعادة المحاولة بلا فائدة.

## نتيجة الاختبار الحي الحالي

أُجريت اختبارات النص والبحث عبر المسار الحقيقي للـrouter باستخدام `config/providers.json` و`config/models.json` كما هما، ومن دون `CHATGPT_API_BASE_URL_OVERRIDE` أو أي override مؤقت. كما اختُبر replica-01 مباشرة بعد نشر Storage State الخاص بحساب `ben2003`.

| الاختبار | النتيجة الفعلية |
|---|---|
| replica-01 مباشرة — نص | **نجح HTTP 200** وأعاد `replica-01 storage state text probe` من endpoint `v1/chat/completions`. |
| replica-01 مباشرة — بحث | **نجح HTTP 200** مع إجابة بحث حي ومراجع نصية. |
| replica-02 مباشرة — نص | **نجح HTTP 200** باستخدام Storage State الخاص بحساب `pn2003`. |
| replica-02 مباشرة — بحث | **نجح HTTP 200** مع إجابة Anthropic ومؤشرات مصادر. |
| replica-04 مباشرة — نص | **نجح HTTP 200** باستخدام Storage State الخاص بحساب `sg`. |
| replica-04 مباشرة — بحث | **نجح HTTP 200** مع إجابة بحث حي ومراجع نصية. |
| router الحقيقي — نص | **نجح**، وأعاد `router final replica-01 text probe` عبر route `text`. |
| router الحقيقي — بحث حي | **نجح** عبر route `text_grounded_search`، وأعاد JSON يتضمن الإجابة واسم النموذج، مع إضافة مسار البحث الحي تلقائيًا. يجب التحقق من الادعاءات والروابط خارجيًا قبل اعتمادها كمعلومة نهائية. |
| router الحقيقي — صورة قبل الإصلاح | فشل bounded: replica-01 لم يعرض image data، replica-02 أعاد `429` بسبب quota، وreplica-04 انتهى بـ`RemoteDisconnected`/timeout. |
| السبب الجذري المكتشف | كان `BrowserGateway` داخل Spaces يستخدم مهلة افتراضية `210` ثانية حتى لطلبات الصور، بينما router ينتظر 540 ثانية؛ كما كان fallback يقبل نقر زر الإرسال دون التحقق من أن composer أُرسل فعليًا. سجل replica-04 أكد `assistant_count=0`, `generation_active=false`, و`prompt_count=1` عند timeout. |
| الإصلاح المنشور | رفع مهلة انتظار الصورة داخليًا إلى 540 ثانية على الأقل، والتحقق من بدء الإرسال/اختفاء prompt بعد Enter وDOM click وmouse click قبل متابعة الانتظار. نُشر إلى Spaces الثلاثة. |
| router الحقيقي — صورة بعد الإصلاح | **نجح** بحالة `exit=0` عبر route `image`، وأعاد PNG بصيغة `image/png`، حجمها `776,668` بايت وأبعادها `1254×1254` وmode `RGB`. |
| الاختبارات المحلية | `38` اختبارًا ناجحًا في router، و`9` اختبارات ناجحة في chatgpt-api قبل نشر replica-01. |
| compileall | ناجح للمصدر والنسخة المضمنة. |

> **الخلاصة التشغيلية:** النص والبحث الحي يعملان في **replica-01 وreplica-02 وreplica-04**، كما يعملان عبر router الحقيقي. وبعد إصلاح مهلة الصور والتحقق من نجاح زر الإرسال، نجح توليد صورة عبر router الحقيقي وأعاد PNG صالحة بأبعاد `1254×1254`. تبقى quota ChatGPT الخاصة بكل حساب حدًا خارجيًا مستقلًا؛ عند ظهور `429` لا يعيد router الطلب بلا حدود.

## أسرار Spaces

`API_SECRET_KEY` يحمي endpoint HTTP؛ يرسله المستهلك في `Authorization: Bearer ...`. `CHATGPT_COOKIES_NETSCAPE` يسجل جلسة ChatGPT Web داخل Space فقط، ولا يجب نسخه إلى router أو Git. Hugging Face Access Token مخصص لإدارة Hub ورفع الملفات، وليس بديلًا عن `API_SECRET_KEY`.

### `CHATGPT_STORAGE_STATE_JSON` — جلسة Playwright الكاملة

هذا Secret اختياري عالي الحساسية، ويُستخدم داخل `chatgpt-api` عندما لا تكفي Netscape Cookies بسبب Cloudflare أو `session expired`. يجب أن يكون JSON كاملًا بصيغة Playwright Storage State، وأن يخص حساب ChatGPT الموجود في Space نفسها. في هذا النشر، يستخدم `replica-01` جلسة `ben2003` فقط، و`replica-02` جلسة `pn2003` فقط، و`replica-04` جلسة `sg` فقط. لا تضع هذا Secret في router أو `AI_ROUTER_CHATGPT_KEYS_JSON`، ولا تخلط جلسة حساب مع Space أخرى.

للحصول عليه، سجّل الدخول يدويًا بالحساب المقصود داخل Chrome/Playwright، صدّر Storage State من السياق المصادق، ثم خزّنه في Hugging Face Space عبر **Settings → Repository secrets and variables → Secrets** بالاسم الدقيق `CHATGPT_STORAGE_STATE_JSON`. لا تطبع JSON في الطرفية، ولا ترفقه في commit أو issue أو سجل CI. نجاحه يُقاس بعودة `/health` إلى `ready: true` ثم نجاح طلب نص مباشر؛ ظهور `session expired` يعني أن الجلسة انتهت ويجب تصدير جلسة جديدة للحساب نفسه.

قيم Secrets write-only في Hugging Face؛ يمكن التحقق من أسماء المفاتيح فقط، لا قراءة قيمها. عند تغيير Cookies أو Storage State أو Secret، تعيد Hugging Face تشغيل Space تلقائيًا. يجب تدوير Cookies وStorage State وAPI keys فورًا إذا ظهرت في سجل أو محادثة، ثم تحديث Space أو router بالقيمة الجديدة واختبار health دون طباعة السر.

## فحوص التشغيل والأمن

```bash
curl -fsS https://yousefsg-chatgpt-api-replica-01.hf.space/health
curl -fsS https://yousefsg-chatgpt-api-replica-02.hf.space/health
curl -fsS https://yousefsg-chatgpt-api-replica-04.hf.space/health

PYTHONPATH=src python -m compileall -q src tests vendors/chatgpt-api
PYTHONPATH=src python -m unittest discover -s tests -v
ai-router --config-dir config --state-db /tmp/chatgpt-router-summary.db summary
```

يجب ألا يظهر Secret في `summary` أو diff أو ملفات JSON. لا تضع Cookies أو Hugging Face tokens أو GitHub tokens داخل `vendors/` أو `config/`.

## الملفات ذات الصلة

| الملف | الوظيفة |
|---|---|
| `config/providers.json` | تعريف replicas الثلاثة وعناوينها والمهل |
| `config/key_pools.json` | ربط مفاتيح ChatGPT بالبيئة |
| `config/models.json` | ترتيب replicas في routes النص والبحث والصورة |
| `src/ai_router/providers/chatgpt_space.py` | HTTP adapter والبحث واستخراج الصور والـfallback |
| `vendors/chatgpt-api/` | نسخة المصدر المطابقة للإصدار المضمنة داخل router |
| `tests/test_multiroute.py` | اختبارات الترتيب والبحث والصورة والـfallback |

## المراجع

[1]: https://huggingface.co/docs/hub/spaces-overview#managing-secrets "Hugging Face Spaces: managing secrets and variables"
[2]: https://huggingface.co/docs/huggingface_hub/en/guides/repository "Hugging Face Hub repository management"
[3]: https://github.com/ysrg2003/chatgpt-api/releases/tag/v1.1.2-image-boundary-docs "chatgpt-api v1.1.2-image-boundary-docs"
[4]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router repository"
