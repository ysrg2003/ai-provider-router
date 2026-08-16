# دليل التشغيل والأسرار

هذا الدليل يشرح إعداد مفاتيح Gemini وHugging Face وOpenRouter وتشغيل الفحص الحي في مستودع `ai-provider-router`. لا تضع أي قيمة حقيقية في Git أو في هذا الملف. يستخدم workflow الأسرار المتاحة فقط، وتُعرض أعداد المفاتيح وتصنيفات الأخطاء دون القيم أو body الخام.

## النتيجة الأولى المتوقعة

بعد إعداد الـSecret وتشغيل workflow يدويًا، يجب أن يظهر تقرير artifact باسم `live-smoke-<run-id>` يحتوي على `live-smoke.json`. التقرير يعرض حالة كل سيناريو، المسار المختار، اسم النموذج، وحجم المخرج فقط. لا يعرض مفاتيح API أو محتوى Base64 للصورة والصوت.

## خريطة الاعتمادات

| الاسم | المكان | الغرض | التصنيف |
|---|---|---|---|
| `AI_ROUTER_GEMINI_KEYS_JSON` | GitHub Actions Secret | قائمة مفاتيح Gemini المرتبة | Secret مطلوب للفحص الحي |
| `AI_ROUTER_HF_KEYS_JSON` | GitHub Actions Secret أو `.env` محلي | fallback النصي في Hugging Face | اختياري، Secret |
| `HF_TOKEN` | GitHub Actions Secret أو `.env` محلي | مفتاح Hugging Face المفرد | اختياري، Secret |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` | GitHub Actions Secret أو `.env` محلي | قائمة مفاتيح OpenRouter المرتبة | اختياري، Secret |
| `OPENROUTER_API_KEY` | GitHub Actions Secret أو `.env` محلي | مفتاح OpenRouter المفرد كـfallback | اختياري، Secret |
| `AI_ROUTER_CONFIG_DIR` | متغير بيئة محلي | مسار مجلد config | اختياري، غير سري |
| `AI_ROUTER_STATE_DB` | متغير بيئة أو CLI | مسار SQLite للحالة | اختياري، غير سري |

يقرأ `config/key_pools.json` الاسم `AI_ROUTER_GEMINI_KEYS_JSON` من pool اسمه `gemini_default`. لا تستخدم اسمًا آخر إلا إذا عدّلت ملف config نفسه.

## صيغة key pool

القيمة هي JSON array. كل عنصر يملك معرّفًا غير سري ومفتاحًا سريًا، ويمكن أن يملك اسم مشروع لأغراض الحالة:

```json
[
  {"id": "gemini-project-1", "key": "<GEMINI_API_KEY_1>", "project": "project-1"},
  {"id": "gemini-project-2", "key": "<GEMINI_API_KEY_2>", "project": "project-2"}
]
```

لا تستخدم علامات الاقتباس الذكية أو فواصل زائدة. يجب أن تكون القيمة JSON صحيحة، ويجب ألا تظهر في commit أو issue أو log أو artifact.

## إعداد Secret من GitHub UI

افتح صفحة [Secrets and variables في إعدادات المستودع](https://github.com/ysrg2003/ai-provider-router/settings/secrets/actions)، ثم اضغط **New repository secret**. اكتب `AI_ROUTER_GEMINI_KEYS_JSON` في حقل الاسم والصق JSON array في حقل القيمة، ثم اضغط **Add secret**. لا تعرض القيمة بعد اللصق ولا تضعها في تعليق أو لقطة شاشة.

إذا ظهر أن الاسم موجود، استخدم **Update** أو أعد حفظه بعد تغيير المفاتيح. GitHub يعرض اسم Secret وتاريخ تحديثه فقط، ولا يعرض القيمة القديمة؛ وهذا طبيعي. أعد الإجراء نفسه للأسماء `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY` عند اختبار OpenRouter.

## إعداد Secret عبر GitHub CLI

نفّذ الأمر من جهاز موثوق، وليس داخل مستودع عام أو سجل CI. المثال التالي يقرأ القيمة من ملف محلي مؤقت ثم يحذف الملف بعد الإضافة:

```bash
cat > /tmp/gemini-keys.json <<'JSON'
[
  {"id":"gemini-project-1","key":"<GEMINI_API_KEY_1>","project":"project-1"}
]
JSON

gh secret set AI_ROUTER_GEMINI_KEYS_JSON \
  --repo ysrg2003/ai-provider-router \
  < /tmp/gemini-keys.json
rm -f /tmp/gemini-keys.json
```

النتيجة المتوقعة هي نجاح الأمر دون طباعة القيمة. إذا ظهر `403`, فراجع صلاحية GitHub token اللازمة لكتابة Actions Secrets، أو استخدم GitHub UI. لا تحاول قراءة قيمة Secret؛ GitHub لا يعيدها بعد التخزين.

## إعداد OpenRouter

أنشئ مفتاحًا من [OpenRouter Keys](https://openrouter.ai/keys)، ثم خزّنه محليًا في `.env` أو في GitHub Actions Secret. الصيغة الأبسط هي:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-<OPENROUTER_API_KEY>
```

ولتدوير عدة مفاتيح:

```dotenv
AI_ROUTER_OPENROUTER_KEYS_JSON=[
  {"id":"openrouter-1","key":"sk-or-v1-<OPENROUTER_API_KEY_1>","project":"openrouter"},
  {"id":"openrouter-2","key":"sk-or-v1-<OPENROUTER_API_KEY_2>","project":"openrouter"}
]
```

يقرأ الراوتر المصفوفة أولًا ثم `OPENROUTER_API_KEY`. لا يحتاج OpenRouter إلى adapter خاص؛ فهو يستخدم OpenAI-compatible `POST /api/v1/chat/completions` [5]. لا تُضاف الأسرار إلى release أو backup أو artifacts.

للتأكد من القراءة دون إرسال طلب:

```bash
cd /path/to/ai-provider-router
ai-router --config-dir config --state-db /tmp/openrouter-summary.db summary
```

إذا ظهر `openrouter` في `providers` وظهر عدد الأسرار دون القيمة، فالإعداد المحلي صحيح. إذا ظهر العدد صفرًا، تحقق من اسم المتغير وJSON array، ولا تطبع secret لتشخيصه.

## تشغيل smoke test

افتح تبويب [Actions](https://github.com/ysrg2003/ai-provider-router/actions)، اختر **Live smoke tests**، واضغط **Run workflow**. ابدأ بـ`routing` لأنه لا يرسل طلبًا إلى Gemini؛ هو يتحقق من اختيار مسارات Live وVeo فقط. بعد ذلك شغّل كل سيناريو منفردًا لتقليل استهلاك الحصة:

| السيناريو | ما يختبره | استهلاك محتمل |
|---|---|---|
| `routing` | اختيار route لـ Live وVeo وتحليل الفيديو | لا يرسل طلبًا |
| `text` | توليد نص صغير | طلب Gemini واحد أو محاولات fallback |
| `openrouter` | سلسلة OpenRouter المجانية وحدها | طلب واحد أو محاولات fallback عبر 16 نموذجًا مجانيًا نشطًا |
| `search` | Google Search grounding | طلب Gemini مع Search grounding |
| `maps` | Google Maps grounding | طلب Gemini مع Maps grounding |
| `image` | توليد صورة صغيرة | طلب Image وقد يستهلك حصة صورة |
| `audio` | TTS قصير | طلب TTS وقد يستهلك حصة صوت |
| `embedding` | متجه قصير | طلب Embedding |
| `all` | كل ما سبق ما عدا أنه يجمعها في تشغيل واحد | أعلى استهلاك؛ استخدمه فقط عند الحاجة |

نجاح workflow يعني أن التقرير احتوى على `status: completed` وأن artifact رُفع. فشل سيناريو واحد يجعل job يفشل، لكن artifact يظل مرفوعًا بسبب `if: always()`.

## تفسير الفشل

| العلامة | السبب المحتمل | الإجراء |
|---|---|---|
| `Secret is empty` | الاسم غير صحيح أو Secret غير متاح للworkflow | تأكد من `AI_ROUTER_GEMINI_KEYS_JSON` على مستوى repository |
| `403` أو `PERMISSION_DENIED` | المفتاح لا يملك وصولًا للنموذج أو المشروع | استخدم نموذجًا آخر في route أو راجع مشروع Google المرتبط بالمفتاح |
| `429` أو `RESOURCE_EXHAUSTED` | الحصة نفدت أو حد يومي/دقيقة بلغ أقصاه | انتظر تجدد الحصة أو انتقل للمفتاح التالي؛ لا تكرر `all` بلا حاجة |
| `invalid_or_unknown` | النموذج أو payload غير مناسب للعملية | راجع `config/models.json` وmethod الخاصة بالroute |
| فشل `live` أو `video_generation` | هذه المسارات تحتاج WebSocket أو async job adapter | استخدم `route-plan` حاليًا؛ لا تعاملها كـ`call-auto` HTTP قصير |

## التدوير والحالة

يستخدم الراوتر ترتيب المفاتيح في `key_pools.json`، ويحفظ cursor مستقلًا لكل مفتاح وكل route في SQLite. عند فشل نموذج، يتقدم ذلك المفتاح إلى النموذج التالي. إذا بدأ مفتاح آخر، يبدأ من أول نموذج في السلسلة. لا تشارك ملف SQLite بين تشغيلين متوازيين إلا إذا كنت تدير قفلًا خارجيًا.

## تدوير المفاتيح وإلغاؤها

عند الاشتباه بتسريب مفتاح Gemini، افتح Google AI Studio أو Google Cloud للمشروع المرتبط، ألغِ المفتاح أو دوّره، أنشئ قيمة جديدة، ثم حدّث `AI_ROUTER_GEMINI_KEYS_JSON` في GitHub. بعد ذلك شغّل `routing` ثم سيناريو `text` واحدًا للتحقق. إذا ظهر المفتاح في أي سجل أو commit، اعتبره مكشوفًا حتى لو كان GitHub قد أخفى قيمته في logs.

أما رمز GitHub نفسه، فلا تضعه في Secret الخاص بالمشروع. استخدم token قصير العمر وبأقل صلاحيات، وألغِه فور انتهاء المهمة من [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens).

## التحقق المحلي دون شبكة

```bash
cd /path/to/ai-provider-router
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
ruff check --select F,I src tests
PYTHONPATH=src python -m ai_router.cli.main \
  --config-dir config --state-db /tmp/ai-router.db \
  route-plan --user "أنشئ صورة مع مصادر حديثة"
```

النجاح المتوقع هو suite ناجحة، وroute plan يعرض `image` مع أول نموذج Native Gemini Image `gemini-3-pro-image` دون أي طلب خارجي. استخدم هذا المسار قبل أي smoke test حي. لفحص OpenRouter دون طلب استخدم `route-plan --user "أجب عبر OpenRouter"` أو راجع route `openrouter_free` مباشرة.

## مرجع النماذج والمدخلات والمخرجات

جدول النماذج والحدود المعتمد لهذا المشروع موجود في [docs/model-catalog.md](model-catalog.md)، وهو نسخة من `available-limits.md` المرفق. يجب أن يطابق كل route تنفيذي صفًا من ذلك الجدول؛ راجع قسم **سياسة اعتماد الجدول داخل ai-provider-router** لمعرفة mapping بين الاسم الظاهر وmodel ID.

> **تصحيح مهم:** كان الخطأ السابق هو اعتبار Imagen 4 المسار التشغيلي الوحيد. التحقيق الرسمي أظهر أن Imagen 4 مُعلن لإيقافه في 2026-08-17، بينما نماذج Nano Banana الحالية (`gemini-3-pro-image` و`gemini-3.1-flash-image` و`gemini-3.1-flash-lite-image` و`gemini-2.5-flash-image`) تعلن `generateContent` في metadata. لذلك يستخدم Image الحالي `generateContent`، وتُحفظ Imagen في `image_legacy` معطلة. مسار TTS يظل `gemini-3.1-flash-tts-preview` و`gemini-2.5-flash-preview-tts` وفق الجدول المرفق.

## نتائج التشغيل الحي الفعلية

تم تشغيل workflow [Live smoke tests](https://github.com/ysrg2003/ai-provider-router/actions/runs/31911509398) على commit `195ae9f` باستخدام Secret `AI_ROUTER_GEMINI_KEYS_JSON`.
 أثبت التقرير أن GitHub Actions حمّل **6 مفاتيح Gemini** بنجاح؛ لذلك أصبحت صيغة الـkey pool الصحيحة هي JSON array الصالحة، وليست قيمة نصية متعددة الأسطر. يتوافق وضع الإعداد هذا مع طريقة GitHub الرسمية لإضافة repository secret عبر `gh secret set NAME < file` [1].

| الفئة | النتيجة الفعلية | الملاحظة التشغيلية |
|---|---|---|
| تحميل المفاتيح | `google_gemini: 6`، و`huggingface: 0` | تم تحميل المفاتيح الستة دون تسجيل قيمها |
| `live` | `route_plan_only` | تم التحقق من اختيار `gemini-3.1-flash-live-preview` فقط؛ لم يُفتح WebSocket |
| `video_generation` | `route_plan_only` | تم التحقق من اختيار `veo-3.1-generate-preview` فقط؛ لم تُنشأ مهمة Veo |
| `video_analysis` | `route_plan_only` | تم التحقق من route؛ لم يُرسل فيديو فعلي في هذا smoke المحدود |
| `text` | `passed` | route `text` أعاد JSON يحوي الحقل `ok`؛ لذلك `text_chars: 0` متوقع وليس فشلًا |
| `search` | `passed` | route `text_grounded_search`، ونتج نص مع تعليقين للمصادر |
| `maps` | `passed` | route `text_grounded_maps`، ونتج نصًا من طلب Maps grounding |
| `embedding` | `passed` | `1` embedding بأبعاد `3072` عبر `gemini-embedding-2` |
| `image` | `failed` | جميع محاولات المفاتيح أعادت `quota/429` للنموذج الأول في route |
| `audio` | `failed` | جميع محاولات المفاتيح أعادت `quota/429` لنموذج TTS الأول في route |

كانت المحصلة `7/9` حالات ناجحة أو مخططة، بينما أدت حالتا Image وTTS إلى exit code غير ناجح للـjob. يظل artifact متاحًا لأن خطوة رفع التقرير تستخدم `if: always()`. نتيجة `429` تعني أن الطلب رُفض بسبب الحصة أو حد الاستخدام في وقت التجربة؛ ولا تكفي وحدها لإثبات أن النموذج مدفوع دائمًا أو غير قابل للاستخدام بعد تجدد الحصة. تتبع وثائق Gemini الرسمية نموذج TTS عبر Interactions مع `response_format: {"type":"audio"}` و`generation_config.speech_config` [2]، كما توثق Image Generation عبر `interaction.output_image` [3].

## الإصلاحات التي تحققت أثناء التجربة

كان سبب ظهور `google_gemini: 0` في التشغيل الأول هو أن ملف المفاتيح المرفق استخدم نهايات أسطر CRLF، فدخل محرف `CR` داخل JSON عند بناء الـSecret بواسطة `awk` وأصبح JSON غير صالح. أُعيد إنشاء القيمة مع إزالة `CR` من كل سطر، والتحقق منها محليًا بواسطة `python3 -m json.tool`، ثم رُفعت إلى GitHub كـJSON array تحتوي ستة عناصر. لا تُطبع القيمة أو أجزاء منها في التقرير.

كما عولجت استجابة `embedContent` التي تعيد كائنًا مفردًا تحت الحقل `embedding` بدل قائمة `embeddings`؛ أصبح الراوتر يطبع الكائن المفرد إلى قائمة موحدة، وهو ما أثبته التشغيل الحي بنتيجة `embedding_count: 1` و`dimensions: 3072`. هذا متوافق مع توثيق Gemini الذي يعرض `embedContent` لإنتاج embeddings، ويذكر أن `gemini-embedding-2` نموذج متعدد الوسائط وأن البعد الافتراضي هو `3072` [4].

أضيف أيضًا إلى رسائل `AllProvidersFailed` تصنيف الخطأ ورقم HTTP، مثل `quota/429`، مع إبقاء body الخام خارج التقرير. بعد إضافة OpenRouter وmetadata الخاصة بـ`response_format` أصبحت مجموعة الاختبارات تحتوي **31 اختبارًا ناجحًا**.

## بوابة الجودة المحلية

نُفذت الأوامر التالية من جذر المستودع بعد الإصلاحات:

```bash
cd /path/to/ai-provider-router
ruff check src scripts tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
```

النتيجة الفعلية: `ruff` نجح، ونجحت الاختبارات الـ31، ونجح `compileall`.
 هذه الاختبارات لا تستهلك حصة Gemini لأنها تستخدم mocks؛ أما workflow الحي فهو منفصل ومحدود زمنيًا إلى 15 دقيقة، ويحتفظ بالartifact سبعة أيام.

## ملاحظات أمنية بعد التجربة

لا يحتوي هذا المستودع أو artifact على قيم مفاتيح Gemini. يجب تدوير مفاتيح Gemini الستة إذا ظهرت في سجل أو ملف غير موثوق، وتحديث Secret بعد التدوير. كما يجب إبطال **رمز GitHub الذي استُخدم لتنفيذ المهمة وظهر في المحادثة** من صفحة [GitHub Personal access tokens](https://github.com/settings/tokens) فور انتهاء التشغيل، ثم إنشاء رمز قصير العمر وبأقل صلاحيات عند الحاجة. لا تضع رمز GitHub داخل `AI_ROUTER_GEMINI_KEYS_JSON`؛ فهذا الـSecret مخصص لمفاتيح Gemini فقط.

## تحقق حي بعد تصحيح جدول النماذج

أُعيد تشغيل المسارين بعد commit `a4d047e` مع ستة مفاتيح محمّلة في كل مرة، وبمطابقة صريحة للمدخل والمخرج:

| التشغيل | المدخل | المخرج | النموذج/المسار | النتيجة |
|---|---|---|---|---|
| [Image run 31926901906](https://github.com/ysrg2003/ai-provider-router/actions/runs/31926901906) | نص | صورة | Imagen 4 عبر REST `predict` | `404 NOT_FOUND`؛ أثبت أن Imagen legacy غير صالح كمسار تشغيلي حالي |
| [TTS run 31927011803](https://github.com/ysrg2003/ai-provider-router/actions/runs/31927011803) | نص وتعليمات صوت | صوت | `gemini-3.1-flash-tts-preview` عبر Interactions | **نجح**؛ `output_type: audio`، وحجم Base64 منزوع الحساسية `166400`، وMIME `audio/l16; rate=24000; channels=1` |

نتيجة TTS تؤكد أن صفّي TTS في الجدول مرتبطان بالمسار الصحيح، وأن parser يتعامل مع كتلة الصوت داخل `steps`. أما تشخيص Image المباشر فأظهر أن metadata لكل نماذج Nano Banana الأربعة يعيد `200` و`generateContent`، بينما استدعاء `generateContent` عبر `v1` و`v1beta` أعاد `429 RESOURCE_EXHAUSTED` مع المفاتيح الستة. هذا يعني أن مسار Image الصحيح أصبح معروفًا، لكن الحصة الحالية تمنع الإخراج؛ أما Imagen فأعاد `404` لأنه legacy مُعلن للإيقاف.

## تشخيص Image العميق

تم فحص metadata مباشرةً بالمفاتيح الستة. أعاد endpoint `GET /v1beta/models` الحالة `200` وأظهر نماذج Nano Banana الأربعة، كما أعاد `GET /v1beta/models/{model}` الحالة `200` لكل نموذج وأعلن `generateContent` ضمن `supportedGenerationMethods`. هذا يثبت أن أسماء النماذج صحيحة وأن المفتاح يرى النماذج.

كان الخلل الأول في adapter: كان يرسل Native Gemini Image إلى `/interactions`، بينما العقدة الرسمية الحالية التي يعلنها metadata وتوثقها Google هي `models/{model}:generateContent`، مع `contents[].parts[]` وقراءة الصورة من `candidates[].content.parts[].inlineData`. تم إصلاح ذلك في commit `7bb2e3f` وإضافة اختبار payload وresponse.

أُعيد اختبار `generateContent` مباشرةً عبر كل مفتاح من المفاتيح الستة، وبنسختي `v1` و`v1beta`. أعادت جميع الطلبات `429 RESOURCE_EXHAUSTED`، بينما أعاد metadata `200`. ثم شُغّل workflow Image بعد الإصلاح في [run 31927571350](https://github.com/ysrg2003/ai-provider-router/actions/runs/31927571350)، فكانت النتيجة `quota/429` بدل `404`. لذلك أصبح التشخيص الآن واضحًا: **المسار البرمجي وأسماء Nano Banana صحيحة، لكن الحصة تمنع الإخراج حاليًا**.

أما Imagen 4، فقد أعاد metadata `200` مع `supportedGenerationMethods: ["predict"]`، لكن طلب `predict` أعاد `404 NOT_FOUND` لكل المفاتيح. وهذا متسق مع إعلان Google أن Imagen 4 سيُغلق في 2026-08-17؛ لذلك بقي في `image_legacy` للتوثيق فقط، وليس كخيار تلقائي.

## OpenRouter live smoke status

أُضيف سيناريو `openrouter` إلى workflow، وهو يستعمل `chain=openrouter_free` فقط ويحقن `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY` دون كشفهما. لم يُنفّذ طلب OpenRouter حي في هذه النسخة لعدم وجود مفتاح OpenRouter مقدم في المهمة؛ لذلك لا يوجد ادعاء بأن أي نموذج OpenRouter نجح فعليًا. بعد إضافة Secret، شغّل **Actions → Live smoke tests → Run workflow → scenario: openrouter**. نجاحه يتطلب artifact بحالة `completed` ونتيجة `passed`، أما `429` فيسجل rate limit/quota وينتقل الراوتر حسب policy.

## References

[1]: https://docs.github.com/actions/security-guides/using-secrets-in-github-actions "Using secrets in GitHub Actions — GitHub Docs"
[2]: https://ai.google.dev/gemini-api/docs/speech-generation "Text-to-speech generation (TTS) — Gemini API"
[3]: https://ai.google.dev/gemini-api/docs/image-generation "Image generation — Gemini API"
[4]: https://ai.google.dev/gemini-api/docs/embeddings "Embeddings — Gemini API"
[5]: https://openrouter.ai/docs/quickstart "OpenRouter Quickstart"
[6]: https://openrouter.ai/openrouter/free "OpenRouter Free Models Router"
[7]: https://openrouter.ai/collections/free-models "OpenRouter Free Models collection"
[8]: https://openrouter.ai/api/v1/models "OpenRouter Models API"

## أحدث تشغيل حي بعد إضافة مفاتيح Hugging Face وOpenRouter

بعد إضافة `HF_TOKEN` و`OPENROUTER_API_KEY` إلى GitHub Secrets، شُغّل workflow الكامل `all` في [run 31931217466](https://github.com/ysrg2003/ai-provider-router/actions/runs/31931217466) على commit `dc65957`. حمّل التشغيل `google_gemini: 6` و`huggingface: 1` و`openrouter: 1`، ولم تُعرض أي قيمة سرية في artifact.

| السيناريو | الحالة | المسار أو المخرج | النتيجة |
|---|---|---|---|
| `live` | `route_plan_only` | Live | تم فحص الخطة فقط؛ لا يوجد WebSocket adapter |
| `video_generation` | `route_plan_only` | Video generation | تم فحص الخطة فقط؛ لا يوجد async Veo adapter |
| `video_analysis` | `route_plan_only` | `video_analysis` | تم فحص الخطة فقط؛ لم يُرسل فيديو خارجي |
| `text` | `passed` | `text` | JSON ناجح بحقل `ok` |
| `openrouter` | `passed` | `openrouter_free` | JSON ناجح بحقل `ok`؛ المفتاح والاتصال وسلسلة OpenRouter يعملون |
| `search` | `passed` | `text_grounded_search` | نص بطول 48 حرفًا |
| `maps` | `passed` | `text_grounded_maps` | نص بطول 176 حرفًا |
| `image` | `failed` | Gemini Image | جميع المحاولات أعادت `quota/429`؛ لم يكن فشلًا في endpoint أو chain |
| `audio` | `passed` | `audio` | صوت فعلي `audio/l16`, 24 kHz، وحجم Base64 منزوع الحساسية 176640 |
| `embedding` | `passed` | `embedding` | embedding واحد بأبعاد 3072 |

المحصلة هي **9 حالات ناجحة أو مخططة من أصل 10**. حالة Image وحدها فشلت بسبب `RESOURCE_EXHAUSTED/429` في مفاتيح Gemini الستة. أما OpenRouter وHugging Face فأصبحا محمّلين فعليًا، ونجح سيناريو OpenRouter المنفصل.

كان التشغيل الأول بعد إضافة المفاتيح يتوقف قبل إنتاج التقرير بسبب أن `scripts/live_smoke.py` مرّر `chain` إلى `complete_auto()` بينما لم تكن الدالة تقبله. أُصلح ذلك في commit `dc65957` بإضافة `chain` اختياري، وإضافة اختبار يمنع عودة الخطأ. بعد الإصلاح أعاد workflow التقرير الكامل بنجاح. هذه الحادثة موثقة لتسهيل التشخيص إذا عاد `TypeError: ... unexpected keyword argument 'chain'` في نسخة قديمة.

لا تُعامل `route_plan_only` كنجاح طلب حي؛ هي تحقق من config فقط. ولا تُعامل `429` في Image كإثبات أن النموذج غير موجود؛ فهي تعني أن الحصة أو rate limit منعت الطلب وقت التشغيل.


## ChatGPT API Space كخيار Image الأول

أصبح مزود `chatgpt_image` هو الخيار الأول في `output_routes.image`. يستخدم الراوتر Space الخاص بالمشروع على `https://yousefsg-chatgpt-api.hf.space` عبر العقد الموثق في مستودع [chatgpt-api](https://github.com/ysrg2003/chatgpt-api): يرسل `POST /v1/visual-assets/jobs` مع `{ "prompt": "..." }`، ثم يستطلع `GET /v1/visual-assets/jobs/{job_id}` حتى تصبح الحالة `done`، وأخيرًا ينزّل الصورة من `/download`. كل الطلبات تستخدم `Authorization: Bearer <CHATGPT_API_KEY>`.

يجب حفظ قيمة `API_KEY` التي عُيّنت في Hugging Face Space كـSecret في مستودع `ai-provider-router` باسم `CHATGPT_API_KEY`، أو استخدام مصفوفة `AI_ROUTER_CHATGPT_IMAGE_KEYS_JSON` إذا كان هناك أكثر من مفتاح. لا تُحفظ القيمة في Git ولا تُطبع في التقارير. عند غياب المفتاح أو إرجاع `401` أو فشل job، ينتقل الراوتر إلى Gemini Image بالترتيب الحالي. عند إرسال `image_data`، يتجنب adapter الخارجي إرسال الصورة كأنها prompt نصي ويترك مسار التعديل لـGemini؛ وهذا يحافظ على دلالة المدخلات والمخرجات.

الاختبار المحلي يثبت إنشاء job، polling، تنزيل `image/png`، وتصنيف خطأ المصادقة. أما الاختبار الحي للصورة عبر Space فيتطلب إضافة `CHATGPT_API_KEY` إلى Secrets الخاصة بمستودع الراوتر؛ فوجود `API_KEY` داخل Space وحده لا يجعل قيمته قابلة للقراءة من الراوتر. الخدمة نفسها هي browser-backed ChatGPT adapter وليست OpenAI Images API، ولذلك يعتمد نجاحها على بقاء جلسة ChatGPT داخل Space صالحة.


## نتيجة اختبار Image بعد إضافة CHATGPT_API_KEY

شُغّل سيناريو `image` منفردًا في workflow [run 31942957994](https://github.com/ysrg2003/ai-provider-router/actions/runs/31942957994) على commit `ab5416b`. أظهر التقرير المنزوع الحساسية أن workflow حمّل `google_gemini: 6` و`huggingface: 1` و`openrouter: 1`، لكنه حمّل `chatgpt_image: 0`. لذلك لم يبدأ طلب `chatgpt-api`، وانتقل الراوتر إلى Gemini Image، حيث أعادت المحاولات `quota/429 RESOURCE_EXHAUSTED`.

هذه النتيجة لا تثبت فشل Space أو adapter؛ بل تثبت أن Secret لم يصل إلى job في ذلك التشغيل. وجود `API_KEY` داخل Hugging Face Space لا يجعل قيمته قابلة للقراءة من GitHub Actions. يجب أن يكون في مستودع `ai-provider-router` repository secret مستقل اسمه حرفيًا `CHATGPT_API_KEY`، وقيمته تساوي قيمة `API_KEY` في Space.

### تصحيح حالة `chatgpt_image: 0`

1. افتح [إعدادات Secrets الخاصة بمستودع ai-provider-router](https://github.com/ysrg2003/ai-provider-router/settings/secrets/actions).
2. اختر **New repository secret**، واكتب الاسم `CHATGPT_API_KEY` حرفيًا.
3. الصق قيمة `API_KEY` الموجودة في Space، ثم اختر **Add secret**. لا تطبع القيمة ولا تحفظها في ملف متتبع.
4. افتح **Actions → Live smoke tests → Run workflow**، واختر `scenario: image`.
5. نزّل artifact `live-smoke-<run-id>` وافحص `loaded_key_counts.chatgpt_image`. يجب أن تكون القيمة `1` أو أكثر.
6. تحقق من أن النتيجة تشير إلى `chatgpt_image/chatgpt-api` وأن job انتقل إلى `done` ثم نُزّلت صورة ذات MIME يبدأ بـ`image/`.

إذا بقي العدد صفرًا، فتحقق من ثلاثة أمور فقط: اسم Secret، مستوى Secret (`repository` لا environment غير مستخدم)، واسم الفرع/الworkflow الذي شُغّل. لا تشخّص المشكلة بطباعة environment أو Authorization header.

لإعادة استخدام Space في مستودع آخر، لا تنسخ Playwright أو `CHATGPT_COOKIES_NETSCAPE`. استخدم HTTP API وضع قيمة `API_KEY` في Secret للمشروع المستدعي باسم مثل `CHATGPT_API_KEY`. الدليل الكامل موجود في [integration-chatgpt-image.md](integration-chatgpt-image.md)، ويشرح أيضًا عقد job وpolling، الاختبارات offline، smoke الحي المحدود، retries، fallback، والتراجع. أما دليل الخدمة نفسها فيشرح المسار العام في [chatgpt-api reuse guide](https://github.com/ysrg2003/chatgpt-api/blob/main/docs/reuse-in-another-project.md).

لا تعتبر route `image` ناجحًا لمجرد أن `route-plan` اختار `chatgpt_image`. النجاح الحي يتطلب مفتاحًا محمّلًا، job مكتملًا، تنزيلًا غير فارغ، ونوع محتوى صوريًا. عند فشل Space أو انتهاء جلسة ChatGPT يجب أن ينتقل الراوتر إلى Gemini أو fallback المشروع المستدعي، وألا يستبدل صورة مرجعية موثوقة بمخرج غير مكتمل.


## تكامل YouTube Video Evidence Router — 2026-08-16

يُستهلك هذا المستودع من [youtube-video-evidence-router](https://github.com/ysrg2003/youtube-video-evidence-router) عبر submodule أو مسار Python مثبت. يستخدم المستهلك `AIRouter.complete_video_json()` لتحليل رابط YouTube عام، مع `config_dir=vendor/ai-provider-router/config` و`state_db=data/ai_router.db`.

أضيفت سلسلة `video_fast` في `config/models.json` وتضم نموذجَي Gemini مخصصين لمسار الفيديو. يستخدم المستهلك هذه السلسلة افتراضيًا عبر `AI_VIDEO_CHAIN=video_fast` لتقليل زمن retry؛ يمكن للمستهلك اختيار chain أخرى عبر argument أو متغير البيئة، لكن يجب أن يكون ذلك مقصودًا ومحدودًا.

| عنصر | العقد |
|---|---|
| المدخل | `video_uri` عام يبدأ بـ`https://www.youtube.com/` أو `https://youtu.be/` |
| المخرج | كائن JSON يطبع schema المشروع المستهلك ويحافظ على source URL |
| state | SQLite يسجل provider/model/key cursor والنجاح والفشل والتبريد |
| retry | تحكمه `config/policies.json`; لا تستخدمه لتجاوز quota أو تدوير مفاتيح غير مسموح |
| fallback | يتم داخل chain وفق models/config؛ إذا فشل الجميع تظهر `AllProvidersFailed` |
| السر | `AI_ROUTER_GEMINI_KEYS_JSON` في GitHub Secret أو `.env` محلي فقط |
| التحقق | unit tests offline أولًا، ثم live smoke محدود لفيديو واحد |

لا يثبت نجاح `complete_video_json()` صحة الادعاءات الواردة في الفيديو. على المستهلك حفظ `limitations` و`verification_needed` وprovenance، وعدم تقديم المخرج كتحقق مستقل. إذا كانت النتيجة `AllProvidersFailed`، يُحفظ الفشل في state وتُترك للمستهلك حالة `NEEDS ANALYSIS RETRY OR ALTERNATIVE EVIDENCE` بدل إعادة الطلب بلا نهاية.

في تشغيل corpus الأخير استُخدمت سلسلة `video_fast` ونجحت البنية في 31 تحليلًا من 50 مقالًا؛ بقيت 12 حالة برابط محفوظ فشل تحليلها، و7 حالات بلا رابط. هذه الأرقام تخص مشروع YouTube ولا تعني نجاح كل provider أو كل model في هذا المستودع.

للتراجع عن سلسلة الفيديو المحدودة، أعد consumer إلى chain سابقة فقط بعد قراءة state وتشغيل الاختبارات. لا تغيّر `config/policies.json` في مشروع المستهلك لتجاوز حد provider؛ أصلح السبب أو انتظر تجدد الحصة. احتفظ بقاعدة SQLite خارج Git، ولا ترفع secrets أو raw provider bodies إلى artifacts.
