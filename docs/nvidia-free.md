# NVIDIA NIM Free Endpoint

أضيف مزود NVIDIA NIM إلى router بعد OpenRouter في سلاسل النماذج ومسارات النص والبحث الحي. يستخدم المزود واجهة OpenAI-compatible الرسمية:

```text
https://integrate.api.nvidia.com/v1/chat/completions
```

## الإعداد السري

لا تُحفظ مفاتيح NVIDIA في Git أو في `config/*.json`. ضع مفتاحك في بيئة التشغيل:

```dotenv
NVIDIA_API_KEY=nvapi-REPLACE_ME
```

وللتدوير بين أكثر من مفتاح يمكن استخدام JSON array:

```dotenv
NVIDIA_API_KEYS_JSON=[{"id":"nvidia-key-1","key":"nvapi-REPLACE_ME","project":"default"}]
```

تُقرأ القيم عبر `key_pools.json` من `NVIDIA_API_KEYS_JSON` أولًا، ثم `NVIDIA_API_KEY` كـfallback. إذا لم يوجد مفتاح، يتجاوز router NVIDIA تلقائيًا وينتقل إلى provider التالي؛ لا يسبب ذلك فشل تهيئة router.

## النماذج المضافة

هذه قائمة snapshot للنماذج ذات `Free Endpoint` الظاهرة في كتالوج NVIDIA وقت إعداد التغيير. أُضيفت فقط النماذج التي يمكن تمثيلها في route نصي عام، واستُبعدت خدمات embedding وsafety والفيديو والصوت والصورة المتخصصة من route النص العام.

| Model ID | الاستخدام العام |
|---|---|
| `nvidia/nemotron-3.5-lightning-30b-a3b` | Agentic وtext-to-text |
| `meta/muse-glimmer-30b` | Multimodal/image-to-text/text-to-text |
| `nvidia/riva-translate-4b-instruct-v2` | Translation/text |
| `nvidia/ising-calibration-1.5-31b` | Vision-language وtechnical text |
| `thinkingmachines/inkling` | Reasoning وimage-to-text |
| `poolside/laguna-xs-2.1` | Coding وagentic reasoning |
| `z-ai/glm-5.2` | Coding وlong-horizon reasoning |
| `minimaxai/minimax-m3` | Coding وreasoning وtool use |
| `google/diffusiongemma-26b-a4b-it` | Text-to-text وreasoning |
| `nvidia/nemotron-3-ultra-550b-a55b` | Frontier reasoning وlong context |
| `stepfun-ai/step-3.7-flash` | Coding وvision/agents |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Text/vision/video/omni reasoning |

المصدر الرسمي هو [NVIDIA Models](https://build.nvidia.com/models)، وقد عرض وقت الالتقاط 124 نموذجًا إجمالًا و57 نموذجًا بوسم `Free Endpoint`. الكتالوج متغير؛ لذلك تُعامل القائمة كـsnapshot قابل للتحديث، وليس كضمان دائم بأن كل model سيظل مجانيًا أو متاحًا لكل حساب.

## الترتيب ومسارات fallback

يأتي NVIDIA بعد OpenRouter في `model_chains.default` و`creative` و`cheap`. كما يأتي بعد OpenRouter في `output_routes.text` و`output_routes.text_grounded_search`. لا تُضاف هذه النماذج إلى `output_routes.image` لأنها نماذج نصية/فهم متعددة الوسائط، وليست مولدات صور. لا تُضاف إلى route الفيديو أو TTS أو embedding دون adapter متخصص.

السلوك عند الفشل هو نفسه لبقية OpenAI-compatible providers: `401/403` يصنف كمشكلة مصادقة غير قابلة لإعادة المحاولة، و`429` كـquota، وأخطاء 408/409/425/5xx كـtransient وفق سياسة router. يسجل SQLite الفشل ويطبق cooldown ثم ينتقل إلى provider/model التالي.

## ملاحظات عملية

«Free Endpoint» يعني وصولًا مجانيًا أو تجريبيًا محدودًا وفق حالة النموذج والحساب والازدحام وسياسة NVIDIA الحالية؛ لا يعني استخدامًا تجاريًا غير محدود، ولا يضمن حدًا ثابتًا مثل 40 RPM لكل نموذج. قد تطلب NVIDIA تحقق الحساب أو الهاتف قبل إصدار API key. يجب مراجعة صفحة النموذج نفسها قبل الاعتماد الإنتاجي.

للاختبار المحلي بعد وضع المفتاح:

```bash
cd /home/ubuntu/work/ai-provider-router
export PYTHONPATH=src
export NVIDIA_API_KEY='nvapi-REPLACE_ME'
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/router-nvidia.db \
  call-auto \
  --output-type text \
  --operation nvidia_probe \
  --user 'قل فقط: NVIDIA router probe'
```

لإجبار اختبار سلسلة NVIDIA وحدها:

```bash
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/router-nvidia-only.db \
  call-auto \
  --chain nvidia_free \
  --output-type text \
  --operation nvidia_free_probe \
  --user 'Return exactly: NVIDIA free chain works'
```

لا تسجل قيمة المفتاح في shell history أو CI logs. استخدم Secret manager أو متغير بيئة خادمي، ولا تضع `NVIDIA_API_KEY` في frontend أو متصفح المستخدم.
