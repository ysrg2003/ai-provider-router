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

## آخر اختبار مباشر لكل Space

شغّل workflow [`../.github/workflows/chatgpt-spaces-functional.yml`](../.github/workflows/chatgpt-spaces-functional.yml) بالتنفيذ التسلسلي في [run 32222693459](https://github.com/ysrg2003/ai-provider-router/actions/runs/32222693459). كانت النتيجة: النص والبحث نجحا في `chatgpt_space_replica_01` و`chatgpt_space_replica_02`، بينما فشل اختبار الصورة فيهما بـHTTP 503. أما `chatgpt_space`، وهو replica-04، ففشل النص والبحث والصورة كلها بـHTTP 503. لا توجد في التقرير رسالة `Free plan limit` أو `429`، لذلك هذه الجولة لا تشير إلى استنفاد quota؛ الأقرب أنها مشكلة runtime أو browser/session state داخل الـSpace أو upstream ChatGPT.

أعيد اختبار replica-04 منفردًا في النص والبحث فقط بعد أن أعادت endpoints العامة `/` و`/health` و`/docs` HTTP 200، في [run 32224351325](https://github.com/ysrg2003/ai-provider-router/actions/runs/32224351325). بقي النص والبحث عند HTTP 503 بعد نحو 223 ثانية لكل طلب. هذا يفصل المشكلة عن image quota ويثبت أن replica-04 يحتاج فحص logs وStorage State وsession/challenge وتهيئة المتصفح داخل Space قبل تعديل router.

| Space | النص | البحث | الصورة | الدليل |
|---|---|---|---|---|
| replica-01 | نجح | نجح | 503 transient | [32222693459](https://github.com/ysrg2003/ai-provider-router/actions/runs/32222693459) |
| replica-02 | نجح | نجح | 503 transient | [32222693459](https://github.com/ysrg2003/ai-provider-router/actions/runs/32222693459) |
| replica-04 | 503 transient | 503 transient | 503 transient | [32222693459](https://github.com/ysrg2003/ai-provider-router/actions/runs/32222693459)، [إعادة النص/البحث 32224351325](https://github.com/ysrg2003/ai-provider-router/actions/runs/32224351325) |

لا تعني `200` من `/health` أن ChatGPT session داخل المتصفح صالحة؛ فالـhealth يثبت runtime HTTP فقط، بينما اختبار `/v1/chat/completions` يمر عبر browser/session وupstream ChatGPT.

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

## نتائج ما بعد نشر generation recovery

نُشر `browser_gateway.py` المصحح إلى Spaces الثلاثة، ثم شُغّل workflow واحد متسلسل [32240146321](https://github.com/ysrg2003/ai-provider-router/actions/runs/32240146321) مع text وlive search وimage مرة واحدة لكل Space. التقرير الأحمر المنقح محفوظ في [`chatgpt-spaces-functional-32240146321.json`](chatgpt-spaces-functional-32240146321.json). النتيجة الإجمالية: **4 passed و5 failed**.

| Space | النص | البحث الحي | الصورة | تفسير مختصر |
|---|---|---|---|---|
| replica-01 | passed | passed | failed: transient 503 | المساران النصي والبحثي نجحا؛ فشل طلب الصورة بعد 212.19s دون رسالة quota في التقرير. |
| replica-02 | passed | passed | failed: invalid_or_unknown | المساران النصي والبحثي نجحا؛ فشل image payload/contract بعد 269.85s، ويحتاج تفاصيل Space logs أو artifact أعمق قبل نسبته إلى quota. |
| replica-04 | failed: transient 503 | failed: transient 503 | failed: transient 503 | كل السيناريوهات فشلت بعد نحو 240–248s؛ Logs الحية أثبتت أن recovery نفّذ reload عند بقاء generation نشطًا، لكن الطلب الجاري نفسه انتهى timeout. |

هذه الجولة **لا تثبت نجاحًا كاملًا بعد الإصلاح**. هي تثبت أن الإصلاح نُشر وأنه ينفذ recovery في الحالة المستهدفة، كما تثبت أن replica-01 وreplica-02 ينجحان في text/search، لكنها تكشف فشلين متبقيين مختلفين: image failures في 01/02، وsession/upstream أو stabilization failure مستمر في 04. لا توجد في التقرير رسالة `Free plan limit` أو HTTP 429؛ لا ينبغي إعادة طلب الصور قبل تشخيص logs أو انتظار reset خارجي.

لأدلة المتصفح الحية المنقحة، راجع [`browser-evidence-2026-08-19.md`](browser-evidence-2026-08-19.md). وللتفصيل البرمجي للإصلاح، راجع [`chatgpt-generation-recovery.md`](chatgpt-generation-recovery.md). وللمقارنة التاريخية والإصلاحات، راجع [`../docs/chatgpt-integration-guide.md`](../docs/chatgpt-integration-guide.md) و[`../docs/chatgpt-space.md`](../docs/chatgpt-space.md).

## نتائج remediation اللاحقة

بعد إضافة فتح محادثة جديدة فعليًا عبر رابط `New chat`/`دردشة جديدة`، شُغّل workflow شامل واحد [32245401088](https://github.com/ysrg2003/ai-provider-router/actions/runs/32245401088) بالتتابع، وكانت النتيجة **6 passed و3 failed**. نجحت text/search/image في replica-01 وreplica-02، بما في ذلك `mime_type=image/png` وimage payload صالح. بقيت replica-04 فاشلة في الأنواع الثلاثة بحالة transient؛ لذلك لم تُكرر الصور بعد هذه الجولة.

| Space | النص | البحث | الصورة | الدليل |
|---|---|---|---|---|
| replica-01 | passed | passed | passed | [32245401088](https://github.com/ysrg2003/ai-provider-router/actions/runs/32245401088) |
| replica-02 | passed | passed | passed | [32245401088](https://github.com/ysrg2003/ai-provider-router/actions/runs/32245401088) |
| replica-04 | failed: transient | failed: transient | failed: transient | [32245401088](https://github.com/ysrg2003/ai-provider-router/actions/runs/32245401088) |

أُجري بعد ذلك اختبار محدود لـreplica-04 في text/search فقط [32247225620](https://github.com/ysrg2003/ai-provider-router/actions/runs/32247225620)، وفشل كلاهما بعد نحو 268 ثانية. Logs الحية أثبتت أن retry وفتح المحادثة الجديدة يعملان، لكن ChatGPT لا ينتج assistant content في هذه الجلسة.

أُضيف endpoint تشخيص محمي `GET /diagnostics/session`. وهو يعيد إشارات redacted فقط: `ready`، و`input_visible`، وعدد cookies وأسماءها، ووجود login/challenge markers، و`visible_auth_controls`؛ ولا يعيد قيم cookies أو Storage State أو prompts. أظهر التشخيص أن replica-01 وreplica-02 لا تحتويان عناصر auth مرئية، بينما replica-04 أظهرت `visible_auth_controls=["log in"]` مع `ready=true` و`input_visible=true`. هذا يثبت أن replica-04 **جزئية المصادقة أو تحتاج إعادة تسجيل دخول**، وليس أن مشكلة image contract ما زالت في router.

بدل ترك كل طلب replica-04 ينتظر timeout طويلًا، أصبح gateway يوقفه فورًا برسالة `ChatGPT session requires re-authentication; visible auth control detected`. تحقق مباشر واحد أعاد HTTP 503 خلال `2.881228` ثانية، مقابل نحو 268 ثانية سابقًا. هذا إصلاح تشغيلي يمنع الهدر والـretries العمياء، لكنه لا يستطيع تسجيل الدخول إلى حساب ChatGPT الخاص بـreplica-04 تلقائيًا؛ يجب تحديث جلسة ذلك الحساب داخل Space نفسها، مع إبقاء Cookies كل replica مستقلة.

## ما كشفه المتصفح الحي عن الصور

لم أرسل prompt صورة جديدًا في هذه الجولة. في الصفحة الرئيسية ظهر prompt صورة موجود مسبقًا داخل textarea، لكنه لم يكن مرسلًا، ولم تظهر صورة assistant أو generation نشطة. أما عند فتح **المكتبة**، ظهرت أصول PNG مولدة سابقة مثل `Vivid Blue Star on White.png` بحجم 765 KB و`image-gen-1.png` بحجم 817 KB. فتح الأصل أظهر preview كبيرًا فعليًا وأزرارًا مستقلة لـ`تنزيل الصورة` و`مشاركة` و`إزالة`.

الاستنتاج العملي هو أن مسار الصورة المكتملة في ChatGPT هو: إرسال prompt → انتظار اكتمال generation → ظهور أصل مكتبة/preview قابل للتنزيل → استخراج `data_url` أو رابط الصورة داخل جلسة المتصفح. لذلك لا ينبغي اعتبار كل `<img>` في الصفحة صورة مولدة؛ الصفحة الرئيسية قد تحتوي صور واجهة أو avatars. وهذا يفسر لماذا يركز gateway على assistant container وbackend/image candidates، بينما يختبر router النتيجة النهائية بوجود `data_base64` صالح.
