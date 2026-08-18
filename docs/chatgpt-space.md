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

تمت مقارنة hash محتوى الملفات، مع استبعاد `.git` وملفات cache:

| النسخة | SHA لمحتوى الملفات |
|---|---|
| `/home/ubuntu/work/chatgpt-api` | `7520671815fa14b8bd32f1e3621d23b7325c92e110342f13a69c427cee4a4213` |
| `chatgpt-api-replica-01` | مطابق |
| `chatgpt-api-replica-02` | مطابق |
| `chatgpt-api-replica-04` | مطابق |

كذلك يطابق commit المصدر المحلي commit `main` في GitHub وcommit وسم الإصدار `v1.1.2-image-boundary-docs`:

```text
5a7ae0d84b59457d13a4e974e95e88f43e6ae025
```

أما `vendors/chatgpt-api/` في router فقد أُعيدت مزامنته مع المصدر الحالي، دون `.git` أو ملفات أسرار.

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

| الاختبار | النتيجة |
|---|---|
| النص عبر router | نجح، وأعاد `نجح اختبار router مع replicas` عبر route `text` |
| البحث الحي عبر router | نجح HTTP وroute `text_grounded_search`، وأضاف prefix البحث الحي؛ يجب التحقق من صحة الادعاءات والروابط خارجياً قبل الاعتماد عليها |
| الصورة عبر router | نجحت عبر route `image`، وأعاد router PNG بصيغة `image/png`، حجمه `2,054,465` بايت وأبعاده `1199×1312` |
| الاختبارات المحلية | `38` اختبارًا ناجحًا |
| compileall | ناجح للمصدر والنسخة المضمنة |

## أسرار Spaces

`API_SECRET_KEY` يحمي endpoint HTTP؛ يرسله المستهلك في `Authorization: Bearer ...`. `CHATGPT_COOKIES_NETSCAPE` يسجل جلسة ChatGPT Web داخل Space فقط، ولا يجب نسخه إلى router أو Git. Hugging Face Access Token مخصص لإدارة Hub ورفع الملفات، وليس بديلًا عن `API_SECRET_KEY`.

قيم Secrets write-only في Hugging Face؛ يمكن التحقق من أسماء المفاتيح فقط، لا قراءة قيمها. عند تغيير Cookies أو Secret، تعيد Hugging Face تشغيل Space تلقائيًا. يجب تدوير Cookies وAPI keys إذا ظهرت في سجل أو محادثة.

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
