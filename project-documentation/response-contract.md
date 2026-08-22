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

بحث الويب في العقد الحالي Gemini-only. يعيد route `text_grounded_search` نصًا ومصادر منظمة. يبدأ الترتيب بـ`gemini-2.5-flash`، ثم يمر عبر بقية نماذج Gemini النصية، وكلها تستخدم `method: grounded_text` وطلب `generateContent` مع Google Search؛ لا يستخدم هذا route `interaction_text` أو مزودًا آخر.

قبل كل طلب بحث، يبني adapter prompt واحدًا مدموجًا من سياسة البحث الموثق الإلزامية وسؤال المستخدم. السياسة تطلب البحث في أحدث المصادر الرسمية، مقارنة المصادر عند الضرورة، التحقق من التواريخ والأسعار والأسماء، التصريح بالخلاف أو عدم اليقين، وترتيب الإجابة: النتيجة ثم التفاصيل ثم المصادر. لا تُرسل السياسة كسؤال منفصل؛ بل تُلحق داخل `contents[0].parts[0].text` قبل سؤال المستخدم مع فاصل `سؤال المستخدم:`. لذلك لا يحتاج التطبيق المستهلك إلى إعادة إضافة هذه التعليمات.

```text
gemini-2.5-flash
→ gemini-3.7-flash
→ gemini-3.6-flash
→ gemini-3.5-flash
→ gemini-3.5-flash-lite
→ gemini-3.1-flash-lite
→ gemini-3-flash
→ gemini-2.5-flash-lite
```

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

يجب أن يتعامل المستهلك مع `url_citations` كمصفوفة قد تكون فارغة في الأنواع الأخرى. في بحث Gemini الناجح لا يعلن router النجاح إذا لم يستخرج رابطًا موثقًا من `groundingMetadata` أو annotations. إذا فشل model بسبب 404 أو 429 أو أعاد نصًا بلا citations، ينتقل router إلى model Gemini التالي وفق `max_attempts`؛ لذلك لا تُعتبر حالة 429 أو غياب citations نجاحًا.

في اختبار GenerateContent الحي المخصص لكل النماذج، نجح `gemini-2.5-flash` مع 4 citations. أعاد `gemini-2.5-flash-lite` نصًا بلا citations، أعاد `gemini-3-flash` 404، وأعادت نماذج Gemini الأخرى في ذلك الوقت 429 بسبب quota. هذه حالات توفر وقتية أو اختلاف قدرة، وليست تغييرًا في شكل envelope. التقرير المنقح الكامل موجود في [`gemini-grounded-search-models-live-2026-08-22.json`](gemini-grounded-search-models-live-2026-08-22.json)، ويُظهر `1 passed`, و`1 invalid`, و`6 failed` من أصل 8 نماذج. كما أثبت live smoke بعد إضافة سياسة البحث أن المسار الفعلي نجح عبر `gemini-2.5-flash` وأعاد 59 حرفًا و6 citations.

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

## 6. نتيجة التحقق المقارن الحالية

شُغّل [`scripts/unified_contract_smoke.py`](../scripts/unified_contract_smoke.py) عبر GitHub Actions على كل نماذج النص الموجودة في routes، وعلى نماذج الترجمة ذات الصلة، إضافة إلى Gemini Search. التقرير الكامل المنقح هو [`unified-response-contract-cross-provider-live-2026-08-22.json`](unified-response-contract-cross-provider-live-2026-08-22.json).

| provider | passed | failed | deferred | ما يثبت فعليًا |
|---|---:|---:|---:|---|
| Gemini (text) | 7 | 1 | 0 | envelope صالح عبر 7 نماذج؛ نموذج `gemini-3-flash` أعاد 404 |
| Hugging Face | 4 | 0 | 0 | envelope صالح عبر 4 نماذج نصية |
| OpenRouter | 13 | 3 | 0 | envelope صالح عبر 13 نموذجًا؛ الإخفاقات 429 أو 404 لنماذج مجانية غير متاحة مؤقتًا |
| NVIDIA | 8 | 5 | 0 | envelope صالح عبر 8 نماذج؛ الإخفاقات model EOL أو payload/response غير متوافق |
| Groq | 0 | 0 | 12 | لم يُختبر في هذه الجولة لغياب `GROQ_API_KEY` و`GROQ_API_KEYS_JSON` في GitHub Secrets |
| Gemini Search | 1 | 0 | 0 | `text_grounded_search` أعاد نصًا و4 `url_citations` |
| **الإجمالي** | **33** | **9** | **12** | **54** نتيجة/سيناريو منقح |

النتيجة العملية هي أن **شكل envelope قابل للاعتماد كواجهة استهلاك** عندما تكون حالة السجل `passed`: الحقول المشتركة بقيت ثابتة عبر Gemini وHugging Face وOpenRouter وNVIDIA، بينما بقيت الحقول الدلالية الخاصة بالنوع منفصلة. لا يعني ذلك أن كل model متاح دائمًا أو أن provider يضمن جودة موحدة؛ الاعتماد يجب أن يكون على `status=passed` لكل `provider/model/method` في تقرير حديث، مع fallback عند 429/503 وعدم تفعيل النماذج التي تعيد 404 أو payload غير صالح.

الإخفاقات ليست فشلًا في envelope نفسه. مثال `gemini-3-flash` هو model غير متاح بعقده الحالي، وبعض نماذج OpenRouter مؤقتة rate-limited أو لم تعد مجانية، وبعض نماذج NVIDIA انتهت دورة حياتها أو أعادت response لا يطابق JSON المطلوب. لذلك لا يجوز معالجة هذه الحالات بتغيير consumer؛ يجب تحديث catalog أو تعطيل model أو إضافة adapter متخصص.

## 7. إعادة اختبار Groq بعد تطبيق العقد

بعد توفير `GROQ_API_KEY` مؤقتًا، أُعيد تشغيل `unified_contract_smoke.py` على Groq وحده، مع كل النماذج الموجودة في routes النص والترجمة. نجحت **10 من 10** حالات Groq التنفيذية:

| النطاق | النماذج التي نجحت | النتيجة |
|---|---|---:|
| `text` | `openai/gpt-oss-120b`, `groq/compound`, `groq/compound-mini`, `openai/gpt-oss-20b` | 4/4 |
| `translation` | النماذج الستة الموجودة في route الترجمة، بما فيها `qwen/qwen3.6-27b` و`allam-2-7b` | 6/6 |

نجحت كل نتيجة في validator وأعادت envelope يحوي `output_type`, `intent`, `route`, `provider`, `model`, و`url_citations`. لم يُختبر البحث في هذا التشغيل المقيّد بـGroq، وسُجل `deferred_no_key` له لأنه Gemini-only.

قبل هذا التحقق، فشل `qwen/qwen3.6-27b` و`allam-2-7b` في route النص العام عند طلب JSON منظم، رغم نجاحهما في الترجمة. لذلك أُبقيا في `translation` وأُزيلا من `default`, `creative`, `cheap`, و`text`. النتيجة الحالية هي أن النماذج الموجودة في Groq text route كلها اجتازت contract، بينما لا يُعمّم ذلك على استخدام raw text أو على أي output type غير المختبر.

التقرير المنقح هو [`groq-unified-response-contract-live-2026-08-22.json`](groq-unified-response-contract-live-2026-08-22.json). لم يحفظ التقرير المفتاح أو body الكامل.

## 8. قواعد الاستهلاك الآمن

تعامل مع النتيجة كـJSON غير موثوق دلاليًا: تحقق من وجود الحقول قبل استخدامها، وتحقق من أن `data_base64` صالح قبل حفظه، ولا تجعل `provider` أو `model` مصدر صلاحيات. استخدم `url_citations` كمصادر بحث فقط عندما يكون `grounding` مطلوبًا، ولا تعتبر روابط ظهرت في نص عادي دليلًا على بحث حي.

الحقول المشتركة تثبت كيف نجح الطلب، لكنها لا تلغي اختلاف القدرات الخارجية أو quota أو permissions. وجود provider في config لا يضمن أن حسابك يملك مفتاحًا أو أن model متاح لحظة التنفيذ.

## المراجع

[1]: https://ai.google.dev/gemini-api/docs/google-search "Grounding with Google Search — Google Gemini API"

[2]: https://ai.google.dev/api/generate-content "GenerateContent API Reference — Google Gemini API"

[3]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router repository"
