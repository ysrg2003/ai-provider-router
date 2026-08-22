# عقد الاستجابة الموحد في `ai-provider-router`

## الخلاصة العملية

الواجهة الموصى بها للمستخدم النهائي هي `AIRouter.complete_auto()`. هذه الواجهة تقرأ الإعدادات الموجودة في `config/`، تكتشف نوع الطلب أو تستخدم `output_type` الصريح، تختار route وmodel، تدير fallback وتدوير المفاتيح، ثم تعيد قاموس Python واحدًا بصيغة JSON قابلة للتسلسل.

لذلك لا يحتاج المستهلك إلى تحديد provider أو model أو method أو endpoint في كل طلب. يكفي ضبط أسرار مزود واحد أو أكثر مرة واحدة في بيئة التشغيل. إذا لم يمرر المستخدم `providers` أو `exclude_providers`، يستخدم router جميع المزودين الذين لديهم credentials صالحة، حسب ترتيب route في `config/models.json`.

> **تمييز مهم:** `complete_auto()` هي الواجهة ذات الـenvelope الموحد. أما `complete_json()` فهي واجهة منخفضة المستوى تعيد JSON الذي أنتجه النموذج في الأساس، و`route_plan()` يعيد خطة دون تنفيذ network request، و`summary()` يعيد ملخص الإعداد والحالة.

## 1. الحقول المشتركة في نتيجة `complete_auto()`

بعد نجاح أي route تنفيذي، يضيف router الحقول التالية إلى النتيجة. قد توجد حقول إضافية أنتجها النموذج أو adapter.

| الحقل | النوع | المعنى |
|---|---|---|
| `output_type` | string | نوع المخرج الفعلي مثل `text`, `translation`, `image`, `audio`, `embedding`, أو `video_analysis` |
| `intent` | string | intent الذي اكتشفه router أو ثبّته المستخدم |
| `route` | string | اسم output route أو chain الذي نجح |
| `provider` | string | المزود الذي أعاد النتيجة فعليًا |
| `model` | string | model ID الذي أعاد النتيجة فعليًا |
| `url_citations` | array of strings | قائمة موحدة من روابط المصادر؛ تكون فارغة عادةً في النتائج غير grounded |

مثال نتيجة نصية يكون فيها JSON الذي أعاده النموذج هو الحقل `answer`:

```json
{
  "answer": "إجابة مختصرة",
  "output_type": "text",
  "intent": "text",
  "route": "text",
  "provider": "google_gemini",
  "model": "gemini-3.7-flash",
  "url_citations": []
}
```

لا تعتمد على provider أو model ثابتين في تطبيقك؛ استخدم الحقلين `provider` و`model` لمعرفة من نجح فعليًا بعد fallback. ولا تفترض أن الحقل الدلالي الذي يعيده النموذج اسمه `answer` إلا إذا فرضته في prompt أو بنيت contract خاصًا بك.

## 2. الحقول حسب نوع المخرج

### النص العام — `output_type: text`

المسار النصي العام يطلب من adapters القابلة لـJSON إعادة object. لذلك تكون الحقول الدلالية مثل `answer` أو `items` أو `plan` خاصة بالـprompt، بينما يضيف router envelope التشغيل الموضح أعلاه.

```json
{
  "answer": "نص منظم من النموذج",
  "output_type": "text",
  "intent": "text",
  "route": "text",
  "provider": "groq",
  "model": "openai/gpt-oss-120b",
  "url_citations": []
}
```

### الترجمة — `output_type: translation`

تعيد الترجمة عادةً `translation` و`text`، إضافة إلى envelope المشترك:

```json
{
  "output_type": "translation",
  "intent": "translation",
  "route": "translation",
  "provider": "nvidia",
  "model": "nvidia/riva-translate-4b-instruct-v2",
  "translation": "This is the translated text",
  "text": "This is the translated text",
  "url_citations": []
}
```

### البحث الحي — `grounding: search`

بحث الويب في العقد الحالي Gemini-only. يعيد route `text_grounded_search` نصًا ومصادر منظمة:

```json
{
  "output_type": "text",
  "intent": "text",
  "route": "text_grounded_search",
  "provider": "google_gemini",
  "model": "gemini-2.5-flash",
  "text": "إجابة مبنية على البحث الحي",
  "annotations": [],
  "grounding_metadata": {},
  "grounding_sources": [
    {"title": "Example source", "url": "https://example.org/source"}
  ],
  "url_citations": ["https://example.org/source"]
}
```

يجب أن يتعامل المستهلك مع `url_citations` كمصفوفة قد تكون فارغة في الأنواع الأخرى. في بحث Gemini الناجح لا يعلن router النجاح إذا لم يستخرج رابطًا موثقًا من `groundingMetadata` أو annotations.

### الصور — `output_type: image`

تعيد routes الصور بيانات الصورة Base64 بدل رابط ملف مؤقت:

```json
{
  "output_type": "image",
  "intent": "image",
  "route": "image",
  "provider": "google_gemini",
  "model": "gemini-3-pro-image",
  "mime_type": "image/png",
  "data_base64": "...",
  "url_citations": []
}
```

على التطبيق المستهلك فك `data_base64` وحفظه كملف بامتداد يطابق `mime_type`. لا تضع القيمة الكاملة في logs أو issues أو artifacts عامة.

### الصوت — `output_type: audio`

```json
{
  "output_type": "audio",
  "intent": "audio",
  "route": "audio",
  "provider": "google_gemini",
  "model": "gemini-3.1-flash-tts-preview",
  "mime_type": "audio/pcm",
  "sample_rate_hz": 24000,
  "data_base64": "...",
  "url_citations": []
}
```

يجب أن يفسر التطبيق المستهلك الترميز حسب `mime_type` و`sample_rate_hz`، وأن يتجنب طباعة Base64 في السجل.

### التضمين — `output_type: embedding`

```json
{
  "output_type": "embedding",
  "intent": "embedding",
  "route": "embedding",
  "provider": "google_gemini",
  "model": "gemini-embedding-2",
  "embeddings": [
    {"values": [0.12, -0.04, 0.31]}
  ],
  "url_citations": []
}
```

قد يحتوي `values` على آلاف الأبعاد؛ لا تفترض بعدًا ثابتًا في التطبيق، بل اقرأ طول المصفوفة أو وثق model الذي اخترته.

### تحليل الفيديو — `output_type: video_analysis`

يعيد تحليل الفيديو حقولًا دلالية يحددها prompt، مع envelope router عند استخدام `complete_auto(video_uri=...)`. يجب تمرير URI عام صالح في `video_uri`. لا يعني نجاح route plan أن الفيديو أُرسل أو حُلّل.

### Live وVideo generation

`live` يعيد خطة جلسة WebSocket عبر `prepare_live_session()` ولا ينفذ طلب HTTP في المسار الحالي. أما `video_generation` فهو غير مدعوم تنفيذيًا حاليًا؛ ستظهر حالة unsupported بدل نتيجة زائفة.

## 3. الواجهات الأخرى وشكلها

### `route_plan()` — تخطيط بلا network request

```json
{
  "output_type": "text",
  "grounding": "search",
  "confidence": "explicit",
  "reason": "...",
  "route": "text_grounded_search",
  "models": [
    {
      "provider": "google_gemini",
      "model": "gemini-2.5-flash",
      "method": "grounded_text",
      "input_types": ["text"],
      "output_types": ["text"],
      "tools": ["search"]
    }
  ]
}
```

يستخدم `route_plan()` للتأكد من الاختيار قبل استهلاك quota. لا يعتبر نجاحه دليلًا على صحة credentials أو إتاحة model خارجي.

### `summary()` — حالة آمنة منقحة

يعيد summary كائنًا يحتوي `config` و`state`. يعرض provider names وcounts وإحصاءات الحالة، ولا يعرض قيم API keys.

### الأخطاء

عند فشل كل المحاولات لا توجد نتيجة موحدة ناجحة؛ يرفع router `AllProvidersFailed` مع ملخص منقح للأخطاء. عند عدم وجود route أو model مناسب يرفع `UnsupportedOutputType`. يجب على التطبيق المستهلك تسجيل نوع الخطأ دون تسجيل الأسرار أو Authorization headers.

## 4. هل يلزم إعداد إضافي لكل طلب؟

| العنصر | هل يلزم كل مرة؟ | التوضيح |
|---|---:|---|
| API key | لا | اضبطه مرة واحدة كـenvironment secret؛ key pool يدير rotation تلقائيًا |
| provider/model/method | لا | يختارها router من `config/` حسب route والترتيب |
| `config_dir` | لا | الافتراضي `config` إذا كان التشغيل من جذر المشروع |
| `state_db` | لا | الافتراضي `data/ai_router.db`؛ يمكن تغييره عند الحاجة |
| `providers` | لا | عدم تمريره يعني كل المزودين المتاحين في route |
| `output_type` | لا | `auto` يحاول اكتشافه من prompt، لكن التصريح به أكثر وضوحًا |
| `grounding` | لا، إلا إذا أردت البحث/الخرائط | استخدم `search` أو `maps` صراحة أو كلمات واضحة يلتقطها intent detector |
| image input | فقط عند تحليل صورة أو image-to-image | مرر `image_data` و`image_mime_type` |
| video input | فقط عند تحليل فيديو | مرر `video_uri` |
| map location | فقط عند Maps grounding | مرر `latitude` و`longitude` عند توفرهما |

أقل إعداد عملي هو credential لمزود واحد. مثال محلي باستخدام Groq:

```dotenv
GROQ_API_KEY=<ضع المفتاح في ملف .env المحلي فقط>
```

أو باستخدام Gemini:

```dotenv
AI_ROUTER_GEMINI_KEYS_JSON=[{"id":"gemini-1","key":"<المفتاح>","project":"default"}]
```

بعد ذلك يمكن استدعاء router دون تحديد endpoint أو model:

```python
from ai_router import AIRouter

router = AIRouter()
try:
    result = router.complete_auto(
        user_prompt="أعد JSON بكائن واحد يحتوي الحقل answer عن عاصمة اليابان.",
        output_type="text",
    )
    print(result["answer"])
    print(result["provider"], result["model"])
finally:
    router.close()
```

لبحث حي صريح:

```python
result = router.complete_auto(
    user_prompt="ما آخر أخبار اكتشافات الفضاء هذا الأسبوع؟",
    output_type="text",
    grounding="search",
)
print(result["text"])
for source in result.get("grounding_sources", []):
    print(source["title"], source["url"])
```

لا يحتاج المثال الثاني إلى اختيار model أو بناء `GenerateContentConfig` داخل التطبيق المستهلك؛ router يطبق إعداد Google Search الخاص بـGemini داخليًا. يحتاج فقط إلى credential Gemini صالح.

## 5. التحقق الحي عبر المزودين والنماذج

لا يكفي أن تتشابه أسماء الحقول في adapter؛ يجب اختبار النتيجة النهائية التي يراها المستهلك. ينفذ `scripts/unified_contract_smoke.py` طلبًا محدودًا لكل model نصي مفعّل في `output_routes.text`، ويختبر الترجمة للنماذج المفعلة في route الترجمة، ثم يشغّل بحث Gemini مرة واحدة. كل نتيجة ناجحة تمر عبر `validate_response_envelope()` في `src/ai_router/response_contract.py`.

```bash
PYTHONPATH=src \
UNIFIED_CONTRACT_ALL_MODELS=true \
UNIFIED_CONTRACT_WORKERS=3 \
python3 scripts/unified_contract_smoke.py
```

| الحالة | معناها | هل تُعد إثباتًا؟ |
|---|---|---:|
| `passed` | استجاب model فعليًا، ونجح envelope والحقول الخاصة بنوع المخرج | نعم لهذا provider/model/method وقت الاختبار |
| `deferred_no_key` | provider أو model قابل للتخطيط لكن لا يوجد Secret في بيئة الاختبار | لا؛ يحتاج credential ثم إعادة الاختبار |
| `deferred_not_in_route` | السجل موجود في config لكنه ليس ضمن route الذي يختبره السكربت | لا؛ لا يُعمّم نجاح route آخر |
| `failed` | يوجد Secret، لكن الطلب أو payload أو الاستجابة خالفت العقد أو فشل المزود | لا؛ يجب تحليل الخطأ قبل التفعيل |

يقيس هذا الاختبار **قابلية الاستهلاك** لا جودة الإجابة أو تفوق model. تشغيله من GitHub Actions يستخدم Secrets المخزنة في المستودع ويرفع JSON منقحًا فقط. لا ينبغي تحويل `deferred_no_key` إلى `passed` يدويًا، ولا اعتبار نجاح model واحد دليلًا على نجاح كل models في provider نفسه.

## 6. قواعد الاستهلاك الآمن

تعامل مع النتيجة كـJSON غير موثوق دلاليًا: تحقق من وجود الحقول قبل استخدامها، وتحقق من أن `data_base64` صالح قبل حفظه، ولا تجعل `provider` أو `model` مصدر صلاحيات. استخدم `url_citations` كمصادر بحث فقط عندما يكون `grounding` مطلوبًا، ولا تعتبر روابط ظهرت في نص عادي دليلًا على بحث حي.

الحقول المشتركة تثبت كيف نجح الطلب، لكنها لا تلغي اختلاف القدرات الخارجية أو quota أو permissions. وجود provider في config لا يضمن أن حسابك يملك مفتاحًا أو أن model متاح لحظة التنفيذ.

## المراجع

[1]: https://ai.google.dev/gemini-api/docs/google-search "Grounding with Google Search — Google Gemini API"

[2]: https://ai.google.dev/api/generate-content "GenerateContent API Reference — Google Gemini API"

[3]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router repository"
