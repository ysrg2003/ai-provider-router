# Capability Audit لجميع نماذج المشروع

## الغرض

يستخدم هذا التدقيق كل نموذج فريد مذكور في `config/models.json`، لا كل تكرار له داخل routes. يختبر التدقيق حيًا methods الآمنة نسبيًا: `json` و`grounded_text` و`interaction_text` و`translation` و`embedding`. method `grounded_text` محصور في Gemini ويشغّل طلب Google Search واحدًا مع فحص `url_citations`. أما الصور والصوت والفيديو والـlive ومواضع النماذج التي تحتاج payload متخصصًا فتسجل `route_only`؛ وهذا يثبت وجود route وعقده في config، ولا يستهلك حصة توليد أو يرسل payload غير مناسب.

## النتائج التشغيلية

التشغيل الكامل [32220522226](https://github.com/ysrg2003/ai-provider-router/actions/runs/32220522226) اختبر 57 سجلًا حيًا، وسجل 47 نجاحًا و10 إخفاقات و25 سجلًا `route_only`.

| المزود | نتائج live الناجحة | الإخفاقات | route-only | التفسير |
|---|---:|---:|---:|---|
| NVIDIA | 12 | 1 | 0 | نماذج النص العامة نجحت؛ نتيجة الفشل تخص نموذج رؤية/لغة لم يحافظ على عقد JSON في هذا الاختبار. Riva مفحوص في route الترجمة مستقلًا. |
| OpenRouter | 14 | 3 | 2 | الإخفاقات تشمل quota أو نماذج متخصصة/متعددة الوسائط لا ينبغي إجبارها على عقد JSON العام. |
| Hugging Face | 7 | 3 | 0 | بعض النماذج أعادت 400 أو output غير صالح؛ تحتاج إعادة اختبار أو adapter/payload خاص قبل إعادة تفعيلها. |
| Gemini | 13 | 1 | 20 | نماذج النص والتضمين نجحت؛ الصور والصوت والفيديو والـlive بقيت route-only، وGemini 3 Flash أعاد 404 عند اختباره بعقد JSON العام. |

أعيد تشغيل الحالات المهمة في [32220960460](https://github.com/ysrg2003/ai-provider-router/actions/runs/32220960460) مع raw-text fallback. نجح بعض الإخفاقات أو بقي فشلها بسبب 404/400/429؛ لذلك لا تُنقل النماذج إلى route جديد لمجرد أنها أعادت نصًا، بل يجب أن يطابق الـadapter العقد الذي يتطلبه route.

## ما الذي يمكن وضعه في أكثر من قسم؟

تسمح البنية بأن يظهر النموذج نفسه في أكثر من route عندما تكون قدرته مثبتة وطريقة النقل مناسبة. Gemini models التي نجحت في text يمكن أن تظهر في `video_analysis` أو `image` أو `audio` فقط عندما يستخدم route الـmethod المتخصص الموجود في config. كما أن Riva يظهر الآن في `output_routes.translation`، لكنه لا يدخل fallback النص العام لأن عقد الترجمة الخام مختلف عن عقد JSON.

ولا تُضاف نماذج NVIDIA أو OpenRouter متعددة الوسائط إلى `output_routes.image` تلقائيًا. وجود `input_types` مثل `image` أو `video` في catalog لا يثبت أن router يملك image adapter لذلك المزود. وبالمثل لا يُصنف أي provider على أنه بحث حي إلا إذا كان route يمرر أداة search فعلية؛ NVIDIA الحالي لا يستقبل search tool.

## إعادة الاختبار

لتشغيل جميع السجلات القابلة للاختبار:

```bash
PYTHONPATH=src python scripts/capability_audit.py
```

ولإعادة اختبار مجموعة محددة مع محاولة raw-text بعد فشل JSON:

```bash
CAPABILITY_AUDIT_MODELS='provider/model-a,provider/model-b' \
CAPABILITY_AUDIT_RAW_FALLBACK=true \
PYTHONPATH=src python scripts/capability_audit.py
```

عبر GitHub Actions استخدم workflow [`../.github/workflows/capability-audit.yml`](../.github/workflows/capability-audit.yml). التقرير المرفوع منقح ولا يحفظ المفاتيح أو Authorization headers أو نصوص الاستجابات الكاملة.

## سياسة القرار

النجاح يعني أن النموذج أعاد payload صالحًا لعقد الـmethod المحدد، لا أنه الأفضل لكل المهام. الفشل `429` أو `503` يعامل كحالة تشغيلية قابلة لإعادة الفحص، بينما `400` أو `404` أو JSON غير صالح يدفع إلى إبقاء النموذج خارج route ذلك العقد حتى يتوفر adapter أو payload مناسب. والـ`route_only` ليس فشلًا؛ بل قرار أمان يمنع استهلاك quota أو إرسال مدخلات غير مدعومة.

## المراجع

[1]: https://github.com/ysrg2003/ai-provider-router/actions/runs/32220522226 "Full capability audit"

[2]: https://github.com/ysrg2003/ai-provider-router/actions/runs/32220960460 "Targeted capability rerun"

[3]: https://github.com/ysrg2003/ai-provider-router/actions/runs/32220367894 "Verified translation smoke"
