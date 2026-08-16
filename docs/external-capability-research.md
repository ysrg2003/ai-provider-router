# مصادر القدرات الخارجية

## Google Search grounding

المصدر: https://ai.google.dev/gemini-api/docs/google-search

توضح وثائق Google أن `google_search` يربط Gemini بمحتوى الويب الحي، ويعيد نصًا مع annotations وURL citations، وأن الأداة تعمل مع نماذج متعددة مثل Gemini 3.6 Flash و3.5 Flash-Lite و3.5 Flash و3.1 Pro Preview و3 Flash Preview و2.5 Pro و2.5 Flash و2.5 Flash-Lite. يمكن استخدام الأداة فقط عندما يدعم النموذج واجهة Interactions/Tools المناسبة.

## Google Maps grounding

المصدر: https://ai.google.dev/gemini-api/docs/maps-grounding

توضح الوثائق أن `google_maps` يحتاج عادةً إلى latitude وlongitude عند توفر موقع المستخدم، ويعيد نصًا مع place citations. الأداة مخصصة للأسئلة الجغرافية والمحلية، وهي مغلقة افتراضيًا ويجب تفعيلها صراحة. حدود الدعم الحالية تشمل نماذج مثل Gemini 3.5 Flash-Lite و3.5 Flash و3.1 Flash-Lite و3 Flash Preview و2.5 Flash و2.5 Flash-Lite. يجب عرض إسناد Google Maps للمستخدم عند استخدام النتائج.

## Native image generation — current

المصدر: https://ai.google.dev/gemini-api/docs/generate-content/image-generation

تسجل الوثائق الرسمية الحالية نماذج Nano Banana `gemini-3-pro-image` و`gemini-3.1-flash-image` و`gemini-3.1-flash-lite-image` و`gemini-2.5-flash-image`. metadata الفعلي للمفتاح أعاد `200` لهذه النماذج وأعلن `generateContent` كطريقة مدعومة. لذلك يستخدم الراوتر endpoint `models/{model}:generateContent`، ويدخل النص داخل `contents[].parts[]`، ويقرأ الصورة من `candidates[].content.parts[].inlineData`.

## Imagen 4 — legacy فقط

المصدر: https://ai.google.dev/gemini-api/docs/imagen

جدول `available-limits.md` المرفق يحتوي صفوف Imagen 4 الثلاثة، لذلك بقيت موثقة في `docs/model-catalog.md`، لكن Google أعلنت إيقاف `imagen-4.0-generate-001` و`imagen-4.0-ultra-generate-001` و`imagen-4.0-fast-generate-001` في 2026-08-17. الاختبار المباشر أعاد `404 NOT_FOUND`، ولذلك لا تُستخدم في route Image التلقائي، بل في `image_legacy` المعطل فقط.

## قرار التصميم

سيحتاج الراوتر إلى `output_type` أو اكتشاف تلقائي من prompt، مع سلاسل منفصلة مثل `text`, `image`, `audio`, `video`, `live`, `embedding`, و`agent`. يجب أن تُحدد كل سلسلة adapter/operation الخاصة بها بدل محاولة إرسال كل الأنواع عبر `generateContent` النصي.

أما Grounding، فيجب أن يكون طبقة capability-aware: إذا طلب المستخدم search أو maps grounding وكان النموذج المختار يدعم الأداة، تُمرر الأداة إلى نفس الاستدعاء. إذا لم يدعمها النموذج، يستخدم الراوتر مسارًا بديلًا يدعمها، ولا ينبغي إرسال `google_search` إلى Hugging Face إلا عبر adapter/connector خاص؛ أدوات Google ليست عامة تلقائيًا لكل مزود OpenAI-compatible.

## Gemini TTS

المصدر: https://ai.google.dev/gemini-api/docs/speech-generation

TTS يحول نصًا مضبوطًا إلى صوت، ويستخدم Interactions مع `response_format: {"type":"audio"}` و`speech_config` للأصوات، ويدعم نموذج `gemini-3.1-flash-tts-preview` إضافة إلى نماذج TTS أخرى. يختلف TTS عن Live: TTS مناسب لتلاوة نص محدد، بينما Live محادثة تفاعلية مستمرة.

## Gemini Embeddings

المصدر: https://ai.google.dev/gemini-api/docs/embeddings

`gemini-embedding-2` يدعم embeddings متعددة الوسائط للنص والصور والفيديو والصوت وPDF في فضاء موحد، و`gemini-embedding-001` مناسب للنص. REST يستخدم `/models/{model}:embedContent` ويعيد vectors، لذلك يحتاج adapter وProviderResponse مخصصًا بدل JSON object.

## Gemini Live

المصدر: https://ai.google.dev/gemini-api/docs/live-api

Live API واجهة WebSocket stateful لتدفق audio وimage وtext وإخراج audio في الزمن الحقيقي. هو مسار streaming/connection وليس طلب HTTP عاديًا، لذلك يحتاج adapter مستقلًا أو طبقة session ولا ينبغي اختباره عبر complete_json.

## أسماء Live وTTS الرسمية

المصادر: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-live-preview وhttps://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-native-audio-preview-12-2025 وhttps://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-tts-preview

الأسماء الحالية التي ظهرت في الوثائق الرسمية هي `gemini-3.1-flash-live-preview` و`gemini-2.5-flash-native-audio-preview-12-2025` لمسار Live، و`gemini-3.1-flash-tts-preview` لمسار TTS. Live يعتمد WebSocket stateful، بينما Image يستخدم `generateContent`؛ كلاهما لا يمر عبر complete_json.

## Video generation

المصادر: https://ai.google.dev/gemini-api/docs/video وhttps://ai.google.dev/gemini-api/docs/veo

Video generation مسار مستقل عن تحليل الفيديو. الوثائق الحالية تعرض نماذج Veo 3.1 مثل `veo-3.1-generate-preview` و`veo-3.1-lite-generate-preview`، مع عمليات async/poll لتنفيذ التوليد. لذلك لا يجوز وضعها في `video` chain الخاصة بتحليل الفيديو النصي؛ تحتاج adapter generate-video مستقلًا وحالة job.

## References

[1]: https://ai.google.dev/gemini-api/docs/google-search "Grounding with Google Search"
[2]: https://ai.google.dev/gemini-api/docs/maps-grounding "Grounding with Google Maps"
[3]: https://ai.google.dev/gemini-api/docs/image-generation "Nano Banana image generation"
[4]: https://ai.google.dev/gemini-api/docs/imagen "Imagen"
[5]: https://ai.google.dev/gemini-api/docs/speech-generation "Gemini text-to-speech"
[6]: https://ai.google.dev/gemini-api/docs/embeddings "Gemini embeddings"
[7]: https://ai.google.dev/gemini-api/docs/live-api "Gemini Live API"
[8]: https://ai.google.dev/gemini-api/docs/video "Video generation in the Gemini API"
