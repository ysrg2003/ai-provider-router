# شرح مجلد config للمبتدئ

إذا كنت تريد تغيير المزود أو النموذج أو ترتيب المحاولات، ابدأ من هذا المجلد. لا تضع مفاتيح API الحقيقية هنا. المفاتيح توضع في `.env` محلياً أو في GitHub Secrets.

## أريد تغيير ترتيب النماذج

افتح `models.json`. إذا كان لديك:

```json
"default": [
  {"provider": "google_gemini", "model": "gemini-2.5-flash", "enabled": true},
  {"provider": "google_gemini", "model": "gemini-2.5-flash-lite", "enabled": true},
  {"provider": "huggingface", "model": "openai/gpt-oss-120b:fastest", "enabled": true}
]
```

فإن النظام يبدأ بـ Flash ثم Flash-Lite ثم Hugging Face. لتعطيل Flash-Lite مؤقتاً، لا تحذف الكائن؛ غيّر فقط:

```json
{"provider": "google_gemini", "model": "gemini-2.5-flash-lite", "enabled": false}
```

## أريد إضافة مفتاح

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

إذا غيّرت `env` إلى `MY_GEMINI_KEYS`، يجب أن تستخدم الاسم نفسه في `.env` أو GitHub Secrets:

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
