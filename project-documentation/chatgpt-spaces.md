# تكامل ChatGPT Spaces

## الفكرة

الـrouter يتعامل مع ChatGPT Spaces كـHTTP providers مستقلة. لكل replica base URL، لكن قيمة API secret تمر عبر key pool مشترك ما لم تقرر توزيع secrets منفصلًا. Cookies وStorage State الخاصة بمتصفح ChatGPT لا تدخل إلى router؛ تبقى داخل Space التي تشغّل Playwright/Chromium.

## replicas الحالية

| Provider ID | Base URL variable | الدور | timeout |
|---|---|---|---:|
| `chatgpt_space_replica_01` | `CHATGPT_API_REPLICA_01_BASE_URL` | replica-01 | 540s |
| `chatgpt_space_replica_02` | `CHATGPT_API_REPLICA_02_BASE_URL` | replica-02 | 540s |
| `chatgpt_space` | `CHATGPT_API_BASE_URL` | replica-04 | 540s |

القيم الافتراضية موجودة في [`../config/providers.json`](../config/providers.json) و[`.env.example`](../.env.example). base URL public identifier، أما `CHATGPT_API_SECRET_KEY` و`AI_ROUTER_CHATGPT_KEYS_JSON` فهما secrets. خطوات الحصول والتدوير في [`../docs/credentials.md`](../docs/credentials.md).

## ما الذي يفعله adapter؟

للنص، يرسل adapter interaction text ويحلل JSON/النص دون فحص HTML. للبحث، يضيف جملة search prefix المطلوبة قبل prompt عندما تكون أداة `search` في route. للصورة فقط ينتظر generation، يتحقق من image candidates، يدعم `data_url`، وينزّل `src` عند توفره؛ لذلك timeout الصور أطول وقد يصل إلى 540 ثانية.

> نجاح النص أو البحث لا يثبت نجاح الصورة؛ الصورة تتأثر بـquota generation، session state، browser DOM، ووقت generation. والعكس صحيح: فشل الصورة لا يعني أن base URL أو text API معطل.

## التشغيل والإعداد

### الخطوة 1: تحضير Space

في كل Space، افتح Hugging Face **Settings → Variables and secrets** وأنشئ Secret باسم `API_SECRET_KEY` بالقيمة التي سيستخدمها router. احتفظ بكل Cookie/Storage State داخل Space نفسها ولا ترفعها إلى repository. بعد حفظ secret أعد تشغيل Space وانتظر health response.

Expected result: Space تظهر Running، وطلب health أو text صغير يعيد HTTP success. إذا كانت Space تبقى Building، افحص logs وDocker/runtime قبل تغيير router.

### الخطوة 2: ضبط base URLs

في `.env` المحلي اترك القيم الافتراضية أو overrideها:

```bash
CHATGPT_API_BASE_URL=https://<replica-04-space>.hf.space
CHATGPT_API_REPLICA_01_BASE_URL=https://<replica-01-space>.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://<replica-02-space>.hf.space
```

Expected result: `summary` يذكر providers الثلاثة. الخطأ الشائع هو وضع `/v1` أو مسار API غير موجود؛ اتبع contract الخاص بـSpace ولا تفترض OpenAI-compatible URL.

### الخطوة 3: ضبط secret pool

لـsingle key:

```bash
CHATGPT_API_SECRET_KEY=<space-api-secret>
```

لـpool:

```bash
AI_ROUTER_CHATGPT_KEYS_JSON=["<space-key-1>","<space-key-2>"]
```

لا تضع `API_SECRET_KEY` أو cookies داخل `providers.json`. يستخدم `key_pools.json` أسماء env vars فقط.

### الخطوة 4: اختبار النص

```bash
export PYTHONPATH=src
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/chatgpt-text.db \
  call-auto --output-type text --operation chatgpt_text_smoke \
  --user 'Return exactly: ChatGPT text works'
```

Expected result: JSON response مع `route` و`intent`. إذا اختار route providerًا آخر، فهذا fallback طبيعي؛ لاستخدام ChatGPT وحده نفّذ chain/نسخة config تقيّد providers.

### الخطوة 5: اختبار البحث

```bash
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/chatgpt-search.db \
  call-auto --output-type text --grounding search \
  --operation chatgpt_search_smoke \
  --user 'ابحث في الويب عن آخر موديل Anthropic AI وأعد المصادر'
```

Expected result: response grounded عندما ينجح ChatGPT search-capable spec. الفشل إذا كان route لا يملك `search` يعني config capability filtering، وليس بالضرورة فشل Space.

### الخطوة 6: اختبار الصورة بحذر

اختبار الصور يستهلك quota وقد يستغرق دقائق. لا تكرره لمجرد progress message. نفّذ request واحدًا، انتظر timeout المسموح، وتحقق من payload/artifact. استخدم prompt قصيرًا لا يحتوي بيانات شخصية، ثم افحص وجود image data أو downloadable `src` في JSON النهائي.

Expected success: artifact صورة صالح أو data URL normalized. إذا ظهرت رسالة `Free plan limit` فهي quota خارجية؛ لا تصلحها بتدوير ChatGPT API keys. إذا ظهر timeout، راجع Space logs وDOM/session state، ثم لا تعاود الطلب إلا بعد التأكد من أن generation لم يكتمل خلفيًا.

## Replica isolation

كل Space يجب أن تملك runtime وStorage State مستقلين. لا تخلط cookie file بين replica-01 وreplica-02 وreplica-04. إذا نجحت replica-01 وفشلت الأخريان، افحص لكل واحدة على حدة: health، `API_SECRET_KEY`، session/challenge state، browser launch، والـquota. تشابه source files لا يساوي تشابه جلسة ChatGPT أو صلاحية account.

## تشخيص الأخطاء

| العرض | الاحتمال | الإصلاح |
|---|---|---|
| `401/403` في الثلاث | secret غير متطابق أو Space لا تقبله | حدّث `API_SECRET_KEY` في Space وrouter |
| النص يفشل قبل الوصول إلى ChatGPT | route/config أو كل providers في cooldown | شغّل `route-plan` ثم state DB جديد للاختبار |
| search لا يعطي مصادر | لا يوجد `search` tool في spec أو Space session لا تملك البحث | راجع `models.json` وSpace capability |
| الصورة تعطي quota | ChatGPT Free image quota | انتظر reset؛ لا تكرر الطلب ولا تغيّر keys |
| الصورة timeout | generation/DOM بطيء أو session state | راجع logs و540s timeout وartifact بعد اكتمال generation |
| Space Running لكن كل الطلبات 503 | app/browser/session initialization | افحص HF logs وStorage State، ثم أعد تشغيل Space |
| replica واحدة تعمل | اختلاف session أو account أو secret، لا source فقط | اختبرها منفردة وسجّل root cause قبل fallback |

## الأمن والتحديث

لا تسجل cookies، Storage State، Authorization، prompts حساسة، أو base64 image في GitHub Actions artifacts. عند تسريب API secret غيّره في Space ثم في router. عند تسريب session state، ألغِ جلسة ChatGPT وأصدر state جديدة؛ لا يكفي تدوير `CHATGPT_API_SECRET_KEY`. قبل release افحص `git diff --check` وsecret patterns و`git ls-files` للتأكد من عدم وجود cookie files.

للمقارنة التاريخية والإصلاحات، راجع [`../docs/chatgpt-integration-guide.md`](../docs/chatgpt-integration-guide.md) و[`../docs/chatgpt-space.md`](../docs/chatgpt-space.md).
