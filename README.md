# AI Provider Router

مكوّن مستقل قابل لإعادة الاستخدام لإدارة عدة مزودات ذكاء اصطناعي وعدة نماذج وعدة مفاتيح API من خلال ملفات إعداد منفصلة. لا يحتوي المشروع على أسرار حقيقية، ويمكن استخدامه من تطبيق فيديو أو نظام تحليل أو أي مشروع يحتاج مخرجات JSON منظمة.

## المبدأ

> غيّر الإعدادات من `config/`، ولا تعاود مراجعة كود المشروع المستهلك عند إضافة مزود أو نموذج أو مفتاح أو تغيير ترتيب الأولوية.

## ملفات الإعداد

| الملف | الوظيفة |
| --- | --- |
| `config/providers.json` | تعريف المزود، نوع المحول، عنوانه، ومجموعة المفاتيح التابعة له |
| `config/models.json` | سلاسل الأولوية مثل `default`, `creative`, و`cheap` |
| `config/key_pools.json` | ربط كل مزود بمتغير البيئة الذي يحمل مفاتيحه |
| `config/policies.json` | الحد الأقصى للمحاولات، timeout، backoff، وتصنيف التبريد |
| `.env.example` | أسماء الأسرار والمسارات فقط، دون قيم حقيقية |
| `data/ai_router.db` | سجل الاستدعاءات وحالات التبريد محلياً؛ لا يرفع إلى Git |

## التثبيت

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## الأسرار

ضع مصفوفة JSON في `AI_ROUTER_GEMINI_KEYS_JSON`:

```json
[
  {"id": "project-a-key-1", "key": "AIza...", "project": "project-a"},
  {"id": "project-b-key-1", "key": "AIza...", "project": "project-b"}
]
```

ولـ Hugging Face:

```json
[
  {"id": "hf-main", "key": "hf_...", "project": "router"}
]
```

يمكن استخدام مفاتيح متعددة داخل كل مجموعة. يسير المدير عليها بالترتيب، ويتجاوز المفتاح الموجود في فترة تبريد، ويسجل السبب دون تسجيل قيمة المفتاح.

## الاستدعاء من أي مشروع

```python
from ai_router import AIRouter

router = AIRouter(config_dir="config", state_db="data/ai_router.db")
result = router.complete_json(
    chain="default",
    operation="create_content_plan",
    system_prompt="Return JSON only. You are a professional editor.",
    user_prompt="Create an original Xiangqi video idea.",
)
print(result)
router.close()
```

## إضافة مزود جديد

إذا كان المزود يستخدم واجهة OpenAI-compatible، أضف تعريفاً في `config/providers.json`، ومجموعة مفاتيح في `config/key_pools.json`، ونموذجاً في `config/models.json`. لا تحتاج إلى تعديل `router.py`.

إذا كان المزود يستخدم واجهة مختلفة، أنشئ محولاً جديداً داخل `src/ai_router/providers/` يطبق `ProviderAdapter`، ثم أضف نوعه إلى نقطة بناء المحولات في `router.py`. بعد ذلك تبقى بقية المشاريع مستهلكة لنفس الواجهة ولا تعرف تفاصيل المزود.

## ترتيب التنفيذ

يقرأ المدير chain المطلوبة من `config/models.json`. لكل نموذج يحمّل مزوده ومجموعة مفاتيحه بالترتيب، ثم ينفذ الطلب. عند 401 أو 403 يسجل خطأ مصادقة ويبرد المفتاح طويلاً. عند 429 يسجل quota ويطبّق التبريد المحدد في `config/policies.json`. عند أخطاء الشبكة و5xx يطبق backoff وينتقل إلى المفتاح التالي. عند فشل جميع السلسلة يرمي `AllProvidersFailed` كي يقرر التطبيق المستهلك هل يستخدم fallback خاصاً به.

## الاختبار

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -v
ai-router --config-dir config --state-db data/ai_router.db summary
```

لا يرسل الاختبار الافتراضي طلباً حقيقياً إذا لم توضع الأسرار. سجل SQLite محلي ومُستبعد من Git.

## الاستهلاك من Chinese Cheese Video

يستهلك المشروع الأصلي هذا المكوّن عبر `AI_ROUTER_PATH` أو تثبيت الحزمة محلياً، ويترك له مسؤولية prompts والتحقق الخاص بـ Xiangqi. أما المزودات والنماذج والمفاتيح والتدوير فهي مسؤولية هذا المستودع وحده.

## المراجع

[1] [Google Gemini API models](https://ai.google.dev/gemini-api/docs/models)

[2] [Google Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)

[3] [Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/en/index)
