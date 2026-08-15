# دليل التشغيل والأسرار

هذا الدليل يشرح إعداد مفاتيح Gemini وتشغيل الفحص الحي في مستودع `ai-provider-router`. لا تضع أي قيمة حقيقية في Git أو في هذا الملف. القيمة الوحيدة التي يحتاجها GitHub Actions هي Secret باسم `AI_ROUTER_GEMINI_KEYS_JSON`.

## النتيجة الأولى المتوقعة

بعد إعداد الـSecret وتشغيل workflow يدويًا، يجب أن يظهر تقرير artifact باسم `live-smoke-<run-id>` يحتوي على `live-smoke.json`. التقرير يعرض حالة كل سيناريو، المسار المختار، اسم النموذج، وحجم المخرج فقط. لا يعرض مفاتيح API أو محتوى Base64 للصورة والصوت.

## خريطة الاعتمادات

| الاسم | المكان | الغرض | التصنيف |
|---|---|---|---|
| `AI_ROUTER_GEMINI_KEYS_JSON` | GitHub Actions Secret | قائمة مفاتيح Gemini المرتبة | Secret مطلوب للفحص الحي |
| `AI_ROUTER_HF_KEYS_JSON` | GitHub Actions Secret أو `.env` محلي | fallback النصي في Hugging Face | اختياري، Secret |
| `HF_TOKEN` | GitHub Actions Secret أو `.env` محلي | مفتاح Hugging Face المفرد | اختياري، Secret |
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

إذا ظهر أن الاسم موجود، استخدم **Update** أو أعد حفظه بعد تغيير المفاتيح. GitHub يعرض اسم Secret وتاريخ تحديثه فقط، ولا يعرض القيمة القديمة؛ وهذا طبيعي.

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

## تشغيل smoke test

افتح تبويب [Actions](https://github.com/ysrg2003/ai-provider-router/actions)، اختر **Live smoke tests**، واضغط **Run workflow**. ابدأ بـ`routing` لأنه لا يرسل طلبًا إلى Gemini؛ هو يتحقق من اختيار مسارات Live وVeo فقط. بعد ذلك شغّل كل سيناريو منفردًا لتقليل استهلاك الحصة:

| السيناريو | ما يختبره | استهلاك محتمل |
|---|---|---|
| `routing` | اختيار route لـ Live وVeo وتحليل الفيديو | لا يرسل طلبًا |
| `text` | توليد نص صغير | طلب Gemini واحد أو محاولات fallback |
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

النجاح المتوقع هو suite ناجحة، وroute plan يعرض `image_grounded_search` دون أي طلب خارجي. استخدم هذا المسار قبل أي smoke test حي.
