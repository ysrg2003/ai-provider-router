# استكشاف الأخطاء وإصلاحها

ابدأ دائمًا بتحديد نوع الفشل: **تحميل config محلي**، **اختيار route**، **مصادقة**، **quota/rate limit**، **availability/timeout**، أو **artifact parsing**. لا تعالج كل خطأ بإعادة الطلب؛ بعض الأخطاء terminal وبعضها retryable.

## بوابة التشخيص الأولى

من جذر المشروع:

```bash
export PYTHONPATH=src
python3 -m compileall -q src tests
python3 -m ai_router.cli.main --config-dir config --state-db /tmp/diagnose-router.db summary
python3 -m ai_router.cli.main --config-dir config route-plan --output-type text --user 'Return exactly: route plan'
```

Expected result: compile exit 0، summary منقح، وroute-plan يعرض route/models. إذا فشل أحدها، لا تنفذ live call بعد؛ أصلح المحلي أولًا.

## جدول الأخطاء

| العرض/الرسالة | الطبقة | السبب المرجح | الإصلاح والتحقق |
|---|---|---|---|
| `FileNotFoundError` لملف config | Config | `AI_ROUTER_CONFIG_DIR` خاطئ أو file ناقص | شغّل من root، تحقق من `providers.json`, `models.json`, `key_pools.json`, `policies.json`، ثم أعد `summary`. |
| JSON decode error | Config | comma أو quote خاطئة | استخدم `python3 -m json.tool <file>` على الملف، ثم أعد الاختبار. |
| `No keys configured` | Credentials | env name خاطئ أو JSON فارغ | قارن الاسم مع `config/key_pools.json`، خزّن secret في `.env`/GitHub Secret، ولا تضعه في JSON config. |
| secret يظهر في summary/log | Security | redaction regression | أوقف التشغيل، لا ترفع artifact، أصلح `public_summary()`/logging، وrotate السر إذا خرج خارج البيئة. |
| `401/403` | Auth | key منتهٍ/منسوخ خطأ/permissions ناقصة | أعد الحصول على key من صفحة provider الرسمية، حدّث secret، ثم test واحد. لا تكرر key القديمة. |
| `400` أو `invalid_request` | Payload | model/method أو response format غير مدعوم | راجع `models.json` وadapter؛ اختبر method الصحيح بدل تعطيل validation. |
| `404` model not found | Provider | model ID غير موجود في provider | استخدم ID من catalog الرسمي/`/v1/models` الخاص بالمزود، ولا تنسخ ID من مزود آخر. |
| `429` | Quota/rate | quota أو RPM limit | انتظر cooldown، خفف الطلبات، أو استخدم provider/key مستقلًا؛ لا تعتبر key rotation حلًا إذا quota على الحساب. |
| `503` | Availability | worker أو Space غير جاهز | افحص health/logs، شغّل provider آخر، وسجل deferred إن تكرر. |
| timeout text | Network/runtime | Space cold start أو service بطيء | تحقق من base URL وtimeout provider، لا ترفع retries بلا حد. |
| timeout image | ChatGPT/Gemini | generation بطيء أو DOM/session | انتظر حتى الحد الموثق، افحص artifact بعد اكتمال generation، ولا تكرر الطلب مباشرة. |
| `AllProvidersFailed` | Router | كل specs/key attempts فشلت أو في cooldown | اقرأ آخر error classes فقط، افحص credentials/routes/state، ثم أعد الاختبار على DB جديد. |
| router يتجاوز provider مع key صالح | State | key/model في cooldown أو cursor متقدم | راجع state DB، شغّل DB مؤقتًا لتأكيد config، ثم لا تمسح الإنتاج قبل backup. |
| text يعمل وsearch يفشل | Capability | لا يوجد `search` tool أو session لا تملك grounding | استخدم `route-plan --grounding search`، راجع tools/spec، ثم اختبر Space search وحدها. |
| text يعمل والصورة تفشل | Image-specific | quota أو image method/artifact parsing | فرّق quota 429 عن parser/timeout؛ افحص `src`/`data_url` في response، ولا تغيّر text config. |
| ChatGPT Spaces الثلاثة لا تتساوى | Session | cookies/Storage State/account مختلفة | اختبر كل Space منفردة: health، secret، session، browser logs؛ لا تنسخ state بين replicas. |
| NVIDIA لا يظهر في route | Config/state | لا يوجد `NVIDIA_API_KEY` أو model disabled/cooling | شغّل `summary`، تحقق من key، اقرأ `nvidia_free_catalog.json`، ولا تفعّل غير live-tested. |
| NVIDIA `/v1/models` يفشل | NVIDIA auth/availability | key مكشوف/منتهي أو account غير مفعّل | ألغِ key القديم، أنشئ جديدًا من NVIDIA Build، اختبر مرة واحدة. |
| NVIDIA model في catalog لكن completion يفشل | Capability | endpoint متخصص أو model غير متاح للحساب | ابقه disabled/deferred؛ لا تسجله كـtext model. |
| GitHub Actions green لكن لا response | Workflow | progress فقط أو artifact فارغ | افتح artifact `live-smoke.json`، تحقق من status/route/payload summary، وافصل CI offline عن live. |
| GitHub Actions لا يبدأ | Workflow | secret/input/workflow path | تأكد من `.github/workflows/live-smoke.yml` وmanual dispatch وSecret names، ثم أعد run محدودًا. |
| `pip` أو import failure | Local runtime | venv غير فعال أو dependencies ناقصة | فعّل `.venv`، ثبّت `requirements.txt`، واضبط `PYTHONPATH=src`. |

## تصنيف ProviderError

`auth` و`invalid_or_unknown` غالبًا terminal حتى يتغير credential أو payload. `quota` يحتاج cooldown أو provider مختلفًا. `transient` قابل لإعادة المحاولة ضمن `max_attempts` مع backoff قصير. router يسجل `error_class`, `status_code`, operation، والرسالة المنقحة في SQLite؛ لا تكتب secret في exception message.

## إعادة التجربة بأمان

استخدم state DB جديدًا للتحقق من أن المشكلة ليست cooldown:

```bash
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/clean-router.db \
  call-auto --output-type text --operation clean_smoke \
  --user 'Return exactly: clean retry works'
```

إذا نجحت التجربة النظيفة وفشلت DB الدائمة، راجع state/cooldown وليس provider أولًا. إذا فشل الاثنان، افحص credential ثم provider health. لا تمسح state الإنتاجية بلا نسخة احتياطية وقرار واضح.

## تشخيص GitHub Actions

offline test workflow لا يحتاج provider secrets؛ يجب أن ينجح على push وpull request بعد `compileall` و`unittest`. live-smoke workflow يدوي ويستهلك quota؛ input `scenario` يحدد `text`, `search`, `maps`, `image`, `audio`, `embedding`, `openrouter`, أو `all`. عند الفشل، افحص أولًا هل `test -n` وجد secret، ثم provider status، ثم artifact المنقح. artifact لا ينبغي أن يحتوي base64 أو Authorization.

## rollback

إذا سبب تعديل config فشلًا:

1. احتفظ بالـlogs المنقحة وcommit hash.
2. أعد config إلى آخر commit معروف النجاح أو عطّل model entry فقط.
3. لا تتراجع عن code وcredentials معًا دون معرفة السبب.
4. شغّل compile/unit tests.
5. نفّذ live smoke واحدًا على route المتأثر.
6. وثق root cause وقرار rollback في release notes.

## تسريب credential أو session

عند تسريب NVIDIA/HF/OpenRouter/Gemini/ChatGPT API key: ألغِه من provider فورًا، أنشئ بديلًا، حدّث GitHub Secret و`.env`، افحص Git history والـartifacts، ثم نفّذ health check واحدًا. عند تسريب Cookie أو Storage State: ألغِ جلسة ChatGPT وأنشئ state جديدة داخل Space؛ لا يكفي تغيير API secret. لا ترسل القيمة إلى issue أو chat أثناء طلب المساعدة.

## متى تطلب مساعدة؟

أرسل provider ID وmodel ID وHTTP status و`error_class` ووقت حدوث الفشل فقط. استبدل كل key وcookie وAuthorization وprompt حساس بـ`<redacted>`. أرفق route-plan ونسخة `summary` المنقحة، ولا ترفق `.env` أو SQLite DB إلا بعد فحصها.
