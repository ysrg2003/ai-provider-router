# OpenRouter Free Models

هذه الوثيقة هي كتالوج OpenRouter المجاني الذي أُضيف إلى `ai-provider-router`. تم جمع البيانات من endpoint النماذج الرسمي وصفحة الترتيب وصفحة `openrouter/free` في 2026-08-16. القائمة متغيرة؛ لذلك يجب إعادة التحقق من المصدر قبل أي release جديد.

> **قاعدة الترتيب:** حُفظ ترتيب [Free Models collection][1] من الأقوى والأكثر تقدمًا إلى الأقل كما نشره OpenRouter. أُضيفت النماذج المجانية التي ظهرت في API ولم تظهر في ترتيب المجموعة بعد ذلك. وُضع `openrouter/free` في النهاية لأنه router يختار نموذجًا عشوائيًا/متاحًا، وليس نموذجًا ثابتًا.

## الحالة التنفيذية

| الفئة | العدد | الحالة |
|---|---:|---|
| كل النماذج المجانية التي ظهرت في API | 19 | محفوظة في `config/models.json` |
| نماذج النص/المتعدد الوسائط النشطة | 16 | موجودة في `model_chains.openrouter_free` و`output_routes.openrouter_free` |
| نماذج الصوت Lyria | 2 | catalog فقط؛ معطلة لغياب adapter صوت OpenRouter |
| نموذج Content Safety | 1 | route moderation فقط؛ معطل من fallback العام |

يستخدم المسار التنفيذي `https://openrouter.ai/api/v1/chat/completions` بصيغة OpenAI-compatible. لا يرسل الراوتر `response_format` للنماذج التي لا تعلن `response_format` أو `structured_outputs` في metadata؛ وهذا يمنع فشلًا مصطنعًا في بعض النماذج المجانية.

## الكتالوج الكامل

| # | Model ID | الاسم | المدخلات | المخرجات | السياق | JSON/structured | الحالة |
|---:|---|---|---|---|---:|---|---|
| 1 | `nvidia/nemotron-3-ultra-550b-a55b:free` | NVIDIA: Nemotron 3 Ultra (free) | text | text | 1000000 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 2 | `poolside/laguna-s-2.1:free` | Poolside: Laguna S 2.1 (free) | text | text | 262144 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 3 | `nvidia/nemotron-3.5-lightning:free` | NVIDIA: Nemotron 3.5 Lightning (free) | text | text | 1000000 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 4 | `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA: Nemotron 3 Super (free) | text | text | 262144 | نعم | نشط في openrouter_free |
| 5 | `cohere/north-mini-code:free` | Cohere: North Mini Code (free) | text | text | 256000 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 6 | `poolside/laguna-xs-2.1:free` | Poolside: Laguna XS 2.1 (free) | text | text | 262144 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 7 | `nvidia/nemotron-3-nano-30b-a3b:free` | NVIDIA: Nemotron 3 Nano 30B A3B (free) | text | text | 256000 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 8 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | NVIDIA: Nemotron 3 Nano Omni (free) | text, audio, image, video | text | 256000 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 9 | `google/gemma-4-26b-a4b-it:free` | Google: Gemma 4 26B A4B  (free) | image, text, video | text | 262144 | نعم | نشط في openrouter_free |
| 10 | `nvidia/nemotron-nano-9b-v2:free` | NVIDIA: Nemotron Nano 9B V2 (free) | text | text | 128000 | نعم | نشط في openrouter_free |
| 11 | `dots-studio/dots-3-note-preview:free` | Dots Studio: Dots3-Note Preview (free) | text, image | text | 512000 | نعم | نشط في openrouter_free |
| 12 | `openai/gpt-oss-20b:free` | OpenAI: gpt-oss-20b (free) | text | text | 131072 | نعم | نشط في openrouter_free |
| 13 | `nvidia/nemotron-nano-12b-v2-vl:free` | NVIDIA: Nemotron Nano 12B 2 VL (free) | image, text, video | text | 128000 | لا؛ الراوتر يحذف الحقل | نشط في openrouter_free |
| 14 | `liquid/lfm-2.5-2.6b:free` | LiquidAI: LFM2.5-2.6B (free) | text | text | 128000 | نعم | نشط في openrouter_free |
| 15 | `google/gemma-4-31b-it:free` | Google: Gemma 4 31B (free) | image, text, video | text | 262144 | نعم | نشط في openrouter_free |
| 16 | `google/lyria-3-clip-preview` | Google: Lyria 3 Clip Preview | text, image | text, audio | 1048576 | نعم | audio catalog؛ معطل |
| 17 | `google/lyria-3-pro-preview` | Google: Lyria 3 Pro Preview | text, image | text, audio | 1048576 | نعم | audio catalog؛ معطل |
| 18 | `nvidia/nemotron-3.5-content-safety:free` | NVIDIA: Nemotron 3.5 Content Safety (free) | text, image | text | 128000 | لا؛ الراوتر يحذف الحقل | moderation؛ معطل |
| 19 | `openrouter/free` | Free Models Router | text, image | text | 200000 | نعم | نشط في openrouter_free |

## الإعداد المحلي

أنشئ مفتاحًا من [OpenRouter Keys][2]، ثم أضف متغيرًا مفردًا:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-ضع_المفتاح_هنا
```

أو استخدم pool مرتبًا لعدة مفاتيح:

```dotenv
AI_ROUTER_OPENROUTER_KEYS_JSON=[
  {"id":"openrouter-1","key":"sk-or-v1-المفتاح_الأول","project":"openrouter"},
  {"id":"openrouter-2","key":"sk-or-v1-المفتاح_الثاني","project":"openrouter"}
]
```

بعد ذلك شغّل الأمر من جذر المستودع:

```bash
ai-router --config-dir config --state-db /tmp/openrouter-check.db summary
```

يجب أن يظهر `openrouter` ضمن providers، وأن يظهر عدد الأسرار دون قيمها. لتجربة أول طلب بعد توفر المفتاح:

```bash
ai-router --config-dir config --state-db /tmp/openrouter-live.db call-json \
  --chain openrouter_free \
  --operation openrouter_smoke \
  --system "Return JSON only." \
  --user "Return a JSON object with ok=true and provider=openrouter."
```

إذا ظهر `429`، فهذا يعني rate limit أو نفاد الحصة المجانية، وسيحوّل الراوتر المحاولة إلى المفتاح أو النموذج التالي بعد cooldown. إذا ظهر `400` بسبب `response_format`، تحقق من أن model metadata محدث وأن `supports_response_format` مضبوطًا في config.

## المصادر

[1]: https://openrouter.ai/collections/free-models "OpenRouter Free Models collection"
[2]: https://openrouter.ai/keys "OpenRouter API keys"
[3]: https://openrouter.ai/openrouter/free "OpenRouter Free Models Router"
[4]: https://openrouter.ai/docs/quickstart "OpenRouter Quickstart"
[5]: https://openrouter.ai/api/v1/models "OpenRouter models API"
