# الصفوف القابلة للاستخدام من AI Studio

> هذا مرجع موحد بجدولين مستقلين: **Models** أولًا ثم **Tools**. صفوف `0 / 0` مستبعدة. Gemini 2.5 Flash محتفظ به مع تنبيه أن الحصة اليومية تتجدد، ويُفترض هنا أنه لم يُستخدم بعد.

**عدد صفوف Models:** 24. **عدد صفوف Tools:** 13. **الإجمالي:** 37 من أصل 61.

## Models — النماذج

| النموذج | الفئة | الوظيفة | المدخلات | المخرجات | RPM | TPM | RPD | الحالة المرجعية | الملاحظة |
|---|---|---|---|---|---|---|---|---|---|
| `Antigravity` | Agents | وكيل لتنفيذ خطوات متعددة أو بحث أو استخدام حاسوب | تعليمات نصية وملفات/سياق المهمة | تقرير نصي ونتائج أو أفعال وكيلية | 0 / 60 | 0 / 100K | 0 / 100 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2.5 Flash` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 3 / 5 | 94.89K / 250K | 26 / 20 | `available_after_daily_refresh` | الحصة اليومية تتجدد؛ اعتُبر الاستخدام الحالي غير مستخدم لهذا الجدول المرجعي. |
| `Gemini 2.5 Flash Lite` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 0 / 10 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2.5 Flash Native Audio Dialog` | Live API | محادثة مباشرة منخفضة الكمون وترجمة صوتية | نص، صورة، صوت وفيديو | نص وصوت | 0 / Unlimited | 0 / 1M | 0 / Unlimited | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2.5 Flash TTS` | Multi-modal generative models | تحويل النص إلى كلام اصطناعي | نص وتعليمات نبرة/صوت | صوت | 0 / 3 | 0 / 10K | 0 / 10 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3 Flash` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 0 / 5 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3 Flash Live` | Live API | محادثة مباشرة منخفضة الكمون وترجمة صوتية | نص، صورة، صوت وفيديو | نص وصوت | 0 / Unlimited | 0 / 65K | 0 / Unlimited | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.1 Flash Lite` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 0 / 15 | 0 / 250K | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.1 Flash TTS` | Multi-modal generative models | تحويل النص إلى كلام اصطناعي | نص وتعليمات نبرة/صوت | صوت | 0 / 3 | 0 / 10K | 0 / 10 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.5 Flash` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 0 / 5 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.5 Flash Lite` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 0 / 15 | 0 / 250K | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.5 Live Translate` | Live API | محادثة مباشرة منخفضة الكمون وترجمة صوتية | نص، صورة، صوت وفيديو | نص وصوت | 0 / Unlimited | 0 / 20K | 0 / Unlimited | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.6 Flash` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 0 / 5 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.7 Flash` | Text-out models | استدلال متعدد الوسائط وتوليد نص واستخراج وترجمة وبرمجة | نص، صورة، فيديو، صوت وPDF | نص | 0 / 5 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini Embedding 1` | Other models | بحث دلالي، استرجاع، توصية وقياس تشابه | نص | متجهات embedding رقمية | 0 / 100 | 0 / 30K | 0 / 1K | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini Embedding 2` | Other models | بحث دلالي، استرجاع، توصية وقياس تشابه | نص | متجهات embedding رقمية | 0 / 100 | 0 / 30K | 0 / 1K | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini Robotics ER 1.5 Preview` | Other models | استدلال وتخطيط لمهام الروبوتات | نص ومدخلات متعددة الوسائط حسب الواجهة | استدلال نصي أو أوامر/خطة | 0 / 10 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini Robotics ER 1.6 Preview` | Other models | استدلال وتخطيط لمهام الروبوتات | نص ومدخلات متعددة الوسائط حسب الواجهة | استدلال نصي أو أوامر/خطة | 0 / 5 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini Robotics ER 2 Preview` | Other models | استدلال وتخطيط لمهام الروبوتات | نص ومدخلات متعددة الوسائط حسب الواجهة | استدلال نصي أو أوامر/خطة | 0 / 5 | 0 / 250K | 0 / 20 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemma 4 26B` | Other models | توليد نص واستدلال عام خفيف | نص، مع دعم الواجهة حسب النموذج | نص | 0 / 30 | 0 / 16K | 0 / 14.4K | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemma 4 31B` | Other models | توليد نص واستدلال عام خفيف | نص، مع دعم الواجهة حسب النموذج | نص | 0 / 30 | 0 / 16K | 0 / 14.4K | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Imagen 4 Fast Generate` | Multi-modal generative models | توليد صور من أوصاف نصية | نص، وقد تدعم بعض المسارات صورة مرجعية | صورة | - | - | 0 / 25 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Imagen 4 Generate` | Multi-modal generative models | توليد صور من أوصاف نصية | نص، وقد تدعم بعض المسارات صورة مرجعية | صورة | - | - | 0 / 25 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Imagen 4 Ultra Generate` | Multi-modal generative models | توليد صور من أوصاف نصية | نص، وقد تدعم بعض المسارات صورة مرجعية | صورة | - | - | 0 / 25 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |

## Tools — الأدوات

| الأداة/السياق | الفئة | الوظيفة | المدخلات | المخرجات | RPD | الحالة المرجعية | الملاحظة |
|---|---|---|---|---|---|---|---|
| `Computer Use Preview` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Deep Research Pro Preview` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2 Flash` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2.5 Flash` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2.5 Flash Lite` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.1 Flash Lite` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.1 Flash TTS` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 3.5 Flash Lite` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini Robotics ER 1.6 Preview` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini Robotics ER 2 Preview` — `map_grounding` | Map grounding | إجابات مرتبطة بالخرائط والأماكن | سؤال أو طلب عن مكان/مسار/خدمة | نص مؤسس على الخرائط وبيانات أماكن | 0 / 500 | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Default` — `search_grounding` | Search grounding | بحث Google وتأصيل الإجابة بالمصادر | سؤال أو prompt يحتاج معلومات حديثة | نص مؤسس مع نتائج/مصادر بحث | 0 / 1.5K | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2` — `search_grounding` | Search grounding | بحث Google وتأصيل الإجابة بالمصادر | سؤال أو prompt يحتاج معلومات حديثة | نص مؤسس مع نتائج/مصادر بحث | 0 / 1.5K | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |
| `Gemini 2.5` — `search_grounding` | Search grounding | بحث Google وتأصيل الإجابة بالمصادر | سؤال أو prompt يحتاج معلومات حديثة | نص مؤسس مع نتائج/مصادر بحث | 3 / 1.5K | `available_reference` | حد غير صفري أو Unlimited في جدول AI Studio. |

## ملاحظات

`available_reference` تعني وجود حد غير صفري في بعد منطبق. `available_after_daily_refresh` خاصة بـGemini 2.5 Flash هنا: احتُفظ به كمرجع مستقبلي، مع افتراض أن الحصة اليومية ستتجدد، ولم يُعامل كصف مستهلك حاليًا.

صفوف Tools ليست نماذج توليد؛ `Map grounding` و`Search grounding` تستخدمان RPD كحد أداة، لذلك لا يظهر لهما RPM أو TPM.

## سياسة اعتماد الجدول داخل ai-provider-router

هذا الملف هو النسخة المرفقة من `available-limits.md`، ويُعد المرجع المحلي الوحيد لتفعيل نماذج Gemini داخل `config/models.json`. لا يجوز إضافة اسم نموذج إلى route تنفيذي إذا لم يظهر في جدول Models أو Tools أعلاه.

| route تنفيذي | صفوف الجدول المسموح بها | model IDs المستخدمة في config | نوع المدخل | نوع المخرج | ملاحظات |
|---|---|---|---|---|---|
| `text` | Text-out models | `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3-flash`, `gemini-2.5-flash`, `gemini-2.5-flash-lite` | نص، صورة، فيديو، صوت، PDF | نص | مرتبة تنازليًا كما في الجدول |
| `image` | `Imagen 4 Ultra Generate`, `Imagen 4 Generate`, `Imagen 4 Fast Generate` | `imagen-4.0-ultra-generate-001`, `imagen-4.0-generate-001`, `imagen-4.0-fast-generate-001` | نص | صورة | تستخدم REST `predict`، وليست Interactions؛ لا توجد أسماء Gemini Image قديمة في route |
| `audio` | `Gemini 3.1 Flash TTS`, `Gemini 2.5 Flash TTS` | `gemini-3.1-flash-tts-preview`, `gemini-2.5-flash-preview-tts` | نص وتعليمات نبرة/صوت | صوت | لا يُستخدم `gemini-2.5-pro-preview-tts` لأنه ليس صف TTS الموجود في المرفق |
| `embedding` | `Gemini Embedding 2`, `Gemini Embedding 1` | `gemini-embedding-2`, `gemini-embedding-001` | نص | متجه embedding | هذه هي الصيغة المدعومة في adapter الحالي |
| `live` | `Gemini 3.5 Live Translate`, `Gemini 3 Flash Live`, `Gemini 2.5 Flash Native Audio Dialog` | `gemini-3.5-live-translate-preview`, `gemini-3-flash-live-preview`, `gemini-2.5-flash-native-audio-preview-12-2025` | نص، صورة، صوت، فيديو | نص وصوت | route plan فقط حاليًا؛ يحتاج WebSocket session adapter |
| `video_analysis` | Text-out models | نماذج text-out الثمانية نفسها | فيديو ونص | نص | تحليل فيديو، وليس توليد فيديو |
| `search_grounding` | Tools: `Default`, `Gemini 2`, `Gemini 2.5` | route capability metadata | سؤال أو prompt حديث | نص مؤسس بالمصادر | يحتاج mapping رسمي مستقل للأداة قبل تفعيل أسماء غير موجودة في Models |
| `map_grounding` | صفوف Tools التي تحتوي `map_grounding` | route capability metadata | سؤال عن مكان/مسار/خدمة | نص مؤسس ببيانات الأماكن | ليست نماذج توليد مستقلة |

### صفوف موثقة وليست مسارات HTTP مفعلة

صفوف `Antigravity` و`Gemini Robotics ER 1.5/1.6/2` و`Gemma 4 26B/31B` موجودة في الجدول المرجعي، لكنها لا تُفعّل في `output_routes` الحالية؛ فالراوتر لا يملك adapter أو عقدة response مخصصة لهذه الفئات. وبالمثل، لم تعد `video_generation` تحتوي نماذج Veo لأن Veo غير موجود في ملف Models المرفق. ستظل هذه الصفوف موثقة هنا حتى يُضاف adapter متوافق معها بدل إرسال payload غير صحيح.

### مصدر mapping

أسماء model IDs الخاصة بـImagen 4 مأخوذة من REST الرسمي الذي يستخدم `models/{model}:predict`، بينما أسماء TTS وLive مأخوذة من واجهات Gemini الرسمية. جدول الحصص والحالة المرجعية نفسه مأخوذ من الملف المرفق ولا يُعاد تخمينه من صفحة أخرى. راجع [دليل Imagen الرسمي][1] و[دليل TTS الرسمي][2] و[دليل Live API][3] عند إضافة adapter جديد.

## References

[1]: https://ai.google.dev/gemini-api/docs/imagen "Imagen — Gemini API"
[2]: https://ai.google.dev/gemini-api/docs/speech-generation "Text-to-speech generation — Gemini API"
[3]: https://ai.google.dev/gemini-api/docs/live-api "Gemini Live API"
