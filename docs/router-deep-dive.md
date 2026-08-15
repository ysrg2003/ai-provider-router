# تحليل بنية AI Provider Router

## الحالة الحالية

المستودع عبارة عن حزمة Python 3.11 قابلة لإعادة الاستخدام، تُشغَّل عبر `ai-router`، وتعتمد على `requests` و`python-dotenv`. الإعدادات منفصلة في `config/providers.json` و`config/models.json` و`config/key_pools.json` و`config/policies.json`.

## العلاقة بين الملفات

`RouterConfig` يقرأ المزودات والسلاسل ومجموعات المفاتيح والسياسات، ثم يعرض ملخصًا عامًا منقحًا لا يطبع الأسرار. `AIRouter` يبني adapters للمزودات ويطبق الحلقة `model chain -> keys`. `GeminiAdapter` ينفذ REST `generateContent` للنص وInteractions API للفيديو، ويحوّل HTTP إلى فئات `auth` و`quota` و`transient` و`invalid_or_unknown`. `RouterStore` يحفظ حالات التبريد والإحصاءات وسجل كل محاولة في SQLite.

## التطورات التاريخية المهمة

بدأ المشروع كراوتر متعدد المزودات، ثم أضيف fallback من عشرة نماذج Hugging Face، ثم parsing أكثر مرونة لمجموعات المفاتيح، ثم دعم تحليل الفيديو عبر Gemini، ثم تدوير المشاريع. آخر تصميم يجعل `provider_state` ذا مفتاح مركب `(provider, model, key_id, project)`، ويحتفظ بـ`rotation_state.next_project_index` لكل `(provider, model)`.

## السلوك بعد التحديث

في `complete_json` و`complete_video_json`، يمر الراوتر على نماذج chain بالترتيب، ثم يختار المفاتيح التي يسمح لها cursor المحفوظ بمحاولة النموذج الحالي. يبدأ المفتاح الجديد من أول نموذج. عند فشل المفتاح في نموذج، يسجل `RouterStore.advance_model_cursor` النموذج التالي لذلك المفتاح فقط. إذا نجح الطلب، يعود الناتج فورًا، ويبقى cursor محفوظًا حتى لا يفقد الراوتر موضع التقدم في الطلب اللاحق.

الجدول `key_model_cursor` يستخدم المفتاح المركب `(provider, chain, key_id, project)` ويحفظ `next_model_index` و`next_model` وسبب آخر فشل. أما `provider_state` فيبقى مسؤولًا عن التبريد والإحصاءات لكل `(provider, model, key_id, project)`. هذا الفصل يمنع اختلاط cooldown مع موضع النموذج.

تظل `rotation_state` متاحة لتدوير المشاريع فقط عندما تكون سياسة pool هي `round_robin`. الإعداد الحالي في `config/key_pools.json` هو `ordered`، لذلك يحافظ الراوتر على ترتيب المفاتيح كما هو في secret، وهو المطلوب للبدء بالمفتاح الأول ثم الثاني.

## ملاحظات التحقق الأساسي

بعد تثبيت الاعتماديات، نجحت اختبارات الراوتر وعددها 9، بما فيها اختبار cursor المستقل لكل مفتاح. فحص `ruff --select F,I` يمر، بينما يحتوي الفحص الشامل على مخالفات تنسيق E501 وقواعد TRY/FURB قديمة خارج نطاق هذا التحديث.

## التوسعة متعددة المسارات

أضيف قسم `output_routes` إلى `config/models.json`. كل عنصر يحمل `method` و`input_types` و`output_types` و`tools`، لذلك لا تختلط نماذج الصور أو TTS أو Embeddings مع chain النصية. `detect_intent` يفسر النص عند غياب `output_type` صريح، لكن المعامل الصريح يتغلب على التخمين.

`route_plan` عملية محلية تعرض المسار والنماذج دون طلب خارجي. `complete_auto` يستخدم الخطة نفسها ثم يمرر الاستدعاء إلى adapter المناسب. مسارات `image` و`audio` و`embedding` و`video_analysis` قابلة للتنفيذ في GeminiAdapter. مسار `live` يعرض session plan لأن Live WebSocket stateful، ومسار `video_generation` يعرض الخطة فقط لأن Veo يحتاج job async وpolling.

Grounding ليس fallback عامًا إلى Hugging Face. عند طلب Search أو Maps يختار الراوتر route يحتوي نماذج Gemini التي تعلن دعم الأداة، ويمرر payload الأداة إلى Interactions. إذا لم يملك النموذج الأول الأداة، لا تُرسل إليه أداة غير مدعومة؛ ينتقل الاختيار إلى route مخصصة. ولإضافة Search/Maps لمزود آخر يلزم adapter أو خدمة أدوات مستقلة.
