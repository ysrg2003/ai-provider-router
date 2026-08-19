# شرح مجلد config للمبتدئ

إذا كنت تريد تغيير المزود أو النموذج أو ترتيب المحاولات، ابدأ من هذا المجلد. لا تضع مفاتيح API الحقيقية هنا. المفاتيح توضع في `.env` محلياً أو في GitHub Secrets. مرجع Gemini والحدود الأصلية هو [جدول available-limits](../docs/model-catalog.md)، أما كتالوج OpenRouter المجاني المستقل فموثق في [docs/openrouter-free.md](../docs/openrouter-free.md) ويُحدّث من OpenRouter Models API.

## أريد تغيير ترتيب النماذج

افتح `models.json`. السلسلة الافتراضية تبدأ بنماذج Gemini النصية بترتيب تنازلي حسب الإصدار:

```text
Gemini 3.7 Flash → 3.6 → 3.5 → 3.5 Lite → 3.1 Lite → 3 → 2.5 → 2.5 Lite
```

ثم تنتقل إلى نماذج Hugging Face. لا تُضاف نماذج TTS أو Image أو Embedding إلى السلسلة الافتراضية لأن لكل فئة route وadapter مختلفين. نماذج الصور التشغيلية الحالية هي Nano Banana (`gemini-3-pro-image` و`gemini-3.1-flash-image` و`gemini-3.1-flash-lite-image` و`gemini-2.5-flash-image`) عبر `generateContent`. صفوف Imagen 4 من الجدول محفوظة في `image_legacy` معطلة بسبب الإيقاف المعلن. نماذج الصوت الفعالة هي Gemini 3.1 Flash TTS وGemini 2.5 Flash TTS كما هو موضح في [جدول النماذج](../docs/model-catalog.md). لتعطيل أي نموذج مؤقتًا، لا تحذف الكائن؛ غيّر `enabled` إلى `false`.

يملك كل مفتاح cursor مستقلًا داخل SQLite. يبدأ المفتاح الجديد من Gemini 3.7، أما المفتاح الذي فشل في نموذج سابق فيستأنف من النموذج التالي في الطلب اللاحق.

## أريد تفعيل Hugging Face بأبسط طريقة

لا تحتاج إلى تعديل `providers.json` أو `models.json`. أنشئ fine-grained Hugging Face Access Token بصلاحية Make calls to Inference Providers، ثم ضع في `.env`:

```dotenv
HF_TOKEN=hf_التوكن_الحقيقي
```

سيحوّل النظام هذا المتغير المفرد تلقائياً إلى مفتاح واحد لمجموعة Hugging Face، ثم يجرب النماذج العشرة الموجودة في `models.json` بالترتيب. في GitHub Actions ضع القيمة نفسها في Secret باسم `HF_TOKEN`.

## أريد إضافة مفتاح Gemini أو تدوير عدة مفاتيح

لا تعدّل `providers.json` ولا `models.json`. افتح `.env` وأضف عنصراً إلى المجموعة المناسبة:

```dotenv
AI_ROUTER_GEMINI_KEYS_JSON=[
  {"id":"gemini-1","key":"المفتاح_الأول","project":"project-a"},
  {"id":"gemini-2","key":"المفتاح_الجديد","project":"project-a"}
]
```

سيستخدم النظام `gemini-1` أولاً ثم `gemini-2`. في GitHub Actions ضع القيمة نفسها في secret اسمه `AI_ROUTER_GEMINI_KEYS_JSON` بدلاً من ملف `.env`.

## أريد تفعيل OpenRouter والنماذج المجانية

أنشئ مفتاحًا من [لوحة OpenRouter](https://openrouter.ai/keys)، ثم اختر إحدى الطريقتين. الطريقة الأبسط تستخدم متغيرًا مفردًا:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-ضع_المفتاح_هنا
```

أما عند الحاجة إلى تدوير عدة مفاتيح، فاستخدم مصفوفة JSON مرتبة:

```dotenv
AI_ROUTER_OPENROUTER_KEYS_JSON=[
  {"id":"openrouter-1","key":"sk-or-v1-المفتاح_الأول","project":"openrouter"},
  {"id":"openrouter-2","key":"sk-or-v1-المفتاح_الثاني","project":"openrouter"}
]
```

يقرأ الراوتر `AI_ROUTER_OPENROUTER_KEYS_JSON` أولًا، ويستخدم `OPENROUTER_API_KEY` كـfallback عندما لا توجد المصفوفة. يحفظ SQLite cursor مستقلًا لكل مفتاح OpenRouter ولكل نموذج، ثم ينتقل إلى النموذج التالي عند `401` أو `403` أو `429` أو timeout أو JSON غير صالح.

تم تثبيت كتالوج OpenRouter في `config/models.json` من [قائمة Free Models](https://openrouter.ai/collections/free-models) و[Free Models Router](https://openrouter.ai/openrouter/free) وendpoint النماذج الرسمي. يضم الكتالوج **19 نموذجًا مجانيًا**، منها **16 نموذجًا نصيًا/متعدد الوسائط نشطًا** مرتبة من الأقوى إلى الأقل حسب ترتيب المجموعة، ويأتي `openrouter/free` أخيرًا لأنه router meta وليس نموذجًا ثابتًا. نموذجا Lyria الصوتيان محفوظان في catalog معطلان لأن هذا المشروع لا يملك adapter صوت OpenRouter، ونموذج Content Safety محفوظ في route moderation معطل لاستخدامه كحارس لا كمولد عام.

للتأكد من الإعداد دون كشف المفتاح:

```bash
ai-router --config-dir config --state-db /tmp/openrouter-check.db summary
```

يجب أن يظهر `openrouter` ضمن providers. عند إضافة المفتاح سيظهر عدد الأسرار تحت `openrouter` فقط، ولا تُطبع القيمة نفسها. يستخدم المشروع endpoint `https://openrouter.ai/api/v1/chat/completions` المتوافق مع OpenAI [1].

## أريد تغيير اسم متغير الأسرار

افتح `key_pools.json`:

```json
"gemini_default": {
  "env": "AI_ROUTER_GEMINI_KEYS_JSON",
  "format": "json_array",
  "rotation": "ordered",
  "cooldown_state": "sqlite"
}
```

إذا غيّرت `env` إلى `MY_GEMINI_KEYS`، يجب أن تستخدم الاسم نفسه في `.env` أو GitHub Secrets. يبقى `fallback_env` مفيداً عندما تريد قبول متغير مفرد مثل `HF_TOKEN` إلى جانب مصفوفة المفاتيح:

```dotenv
MY_GEMINI_KEYS=[{"id":"gemini-1","key":"المفتاح","project":"project-a"}]
```

إذا غيّرت الاسم في ملف واحد فقط، فلن يجد البرنامج المفاتيح وسيظهر العدد `0` في أمر `summary`.

## أريد تعديل مدة الانتظار بعد 429

افتح `policies.json`:

```json
"cooldowns_seconds": {
  "auth": 86400,
  "quota": 900,
  "transient": 120,
  "invalid_or_unknown": 300
}
```

القيمة `900` تعني 900 ثانية، أي 15 دقيقة. لا تغيّرها إلا إذا كنت تعرف سياسة الحصة لدى مزودك.

## أريد إضافة مزود OpenAI-compatible

أضف تعريفاً في `providers.json`:

```json
{
  "id": "my_openai_provider",
  "kind": "openai_compatible",
  "enabled": true,
  "base_url": "https://example.com/v1",
  "key_pool": "my_provider_keys",
  "default_timeout_seconds": 90
}
```

ثم أضف مجموعة المفاتيح في `key_pools.json`:

```json
"my_provider_keys": {
  "env": "AI_ROUTER_MY_PROVIDER_KEYS_JSON",
  "format": "json_array",
  "rotation": "ordered",
  "cooldown_state": "sqlite"
}
```

ثم أضف النموذج في `models.json`:

```json
{"provider": "my_openai_provider", "model": "my-model-name", "enabled": true}
```

وأخيراً ضع السر في `.env`:

```dotenv
AI_ROUTER_MY_PROVIDER_KEYS_JSON=[{"id":"my-key-1","key":"المفتاح","project":"my-project"}]
```

## NVIDIA NIM

أضيف NVIDIA NIM كمزود `openai_compatible` بعد OpenRouter. يستخدم `https://integrate.api.nvidia.com/v1`، ويقرأ المفتاح من `NVIDIA_API_KEYS_JSON` أو من `NVIDIA_API_KEY` كـfallback. لا تضع المفتاح في JSON أو Git:

```dotenv
NVIDIA_API_KEY=nvapi-REPLACE_ME
NVIDIA_API_KEYS_JSON=[]
```

توجد قائمة النماذج ومسار التشغيل في `docs/nvidia-free.md`. يحتوي `config/nvidia_free_catalog.json` على snapshot كامل لنتائج NVIDIA Free Endpoint وعددها 57، بينما تُفعّل routes العامة فقط النماذج غير المتخصصة وغير deprecated. عند غياب المفتاح يتجاوز router NVIDIA وينتقل إلى المزود التالي، وعند quota أو transient failure يطبق cooldown وfallback المعتاد.

## أريد إضافة مزود API مختلف تماماً

إذا لم يكن المزود يستخدم Gemini REST أو OpenAI-compatible، لا تحاول تغيير `models.json` فقط. يجب إنشاء adapter جديد داخل `src/ai_router/providers/`، ثم تسجيل نوعه في `src/ai_router/router.py`. اقرأ قسم **إضافة مزود جديد** في README الرئيسي قبل تنفيذ ذلك.

## أريد استخدام نوع مخرج مختلف

يحتوي `models.json` على `output_routes` مستقلة. لا تضف نموذج صورة إلى `default` النصي؛ أضفه إلى route المناسبة:

| route | الاستخدام |
|---|---|
| `text` | نص وJSON |
| `image` | توليد وتحرير الصور |
| `audio` | تحويل النص إلى صوت |
| `embedding` | المتجهات والبحث الدلالي |
| `video_analysis` | تحليل فيديو وإخراج نص |
| `live` | خطة جلسة Live عبر WebSocket |
| `video_generation` | غير مفعّل؛ لا يوجد صف Veo في جدول available-limits المرفق |
| `openrouter_free` | سلسلة OpenRouter المجانية المرتبة، وتدعم text ثم multimodal input حسب model metadata |
| `openrouter_moderation` | نموذج Content Safety موثق لكنه معطل؛ يحتاج سياسة moderation مستقلة |

يمكن فحص الاختيار دون إرسال طلب إلى المزود:

```bash
PYTHONPATH=src python -m ai_router.cli.main \
  --config-dir config --state-db /tmp/router.db \
  route-plan --user "أنشئ صورة مع معلومات حديثة"
```

## أريد Grounding

استخدم `--grounding search` أو `--grounding maps` مع `call-auto`، أو اذكر كلمات مثل «مصادر حديثة» أو «خرائط Google» في الطلب. سيختار الراوتر نماذج Gemini التي تعلن دعم الأداة فقط. لا تُرسل أدوات Google تلقائيًا إلى Hugging Face أو OpenRouter تلقائيًا؛ ذلك يحتاج plugin أو مزود Search/Maps مستقلًا. OpenRouter نفسه يدعم plugins مثل web search، لكن لم نفعّلها في هذا الإصدار لأن adapter الحالي يمرر chat completions العامة فقط [2].

[1]: https://openrouter.ai/docs/quickstart "OpenRouter Quickstart"
[2]: https://openrouter.ai/docs/api-reference/overview "OpenRouter API Reference"
