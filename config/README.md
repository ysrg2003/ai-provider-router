# دليل إعدادات ai-provider-router

هذا المجلد هو مصدر ترتيب المزودات والنماذج والسياسات. عدّل JSON هنا عندما تريد تغيير route أو تعطيل model، ولا تضع أي secret داخل هذه الملفات.

## الملفات

| الملف | السؤال الذي يجيب عنه |
|---|---|
| `providers.json` | أين يوجد provider؟ وما نوع adapter والـtimeout والـkey pool؟ |
| `models.json` | أي model يُستخدم لكل output route وبأي method؟ |
| `key_pools.json` | أي environment variable يمد كل provider بالمفاتيح؟ |
| `policies.json` | كم محاولة؟ ما timeout وcooldown وbackoff؟ |

## الترتيب الحالي

يبدأ route `image` بـ`chatgpt_conversation/chatgpt-conversation`، ثم `chatgpt_image/chatgpt-api`، ثم Gemini image models. يبدأ route `text` بـChatGPT conversation، بينما يبدأ `text_grounded_search` به ثم يستخدم Gemini `gemini-2.5-flash` كـfallback. خرائط Google، الصوت، embedding، وتحليل الفيديو لها routes مستقلة.

لا تعكس `model_chains.default` بالضرورة `output_routes.text`: الأولى مخصصة لعمليات `complete_json` الداخلية، أما اختيار المستخدم حسب نوع المخرج فيمر عبر `output_routes` و`complete_auto`.

## إضافة أو تعطيل model

لتعطيل model مؤقتًا، غيّر `enabled` إلى `false` بدل حذف العنصر؛ هذا يحافظ على وضوح catalog ويمكّن rollback:

```json
{
  "provider": "google_gemini",
  "model": "gemini-2.5-flash-image",
  "method": "image",
  "input_types": ["text", "image"],
  "output_types": ["image", "text"],
  "enabled": false
}
```

لإضافة model، يجب أن يكون provider مسجلًا في `providers.json` وأن يكون `method` مدعومًا داخل adapter. لا يكفي إضافة الاسم إلى JSON إذا لم يعرف `router.py` نوع provider أو method.

## إضافة provider جديد

أضف provider في `providers.json` مع `id` فريد و`kind` معروف و`base_url` و`key_pool`. أضف pool في `key_pools.json`، ثم أضف adapter في `src/ai_router/providers/`. بعد ذلك سجّل `kind` في `src/ai_router/router.py`، وأضف اختبارًا offline باستخدام mock response قبل أي smoke حي.

## التحقق بعد تعديل config

```bash
cd ai-provider-router
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m json.tool config/key_pools.json >/dev/null
python3 -m json.tool config/policies.json >/dev/null
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

إذا نجحت JSON والاختبارات، استخدم `route_plan` للتأكد من أن أول model هو ما قصدته قبل إرسال طلب حي. لا تستخدم `all` smoke لمجرد التحقق من تعديل ترتيب واحد.

## مراجع المزودات

يجب مراجعة [Gemini API][1]، [Hugging Face Inference][2]، و[OpenRouter API][3] قبل إضافة model جديد. قيم `input_types` و`output_types` و`supports_response_format` يجب أن تطابق adapter الفعلي، لا وصفًا تسويقيًا.

[1]: https://ai.google.dev/gemini-api/docs "Gemini API Documentation"
[2]: https://huggingface.co/docs/huggingface_hub/en/guides/inference "Hugging Face Inference Documentation"
[3]: https://openrouter.ai/docs/api-reference/overview "OpenRouter API Reference"
