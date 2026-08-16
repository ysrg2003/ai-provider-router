# إعادة استخدام ai-provider-router في مشروع آخر

الحدّ الأساسي هو **native Python import** عندما يكون المشروع المستهلك Python، و**HTTP إلى chatgpt-api** داخل adapter فقط عندما يحتاج المشروع ChatGPT. لا تنسخ cookies أو BrowserContext إلى المشروع المستهلك.

## مشروع Python مستهلك

أنشئ مجلدًا جديدًا:

```bash
mkdir my-ai-client
cd my-ai-client
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install requests
mkdir -p vendor
cd vendor
git clone https://github.com/ysrg2003/ai-provider-router.git ai-provider-router
cd ../
export PYTHONPATH="$PWD/vendor/ai-provider-router/src"
```

النتيجة المتوقعة أن يستورد Python `ai_router`. إذا فشل import، تحقق من `PYTHONPATH` ومن أنك في مجلد المشروع المستهلك، لا في `vendor`.

ضع secrets في environment أو secret manager للمشروع المستهلك، ثم شغّل:

```bash
export AI_ROUTER_CONFIG_DIR="$PWD/vendor/ai-provider-router/config"
export AI_ROUTER_STATE_DB="$PWD/data/ai_router.db"
mkdir -p data
```

أصغر استدعاء:

```python
from ai_router import AIRouter, AllProvidersFailed

router = AIRouter(
    config_dir="vendor/ai-provider-router/config",
    state_db="data/ai_router.db",
)
try:
    result = router.complete_auto(
        user_prompt="اكتب إجابة قصيرة.",
        output_type="text",
        operation="client_text",
    )
    if result.get("output_type") != "text" or not result.get("text"):
        raise RuntimeError("provider returned no validated text")
finally:
    router.close()
```

## مشروع غير Python

استخدم HTTP إلى خدمة chatgpt-api مباشرة للصور والنص والبحث الحي، أو شغّل Python worker منفصلًا وقرأ JSON الناتج. لا تستخدم subprocess غير محدود؛ ضع timeout، افحص exit code، وتحقق من `output_type` ووجود data قبل حفظ الملف.

## الترقية والتثبيت

ثبّت commit معروفًا بدل الاعتماد على branch متحرك في الإنتاج. بعد التحديث، شغّل JSON validation وoffline tests، ثم `route_plan`، وبعدها smoke واحد محدود. احتفظ بالـcommit السابق للرجوع.

## الحالة والـidempotency

`AIRouter` يكتب state إلى SQLite. أعط كل worker DB مستقلة أو نفّذ الطلبات بشكل متسلسل. إذا كان التطبيق يعيد المحاولة على مستوى أعلى، استخدم operation/idempotency key خاصًا به حتى لا ينشئ صورتين أو يكرر بحثًا حيًا دون داعٍ.

## التحقق والفشل

اعتبر `AllProvidersFailed` فشل route كاملًا. افصل بين `auth`, `quota`, `transient`, و`invalid_or_unknown`. لا تسجل secret أو prompt كامل أو `data_base64`. عند صورة ناجحة تحقق من `mime_type` وBase64 غير الفارغ قبل الكتابة إلى القرص.

## rollback والتنظيف

للرجوع، أعد pin إلى commit السابق، لا تحذف SQLite مباشرة قبل أخذ نسخة منها. بعد إيقاف التطبيق، احذف virtualenv أو ملفات artifacts المؤقتة حسب سياسة المشروع. تبقى cookies داخل خدمة chatgpt-api فقط.

## مراجع

[1]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router"
[2]: https://github.com/ysrg2003/chatgpt-api "chatgpt-api"
