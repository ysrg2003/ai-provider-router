# شرح مجلد config للمبتدئ

إذا كنت تريد تغيير المزود أو النموذج أو ترتيب المحاولات، ابدأ من هذا المجلد. لا تضع مفاتيح API الحقيقية هنا. المفاتيح توضع في `.env` محلياً أو في GitHub Secrets.

## أريد تغيير ترتيب النماذج

افتح `models.json`. السلسلة الافتراضية تبدأ بنماذج Gemini النصية بترتيب تنازلي حسب الإصدار:

```text
Gemini 3.7 Flash → 3.6 → 3.5 → 3.1 → 3 → 2.5
```

ثم تنتقل إلى نماذج Hugging Face. لا تُضاف نماذج TTS أو Image أو Embedding إلى السلسلة الافتراضية لأن adapter الحالي مخصص لطلب JSON نصي. لتعطيل أي نموذج مؤقتًا، لا تحذف الكائن؛ غيّر `enabled` إلى `false`.

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
| `video_generation` | خطة job لتوليد فيديو عبر Veo |

يمكن فحص الاختيار دون إرسال طلب إلى المزود:

```bash
PYTHONPATH=src python -m ai_router.cli.main \
  --config-dir config --state-db /tmp/router.db \
  route-plan --user "أنشئ صورة مع معلومات حديثة"
```

## أريد Grounding

استخدم `--grounding search` أو `--grounding maps` مع `call-auto`، أو اذكر كلمات مثل «مصادر حديثة» أو «خرائط Google» في الطلب. سيختار الراوتر نماذج Gemini التي تعلن دعم الأداة فقط. لا تُرسل أدوات Google تلقائيًا إلى Hugging Face؛ ذلك يحتاج مزودًا خارجيًا مستقلًا للبحث أو الخرائط.
