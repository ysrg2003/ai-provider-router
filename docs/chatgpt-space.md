# تكامل ChatGPT Space

## الغرض

يستخدم `ai-provider-router` خدمة `chatgpt-api` المنشورة في Hugging Face Space كمصدر أول لمسارات **النص** و**البحث الحي** و**توليد الصور**. يجري الاتصال عبر HTTP فقط؛ لذلك لا تُنسخ Cookies أو جلسة Playwright إلى الراوتر، ولا يحتاج المشروع المستهلك إلى تشغيل Chromium محليًا.

> عنوان الخدمة الافتراضي هو `https://yousefsg-chatgpt-api.hf.space`، بينما يبقى Secret داخل البيئة أو مدير أسرار CI ولا يدخل Git.

## الملفات ذات الصلة

| الملف | الوظيفة |
|---|---|
| `config/providers.json` | تعريف `chatgpt_space` ونقطة Space والمهلة الافتراضية البالغة 300 ثانية |
| `config/key_pools.json` | قراءة المفتاح من `AI_ROUTER_CHATGPT_KEYS_JSON` أو `CHATGPT_API_SECRET_KEY` |
| `config/models.json` | وضع ChatGPT في أول عناصر routes الخاصة بـ`text` و`text_grounded_search` و`image` و`image_grounded_search` |
| `src/ai_router/providers/chatgpt_space.py` | adapter HTTP، وتطبيع النص والصورة ومعالجة أخطاء HTTP |
| `vendors/chatgpt-api/` | نسخة مستقلة من ملفات خدمة Space للرجوع والتشغيل المنفصل، دون `.git` أو أسرار |
| `tests/test_multiroute.py` | اختبارات headers، بادئة البحث، وتحويل `data_url` إلى `data_base64` |

## الإعداد المحلي

انسخ نموذج البيئة، ثم ضع Secret الحقيقي محليًا فقط:

```bash
cp .env.example .env
```

للاستخدام البسيط:

```dotenv
CHATGPT_API_BASE_URL=https://yousefsg-chatgpt-api.hf.space
CHATGPT_API_SECRET_KEY=ضع_المفتاح_الحقيقي_هنا
```

وللتدوير المرتب بين أكثر من Secret:

```dotenv
AI_ROUTER_CHATGPT_KEYS_JSON=[
  {"id":"chatgpt-primary","key":"ضع_المفتاح_الأول_هنا","project":"chatgpt-space"},
  {"id":"chatgpt-secondary","key":"ضع_المفتاح_الثاني_هنا","project":"chatgpt-space"}
]
```

عند وجود المصفوفة، يقرأها الراوتر أولًا. وإذا كانت فارغة أو غير موجودة، يستخدم `CHATGPT_API_SECRET_KEY`. لا تحفظ `.env` في Git، ولا تضع Cookies أو مفاتيح HF أو مفاتيح GitHub في `config/` أو `vendors/`.

## أولوية المسارات

يُظهر الأمر الآتي ترتيب المصدر الأول دون تنفيذ طلب نموذج:

```bash
ai-router --config-dir config --state-db /tmp/ai-router-plan.db \
  route-plan --user "أنشئ صورة عن مكتبة مستقبلية"
```

ترتيب المسارات هو:

| المسار | أول provider | method | ملاحظة |
|---|---|---|---|
| `text` | `chatgpt_space` | `interaction_text` | يعيد نصًا عاديًا؛ وهذا هو المسار المناسب لطلبات النص العامة |
| `text_grounded_search` | `chatgpt_space` | `interaction_text` | يرسل الراوتر أداة `search` ويضيف Space بادئة البحث الحي |
| `image` | `chatgpt_space` | `image` | يبحث عن `images[].data_url` ثم يدعم `images[].src` كمسار تنزيل احتياطي |
| `image_grounded_search` | `chatgpt_space` | `image` | يجمع أولوية الصور مع مؤشر البحث الحي |

لا يُضاف `chatgpt_space` إلى `model_chains.default` تلقائيًا؛ هذا يحافظ على عقد `call-json` الحالية للسلاسل المنظمة. أما `complete_auto` فيختار output route وفق نوع الطلب، ولذلك يبدأ من ChatGPT في الفئات المحددة أعلاه.

## البحث الحي

عند اختيار مسار `text_grounded_search`، يمرر الراوتر أداة `search` إلى adapter. ويحوّل adapter الطلب إلى نص يبدأ بالعبارة:

```text
ابحث في الويب بحث حي:
```

إذا كانت العبارة موجودة أصلًا فلن يكررها. كما أن خدمة Space نفسها تملك كشفًا مستقلًا لمؤشرات البحث، ولذلك يظل السلوك متوافقًا مع الاستخدام المباشر للخدمة.

مثال:

```bash
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا \
ai-router --config-dir config --state-db /tmp/ai-router-search.db \
  call-auto --output-type text --grounding search \
  --system "أجب بالعربية مع ذكر روابط المصادر." \
  --user "ما آخر أخبار نماذج الذكاء الاصطناعي؟"
```

## النص العام

يستخدم النص العام `interaction_text` لأن endpoint Space يعيد `choices[0].message.content` كنص. مثال smoke test:

```bash
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا \
ai-router --config-dir config --state-db /tmp/ai-router-text.db \
  call-auto --output-type text \
  --system "أجب بكلمة واحدة فقط." \
  --user "قل: نجح"
```

أما إذا احتاج المستهلك كائن JSON من سلسلة منظمة، فيبقى `call-json` و`complete_json` متاحين، ويقوم adapter بتحليل النص وإزالة code fences عند الحاجة. يجب أن يطلب system prompt صراحةً JSON صالحًا.

## توليد الصور

يستخدم adapter نفس endpoint `/v1/chat/completions`، ثم يتوقع من Space أن يعيد `images`. يفضّل adapter الحقل `images[].data_url` ويحوّله إلى:

```json
{
  "output_type": "image",
  "mime_type": "image/png",
  "data_base64": "...",
  "source": "chatgpt_space"
}
```

وإذا أعاد Space `images[].src` فقط، يحاول adapter تنزيل الرابط باستخدام Secret الموجود في الذاكرة، بشرط أن يكون الرابط HTTP(S) وأن يعيد `content-type` يبدأ بـ`image/`. لا تُسجل قيمة الرابط أو Secret في الرسائل التشخيصية.

مثال:

```bash
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا \
ai-router --config-dir config --state-db /tmp/ai-router-image.db \
  call-auto --output-type image \
  --operation image_smoke \
  --user "generate image of a wise stickman reading a book in a library"
```

قد يستغرق توليد الصورة عدة دقائق. لذلك يفرض adapter مهلة 540 ثانية، ويحاكي workflow الناجح في `chatgpt-api` بثلاث محاولات كحد أقصى مع انتظار 20 ثانية بين المحاولات إذا أعادت الخدمة نصًا بلا `images`. إذا أعادت الخدمة رسالة Free-plan quota، يتوقف adapter مباشرة ويسجل `quota` بدل إعادة الطلب بلا فائدة. إذا لم تعُد `images` بعد المحاولات المحدودة، يسجل الراوتر فشل المصدر الأول وينتقل إلى المصدر التالي وفق سياسة fallback؛ لا ينبغي اعتبار نص الوصف وحده صورة ناجحة.

## فحوص التشغيل

ابدأ بفحص الجاهزية دون Secret:

```bash
curl -fsS https://yousefsg-chatgpt-api.hf.space/health
```

ثم شغّل الاختبارات المحلية دون أسرار:

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

وتحقق من أن الملخص لا يطبع القيم:

```bash
ai-router --config-dir config --state-db /tmp/ai-router-summary.db summary
```

> نجاح الاختبارات المحلية يثبت wiring وnormalization فقط. أما نجاح الطلب الحي فيعتمد على جاهزية Space، صلاحية Secret، جلسة ChatGPT وCookies الموجودة في Space، والحصة المتاحة.

## بطاقات الاعتماد والمتغيرات

### `CHATGPT_API_SECRET_KEY` — مفتاح الوصول إلى Space

**الغرض.** هذا Secret يثبت أن الراوتر مخول لاستدعاء endpoint الخاص بـ`chatgpt-api`. بدونه يعيد Space خطأ مصادقة، ولا يعمل أي طلب حي.

**التصنيف.** Secret عالي الحساسية؛ يعادل كلمة مرور API ولا يجوز وضعه في Git أو URL أو سجل الأوامر.

**قبل البدء.** تحتاج إلى صلاحية تعديل Space `Yousefsg/chatgpt-api` أو إلى Secret بديل أنشأه مالك الخدمة. المفتاح الذي يقبله Space هو القيمة التي عُيّنت في Space باسم `API_SECRET_KEY`؛ لا تستخدم Hugging Face Access Token بدلًا منه.

**طريقة الإنشاء أو التحقق.**

1. افتح [إعدادات Space](https://huggingface.co/spaces/Yousefsg/chatgpt-api/settings) وسجّل الدخول بالحساب المالك أو المتعاون.
2. افتح قسم **Variables and secrets** ثم اختر **Secrets**، لا **Variables**؛ توصي Hugging Face بحفظ مفاتيح API والاعتمادات في Secrets، وتعرضها للتطبيق كمتغيرات بيئة دون إظهار قيمتها بعد الحفظ [1].
3. أنشئ أو حدّث Secret باسم `API_SECRET_KEY` داخل Space، ثم أعد تشغيل Space إذا طلبت الواجهة ذلك.
4. انسخ القيمة مرة واحدة إلى مدير أسرار محلي أو GitHub؛ لا تطبعها ولا تحفظها في ملف متعقب.

**صيغة آمنة فقط.**

```text
REPLACE_WITH_CHATGPT_SPACE_SECRET
```

**مكان التخزين.** محليًا ضعه في `.env` تحت الاسم `CHATGPT_API_SECRET_KEY`. في GitHub افتح المستودع `ysrg2003/ai-provider-router` ثم **Settings → Secrets and variables → Actions → Secrets → New repository secret**، وأنشئ الاسم `CHATGPT_API_SECRET_KEY`. لا تستخدم GitHub Variables لهذا المفتاح.

**كيف يقرأه الكود.** `config/key_pools.json` يربط `CHATGPT_API_SECRET_KEY` كـfallback، وتقرأه `RouterConfig.keys_for()` دون إدراجه في `summary` أو payload.

**التحقق الأدنى.** نفّذ طلبًا نصيًا قصيرًا مع تمرير المتغير إلى العملية، ثم تحقق من `route: "text"` و`output_type: "text"` دون طباعة المتغير. النجاح المتوقع هو HTTP 200 من Space ووجود `choices[0].message.content`.

**الفشل والاسترداد.** خطأ 401 يعني أن القيمة لا تطابق `API_SECRET_KEY` في Space أو أن Space لم يُعد تشغيله بعد التغيير؛ طابق الاسمين، حدّث Secret، ثم أعد smoke test. خطأ 503 يعني أن Space أو جلسة المتصفح غير جاهزة؛ افحص `/health`. خطأ 429 يعني معدل أو حصة؛ انتظر cooldown أو عطّل المصدر مؤقتًا.

**التدوير والإلغاء.** أنشئ قيمة جديدة في Space، حدّث Secret في كل بيئة، نفّذ smoke test، ثم احذف القيمة القديمة من Space ومدير أسرار GitHub. إذا ظهرت القيمة في المحادثة أو سجل أو commit، ألغها فورًا واعتبرها مكشوفة حتى لو لم يستخدمها طرف آخر.

### `AI_ROUTER_CHATGPT_KEYS_JSON` — مجموعة مفاتيح اختيارية

**الغرض.** تسمح هذه المصفوفة بتدوير أكثر من Secret بالترتيب، مع حفظ cursor وحالة cooldown لكل مفتاح في SQLite.

**التصنيف.** Secret JSON؛ كل قيمة `key` داخله حساسة.

**الصيغة الآمنة.**

```json
[
  {"id":"chatgpt-primary","key":"REPLACE_WITH_SECRET_1","project":"chatgpt-space"},
  {"id":"chatgpt-secondary","key":"REPLACE_WITH_SECRET_2","project":"chatgpt-space"}
]
```

**مكان التخزين وكيف يقرأه الكود.** ضعه في `.env` أو GitHub Secret باسم `AI_ROUTER_CHATGPT_KEYS_JSON`. يقرأه `RouterConfig.keys_for("chatgpt_space")` أولًا؛ إذا كانت القيمة فارغة أو `[]` يعود إلى `CHATGPT_API_SECRET_KEY`. يحافظ ترتيب العناصر على ترتيب المحاولة، ولا يطبع الراوتر محتوى المصفوفة.

**التحقق والاسترداد.** استخدم `ai-router ... summary` وتأكد من ظهور عدد الأسرار فقط. إذا ظهر خطأ JSON، تأكد من الأقواس والاقتباسات وعدم وجود تعليق داخل القيمة. عند 401 أوقف المفتاح المخالف ودوّره بدل تكرار الطلب بلا نهاية.

### `CHATGPT_API_BASE_URL` — عنوان Space

**التصنيف.** متغير تشغيل غير سري.

**الافتراضي والقيم المقبولة.** القيمة الافتراضية `https://yousefsg-chatgpt-api.hf.space`، ويجب أن تكون URL لـSpace أو خدمة متوافقة مع endpoint `/v1/chat/completions` عبر HTTPS. يقرأه `config/providers.json` من خلال `base_url_env`.

**مكان الضبط والتحقق.** ضعه في `.env` أو GitHub Variable باسم `CHATGPT_API_BASE_URL`، ثم نفّذ `curl -fsS "$CHATGPT_API_BASE_URL/health"`. النجاح هو HTTP 200؛ إذا اختلف العنوان، افحص أن المسار لا يحتوي `/v1` مرتين لأن adapter يضيفه بنفسه.

### `CHATGPT_COOKIES_NETSCAPE` — جلسة ChatGPT داخل Space فقط

**التصنيف.** Cookie/session Secret عالي الخطورة، وليس إعدادًا مطلوبًا في `ai-provider-router`.

**الاستخدام.** تقرأه الخدمة الموجودة في `vendors/chatgpt-api/` عند تشغيل Space، وليس الراوتر. يجب وضعه فقط في **Secrets** داخل Space باسم `CHATGPT_COOKIES_NETSCAPE`، مع إبقائه خارج المستودعين؛ Cookies قد تمنح صلاحية حساب كاملة وقد تنتهي أو تُلغى.

**الفشل والتدوير.** إذا أصبح `/health` غير جاهز أو ظهرت رسالة انتهاء الجلسة، حدّث Cookie عبر قناة آمنة، استبدل Secret في Space، وأعد التشغيل. عند التعرض، سجّل الخروج أو ألغِ جلسة ChatGPT، استخرج Cookie جديدًا، ودوّر `API_SECRET_KEY` أيضًا إذا ظهر في السجل نفسه. لا تنسخ Cookie إلى الراوتر أو GitHub Actions.

## سياسة الأسرار والأمن

| السر | مكانه الصحيح | ما يجب تجنبه |
|---|---|---|
| `CHATGPT_API_SECRET_KEY` | `.env` محليًا أو GitHub Secret | وضعه في README أو JSON أو command history إن أمكن |
| `AI_ROUTER_CHATGPT_KEYS_JSON` | مدير أسرار البيئة | commit للمصفوفة الحقيقية |
| `CHATGPT_COOKIES_NETSCAPE` | إعدادات Space فقط | نسخ Cookies إلى `vendors/chatgpt-api` |
| GitHub token أو HF token | مدير أسرار المزود المعني | إعادة استخدامه في هذا المستودع أو طباعته في logs |

قبل الإصدار، نفذ:

```bash
git status --short
git grep -nE 'ghp_|hf_[A-Za-z0-9]{20,}|CHATGPT_COOKIES_NETSCAPE=.{20,}' || true
git ls-files .env
```

يجب ألا يظهر `.env` ضمن الملفات المتعقبة، ويجب ألا يحتوي diff على Secret حقيقي.

## حالة التحقق الحالية

| الاختبار | النتيجة |
|---|---|
| `compileall` | ناجح |
| اختبارات الوحدة الكاملة | ناجحة، 37 اختبارًا |
| route plan للنص والبحث والصورة | ChatGPT ظاهر كأول provider |
| اختبار حي للنص العام | ناجح وأعاد `نجح` عبر route `text` |
| اختبار حي للبحث | وصل إلى ChatGPT وأعاد response عبر `text_grounded_search` |
| اختبار حي للصورة | التشغيل السابق في GitHub Actions نجح وأعاد `images[].data_url` وملف PNG، لكن الاختبار اللاحق من الراوتر واجه حالة Space بطيئة/محدودة؛ تم توحيد مهلة 540 ثانية وإضافة 3 محاولات محدودة |

التشخيص يفرق بين مرحلتين: التشغيل الناجح السابق استخدم مهلة 540 ثانية وثلاث محاولات، وكانت `response.json` تحتوي `images` فعلًا حتى مع وجود رسالة نصية عن حد الخطة المجانية؛ أما الراوتر القديم فكان يستخدم 300 ثانية ومحاولة واحدة. لذلك كان يفشل عند غياب `images` في الاستجابة الحالية. عُدّل adapter الآن ليطابق سلوك workflow، مع بقاء quota وغياب الصور فشلًا صريحًا لا يتحول إلى صورة وهمية.

## مراجع

[1]: https://huggingface.co/docs/hub/spaces-overview#managing-secrets "Hugging Face Spaces: managing secrets and variables"
[2]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions: using secrets"
[3]: https://yousefsg-chatgpt-api.hf.space/health "ChatGPT API Space health endpoint"
[4]: https://github.com/ysrg2003/chatgpt-api "chatgpt-api source repository"
