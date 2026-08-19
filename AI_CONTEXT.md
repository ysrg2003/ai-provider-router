# AI_CONTEXT.md

## 1. الهوية والحدود

`ai-provider-router` هو **موجّه JSON متعدد المزودين** مكتوب بـPython 3.11+؛ يستقبل طلبًا واحدًا، يختار route حسب نوع المخرج والـgrounding، ثم يجرّب providers وmodels وkeys بالترتيب، ويسجل النجاح والفشل وحالة التدوير في SQLite. وصف المشروع الرسمي موجود في [`pyproject.toml`](pyproject.toml) وشرح الاستخدام للمبتدئ في [`README.md`](README.md).

المشروع **ليس** model server ولا مخزنًا للمفاتيح، ولا ينفذ تلقائيًا كل endpoint في كتالوج خارجي. هو orchestration layer: يملك config، adapters، fallback، cooldown، وحالة rotation، بينما تملك كل خدمة خارجية inference الفعلي وquota والـauthentication.

> **القاعدة الذهبية:** عدّل `config/` لإضافة provider/model/order عندما تكون طبقة adapter موجودة، ولا تضع أي secret أو cookie أو Storage State في Git أو في هذا الملف.

## 2. النتيجة الأولى القابلة للتحقق

بعد clone وتثبيت dependencies، شغّل:

```bash
python3 -m compileall -q src tests
python3 -m unittest discover -s tests -v
```

النتيجة المثبتة الحالية: **43 اختبارًا ناجحًا**. لتشغيل طلب حقيقي، انسخ [`.env.example`](.env.example)، أضف secret لمزود واحد على الأقل، ثم استخدم:

```bash
export PYTHONPATH=src
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/ai-router.db \
  call-auto \
  --output-type text \
  --operation first_run \
  --user 'Return exactly: router works'
```

`call-auto` يعيد JSON؛ الحقلان `route` و`intent` يثبتان route المختار. لا تعتبر نجاح progress أو تهيئة config دليلًا على live API success؛ يجب أن يظهر response فعلي أو artifact صالح.

## 3. خريطة الملفات والطبقات

| الطبقة | الملفات | المسؤولية والعقد |
|---|---|---|
| CLI | [`src/ai_router/cli/main.py`](src/ai_router/cli/main.py) | أوامر `summary` و`call-json` و`route-plan` و`call-auto`; يطبع JSON ويغلق router في `finally`. |
| Discovery/intent | [`src/ai_router/intent.py`](src/ai_router/intent.py) | يكتشف `text`, `image`, `audio`, `embedding`, `video_analysis`, `video_generation`, `live` و`search/maps` من markers، مع أولوية `output_type` الصريح. |
| Config | [`src/ai_router/config.py`](src/ai_router/config.py), [`config/providers.json`](config/providers.json), [`config/models.json`](config/models.json), [`config/key_pools.json`](config/key_pools.json), [`config/policies.json`](config/policies.json) | تحميل providers وchains وroutes وkeys وcooldowns، وتطبيق `base_url_env`، والتحقق من المراجع. |
| Orchestration | [`src/ai_router/router.py`](src/ai_router/router.py) | يحل route، يبني tools، يمر على model/key، يستدعي adapter، ويسجل success/failure ويحرّك cursor. |
| Adapter contract | [`src/ai_router/providers/base.py`](src/ai_router/providers/base.py) | `ProviderResponse` و`ProviderError` والعقود العامة للـadapters. |
| OpenAI-compatible | [`src/ai_router/providers/openai_compatible.py`](src/ai_router/providers/openai_compatible.py) | POST إلى `/chat/completions`، JSON parsing، وclassification لأخطاء HTTP؛ يستخدمه Hugging Face وOpenRouter وNVIDIA. |
| Gemini | [`src/ai_router/providers/gemini.py`](src/ai_router/providers/gemini.py) | JSON text، grounded interactions، image، TTS، embedding، وvideo analysis حسب method. |
| ChatGPT Spaces | [`src/ai_router/providers/chatgpt_space.py`](src/ai_router/providers/chatgpt_space.py) | text/search prefix، image capture، quota detection، data-url/src fallback، ومهلة الصور الطويلة. |
| Persistence | [`src/ai_router/store.py`](src/ai_router/store.py) | SQLite tables لحالات provider، calls، rotation، وper-key model cursor؛ WAL/checkpoint وحالة تبقى بعد restart. |
| Tools | [`src/ai_router/tools.py`](src/ai_router/tools.py) | يبني tools للبحث والخرائط عندما يطلبها route. |
| Examples/automation | [`examples/one_request.py`](examples/one_request.py), [`scripts/live_smoke.py`](scripts/live_smoke.py), [`.github/workflows/test.yml`](.github/workflows/test.yml), [`.github/workflows/live-smoke.yml`](.github/workflows/live-smoke.yml) | تشغيل محلي، live smoke محدود، سيناريو `nvidia`، CI offline، وworkflow يدوي يرفع artifact منقحًا لمدة 7 أيام. |
| Documentation | [`docs/operations.md`](docs/operations.md), [`docs/nvidia-free.md`](docs/nvidia-free.md), [`docs/nvidia-ranking.md`](docs/nvidia-ranking.md), [`docs/credentials.md`](docs/credentials.md) | التشغيل، الأسرار، NVIDIA، والترتيب والتحقيقات. |

## 4. العقود والبيانات والإعداد

### ProviderSpec

كل provider في `config/providers.json` يملك `id`, `kind`, `enabled`, `base_url`، وربما `base_url_env`, `key_pool`, و`default_timeout_seconds`. الأنواع الحية هي `chatgpt_space`, `gemini_rest`, و`openai_compatible`. إضافة kind جديد تتطلب adapter وتسجيله في constructor داخل `AIRouter`.

### ModelSpec وroutes

`config/models.json` يعرّف `model_chains` للتدوير العام، و`output_routes` للتوجيه حسب المخرج، و`reference_catalog` للمصادر والـsnapshots. كل row يحدد provider/model/method/input_types/output_types/tools و`supports_response_format` و`enabled`. route لا يثبت أن endpoint متاح دائمًا؛ availability وquota خارجية.

الترتيب الحالي المهم هو: ChatGPT Spaces أولًا في text/search/image، ثم Gemini/Hugging Face/OpenRouter وفق route، وNVIDIA بعد OpenRouter في السلاسل العامة. سلسلة `nvidia_free` تحتوي **13 نموذجًا نصيًا عامًا** بعد الاختبار الوظيفي، بترتيب [`docs/nvidia-ranking.md`](docs/nvidia-ranking.md). Riva مصنف ترجمة متخصصة خارج السلسلة العامة، وLlama Vision أُخرج من عقد JSON العام. catalog NVIDIA الكامل يحتوي 57 نتيجة في [`config/nvidia_free_catalog.json`](config/nvidia_free_catalog.json)، لكن غير المؤكد أو المتخصص يبقى خارج routes العامة.

### KeySpec والسرية

`RouterConfig.keys_for()` يقبل JSON array أو single-token fallback، وwrapper keys مثل `keys/items/entries`، وaliases مثل `key/api_key/token/secret/value`. المفاتيح تُمرر إلى adapter ولا تُعاد في `public_summary()`. الأسماء ومكان الحصول والتدوير والإلغاء موثقة في [`docs/credentials.md`](docs/credentials.md).

### ProviderResponse وProviderError

الـadapter يعيد payload JSON وusage إن وُجد. `ProviderError` يحمل `error_class`, `status_code`, و`retryable`. التصنيفات التشغيلية الأساسية هي `auth`, `quota`, `transient`, و`invalid_or_unknown`. router يسجلها ثم يقرر cooldown وcursor advancement؛ لا يخفي الخطأ النهائي إذا فشلت كل المحاولات، بل يرفع `AllProvidersFailed`.

## 5. دورة البيانات وحالة التدوير

```text
CLI input
  -> detect_intent(output_type/markers/grounding)
  -> resolve output route or explicit model chain
  -> build search/maps tools when applicable
  -> iterate provider -> model -> ordered keys
  -> skip cooling key/model
  -> adapter request
  -> parse ProviderResponse or ProviderError
  -> record SQLite success/failure and usage
  -> advance per-key model cursor on failure
  -> return payload + route + intent
     OR raise AllProvidersFailed
```

حالة SQLite ليست cache عابرة. `RouterStore` يملك provider state وprovider calls وrotation state وkey/model cursor؛ الـcursor مركب من provider وchain وkey وproject، لذلك يمكن لكل key أن يستأنف من موضعه بعد فشل سابق، وتبقى الحالة بعد restart. `cooldown` يمنع إعادة استخدام key/model المتعطل قبل انتهاء المدة. المسح المقصود للـstate يتم باختيار state DB جديد، مثل `/tmp/new-router.db`، وليس بتعديل config.

## 6. سلوك المخرجات والقدرات

| output type | الحالة الحالية | المالك |
|---|---|---|
| `text` | executable، مع fallback متعدد providers | `complete_json`/`_complete_route` |
| `text` + `search/maps` | executable عندما يملك spec أداة grounding؛ ChatGPT adapter يضيف search prefix حسب contract | `tools.py`, `chatgpt_space.py`, Gemini interactions |
| `image` | executable عبر ChatGPT/Gemini routes؛ NVIDIA غير مضاف لأن Free Endpoint ليس دليل image generation | `chatgpt_space.py`, `gemini.py` |
| `audio`/TTS | executable عبر Gemini route الحالي | `gemini.py` |
| `embedding` | executable عبر Gemini route؛ لا ترسل NVIDIA embedding إلى text route | `gemini.py` |
| `video_analysis` | plan/executable فقط عندما يوجد `video_uri` وadapter داعم | `complete_video_json`, Gemini |
| `video_generation` | route plan يرفض التنفيذ الحالي باعتباره asynchronous Veo job غير موصل | `complete_auto` |
| `live` | `prepare_live_session()` يعيد plan فقط؛ لا HTTP request | `prepare_live_session()` |

## 7. Providers الحالية والـfallback

| provider | kind | key pool | timeout | ملاحظة تحقق |
|---|---|---|---:|---|
| ChatGPT replica 01/02/04 | `chatgpt_space` | `chatgpt_space_default` | 540s | النص والبحث والصورة عبر router موثقة؛ كل Space له Storage State خاص خارج Git. |
| Gemini | `gemini_rest` | `gemini_default` | 180s | يدعم مسارات multimodal إضافية. |
| Hugging Face | `openai_compatible` | `huggingface_default` | 90s | fallback token `HF_TOKEN`. |
| OpenRouter | `openai_compatible` | `openrouter_default` | 120s | catalog مجاني مستقل. |
| NVIDIA | `openai_compatible` | `nvidia_default` | 120s | 13 نموذجًا نصيًا عامًا في routes بعد OpenRouter؛ Riva ترجمة متخصصة خارجها، وVision JSON-incompatible خارجها. |

## 8. الأخطاء والإصلاحات المثبتة

- `401/403`: افحص secret واسم pool والـbase URL؛ لا تعالجها بإعادة الطلب بلا تغيير.
- `429`: quota/rate limit؛ يسجل router cooldown وينتقل إلى key/model/provider التالي.
- `408/409/425/5xx` أو `RemoteDisconnected`: transient؛ تحقق من timeout وhealth ثم اسمح بالـfallback المحدود.
- JSON غير صالح أو response فارغ: `invalid_or_unknown`؛ راجع method وpayload وmodel capability.
- ChatGPT image: كان السبب المؤكد مهلة 210s والتحقق الضعيف من نجاح الإرسال؛ الإصلاح رفع مهلة الصورة إلى 540s والتحقق من بدء generation، ونجح PNG حيًا.
- NVIDIA: الكتالوج العام 57، وظهر 30 مرشحًا في اختبار `/v1/models` السابق. الاختبار الوظيفي [32218928597](https://github.com/ysrg2003/ai-provider-router/actions/runs/32218928597) اختبر 15 نموذجًا بسؤال معرفة ومسألة استدلال؛ نجحت 12 من 13 العامة، ونجحت Riva في اختبار ترجمة متخصص، بينما واجه GLM quota وLlama Vision عقد JSON غير مناسب.

## 9. الاختبارات وبوابات release

الاختبار offline الرئيسي:

```bash
python3 -m compileall -q src tests
python3 -m unittest discover -s tests -v
```

الاختبارات عالية القيمة في [`tests/test_multiroute.py`](tests/test_multiroute.py) و[`tests/test_router.py`](tests/test_router.py) و[`tests/test_model_catalog.py`](tests/test_model_catalog.py) و[`tests/test_nvidia.py`](tests/test_nvidia.py). وهي تثبت intent، search prefix، image filtering/retry/data-url، Gemini payloads، state cursor، secret redaction، ترتيب OpenRouter/NVIDIA، وعدم دخول NVIDIA إلى image route.

لـlive smoke استخدم workflow يدويًا أو `scripts/live_smoke.py`؛ workflow يحقن Gemini/HF/OpenRouter/NVIDIA من GitHub Secrets فقط، ويقبل scenario مثل `nvidia`. live test ليس جزءًا من CI offline؛ سجّل status/model/route والأحجام فقط، ولا تسجل base64 أو headers أو prompts الحساسة.

## 10. بروتوكول تعديل المشروع

قبل تعديل provider أو model:

1. حدّد هل المطلوب route موجود أم adapter جديد.
2. اقرأ `config.py` و`router.py` و`base.py` والـadapter المقابل.
3. أضف أو عدّل config دون secrets.
4. اكتب regression test يثبت request shape والـfallback وترتيب route.
5. شغّل JSON validation و`compileall` و43+ unit tests و`git diff --check` وفحص secrets.
6. إن كان التكامل خارجيًا، نفّذ live smoke محدودًا فقط بعد توفير credential، وسجّل deferred عندما لا يكون متاحًا.
7. حدث docs وAI_CONTEXT ثم commit/release مع ملاحظة ما تم اختباره وما بقي غير مؤكد.

لإضافة provider جديد: أضف ProviderSpec وkey pool وadapter method، ثم اربط `kind` في `AIRouter.__init__`, صنّف HTTP errors، أضف route/model specs، واكتب test offline قبل أي live call. لا تستخدم OpenAI-compatible adapter لنموذج يتطلب payload مختلفًا لمجرد أن عنوانه يشبه `/v1`.

## 11. الحالة الحالية والقدرات المؤجلة

**Verified:** 43 unit tests، catalog NVIDIA 57، اختبار وظيفي حقيقي [32218928597](https://github.com/ysrg2003/ai-provider-router/actions/runs/32218928597) شغّل 15 نموذجًا؛ نجحت 12 من 13 العامة في سؤال معرفة ومسألة استدلال، ونجحت Riva في اختبار ترجمة متخصص. بعد إضافة المفتاح الجديد إلى GitHub Secrets، نجح أيضًا تشغيل smoke رقم [`32217577979`](https://github.com/ysrg2003/ai-provider-router/actions/runs/32217577979) على route=`nvidia_free`.

**Deferred:** البحث الحي عبر NVIDIA لأن adapter الحالي لا يرسل search tool، routes متخصصة للنماذج NVIDIA audio/video/embedding/rerank/moderation/image، وtranslation route لـRiva. لا تصف هذه العناصر كميزات حية قبل إضافة adapter واختبار contract.

## 12. المراجع

- [`README.md`](README.md) — المسار المبتدئ والتشغيل.
- [`docs/credentials.md`](docs/credentials.md) — credential cards والتدوير والإلغاء.
- [`docs/operations.md`](docs/operations.md) — التشغيل وGitHub Actions/live smoke.
- [`docs/nvidia-free.md`](docs/nvidia-free.md) — NVIDIA catalog والسياسة.
- [`docs/nvidia-ranking.md`](docs/nvidia-ranking.md) — ترتيب النماذج الناجحة.
- [`config/nvidia_free_catalog.json`](config/nvidia_free_catalog.json) — evidence snapshot وlive status.
- [`tests/test_multiroute.py`](tests/test_multiroute.py) و[`tests/test_router.py`](tests/test_router.py) — contracts السلوكية.
