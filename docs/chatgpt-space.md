# تكامل ChatGPT Spaces مع ai-provider-router

يستخدم `ai-provider-router` نسختين مستقلتين من `chatgpt-api` كمصادر ChatGPT مرتبة لمسارات النص والبحث الحي والصورة. الاتصال بين router وSpaces يتم عبر HTTP فقط؛ لا تُنسخ Cookies أو جلسة Playwright أو `CHATGPT_STORAGE_STATE_JSON` إلى router، وتبقى حالة الجلسة داخل إعدادات Hugging Face لكل Space.

> **النطاق المعتمد:** router يستخدم `replica-01` ثم `replica-02` فقط. توجد Space قديمة على Hugging Face محفوظة كما طلب المستخدم، لكنها ليست جزءًا من الإعداد أو fallback أو الاختبارات.

## Spaces المعتمدة

| الترتيب | Provider ID | Space | Base URL |
|---:|---|---|---|
| 1 | `chatgpt_space_replica_01` | `Yousefsg/chatgpt-api-replica-01` | `https://yousefsg-chatgpt-api-replica-01.hf.space` |
| 2 | `chatgpt_space_replica_02` | `Yousefsg/chatgpt-api-replica-02` | `https://yousefsg-chatgpt-api-replica-02.hf.space` |

المصدر المرجعي الحالي هو `chatgpt-api` commit `2ac0d0e`، ونسخة gateway المضمنة في router مطابقة له في commit `1a209bd` السابق، بينما آخر تحديث توثيقي هو commit الذي يثبت live smoke للنسختين. لا توجد Cookies أو Storage State أو API secrets في Git.

## فصل المسارات

يستخدم `chatgpt-api` فحص DOM/HTML للصور فقط. مسارات `text` و`text_grounded_search` تعتمد على `choices[0].message.content` ولا تستدعي image locators. عند طلب الصورة فقط يُفعل `capture_images`، ثم تُقبل الصور التي تحمل marker مناسبًا أو رابط ChatGPT backend لملف مولد.

يطبق router القاعدة نفسها على adapter. في البحث الحي يضيف الجملة التالية تلقائيًا قبل prompt عند اكتشاف أداة البحث:

```text
ابحث في الويب بحث حي:
```

## الإعداد

يتم تعريف Space المعتمدة في `config/providers.json`، ويمكن override عناوينها بمتغيرات البيئة التالية:

```dotenv
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا
AI_ROUTER_CHATGPT_KEYS_JSON=[]
```

القيم الافتراضية موجودة في `config/providers.json`. لا تحفظ `.env` في Git. يستخدم الـproviderان مجموعة المفاتيح نفسها `chatgpt_space_default`. يستطيع router قراءة Secret واحد من `CHATGPT_API_SECRET_KEY` أو مصفوفة مرتبة من `AI_ROUTER_CHATGPT_KEYS_JSON`، ويجب أن تطابق القيمة Secret `API_SECRET_KEY` في Space الهدف.

أما `CHATGPT_STORAGE_STATE_JSON` و`CHATGPT_COOKIES_NETSCAPE` فهما Secrets داخل كل Space فقط، ولا يعرف router محتواهما. يجب أن تخص كل جلسة الحساب المقصود داخل Space نفسها، ولا يجوز نقلها بين البيئات.

## ترتيب routes

يظهر ترتيب ChatGPT في `config/models.json` كما يلي:

| المسار | ترتيب ChatGPT |
|---|---|
| `text` | `replica-01` ثم `replica-02` |
| `text_grounded_search` | `replica-01` ثم `replica-02` |
| `image` | `replica-01` ثم `replica-02` |
| `image_grounded_search` | `replica-01` ثم `replica-02` |

بعد فشل provider الأول بخطأ قابل للانتقال أو quota أو payload صورة فارغ، ينتقل router إلى provider الثاني ثم إلى providers الأخرى الموجودة في route، دون وجود fallback ثالث من ChatGPT.

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
  --user "ابحث عن آخر موديل Anthropic AI"
```

### الصورة

```bash
CHATGPT_API_SECRET_KEY=ضع_المفتاح_هنا \
ai-router --config-dir config --state-db /tmp/chatgpt-router-image.db \
  call-auto --output-type image \
  --operation replica_image \
  --user "generate image of a wise stickman reading a book in a library"
```

تستخدم الصورة مهلة لا تقل عن 540 ثانية. إذا أعادت ChatGPT رسالة Free-plan quota، يسجل router `quota` وينتقل إلى provider التالي وفق السياسة؛ لا ينبغي تكرار الطلب بلا حاجة.

## آخر تحقق حي

في آخر live smoke، أعاد `/health` `ready=true` للنسختين، ونجح النص والبحث الحي في `replica-01` و`replica-02` HTTP 200. أُرسل طلب صورة واحد فقط لكل نسخة؛ أعادت كلتاهما HTTP 200 مع `images=[]` ورسالة ChatGPT Free plan image-generation limit. لذلك تُصنف الصورة كـ`quota` في هذه الجولة، وليس كفشل Base URL أو Secret أو router.

يوجد دليل تاريخي سابق على فك PNG صالح من `replica-02` بحجم 831230 bytes وأبعاد 1254×1254، لكن quota الحالية منعت إعادة التحقق في آخر جولة. التفاصيل والـartifacts الآمنة في [`../project-documentation/live-test-report-2026-08-19.md`](../project-documentation/live-test-report-2026-08-19.md) و[`../project-documentation/live-verification-2026-08-19/summary.json`](../project-documentation/live-verification-2026-08-19/summary.json).

## أسرار Spaces

`API_SECRET_KEY` يحمي endpoint HTTP ويرسله المستهلك في `Authorization: Bearer ...`. `CHATGPT_COOKIES_NETSCAPE` و`CHATGPT_STORAGE_STATE_JSON` يسجلان جلسة ChatGPT Web داخل Space فقط، ولا يجب نسخهما إلى router أو Git. Hugging Face Access Token مخصص لإدارة Hub ورفع الملفات، وليس بديلًا عن `API_SECRET_KEY`.

عند تغيير Cookies أو Storage State أو Secret، تعيد Hugging Face تشغيل Space تلقائيًا. يجب تدوير القيم فورًا إذا ظهرت في سجل أو محادثة، ثم تحديث Space أو router بالقيمة الجديدة واختبار health دون طباعة السر.

## فحوص التشغيل والأمن

```bash
curl -fsS https://yousefsg-chatgpt-api-replica-01.hf.space/health
curl -fsS https://yousefsg-chatgpt-api-replica-02.hf.space/health

PYTHONPATH=src python -m compileall -q src tests vendors/chatgpt-api
PYTHONPATH=src python -m unittest discover -s tests -v
ai-router --config-dir config --state-db /tmp/chatgpt-router-summary.db summary
```

يجب ألا يظهر Secret في `summary` أو diff أو ملفات JSON. لا تضع Cookies أو Hugging Face tokens أو GitHub tokens داخل `vendors/` أو `config/`.

## الملفات ذات الصلة

| الملف | الوظيفة |
|---|---|
| `config/providers.json` | تعريف replica-01 وreplica-02 وعناوينهما والمهل |
| `config/key_pools.json` | ربط مفاتيح ChatGPT بالبيئة |
| `config/models.json` | ترتيب replica-01 وreplica-02 في routes |
| `scripts/chatgpt_spaces_functional.py` | live smoke للنسختين المعتمدتين فقط |
| `src/ai_router/providers/chatgpt_space.py` | HTTP adapter والبحث واستخراج الصور والـfallback |
| `vendors/chatgpt-api/` | نسخة المصدر المضمنة داخل router |
| `tests/test_multiroute.py` | اختبارات الترتيب والبحث والصورة والـfallback |

## المراجع

[1]: https://huggingface.co/docs/hub/spaces-overview#managing-secrets "Hugging Face Spaces: managing secrets and variables"
[2]: https://huggingface.co/docs/huggingface_hub/en/guides/repository "Hugging Face Hub repository management"
[3]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router repository"
