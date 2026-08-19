# ترتيب نماذج NVIDIA التي اجتازت الاختبار الحي

## نطاق الترتيب

هذا ترتيب عملي لـ13 نموذجًا نصيًا عامًا بقيت مفعّلة بعد الاختبار الوظيفي الواقعي. الترتيب ليس leaderboard عالميًا؛ بل heuristic موجه لاختيار fallback عام داخل router. أعطيت الأولوية للقدرة العامة، والاستدلال، والسياق الطويل، والبرمجة، والتخطيط، واستدعاء الأدوات، ثم الوسائط المتعددة، مع إبقاء النماذج المتخصصة في تصنيف مستقل حتى لو كانت قوية جدًا في مجالها.

> **مهم:** الترتيب يصف الأفضلية الافتراضية للمهام العامة. لا يعني أن نموذج الترجمة أو نموذج الرؤية أقل جودة في مجاله المتخصص.

## الترتيب

| الترتيب | النموذج | الفئة العملية | سبب الترتيب |
|---:|---|---|---|
| 1 | `nvidia/nemotron-3-ultra-550b-a55b` | reasoning/agents | أكبر نموذج عام في المجموعة الناجحة، مع وصف رسمي يركز على السياق الطويل جدًا، reasoning، coding، planning، وtool calling. |
| 2 | `nvidia/nemotron-3-super-120b-a12b` | reasoning/agents | نموذج MoE كبير بسياق طويل وقدرات قوية في reasoning والبرمجة والتخطيط والأدوات. |
| 3 | `z-ai/glm-5.2` | general/agents | نموذج flagship للـagentic workflows والبرمجة والاستدلال طويل الأفق، وقد نجح في الاختبار الحي بالنص الحرفي. |
| 4 | `nvidia/llama-3.3-nemotron-super-49b-v1.5` | general/reasoning | نسخة Nemotron Super عالية الكفاءة للـreasoning وtool calling وchat وinstruction following. |
| 5 | `nvidia/llama-3.3-nemotron-super-49b-v1` | general/reasoning | قدرات عامة قوية في reasoning وchat وtool calling، مع حجم أقل من النماذج الثلاثة الأولى. |
| 6 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | omni-modal | يفهم image وvideo وspeech وtext، ولذلك يتقدم في المهام متعددة الوسائط حتى مع حجم أصغر. |
| 7 | `nvidia/nemotron-3-nano-30b-a3b` | general/reasoning | نموذج MoE عام بسياق طويل للبرمجة والاستدلال والتعليمات واستدعاء الأدوات. |
| 8 | `nvidia/nemotron-3.5-lightning-30b-a3b` | fast agents | مخصص للسرعة والـthroughput في مهام agentic؛ نجح حيًا لكنه ليس الخيار الأول لأقصى عمق reasoning. |
| 9 | `meta/llama-3.1-70b-instruct` | general chat | نموذج عام كبير للاستدلال وفهم السياق وتوليد النص، لكنه أقدم وأضيق من نماذج Nemotron الحديثة في هذه السلسلة. |
| 10 | `nvidia/nemotron-nano-12b-v2-vl` | vision-language | مناسب لفهم الصور والفيديو وvisual QA والتلخيص؛ أقل عمومية من النماذج النصية الأعلى. |
| 11 | `nvidia/llama-3.1-nemotron-nano-vl-8b-v1` | vision-language | نموذج رؤية/لغة صغير لفهم النص والصورة، مفيد عند الحاجة إلى latency أقل. |
| 12 | `nvidia/ising-calibration-1.5-31b` | specialized vision | نموذج كبير متعدد الوسائط، لكنه موجه لتحليل مخططات معايرة الحوسبة الكمومية والنص التقني، لذلك لا يناسب fallback العام. |
| 13 | `meta/llama-3.1-8b-instruct` | lightweight general | نموذج عام صغير مناسب للسرعة والتكلفة، لكنه أقل قدرة عامة من النماذج الأكبر الناجحة. |

## نتائج الاختبار الوظيفي والتصنيفات المنفصلة

شغّل GitHub Actions الوظيفي [32218928597](https://github.com/ysrg2003/ai-provider-router/actions/runs/32218928597) نموذجًا نموذجًا، باستخدام سؤال معرفة عربي ومسألة حسابية عربية لكل نموذج عام. نجحت 12 من 13 نماذج عامة في الاختبارين. فشل `z-ai/glm-5.2` في مسألة الاستدلال بسبب `429 quota` في ذلك التشغيل، لذلك لا نعدّه فشل قدرة دائمًا. أما `meta/llama-3.2-11b-vision-instruct` فأعاد output غير متوافق مع عقد JSON العام، ولذلك أُخرج من routes النص العامة. ونجح `nvidia/riva-translate-4b-instruct-v2` عند اختباره برسالة ترجمة مباشرة، فصُنّف **ترجمة متخصصة** ولم يُترك في fallback النص العام.

| التصنيف | النماذج | قرار router |
|---|---|---|
| نص عام | 13 نموذجًا في `model_chains.nvidia_free` | مفعّلة بعد OpenRouter |
| ترجمة متخصصة | `nvidia/riva-translate-4b-instruct-v2` | غير مفعّل حتى وجود translation route/adapter |
| رؤية/لغة غير متوافق مع عقد JSON العام | `meta/llama-3.2-11b-vision-instruct` | disabled من routes النص العامة |
| بحث حي | لا يوجد NVIDIA model مفعّل بأداة search | لا يُصنّف NVIDIA كمزود بحث حي |
| صور | لا يوجد NVIDIA image route | لا تُرسل طلبات image إلى NVIDIA عبر router |

## ترتيب router

يظهر هذا الترتيب في `config/models.json` داخل `model_chains.nvidia_free`. وتُضاف السلسلة بعد OpenRouter في `default` و`creative` و`cheap` ومساري `text` و`text_grounded_search`. لا تدخل نماذج NVIDIA في `output_routes.image`، لأن Free Endpoint لا يعني أن النموذج مولد صور.

## دليل الاختيار السريع

للمهام العامة المعقدة ابدأ بـNemotron Ultra أو Super أو GLM 5.2، مع مراقبة quota. للـagents والبرمجة طويلة الأفق استخدم GLM 5.2 أو أحد Nemotron Super. للسرعة استخدم Nemotron Lightning. لفهم الصور والفيديو، لا يعني نجاح text completion أن route image جاهز؛ تحتاج capability وadapter مثبتين. للترجمة استخدم Riva Translate عبر route متخصص عند إضافته. للنص الخفيف منخفض الكلفة استخدم Llama 3.1 8B.

## الأدلة والمراجع

النجاح التشغيلي ونتائج الاختبار الوظيفي لكل نموذج موثقة في [`config/nvidia_free_catalog.json`](../config/nvidia_free_catalog.json)، ويتضمن ذلك run `32218928597` وحالات quota وJSON contract والتخصص. لا تخلط بين live HTTP 200 وبين نجاح مهمة وظيفية كاملة. القدرات الوصفية مأخوذة من كتالوج NVIDIA وصفحات النماذج الرسمية [1] [2] [3].

[1]: https://build.nvidia.com/models?filters=nimType%3Anim_type_preview "NVIDIA Free Endpoint catalog"
[2]: https://build.nvidia.com/llms.txt "NVIDIA NIM llms.txt and OpenAI-compatible API"
[3]: https://build.nvidia.com/models.md "NVIDIA canonical model catalog"
