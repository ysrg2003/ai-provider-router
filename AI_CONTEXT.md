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

النتيجة المثبتة الحالية في router: **47 اختبارًا ناجحًا**، إضافة إلى **13 اختبارًا** في مستودع chatgpt-api المصدر. لتشغيل طلب حقيقي، انسخ [`.env.example`](.env.example)، أضف secret لمزود واحد على الأقل، ثم استخدم:

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
| ChatGPT Spaces | [`src/ai_router/providers/chatgpt_space.py`](src/ai_router/providers/chatgpt_space.py) | text/search prefix، explicit `output_type=image`، image capture، quota detection، data-url/src/url fallback، ومحاولتان كحد أقصى للصور. |
| Persistence | [`src/ai_router/store.py`](src/ai_router/store.py) | SQLite tables لحالات provider، calls، rotation، وper-key model cursor؛ WAL/checkpoint وحالة تبقى بعد restart. |
| Tools | [`src/ai_router/tools.py`](src/ai_router/tools.py) | يبني tools للبحث والخرائط عندما يطلبها route. |
| Examples/automation | [`examples/one_request.py`](examples/one_request.py), [`scripts/live_smoke.py`](scripts/live_smoke.py), [`.github/workflows/test.yml`](.github/workflows/test.yml), [`.github/workflows/live-smoke.yml`](.github/workflows/live-smoke.yml) | تشغيل محلي، live smoke محدود، سيناريو `nvidia`، CI offline، وworkflow يدوي يرفع artifact منقحًا لمدة 7 أيام. |
| Documentation | [`docs/operations.md`](docs/operations.md), [`docs/nvidia-free.md`](docs/nvidia-free.md), [`docs/nvidia-ranking.md`](docs/nvidia-ranking.md), [`docs/credentials.md`](docs/credentials.md) | التشغيل، الأسرار، NVIDIA، والترتيب والتحقيقات. |

## 4. العقود والبيانات والإعداد

### ProviderSpec

كل provider في `config/providers.json` يملك `id`, `kind`, `enabled`, `base_url`، وربما `base_url_env`, `key_pool`, و`default_timeout_seconds`. الأنواع الحية هي `chatgpt_space`, `gemini_rest`, و`openai_compatible`. إضافة kind جديد تتطلب adapter وتسجيله في constructor داخل `AIRouter`.

### ModelSpec وroutes

`config/models.json` يعرّف `model_chains` للتدوير العام، و`output_routes` للتوجيه حسب المخرج، و`reference_catalog` للمصادر والـsnapshots. كل row يحدد provider/model/method/input_types/output_types/tools و`supports_response_format` و`enabled`. route لا يثبت أن endpoint متاح دائمًا؛ availability وquota خارجية.

الترتيب الحالي المهم هو: ChatGPT Spaces أولًا في text/search/image، ثم Gemini/Hugging Face/OpenRouter وفق route، وNVIDIA بعد OpenRouter في السلاسل العامة. سلسلة `nvidia_free` تحتوي **12 نموذجًا نصيًا عامًا** بعد الاختبار الوظيفي، بترتيب [`docs/nvidia-ranking.md`](docs/nvidia-ranking.md). Riva مصنف ترجمة متخصصة وله الآن `output_routes.translation` مستقل مع `method=translation` وraw-text contract، بينما Llama Vision وLlama 8B أُخرجا من عقد JSON العام. catalog NVIDIA الكامل يحتوي 57 نتيجة في [`config/nvidia_free_catalog.json`](config/nvidia_free_catalog.json)، لكن غير المؤكد أو المتخصص يبقى خارج routes العامة.

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
| ChatGPT replica 01/02/04 | `chatgpt_space` | `chatgpt_space_default` | 540s | text/search مثبتان في 01/02؛ صورة 02 موثقة بPNG صالح، أما 01 فآخر تحقق أعاد HTTP 200 مع `images=[]` ورسالة Free plan image quota بعد نشر extraction fix، لذلك image=deferred until quota reset. replica-04 تُظهر زر login مرئيًا حقيقيًا بحجم 68.2×36 وتفشل بإشارة re-authentication سريعة. كل Space له Storage State خاص خارج Git. |
| Gemini | `gemini_rest` | `gemini_default` | 180s | يدعم مسارات multimodal إضافية. |
| Hugging Face | `openai_compatible` | `huggingface_default` | 90s | fallback token `HF_TOKEN`. |
| OpenRouter | `openai_compatible` | `openrouter_default` | 120s | catalog مجاني مستقل. |
| NVIDIA | `openai_compatible` | `nvidia_default` | 120s | 12 نموذجًا نصيًا عامًا في routes بعد OpenRouter؛ Riva في `output_routes.translation`، وVision/Llama 8B غير موثوقين لعقد JSON العام. |

## 8. الأخطاء والإصلاحات المثبتة

- `401/403`: افحص secret واسم pool والـbase URL؛ لا تعالجها بإعادة الطلب بلا تغيير.
- `429`: quota/rate limit؛ يسجل router cooldown وينتقل إلى key/model/provider التالي.
- `408/409/425/5xx` أو `RemoteDisconnected`: transient؛ تحقق من timeout وhealth ثم اسمح بالـfallback المحدود. في ChatGPT Spaces، recovery يفتح محادثة جديدة فعليًا ويعيد الطلب مرة واحدة فقط؛ إذا ظهر login control، fail-fast يعيد re-authentication بدل انتظار timeout.
- JSON غير صالح أو response فارغ: `invalid_or_unknown`؛ راجع method وpayload وmodel capability.
- ChatGPT image: أرسل router `output_type=image` صراحة، ويقبل data_url/src/url، مع حد محاولتين. extraction في المصدر أضيف له `image_dom` redacted، وفحص الصور للصورة فقط يمتد إلى `body` ويستخدم أبعاد العرض عند غياب `naturalWidth`. replica-02 لها PNG حي موثق؛ replica-01 آخر تحقق فيها `images=[]` مع رسالة Free plan image quota، لذا لا تُوصف كصورة ناجحة حتى reset الحصة.
- NVIDIA: الكتالوج العام 57، وظهر 30 مرشحًا في اختبار `/v1/models` السابق. الاختباران الوظيفيان [32218928597](https://github.com/ysrg2003/ai-provider-router/actions/runs/32218928597) و[32219540211](https://github.com/ysrg2003/ai-provider-router/actions/runs/32219540211) اختبرا النماذج بسؤال معرفة ومسألة استدلال؛ نجحت النماذج العامة الـ12 بعد إعادة اختبار transient، ونجحت Riva في ترجمة مباشرة، بينما أخرج Vision وLlama 8B بسبب عقد JSON غير مناسب. واجه GLM quota مؤقتًا ثم نجح في الجولة اللاحقة.

## 9. الاختبارات وبوابات release

الاختبار offline الرئيسي:

```bash
python3 -m compileall -q src tests
python3 -m unittest discover -s tests -v
```

الاختبارات عالية القيمة في [`tests/test_multiroute.py`](tests/test_multiroute.py) و[`tests/test_router.py`](tests/test_router.py) و[`tests/test_model_catalog.py`](tests/test_model_catalog.py) و[`tests/test_nvidia.py`](tests/test_nvidia.py). وهي تثبت intent، search prefix، image filtering/retry/data-url، Gemini payloads، state cursor، secret redaction، ترتيب OpenRouter/NVIDIA، وعدم دخول NVIDIA إلى image route.

لـlive smoke استخدم workflow يدويًا أو `scripts/live_smoke.py`؛ workflow يحقن Gemini/HF/OpenRouter/NVIDIA من GitHub Secrets فقط، ويقبل scenarios مثل `nvidia` و`translation`. live test ليس جزءًا من CI offline؛ سجّل status/model/route والأحجام فقط، ولا تسجل base64 أو headers أو prompts الحساسة. لتدقيق كل النماذج استخدم [`scripts/capability_audit.py`](scripts/capability_audit.py) وworkflow [`capability-audit.yml`](.github/workflows/capability-audit.yml): جرد 82 سجلًا فريدًا، نفذ 57 probe حيًا، وسجل 25 route-only للصور والصوت والفيديو والـlive والـmethods المتخصصة.

## 10. بروتوكول تعديل المشروع

قبل تعديل provider أو model:

1. حدّد هل المطلوب route موجود أم adapter جديد.
2. اقرأ `config.py` و`router.py` و`base.py` والـadapter المقابل.
3. أضف أو عدّل config دون secrets.
4. اكتب regression test يثبت request shape والـfallback وترتيب route.
5. شغّل JSON validation و`compileall` و47 router tests و14 source tests و`git diff --check` وفحص secrets.
6. إن كان التكامل خارجيًا، نفّذ live smoke محدودًا فقط بعد توفير credential، وسجّل deferred عندما لا يكون متاحًا.
7. حدث docs وAI_CONTEXT ثم commit/release مع ملاحظة ما تم اختباره وما بقي غير مؤكد.

لإضافة provider جديد: أضف ProviderSpec وkey pool وadapter method، ثم اربط `kind` في `AIRouter.__init__`, صنّف HTTP errors، أضف route/model specs، واكتب test offline قبل أي live call. لا تستخدم OpenAI-compatible adapter لنموذج يتطلب payload مختلفًا لمجرد أن عنوانه يشبه `/v1`.

## 11. الحالة الحالية والقدرات المؤجلة

**Verified:** 46 unit tests، catalog NVIDIA 57، اختباران وظيفيان حقيقيان [32218928597](https://github.com/ysrg2003/ai-provider-router/actions/runs/32218928597) و[32219540211](https://github.com/ysrg2003/ai-provider-router/actions/runs/32219540211)؛ نجحت النماذج العامة الـ12 في سؤال معرفة ومسألة استدلال بعد إعادة فحص transient، ونجحت Riva في اختبار ترجمة متخصص. بعد إضافة المفتاح الجديد إلى GitHub Secrets، نجح أيضًا تشغيل smoke رقم [`32217577979`](https://github.com/ysrg2003/ai-provider-router/actions/runs/32217577979) على route=`nvidia_free`.

**Verified:** أضيف `translation route` مستقل واختُبر حيًا في [32220367894](https://github.com/ysrg2003/ai-provider-router/actions/runs/32220367894) بالمفتاح الجديد؛ route=`translation` وoutput_type=`translation` وRiva أعاد نصًا غير فارغ.

**Capability audit:** التشغيل الكامل [32220522226](https://github.com/ysrg2003/ai-provider-router/actions/runs/32220522226) فحص 82 سجلًا فريدًا، نفذ 57 live probes، وسجل 47 passed و10 failed و25 route-only. إعادة الاختبار المستهدف [32220960460](https://github.com/ysrg2003/ai-provider-router/actions/runs/32220960460) فرّقت بين quota/transient و404/400 وعقد JSON غير المناسب. التفاصيل في [`project-documentation/capability-audit.md`](project-documentation/capability-audit.md).

**Current checkpoint:** المصدر الحالي `2ac0d0e`، وrouter الحالي `1a209bd`، وHF replica-01 الحالي `d2c5bee`. أضيف bounded recovery، فتح New chat فعليًا، diagnostics redacted، وتمييز auth control المرئي، fail-fast عند login marker، ثم image DOM diagnostics redacted وتوسيع استخراج الصور إلى `body` للصورة فقط. نجحت 47 اختبارات router و14 اختبارًا في المصدر. text/search في 01/02 مثبتان؛ صورة 02 مثبتة بPNG صالح؛ أما آخر image request إلى 01 فأعاد HTTP 200 مع `images=[]` ورسالة ChatGPT Free plan image quota، لذا verification للصورة deferred حتى reset. replica-04 تحتاج re-authentication. نقطة الاستعادة والإجراءات الآمنة في [`project-documentation/checkpoint-2026-08-19.md`](project-documentation/checkpoint-2026-08-19.md)، والدليل النهائي في [`project-documentation/replica-01-image-final-verification-2026-08-19.md`](project-documentation/replica-01-image-final-verification-2026-08-19.md)، والتفاصيل في [`project-documentation/chatgpt-generation-recovery.md`](project-documentation/chatgpt-generation-recovery.md) و[`project-documentation/chatgpt-spaces.md`](project-documentation/chatgpt-spaces.md).

**Deferred:** البحث الحي عبر NVIDIA لأن adapter الحالي لا يرسل search tool، والقدرات المتخصصة للصورة والصوت والفيديو والـlive عندما لا يملك provider adapter مناسبًا. لا تصف هذه العناصر كميزات حية قبل إضافة adapter واختبار contract.

## 12. المراجع

- [`README.md`](README.md) — المسار المبتدئ والتشغيل.
- [`docs/credentials.md`](docs/credentials.md) — credential cards والتدوير والإلغاء.
- [`docs/operations.md`](docs/operations.md) — التشغيل وGitHub Actions/live smoke.
- [`docs/nvidia-free.md`](docs/nvidia-free.md) — NVIDIA catalog والسياسة.
- [`docs/nvidia-ranking.md`](docs/nvidia-ranking.md) — ترتيب النماذج الناجحة.
- [`project-documentation/capability-audit.md`](project-documentation/capability-audit.md) — تدقيق جميع النماذج وتصنيف route-only/live.
- [`project-documentation/checkpoint-2026-08-19.md`](project-documentation/checkpoint-2026-08-19.md) — نقطة الاستعادة الحالية ونتائج ChatGPT Spaces.
- [`config/nvidia_free_catalog.json`](config/nvidia_free_catalog.json) — evidence snapshot وlive status.
- [`tests/test_multiroute.py`](tests/test_multiroute.py) و[`tests/test_router.py`](tests/test_router.py) — contracts السلوكية.
