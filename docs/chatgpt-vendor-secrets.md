# دليل Spaces الخاصة بـChatGPT وSecrets

هذا الدليل يشرح **أي Spaces** يستخدمها `ai-provider-router`، وكيف أُنشئت من مصدر `chatgpt-api`، وما الذي يجب وضعه في كل Space وفي router. لا يحتوي على Cookies أو Storage State أو API secret حقيقي.

> `chatgpt-api` ليس OpenAI API رسميًا؛ هو FastAPI + Playwright + Chromium يحول جلسة ChatGPT Web إلى HTTP API متوافق جزئيًا مع شكل OpenAI. قد تتغير واجهة ChatGPT أو شروطها أو حصصها، لذلك لا ينبغي اعتباره تجاوزًا لحدود المزود أو بديلًا رسميًا لـOpenAI.

## 1. ما هي Spaces التي يتحدث عنها router؟

النسخة الحالية من router تعتمد **نسختين مستقلتين فقط**:

| الأولوية | اسم Space الكامل | اسم الـSpace | Base URL | Provider ID في router | الدور |
|---:|---|---|---|---|---|
| 1 | `Yousefsg/chatgpt-api-replica-01` | `chatgpt-api-replica-01` | `https://yousefsg-chatgpt-api-replica-01.hf.space` | `chatgpt_space_replica_01` | المصدر الأول للنص والبحث والصورة |
| 2 | `Yousefsg/chatgpt-api-replica-02` | `chatgpt-api-replica-02` | `https://yousefsg-chatgpt-api-replica-02.hf.space` | `chatgpt_space_replica_02` | fallback مستقل للنص والبحث والصورة |

تظهر هذه المطابقة في [`config/providers.json`](../config/providers.json)، وتظهر الأولوية داخل [`config/models.json`](../config/models.json). لا توجد replica-04 في router الحالي. إبقاء أي Space قديمة على Hugging Face لا يجعلها provider فعالة؛ لا تصبح فعالة إلا إذا أضيفت صراحة إلى config والroutes.

كل Space لها **جلسة ChatGPT Web مستقلة**. لا تنسخ Cookies أو Storage State من Space إلى الأخرى؛ الجلسة والحساب والحصة وحالة التحدي يجب أن تبقى مستقلة.

## 2. من أين جاءت ملفات كل Space؟

المصدر التشغيلي لملفات Space هو مستودع [`ysrg2003/chatgpt-api`](https://github.com/ysrg2003/chatgpt-api)، وليس جذر `ai-provider-router`. في لحظة إعداد هذا الدليل، الـsource revision المثبت هو `2ac0d0e4f07fb78805b81b2633a33d9e3ab45e42`. توجد نسخة runtime مضمنة داخل router في [`vendors/chatgpt-api/`](../vendors/chatgpt-api)، وملفاتها الأساسية (`main.py` و`browser_gateway.py` و`Dockerfile` و`requirements.txt` و`.env.example`) مطابقة للـsource revision من حيث SHA-256؛ استخدم source repository أو هذه النسخة المضمنة، لكن لا تستخدم `Dockerfile` الجذري لـrouter لبناء ChatGPT Space.

كل Space من 01 و02 أُنشئت كنسخة Docker مستقلة من نفس مصدر `chatgpt-api`:

| الجزء | الملف أو المكان | الوظيفة |
|---|---|---|
| FastAPI entrypoint | `main.py` | endpoints مثل `/health` و`/v1/chat/completions` |
| browser gateway | `browser_gateway.py` | Chromium/Playwright، session، text/search/image extraction |
| dependencies | `requirements.txt` | FastAPI وPlaywright وبقية runtime |
| container | `Dockerfile` | تثبيت Chromium/Xvfb وتشغيل المنفذ 7860 |
| environment template | `.env.example` | أسماء Secrets وVariables فقط |
| tests | `tests/` | اختبارات core وHTTP |
| docs | `docs/` | التشغيل والأسرار والتكامل |

الاختلاف المقصود بين النسختين ليس ملفات الكود؛ بل **Space identity وruntime session وSecrets وحالة ChatGPT والحصة**.

## 3. الإنشاء من الصفر — Space-01

نفّذ هذه الخطوات في حساب Hugging Face الذي يملك Space، وفي repository source الذي تريد نشره. لا تضع أي Secret في commit.

### الخطوة 1: إنشاء Space

1. افتح [Hugging Face New Space](https://huggingface.co/new-space) وسجّل الدخول بالحساب المالك.
2. أدخل Owner: `Yousefsg`.
3. أدخل Space name: `chatgpt-api-replica-01`.
4. اختر SDK: **Docker**.
5. اختر visibility المناسبة، ويفضل Private إذا كان الاستخدام شخصيًا.
6. أنشئ Space وانتظر ظهور repository فارغ أو scaffold Docker.

النتيجة المتوقعة أن يظهر repository:

```text
https://huggingface.co/spaces/Yousefsg/chatgpt-api-replica-01
```

### الخطوة 2: نشر مصدر chatgpt-api

من clone مصدر `ysrg2003/chatgpt-api`، ثبّت revision المعروف ثم ادفع محتوى المصدر إلى فرع `main` في Space-01. يجب أن تكون ملفات `Dockerfile` و`main.py` و`browser_gateway.py` و`requirements.txt` في جذر Space:

```bash
git clone https://github.com/ysrg2003/chatgpt-api.git
cd chatgpt-api
git checkout 2ac0d0e4f07fb78805b81b2633a33d9e3ab45e42
git remote add space01 https://huggingface.co/spaces/Yousefsg/chatgpt-api-replica-01.git
git push space01 HEAD:main
```

بهذا الأمر يجد المستخدم الملفات من GitHub source فعليًا: `main.py` و`browser_gateway.py` و`Dockerfile` و`requirements.txt` و`.env.example`، ثم يرفعها إلى repository الخاص بـSpace-01.

إذا كان remote يتطلب مصادقة، استخدم Hugging Face CLI أو Git credential manager محليًا. لا تضع Access Token داخل remote URL أو commit أو log. بعد الدفع، افتح تبويب **Logs** في Space وانتظر Docker build.

### الخطوة 3: إضافة Secrets إلى Space-01

افتح Space-01 ثم **Settings → Variables and secrets → Secrets → New secret** وأضف:

| الاسم | القيمة | الوظيفة |
|---|---|---|
| `API_SECRET_KEY` | قيمة عشوائية طويلة، placeholder: `<space-01-api-secret>` | Bearer token الذي يحمي HTTP API |
| `CHATGPT_COOKIES_NETSCAPE` | export Cookies للحساب المصرح به في Space-01 | جلسة ChatGPT Web التي يستخدمها Chromium |

إذا كان source يدعم `CHATGPT_STORAGE_STATE_JSON` بدل cookies، استخدمه فقط وفق دليل source، وفي Space-01 نفسها. لا تضع القيمتين في router ولا في Git.

أنشئ secret عشوائيًا محليًا دون طباعته في logs، مثل:

```bash
openssl rand -hex 32
```

انسخ الناتج مباشرة إلى خانة Secret، ثم خزّنه في مدير أسرار router باسم `CHATGPT_API_SECRET_KEY` فقط إذا كانت Space تقبل هذه القيمة.

### الخطوة 4: readiness لـSpace-01

بعد اكتمال build، نفّذ من terminal:

```bash
curl -fsS https://yousefsg-chatgpt-api-replica-01.hf.space/health
```

النجاح المتوقع JSON يحتوي `ready: true`. ظهور `initializing` يعني أن Chromium لم يجهز بعد. ظهور `503` مع جلسة غير جاهزة يعني أن cookies/session أو runtime تحتاج معالجة؛ لا تغيّر router قبل فحص Logs الخاصة بـSpace-01.

## 4. الإنشاء من الصفر — Space-02

Space-02 نسخة مستقلة من **نفس source revision**، لكن لا تعيد استخدام session.

### الخطوة 1: إنشاء Space-02

1. افتح [Hugging Face New Space](https://huggingface.co/new-space).
2. استخدم Owner: `Yousefsg`.
3. استخدم Space name: `chatgpt-api-replica-02`.
4. اختر SDK: **Docker** والـvisibility المناسبة.
5. أنشئ Space وانتظر repository.

النتيجة المتوقعة:

```text
https://huggingface.co/spaces/Yousefsg/chatgpt-api-replica-02
```

### الخطوة 2: نشر نفس المصدر بنفس revision

استخدم clone مصدر `chatgpt-api` نفسه، وثبّت **نفس commit `2ac0d0e4f07fb78805b81b2633a33d9e3ab45e42`** الذي نشرته في Space-01، ثم ادفعه إلى Space-02:

```bash
cd chatgpt-api
git checkout 2ac0d0e4f07fb78805b81b2633a33d9e3ab45e42
git remote add space02 https://huggingface.co/spaces/Yousefsg/chatgpt-api-replica-02.git
git push space02 HEAD:main
```

لا تنشئ ملفات مختلفة للنسخة الثانية؛ الاختلاف المقصود هو Space repository والـSecrets والجلسة، لا source code.

لا تستخدم `git push --force` إلا إذا كنت تملك قرار rollback واضحًا؛ الدفع العادي يجعل تاريخ Space قابلًا للمراجعة.

### الخطوة 3: إضافة Secrets مستقلة

في Space-02 افتح **Settings → Variables and secrets → Secrets** وأضف:

| الاسم | القيمة | القاعدة |
|---|---|---|
| `API_SECRET_KEY` | `<space-02-api-secret>` | يمكن أن تكون مستقلة عن Space-01 |
| `CHATGPT_COOKIES_NETSCAPE` | cookies جديدة للحساب المصرح به لـSpace-02 | لا تنسخ cookies من Space-01 |

إذا استخدمت `CHATGPT_STORAGE_STATE_JSON`، أنشئه أو صدّره للحساب نفسه الذي ستشغله في Space-02. لا تضع session state في router.

### الخطوة 4: readiness لـSpace-02

```bash
curl -fsS https://yousefsg-chatgpt-api-replica-02.hf.space/health
```

لا تعتبر Space-02 جاهزة لمجرد اكتمال Docker build؛ يجب أن تعيد `/health` `ready: true` ثم ينجح text smoke مصادق عليه.

## 5. إذا كان المصدر لديك من داخل ai-provider-router

إذا لم ترد clone مستودع `chatgpt-api` مباشرة، يمكنك استخدام النسخة المضمنة المطابقة لملفات runtime. انسخ **محتوى** `vendors/chatgpt-api` إلى مجلد مؤقت مستقل، ثم أنشئ له Git history وادفعه إلى Space؛ لا ترفع مجلد `vendors/chatgpt-api` كطبقة داخل Space ولا تستخدم Dockerfile الجذري للrouter:

```bash
rm -rf /tmp/chatgpt-space-source
git clone https://github.com/ysrg2003/ai-provider-router.git /tmp/router-source
mkdir -p /tmp/chatgpt-space-source
cp -a /tmp/router-source/vendors/chatgpt-api/. /tmp/chatgpt-space-source/
cd /tmp/chatgpt-space-source
git init
git add .
git commit -m "Import chatgpt-api runtime source"
git remote add space01 https://huggingface.co/spaces/Yousefsg/chatgpt-api-replica-01.git
git push space01 HEAD:main
```

لـSpace-02 كرر من نفس source snapshot إلى remote `space02`. يُفضّل دائمًا pin source commit ومراجعة SHA-256 قبل الدفع:

```bash
sha256sum main.py browser_gateway.py Dockerfile requirements.txt .env.example
```

## 6. ربط Space-01 وSpace-02 بالrouter

`config/providers.json` يربط كل Space بـprovider ID وkey pool وtimeout:

```json
{
  "id": "chatgpt_space_replica_01",
  "kind": "chatgpt_space",
  "base_url_env": "CHATGPT_API_REPLICA_01_BASE_URL",
  "key_pool": "chatgpt_space_default",
  "default_timeout_seconds": 540
}
```

Base URL هو origin فقط، بلا `/v1` أو `/v1/chat/completions`:

```dotenv
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
```

في الإعداد الحالي يستخدم providerان pool باسم `chatgpt_space_default`. أبسط إعداد هو أن تقبل Space-01 وSpace-02 نفس قيمة `API_SECRET_KEY`، ثم تضعها في router باسم:

```dotenv
CHATGPT_API_SECRET_KEY=<same-router-space-secret>
```

أو:

```dotenv
AI_ROUTER_CHATGPT_KEYS_JSON=["<same-router-space-secret>"]
```

إذا أردت Secret مختلفًا لكل Space، لا تضع القيمتين عشوائيًا في pool مشترك؛ لأن router الحالي يربط Space-01 وSpace-02 بنفس key pool وقد يجرب key غير مناسب على Space أخرى. عند اختلاف secrets يلزم فصل key pools/provider config واختبار ذلك كتغيير هندسي مستقل.

## 7. التحقق لكل Space ثم التحقق من fallback

تحقق من كل طبقة منفصلة:

| الاختبار | Space-01 | Space-02 | ماذا يثبت |
|---|---|---|---|
| `GET /health` | `ready: true` | `ready: true` | runtime وChromium جاهزان |
| text call | response غير فارغ | response غير فارغ | session وAPI secret صالحان |
| search call | نص ومصدر | نص ومصدر | grounding والطلب الخارجي |
| image call | `images[]` وbytes قابلة للفك | `images[]` وbytes قابلة للفك | generation/extraction؛ يستهلك quota |

ابدأ بالنص ثم البحث. لا ترسل image request إلا عند الحاجة، وبحد أقصى طلب واحد لكل Space في smoke مقيد. HTTP 200 وحده لا يثبت الصورة؛ يجب فحص `images[]` وMIME والأبعاد، ورسالة Free-plan limit تعني quota خارجية لا خطأ Base URL.

أمر router للنص:

```bash
CHATGPT_API_SECRET_KEY="$CHATGPT_API_SECRET_KEY" \
ai-router --config-dir config --state-db /tmp/chatgpt-text.db \
  call-auto --output-type text --providers chatgpt \
  --operation chatgpt_text \
  --user "قل فقط: نجح اختبار النص"
```

للاختبار دون network:

```bash
ai-router --config-dir config route-plan \
  --output-type text --providers chatgpt \
  --user "اكتب إجابة قصيرة"
```

## 8. بطاقات أسرار وVariables الـSpace

### `API_SECRET_KEY`

هو Bearer secret الخاص بـHTTP gateway داخل كل Space. أنشئه كقيمة عشوائية طويلة، خزّنه في Space Secret، ثم اجعل router يستخدم القيمة المطابقة عبر `CHATGPT_API_SECRET_KEY` أو pool. لا علاقة له بـChatGPT cookies.

التحقق: `401/403` يعني أن القيمة لا تطابق ما في Space أو أن header غير صحيح. التدوير: أنشئ قيمة جديدة، حدّث Space ثم router، اختبر، ثم ألغِ القديمة.

### `CHATGPT_COOKIES_NETSCAPE`

هو session credential لحساب ChatGPT Web داخل Space فقط. صدّر cookies من متصفح مصرح به بصيغة Netscape، خزّنها في Space Secret، ولا تنقلها إلى router. عند `session expired` أو `re-auth required` حدّثها داخل Space نفسها، ولا تعالج المشكلة بتغيير Base URL.

### `CHATGPT_STORAGE_STATE_JSON`

بديل session state إذا كان source مضبوطًا عليه. يبقى داخل Space Secret، وقد يحتوي tokens/session metadata. لا تضعه في Git أو router أو issue أو artifact.

### Variables runtime

`PORT=7860`، `CHATGPT_HEADLESS=true`، `CHATGPT_READY_TIMEOUT=180`، `CHATGPT_REQUEST_TIMEOUT=210`، `MAX_PROMPT_CHARS=50000`، `RATE_LIMIT_REQUESTS=20`، `RATE_LIMIT_WINDOW_SECONDS=60`، `LOG_LEVEL=INFO`، و`ALLOWED_ORIGINS` الفارغ افتراضيًا. هذه Variables تشغيلية وليست أسرارًا، لكن لا ترفع rate limits بلا حساب للحمل.

## 9. التدوير والإلغاء والاستعادة

عند تعرض `API_SECRET_KEY`: غيّر القيمة في Space، حدّث router Secret، أعد التشغيل، نفّذ text smoke، ثم افحص logs. عند تعرض cookies أو Storage State: ألغِ جلسات ChatGPT المتأثرة أو سجّل الخروج، صدّر session جديدة من الحساب الصحيح، استبدل Space Secret، ثم أعد تشغيل Space.

إذا فشلت Space-01 فقط، يبقى Space-02 fallback في route. إذا فشلتا بسبب quota أو session، ينتقل router إلى providers الأخرى عندما يكون model route مؤهلًا. لا تعتبر fallback دليلًا على أن Space الفاشلة سليمة.

## 10. مراجع المصدر

[1]: [chatgpt-api README](../vendors/chatgpt-api/README.md)
[2]: [chatgpt-api environment template](../vendors/chatgpt-api/.env.example)
[3]: [router providers config](../config/providers.json)
[4]: [router key pools config](../config/key_pools.json)
[5]: [ChatGPT integration guide](chatgpt-integration-guide.md)
[6]: https://huggingface.co/docs/hub/spaces-overview "Hugging Face Spaces overview"
[7]: https://huggingface.co/docs/hub/spaces-overview#managing-secrets "Hugging Face Space secrets"
