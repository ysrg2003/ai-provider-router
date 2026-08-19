# ترتيب نماذج NVIDIA التي اجتازت الاختبار الحي

## نطاق الترتيب

هذا ترتيب عملي للنماذج الـ15 التي ظهرت في `/v1/models` لحساب الاختبار ونجحت في live completion نصي محدود. الترتيب ليس leaderboard عالميًا؛ بل heuristic موجه لاختيار fallback عام داخل router. أعطيت الأولوية للقدرة العامة، والاستدلال، والسياق الطويل، والبرمجة، والتخطيط، واستدعاء الأدوات، ثم الوسائط المتعددة، مع خفض ترتيب النماذج المتخصصة حتى لو كانت قوية جدًا في مجالها.

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
| 12 | `meta/llama-3.2-11b-vision-instruct` | vision-language | نموذج عام متعدد الوسائط ناجح، لكن حجمه وقدراته العامة أقل من نماذج Nemotron الأكبر. |
| 13 | `nvidia/ising-calibration-1.5-31b` | specialized vision | نموذج كبير متعدد الوسائط، لكنه موجه لتحليل مخططات معايرة الحوسبة الكمومية والنص التقني، لذلك لا يناسب fallback العام. |
| 14 | `nvidia/riva-translate-4b-instruct-v2` | translation | متخصص في الترجمة متعددة اللغات، ويُفضّل عندما تكون المهمة ترجمة لا reasoning عامًا. |
| 15 | `meta/llama-3.1-8b-instruct` | lightweight general | نموذج عام صغير مناسب للسرعة والتكلفة، لكنه أقل قدرة عامة من النماذج الأكبر الناجحة. |

## ترتيب router

يظهر هذا الترتيب في `config/models.json` داخل `model_chains.nvidia_free`. وتُضاف السلسلة بعد OpenRouter في `default` و`creative` و`cheap` ومساري `text` و`text_grounded_search`. لا تدخل نماذج NVIDIA في `output_routes.image`، لأن Free Endpoint لا يعني أن النموذج مولد صور.

## دليل الاختيار السريع

للمهام العامة المعقدة ابدأ بـNemotron Ultra أو Super أو GLM 5.2. للـagents والبرمجة طويلة الأفق استخدم GLM 5.2 أو أحد Nemotron Super. للسرعة استخدم Nemotron Lightning. لفهم الصور والفيديو استخدم Nemotron Nano VL أو Nano Omni أو Llama Vision. للترجمة استخدم Riva Translate. للنص الخفيف منخفض الكلفة استخدم Llama 3.1 8B.

## الأدلة والمراجع

النجاح التشغيلي لكل نموذج موثق في [`config/nvidia_free_catalog.json`](../config/nvidia_free_catalog.json)، ويتضمن حالة live test ووقت الاختبار. القدرات الوصفية مأخوذة من كتالوج NVIDIA وصفحات النماذج الرسمية [1] [2] [3].

[1]: https://build.nvidia.com/models?filters=nimType%3Anim_type_preview "NVIDIA Free Endpoint catalog"
[2]: https://build.nvidia.com/llms.txt "NVIDIA NIM llms.txt and OpenAI-compatible API"
[3]: https://build.nvidia.com/models.md "NVIDIA canonical model catalog"
