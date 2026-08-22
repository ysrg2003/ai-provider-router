# مزودو الذكاء الاصطناعي

هذا الملف يشرح الفرق بين **provider** و**model** و**key pool** و**chain**. provider هو الخدمة التي تستقبل الطلب، model هو النموذج داخلها، key pool هو مجموعة الأسرار المرتبة، وchain هو ترتيب provider/model الذي يطبقه router. التفاصيل التنفيذية في [`../config/providers.json`](../config/providers.json) و[`../config/models.json`](../config/models.json).

## قاعدة الاختيار

يبدأ `complete_auto()` من intent. إذا كان هناك `grounding`، يرشح فقط specs التي تملك الأداة المطلوبة. إذا أعطي `chain` صريح، يستخدمه بدل route auto ولا يسمح بدمج `grounding` معه. داخل route يمر router بالـmodels بالترتيب، ثم يختار keys غير الموجودة في cooldown، ويسجل كل نتيجة في SQLite.

## جدول providers

| Provider ID | Kind | Base URL | Key pool | Default timeout | الاستخدام |
|---|---|---|---|---:|---|
| `google_gemini` | `gemini_rest` | Google `v1beta` | `gemini_default` | 180s | Gemini text/multimodal/search |
| `groq` | `openai_compatible` | Groq `/openai/v1` | `groq_default` | 120s | Groq text/translation |
| `huggingface` | `openai_compatible` | Hugging Face `/v1` | `huggingface_default` | 90s | HF inference |
| `openrouter` | `openai_compatible` | OpenRouter `/api/v1` | `openrouter_default` | 120s | OpenRouter/free catalog |
| `nvidia` | `openai_compatible` | NVIDIA `/v1` | `nvidia_default` | 120s | NVIDIA Free Endpoint models |


### الاستخدام والعقد


### التشغيل


### الفشل والاستعادة


## Gemini

Gemini adapter ليس OpenAI-compatible؛ يستخدم payloads خاصة لـ`generateContent` و`interactions` ومسارات image/TTS/embedding/video analysis. لذلك لا تنسخ model ID إلى OpenRouter أو NVIDIA. key pool هو `AI_ROUTER_GEMINI_KEYS_JSON`، وroute يحدد method صراحة.

يجب أن يكون لكل live test output type واضح؛ text smoke أقل كلفة، بينما image/audio/video قد تستهلك quota أو تنتج artifact. عند `400` راجع method وschema، وعند `429` افحص quota قبل تدوير مفاتيح كثيرة.

## Hugging Face

Hugging Face يستخدم `OpenAICompatibleAdapter` على `https://router.huggingface.co/v1`، ويقرأ `AI_ROUTER_HF_KEYS_JSON` أو `HF_TOKEN`. نجاح route plan لا يعني أن model worker متاح؛ الاختبار الصحيح هو completion صغير. استخدم fine-grained token بأقل صلاحية، وراجع provider/model availability عند `503`.

## OpenRouter

OpenRouter يستخدم `OpenAICompatibleAdapter` على `https://openrouter.ai/api/v1`، ويقرأ `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY`. `config/models.json` يحتوي catalog وترتيبًا منفصلًا للنماذج المجانية. عند `404` افحص model ID كما يظهر في OpenRouter، ولا تفترض أن model ID من provider آخر صالح هنا.

## NVIDIA NIM

NVIDIA يستخدم OpenAI-compatible `/v1/chat/completions` وkey pool `NVIDIA_API_KEYS_JSON` أو `NVIDIA_API_KEY`. الـcatalog الكامل في [`../config/nvidia_free_catalog.json`](../config/nvidia_free_catalog.json)، أما models المفعّلة فهي التي نجحت في live text completion فقط. يوجد 57 Free Endpoint في snapshot، واختُبر 30 مرشحًا، ونجح 15؛ ترتيبها من الأكثر تقدمًا إلى الأقل في [`../docs/nvidia-ranking.md`](../docs/nvidia-ranking.md).

> **سياسة NVIDIA:** وجود model في صفحة Free Endpoint أو `/v1/models` لا يثبت أن payload text صالح أو أن endpoint متاح لحسابك. لا تفعّل model جديدًا قبل test صغير يسجل status وresponse صالحين دون حفظ المفتاح.

عند `401/403` أعد إصدار key من NVIDIA Build. عند `429/503` احترم quota/worker availability ولا تحوّل الخطأ إلى نجاح. النماذج المتخصصة للصوت والفيديو والصور والـembedding غير مضافة إلى routes لمجرد وجودها في catalog؛ تحتاج adapter method واختبارًا مستقلًا.

## كيف يعمل fallback؟

| المرحلة | ما يحدث |
|---|---|
| 1 | يحدد router route وmodel specs من config. |
| 2 | يأخذ keys ordered أو round-robin حسب pool policy. |
| 3 | يتجاوز key/model في cooldown. |
| 4 | يرسل الطلب إلى adapter. |
| 5 | يسجل success أو failure في SQLite. |
| 6 | عند retryable error ينتظر backoff قصيرًا، ويحرّك cursor إلى model التالي لنفس key. |
| 7 | عند انتهاء `max_attempts` يرفع `AllProvidersFailed`. |

لا يعيد fallback المحاولة بلا حد، ولا يضمن أن provider التالي يملك القدرة نفسها؛ route filtering هو الذي يحدد capability. لهذا يجب قراءة `output_routes` قبل القول إن fallback للصورة أو الفيديو موجود.

## إضافة provider أو model

إضافة model في adapter موجود غالبًا config-only: أضف model spec، ضعه في chain/route مناسب، أضف test لترتيبه وcapability، ثم نفّذ live smoke محدودًا. إضافة provider kind جديد تتطلب adapter، تسجيل kind في `AIRouter.__init__`, error mapping، key pool، config، tests، ودليل credential. لا تضع secret في JSON ولا تعدل `base_url` بإضافة token.

## Groq

Groq يستخدم `OpenAICompatibleAdapter` على `https://api.groq.com/openai/v1`، ويقرأ `GROQ_API_KEYS_JSON` أو fallback المفرد `GROQ_API_KEY`. في السلاسل العامة يأتي **مباشرة بعد كتلة Gemini وقبل Hugging Face**، ثم OpenRouter وNVIDIA. هذا ترتيب fallback تشغيلي، وليس benchmark عالميًا ثابتًا.

ترتيب نماذج Groq النصية المفعّلة من الأقوى/الأكثر قدرة تشغيليًا إلى الأقل هو:

| الترتيب | النموذج | سبب الترتيب التشغيلي |
|---:|---|---|
| 1 | `openai/gpt-oss-120b` | نموذج reasoning كبير بسعة سياق واسعة |
| 2 | `groq/compound` | نظام agentic يدمج نموذجًا وأدوات، لكنه ليس بديلًا عن Google Search في عقد router |
| 3 | `groq/compound-mini` | نظام Compound أخف للاستخدامات العامة السريعة |
| 4 | `openai/gpt-oss-20b` | reasoning أصغر وأسرع كـfallback |

هذا ترتيب heuristic مبني على نوع النظام والحجم والقدرات المعلنة، وليس نتيجة اختبار معياري شامل. أثبت الاختبار الحي لعقد الاستجابة نجاح النماذج الأربعة الحالية في route النص، بينما فشل `qwen/qwen3.6-27b` و`allam-2-7b` عند طلب JSON منظم؛ لذلك بقي النموذجان في route الترجمة فقط حيث نجحا. لا تُضاف نماذج Whisper أو Orpheus أو Guard/Safeguard إلى مسارات النص لأنها تحتاج عقدًا مختلفًا.

يستخدم `scripts/groq_models.py` endpoint `/models` لحفظ catalog منزوع الأسرار، ويستخدم `scripts/groq_functional.py` طلبًا واحدًا bounded لكل نموذج، بينما يستخدم `scripts/unified_contract_smoke.py` validator النهائي على routes الفعلية. نجحت 4/4 حالات `text` و6/6 حالات `translation` في إعادة اختبار Groq المخصص. نماذج GPT OSS تحتاج `max_completion_tokens` كافيًا لأن جزءًا من الميزانية قد يذهب إلى reasoning قبل `message.content`.

Groq لا يُدرج في `text_grounded_search`. وجود chat completions، وحتى وجود Compound ذي أدوات خارجية، لا يغيّر عقد البحث الخاص بالمشروع: البحث الحي هنا **Gemini فقط** باستخدام أداة `google_search` في طلب `generateContent`، ثم استخراج `candidates[].groundingMetadata.groundingChunks` و`web.uri` وتحويلها إلى `url_citations`.

ترتيب `text_grounded_search` يبدأ بـ`gemini-2.5-flash` ثم `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3-flash`, و`gemini-2.5-flash-lite`. كل نموذج يستخدم `grounded_text` وGenerateContent مع Google Search. في الاختبار الحي المنقح نجح `gemini-2.5-flash` مع 4 citations، بينما سجلت بقية النماذج 429 quota أو 404 أو نصًا بلا citations في وقت الاختبار؛ لذلك يظل fallback موجودًا، ولا يُعلن نجاح search بلا مصادر.

عند `401/403` أعد إصدار مفتاح Groq، وعند `429` احترم rate limits وانتقل إلى key/model آخر عبر policy. لا تعتبر نجاح `/models` دليلًا على نجاح كل model؛ يجب تنفيذ smoke على `chat/completions` وتسجيل status وshape فقط دون حفظ الرد أو المفتاح.
