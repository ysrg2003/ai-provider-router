# نظرة عامة على ai-provider-router

## ما المشروع؟

`ai-provider-router` طبقة orchestration صغيرة وقابلة لإعادة الاستخدام لمشاريع تحتاج إلى إرسال طلبات JSON إلى أكثر من مزود ذكاء اصطناعي. يختار النظام route مناسبًا لنوع المخرج، ثم يجرّب provider/model/key وفق ترتيب config، ويطبّق fallback محدودًا، ويسجل حالة النجاح والفشل في SQLite حتى لا يعيد استخدام زوج provider/model/key في cooldown بلا داعٍ.

> المشروع ينسّق الوصول إلى الخدمات الخارجية؛ لا يستضيف النماذج، ولا يحوّل ChatGPT Spaces إلى خدمة مستقلة، ولا يضمن أن كل model في كتالوج مزود خارجي متاح لحسابك.

## ماذا ستحقق في أول تشغيل؟

ستحصل على استجابة JSON حقيقية من أول provider يملك credential صالحًا. ويمكنك قبل استهلاك quota تشغيل `summary` و`route-plan` لفحص config وتوقع route. نجاح التخطيط وحده لا يثبت أن مزودًا خارجيًا يعمل؛ البرهان هو response صالح أو artifact فعلي.

## المتطلبات

| العنصر | الحالة | الاستخدام |
|---|---|---|
| Python 3.11+ | مطلوب | runtime والاختبارات |
| `requests` و`python-dotenv` | مطلوبان | HTTP وتحميل `.env` |
| credential لمزود واحد | مطلوب لأول live call | ChatGPT أو Gemini أو Hugging Face أو OpenRouter أو NVIDIA |
| GitHub account | اختياري | CI وlive smoke اليدوي |
| Hugging Face Spaces | اختياري | ChatGPT provider |
| SQLite قابل للكتابة | مطلوب | persistence وcooldown/cursor |

## خريطة المشروع

| المسار | دوره |
|---|---|
| `src/ai_router/router.py` | orchestration، route resolution، fallback، retry، state recording |
| `src/ai_router/config.py` | config/env/key parsing والتحقق |
| `src/ai_router/providers/` | adapters الخاصة بكل API family |
| `src/ai_router/store.py` | SQLite state والـcursor والـcooldown |
| `config/providers.json` | providers وbase URLs وkey pools |
| `config/models.json` | model chains وoutput routes وترتيب الأولوية |
| `config/key_pools.json` | أسماء env vars وسياسة rotation |
| `config/policies.json` | timeout/backoff/cooldown/max attempts |
| `docs/` | التشغيل والاعتمادات والـprovider-specific behavior |
| `project-documentation/` | التوثيق الشامل المنظم للمبتدئ والمشغل |
| `tests/` | عقود behavior وconfig/state regression |
| `.github/workflows/test.yml` | offline CI على push وpull request |
| `.github/workflows/live-smoke.yml` | manual bounded live checks مع artifact منقح |

## كيف يسير الطلب؟

يبدأ الطلب من CLI أو Python API. يحدد `detect_intent()` output type وgrounding، ثم يختار `AIRouter` route أو chain صريحًا. بعد ذلك يبني search/maps tools إن طلبتها السياسة، ويمر على specs بالترتيب، ثم على keys غير الموجودة في cooldown. adapter يرسل الطلب، والـrouter يعيد payload مع `route` و`intent` أو يسجل الخطأ وينتقل إلى المرشح التالي. إذا انتهت المحاولات يرفع `AllProvidersFailed` برسالة مختصرة لا تتضمن secrets.

## مزودو الإصدار الحالي

ChatGPT Spaces الثلاثة هي الخيار الأول في النص والبحث والصور عند وجودها في route. Gemini يضيف مسارات text-grounding وimage وTTS وembedding وvideo analysis. Hugging Face وOpenRouter مزودان OpenAI-compatible، وNVIDIA يستخدم adapter نفسه بعد OpenRouter في السلاسل ذات الصلة. NVIDIA catalog فيه 57 Free Endpoint، لكن الإصدار يفعّل 15 نموذجًا فقط بعد live completion verification، كما يشرح [`../docs/nvidia-ranking.md`](../docs/nvidia-ranking.md).

## حالة القدرات

| القدرة | الوضع |
|---|---|
| text | تنفيذ حي عبر routes المهيأة |
| search/maps | تنفيذ حي عندما يملك model spec أداة grounding |
| image | تنفيذ حي عبر ChatGPT/Gemini routes؛ quota ChatGPT خارجية |
| audio/TTS | route Gemini مهيأ |
| embedding | route Gemini مهيأ |
| video analysis | يحتاج `video_uri` وadapter داعم |
| video generation | plan فقط؛ لا asynchronous Veo adapter حاليًا |
| live | WebSocket plan فقط، لا HTTP request |

## مساران للاستخدام

### Mode A: تشغيل المشروع وحده

من مجلد clone الذي يحتوي `pyproject.toml`، أنشئ virtual environment وثبّت dependencies ثم انسخ `.env.example` إلى `.env` وأضف secret واحدًا على الأقل. شغّل `summary` أولًا؛ إذا ظهر config summary منقح فانتقل إلى `call-auto` مع text قصير. استخدم `data/ai_router.db` للحالة الدائمة، أو `/tmp/router-smoke.db` لتجربة مؤقتة.

### Mode B: استهلاكه من مشروع آخر

الحد الموصى به عندما يكون المشروع الآخر Python هو **native import**. ثبّت router من commit/tag محدد أو vendored source، وأضف `src` إلى بيئة host، ثم استورد `AIRouter` واستدعِ `complete_auto()` أو `route_plan()`. لا تشارك SQLite DB بين عمال متعددين بلا قرار واضح؛ لكل worker state DB مستقل أو storage contract مضبوط.

مثال الاستيراد:

```python
from ai_router.router import AIRouter

router = AIRouter(config_dir="/path/to/ai-provider-router/config", state_db="data/ai-router.db")
try:
    result = router.complete_auto(
        user_prompt="Return exactly: host integration works",
        output_type="text",
        operation="host_smoke",
    )
    assert result.get("route") and result.get("intent") == "text"
finally:
    router.close()
```

إذا كان host بلغة أخرى، استخدم CLI subprocess أو HTTP boundary يضيفه host بنفسه؛ لا تفترض أن `import` يعمل خارج Python.

## الأمان

كل القيم الحساسة تبقى في `.env` غير المتعقب أو GitHub Secrets. لا تضع ChatGPT cookies أو Storage State أو Hugging Face/GitHub/NVIDIA tokens في Git. افحص diff قبل commit، واستخدم [`../docs/credentials.md`](../docs/credentials.md) للتوليد والتخزين والتدوير والإلغاء. state DB يحتوي metadata تشغيلية وقد يحتوي رسائل خطأ؛ احفظه خارج المستودع وقلل صلاحياته.

## التحقق النهائي

من جذر المشروع شغّل:

```bash
python3 -m compileall -q src tests
python3 -m unittest discover -s tests -v
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/router-summary.db summary
```

إذا فشل compile فالمشكلة محلية قبل أي API. إذا نجحت unit tests وفشل live call، افصل بين config/credential/quota/availability واستخدم [`troubleshooting.md`](troubleshooting.md) بدل تغيير ترتيب النماذج عشوائيًا.
