# NVIDIA NIM Free Endpoint

أضيف مزود NVIDIA NIM إلى router بعد OpenRouter في سلاسل النماذج ومسارات النص والبحث الحي. يستخدم المزود واجهة OpenAI-compatible الرسمية:

```text
https://integrate.api.nvidia.com/v1/chat/completions
```

## إعداد المفتاح

لا تُحفظ مفاتيح NVIDIA في Git أو في `config/*.json`. ضع المفتاح في بيئة التشغيل:

```dotenv
NVIDIA_API_KEY=nvapi-REPLACE_ME
```

وللتدوير بين أكثر من مفتاح:

```dotenv
NVIDIA_API_KEYS_JSON=[{"id":"nvidia-key-1","key":"nvapi-REPLACE_ME","project":"default"}]
```

تُقرأ القيم عبر `config/key_pools.json` من `NVIDIA_API_KEYS_JSON` أولًا، ثم `NVIDIA_API_KEY` كـfallback. إذا لم يوجد مفتاح، يتجاوز router NVIDIA تلقائيًا وينتقل إلى provider التالي؛ لا يسبب ذلك فشل تهيئة router.

## الكتالوج الكامل

الرابط الرسمي المحدد للفلتر هو [NVIDIA Free Endpoint](https://build.nvidia.com/models?filters=nimType%3Anim_type_preview). وقت الالتقاط كان يعرض **57 Free Endpoint** موزعة على ثلاث صفحات. توجد القائمة الكاملة الملتقطة في [`config/nvidia_free_catalog.json`](../config/nvidia_free_catalog.json)، وتشمل لكل نتيجة الاسم و`api_model` والقدرة وحالة deprecation.

المصدر النصي الرسمي [llms.txt](https://build.nvidia.com/llms.txt) يؤكد Base URL والتوافق مع Chat Completions، بينما [models.md](https://build.nvidia.com/models.md) يوفر روابط canonical للنماذج.

## ما يدخل routes العامة

من أصل 57 نتيجة، فُعّل **34 نموذجًا غير deprecated** في `model_chains.nvidia_free`، ثم أُضيفت بعد OpenRouter إلى `default` و`creative` و`cheap` وإلى `output_routes.text` و`output_routes.text_grounded_search`. تشمل القائمة نماذج text وvision-to-text وomni وtranslation التي يمكن تمثيلها عبر JSON Chat Completions.

النماذج الـ23 الأخرى ما زالت محفوظة في catalog الكامل لكنها لا تدخل route النص العام، لأنها embeddings أو reranking أو moderation أو audio/TTS أو video/3D/autonomous-driving أو image/vision specialized، أو عليها deprecation. عدم إدخالها في route النص لا يعني حذفها؛ بل يمنع إرسال prompt نصي عام إلى endpoint يتطلب payload أو adapter مختلفًا.

| الفئة | عدد تقريبي في snapshot | سياسة router |
|---|---:|---|
| Text وreasoning | 21 | مفعلة في routes النصية إذا لم تكن deprecated |
| Vision/Text وOmni | 12 | مفعلة كمدخل نصي، ولا يعني ذلك أن router يرسل صورًا لها في هذا الإصدار |
| Translation | 2 | مفعلة في routes النصية |
| Embedding وrerank والبروتين | 6 | catalog فقط؛ تحتاج routes/normalizers مخصصة |
| Moderation | 3 | catalog فقط؛ تحتاج route moderation |
| Audio وTTS | 3 | catalog فقط؛ تحتاج adapter صوت |
| Video وvideo analysis | 8 | catalog فقط؛ تحتاج route/adapter فيديو |
| Deprecated entries | 5 | غير مفعلة حتى تحديث/إزالة حالة deprecation |

العدد الدقيق والتقسيم القابل للمعالجة محفوظان في `config/nvidia_free_catalog.json`، لأن الكتالوج يتغير باستمرار.

## الترتيب وfallback

يأتي NVIDIA بعد OpenRouter في `model_chains.default` و`creative` و`cheap`. كما يأتي بعد OpenRouter في `output_routes.text`، وفي نهاية `output_routes.text_grounded_search` لأن هذا المسار لا يحتوي OpenRouter حاليًا. لا تُضاف نماذج NVIDIA إلى `output_routes.image`؛ فوجود Free Endpoint لا يعني أن endpoint هو مولد صور، ومخرجات الصور تحتاج adapter مخصصًا.

السلوك عند الفشل هو نفسه لبقية OpenAI-compatible providers: `401/403` يصنف كمشكلة مصادقة غير قابلة لإعادة المحاولة، و`429` كـquota، وأخطاء 408/409/425/5xx كـtransient وفق سياسة router. يسجل SQLite الفشل ويطبق cooldown ثم ينتقل إلى provider/model التالي.

## الاختبار المحلي

بعد وضع المفتاح:

```bash
cd /home/ubuntu/work/ai-provider-router
export PYTHONPATH=src
export NVIDIA_API_KEY='nvapi-REPLACE_ME'
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/router-nvidia.db \
  call-auto \
  --chain nvidia_free \
  --output-type text \
  --operation nvidia_free_probe \
  --user 'Return exactly: NVIDIA free chain works'
```

لا تسجل قيمة المفتاح في shell history أو CI logs. استخدم Secret manager أو متغير بيئة خادمي، ولا تضع `NVIDIA_API_KEY` في frontend أو متصفح المستخدم.

## قيود مهمة

Free Endpoint يعني free trial أو وصولًا مجانيًا محدودًا وفق حالة النموذج والحساب والازدحام وسياسة NVIDIA الحالية؛ لا يعني استخدامًا تجاريًا غير محدود، ولا يضمن حدًا ثابتًا لكل نموذج. قد تطلب NVIDIA تحقق الحساب أو الهاتف قبل إصدار API key. راجع صفحة النموذج قبل الاعتماد الإنتاجي.
