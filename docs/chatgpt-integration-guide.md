# دليل تكامل ChatGPT مع ai-provider-router

هذا الدليل يشرح استخدام `chatgpt-api` كمصدر HTTP أول داخل `ai-provider-router`، من إعداد Spaces والأسرار إلى أول طلب نص، بحث حي، وصورة. المسار المعتمد هو HTTP بين router وHugging Face Spaces؛ لا يشغل router Chromium ولا يقرأ Cookies ChatGPT.

> `chatgpt-api` ليس OpenAI API رسميًا. هو خدمة أتمتة لجلسة ChatGPT Web، وقد تتغير واجهة ChatGPT أو شروطها أو حصصها. استخدمه في بيئة تملك حق تشغيلها، ولا تستخدمه لتجاوز حدود أو ضوابط المزود.

## 1. النتيجة النهائية

بعد إعداد هذا الدليل، يستطيع router استقبال طلب واحد واختيار ChatGPT replicas بالترتيب التالي:

| الأولوية | Provider ID | Space | Base URL |
|---:|---|---|---|
| 1 | `chatgpt_space_replica_01` | `Yousefsg/chatgpt-api-replica-01` | `https://yousefsg-chatgpt-api-replica-01.hf.space` |
| 2 | `chatgpt_space_replica_02` | `Yousefsg/chatgpt-api-replica-02` | `https://yousefsg-chatgpt-api-replica-02.hf.space` |
| 3 | `chatgpt_space` | `Yousefsg/chatgpt-api-replica-04` | `https://yousefsg-chatgpt-api-replica-04.hf.space` |

عند فشل المصدر الأول، ينتقل router إلى الثاني ثم الثالث وفق سياسة `max_attempts` وcooldown. عند نجاح المصدر الأول لا يُرسل الطلب نفسه إلى البقية، حتى لا تتكرر الرسالة أو تُستهلك الحصة ثلاث مرات.

## 2. المتطلبات

| المتطلب | مطلوب؟ | أين يستخدم؟ |
|---|---:|---|
| Python 3.11+ | نعم | router والاختبارات |
| `requests` و`python-dotenv` | نعم | adapter والتهيئة |
| ثلاث Spaces جاهزة أو Space واحدة | نعم | مصادر ChatGPT HTTP |
| `API_SECRET_KEY` في كل Space | نعم | مصادقة router مع Space |
| `CHATGPT_COOKIES_NETSCAPE` في كل Space | نعم للتشغيل الحقيقي | جلسة ChatGPT داخل Space فقط |
| Hugging Face Access Token | للإدارة فقط | إنشاء/رفع/ضبط Space، وليس runtime API |
| GitHub repository | اختياري | CI والإصدارات |

تستخدم Docker Spaces موارد compute. راجع شروط خطة Hugging Face الحالية قبل إنشاء أو تكرار Docker Space؛ توضح الوثائق الرسمية أن إنشاء Docker أو Gradio Space مرتبط بخطة الحساب/المؤسسة [1].

## 3. كيف يعمل التكامل

يقرأ `RouterConfig` المزودات من `config/providers.json`، ويقرأ المفاتيح من `config/key_pools.json`. يربط كل provider بـ`ChatGPTSpaceAdapter` مستقل، لذلك لكل replica عنوان مختلف، بينما يمكنها مشاركة key pool نفسه إذا كانت Secrets متطابقة.

| المفهوم | المعنى في هذا المشروع |
|---|---|
| Provider | Space يستقبل HTTP request |
| Model | قيمة `gpt-4o-mini` التي يرسلها router إلى عقد Space |
| Key pool | Secrets مرتبة تستخدمها providers الثلاثة |
| Route | ترتيب providers لمسار text/search/image |
| Cooldown | إيقاف مؤقت لمفتاح أو provider بعد فشل قابل للتسجيل |
| State DB | SQLite يسجل النجاح والفشل والـcursor دون حفظ Cookies |

مسارات النص والبحث لا تستخدم HTML أو image extraction. مسار الصورة فقط يقبل `images[].data_url` أو `images[].src` بعد التحقق من أنها صورة مولدة، ويرفض favicon وavatar والصور القديمة.

### Base URLs: مكانها الصحيح في router

على عكس `chatgpt-api`، فإن `ai-provider-router` عميل يتصل بالـSpaces؛ لذلك يحتاج إلى معرفة عناوينها. هذه العناوين **ليست Secrets**، وتُضبط كـVariables مستقلة، واحد لكل replica:

```dotenv
CHATGPT_API_REPLICA_01_BASE_URL=https://OWNER-REPLICA-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://OWNER-REPLICA-02.hf.space
CHATGPT_API_BASE_URL=https://OWNER-REPLICA-04.hf.space
```

يقرأ router المتغير إذا كان موجودًا، وإلا يستخدم `base_url` الافتراضي المطابق في `config/providers.json`. يجب أن تكون القيمة origin فقط دون `/v1` أو `/v1/chat/completions`:

```text
صحيح: https://OWNER-SPACE.hf.space
خطأ:   https://OWNER-SPACE.hf.space/v1/chat/completions
```

| القيمة | مكانها |
|---|---|
| `API_SECRET_KEY` | Secret داخل Space المقابلة |
| `CHATGPT_COOKIES_NETSCAPE` | Secret داخل Space فقط |
| `CHATGPT_API_REPLICA_01_BASE_URL` | Variable في router |
| `CHATGPT_API_REPLICA_02_BASE_URL` | Variable في router |
| `CHATGPT_API_BASE_URL` | Variable في router |
| `CHATGPT_API_SECRET_KEY` | Secret في router، ويطابق `API_SECRET_KEY` في Space |

فحص العناوين لا يحتاج إلى Secret:

```bash
for url in "$CHATGPT_API_REPLICA_01_BASE_URL" "$CHATGPT_API_REPLICA_02_BASE_URL" "$CHATGPT_API_BASE_URL"; do
  curl -fsS "$url/health"
done
```

## 4. جرد الملفات

| الملف | الوظيفة |
|---|---|
| `config/providers.json` | الثلاثة Base URLs والـprovider IDs والمهل |
| `config/key_pools.json` | أسماء متغيرات الأسرار وسياسة التدوير |
| `config/models.json` | ترتيب replicas في routes |
| `.env.example` | أسماء المتغيرات غير السرية وplaceholders |
| `src/ai_router/config.py` | تحميل providers وkeys والتحقق منها |
| `src/ai_router/providers/chatgpt_space.py` | HTTP adapter للنص والبحث والصورة |
| `src/ai_router/router.py` | fallback والـcooldown وتسجيل الحالة |
| `vendors/chatgpt-api/` | نسخة المصدر المطابقة لـchatgpt-api release |
| `docs/chatgpt-space.md` | التفاصيل التشغيلية المتخصصة |
| `tests/test_multiroute.py` | اختبارات adapter وترتيب routes |

## 5. إعداد Spaces قبل إعداد router

كل Space يجب أن يحتوي نسخة `chatgpt-api` وأن يكون runtime جاهزًا على `/health`. في Hugging Face:

1. افتح صفحة Space.
2. اختر **Settings**.
3. افتح **Variables and secrets**.
4. ضع القيم الحساسة في **Secrets** والقيم العامة في **Variables**.
5. بعد تغيير Secret، أعد تشغيل Space وانتظر `RUNNING` ثم `ready: true`.

Hugging Face يوضح أن Variables عامة وقد تُنسخ عند duplicate، بينما Secrets خاصة ولا تُنسخ قيمها تلقائيًا [1].

### فحص Space

```bash
export CHATGPT_API_BASE_URL="https://yousefsg-chatgpt-api-replica-01.hf.space"
curl -fsS "$CHATGPT_API_BASE_URL/health"
```

النجاح المتوقع:

```json
{"status":"running","ready":true,"service":"chatgpt-web-api"}
```

إذا أعاد `/health` `503`، افحص build/runtime وCookies قبل تعديل router.

## 6. بطاقة `API_SECRET_KEY` داخل كل Space

**Exact name:** `API_SECRET_KEY`.

**Classification:** Secret.

**Required or optional:** مطلوب لاستدعاء endpoints المحمية.

**Used by:** `chatgpt-api/main.py` لمقارنة `Authorization: Bearer ...`.

**Where to obtain it:** لا يأتي من Hugging Face ولا OpenAI. أنشئ قيمة عشوائية طويلة على جهازك:

```bash
openssl rand -hex 32
```

**Safe placeholder:**

```text
REPLACE_WITH_SPACE_HTTP_SECRET
```

**Where to store it:** Hugging Face Space → **Settings → Variables and secrets → Secrets** → الاسم `API_SECRET_KEY`.

**Minimal verification:**

```bash
curl -fsS "$CHATGPT_API_BASE_URL/v1/models" \
  -H "Authorization: Bearer $CHATGPT_API_SECRET_KEY"
```

**Expected success:** HTTP 200 وقائمة models. HTTP 401 يعني mismatch أو ترويسة ناقصة.

**Rotation:** أنشئ قيمة جديدة في كل Space، حدّث router Secret، اختبر، ثم ألغِ القيمة القديمة. إذا كانت replicas الثلاثة تستخدم القيمة نفسها، يجب تحديثها في الثلاثة معًا.

**Exposure recovery:** بدّل القيمة فورًا، راجع logs وGit history وActions artifacts، ثم احذف القيمة المكشوفة من كل مكان.

## 7. بطاقة `CHATGPT_COOKIES_NETSCAPE` داخل كل Space

**Exact name:** `CHATGPT_COOKIES_NETSCAPE`.

**Classification:** Session Secret عالي الخطورة.

**Required or optional:** مطلوب لتفاعل ChatGPT الحقيقي.

**Used by:** Playwright داخل Space؛ لا يقرأه router.

**How to obtain it:**

1. افتح [chatgpt.com](https://chatgpt.com) وسجّل الدخول بالحساب الذي تملك حق استخدامه.
2. استخدم أداة محلية موثوقة لتصدير Cookies للموقع بصيغة Netscape/cookies.txt.
3. لا ترفع ملف Cookies إلى خدمة تحويل أو repository.
4. الصق المحتوى في Secret باسم `CHATGPT_COOKIES_NETSCAPE` داخل Space المناسب.
5. احذف ملف التصدير المحلي أو احفظه في vault مشفر بعد نجاح الاختبار.

**Safe format:**

```text
# Netscape HTTP Cookie File
.example.com	TRUE	/	TRUE	0	COOKIE_NAME	REPLACE_WITH_COOKIE_VALUE
```

**Verification:**

```bash
curl -fsS "$CHATGPT_API_BASE_URL/health"
```

`ready: true` يثبت جاهزية التطبيق والمتصفح، ثم نفذ نصًا قصيرًا لإثبات صلاحية الجلسة.

**Failures:** login page أو `Locator.click` timeout يعني أن session غير صالحة أو واجهة ChatGPT تغيرت. صدّر Cookies جديدة وأعد التشغيل. لا تحاول إصلاح ذلك بتغيير router API key فقط.

**Revocation:** سجّل الخروج من ChatGPT أو ألغِ الجلسة، ثم استبدل Secret. عند exposure اعتبر الحساب مكشوفًا ودوّر Cookies و`API_SECRET_KEY` معًا.

## 8. بطاقة Hugging Face Access Token

**Purpose:** إدارة Hub فقط، مثل clone/push وتحديث Secrets وإعادة التشغيل.

**Classification:** Secret.

**Not used for:** مصادقة `/v1/chat/completions`. هذا endpoint يحتاج `API_SECRET_KEY` الخاص بـSpace.

**How to obtain it:**

1. افتح [Settings → Access Tokens](https://huggingface.co/settings/tokens).
2. أنشئ User Access Token.
3. اختر read للقراءة فقط، أو write عند الحاجة إلى push/create/update؛ توصي Hugging Face بأقل صلاحية ممكنة [2].
4. استخدم `hf auth login` بدل كتابة token في URL أو command history.

```bash
hf auth login
hf auth whoami
```

**Rotation/revocation:** من صفحة Access Tokens احذف token القديم وأنشئ آخر بصلاحية أقل. لا تضف `HF_TOKEN` إلى `config/` أو `.env` المتعقب.

## 9. بطاقة `CHATGPT_API_SECRET_KEY` في router

**Exact name:** `CHATGPT_API_SECRET_KEY`.

**Classification:** Secret.

**Purpose:** fallback key pool عندما لا توجد `AI_ROUTER_CHATGPT_KEYS_JSON` أو تكون `[]`.

**Where to store:** `.env` المحلي غير المتعقب، GitHub Actions Secret، أو مدير أسرار deployment.

**Safe setup:**

```bash
export CHATGPT_API_SECRET_KEY="REPLACE_WITH_API_SECRET_KEY_FROM_SPACE"
```

لا تضع Cookies هنا. Router لا يحتاج `CHATGPT_COOKIES_NETSCAPE`.

**Verification without printing:**

```bash
ai-router --config-dir config --state-db /tmp/chatgpt-summary.db summary
```

يجب أن يعرض provider IDs وعدد المفاتيح فقط دون القيم.

**Common failures:** 401 من Space يعني أن القيمة لا تطابق `API_SECRET_KEY` في Space. إذا نجح replica-01 وفشل replica-02، راجع Secret الخاص بالنسخة الثانية وحدها.

## 10. بطاقة `AI_ROUTER_CHATGPT_KEYS_JSON`

**Purpose:** مجموعة Secrets مرتبة. Router يحاول العناصر بالترتيب ويسجل cooldown لكل provider/key.

**Classification:** Secret JSON.

**Safe format:**

```json
[
  {"id":"replica-01-key","key":"REPLACE_WITH_SECRET_01","project":"chatgpt"},
  {"id":"replica-02-key","key":"REPLACE_WITH_SECRET_02","project":"chatgpt"}
]
```

ضع JSON في `.env` أو GitHub Actions Secret، وليس `config/key_pools.json`. عند وجود مصفوفة غير فارغة، يقرأها router بدل fallback. لا تستخدم Cookies داخلها.

**Validation:**

```bash
python -m json.tool <<< "$AI_ROUTER_CHATGPT_KEYS_JSON" >/dev/null
ai-router --config-dir config --state-db /tmp/chatgpt-summary.db summary
```

إذا ظهر JSON error، افحص الاقتباسات والأقواس ولا تطبع القيمة في log.

## 11. بطاقات Base URLs

| الاسم | النوع | default | consumer | effect |
|---|---|---|---|---|
| `CHATGPT_API_REPLICA_01_BASE_URL` | URL | عنوان replica-01 | provider `chatgpt_space_replica_01` | يبدل عنوان النسخة الأولى |
| `CHATGPT_API_REPLICA_02_BASE_URL` | URL | عنوان replica-02 | provider `chatgpt_space_replica_02` | يبدل عنوان النسخة الثانية |
| `CHATGPT_API_BASE_URL` | URL | عنوان replica-04 | provider `chatgpt_space` | يحافظ على التوافق القديم ويشير إلى النسخة الثالثة |

القيم ليست أسرارًا، ويُسمح بوجودها في `.env.example` وGit. يجب أن تكون Base URL دون `/v1` لأن adapter يضيف `/v1/chat/completions`.

### بطاقات المتغيرات التفصيلية

#### `CHATGPT_API_REPLICA_01_BASE_URL`

| الحقل | القيمة |
|---|---|
| Type / default | URL string / عنوان replica-01 في `providers.json` |
| Allowed values | HTTPS origin ينتهي بـ`.hf.space` أو endpoint متوافق؛ دون `/v1` |
| Set location | `.env` أو GitHub Actions Variable أو deployment environment |
| Consumer / effect | provider `chatgpt_space_replica_01`؛ يحدد أول Space في fallback |
| Safe example | `CHATGPT_API_REPLICA_01_BASE_URL=https://OWNER-SPACE.hf.space` |
| Verification | `curl -fsS "$CHATGPT_API_REPLICA_01_BASE_URL/health"` يعيد readiness JSON |
| Common mistake | وضع `/v1/chat/completions` داخل القيمة؛ احذفه لأن adapter يضيف المسار |

#### `CHATGPT_API_REPLICA_02_BASE_URL`

| الحقل | القيمة |
|---|---|
| Type / default | URL string / عنوان replica-02 في `providers.json` |
| Allowed values | HTTPS origin ينتهي بـ`.hf.space` أو endpoint متوافق؛ دون `/v1` |
| Set location | `.env` أو GitHub Actions Variable أو deployment environment |
| Consumer / effect | provider `chatgpt_space_replica_02`؛ يستخدم بعد فشل الأولى |
| Safe example | `CHATGPT_API_REPLICA_02_BASE_URL=https://OWNER-SPACE.hf.space` |
| Verification | نفذ health check للعنوان وتحقق من أن النسخة الثانية هي المقصودة |
| Common mistake | نسخ عنوان replica-01 بالخطأ؛ قارنه باسم Space في Hugging Face |

#### `CHATGPT_API_BASE_URL`

| الحقل | القيمة |
|---|---|
| Type / default | URL string / عنوان replica-04 المتوافق قديمًا |
| Allowed values | HTTPS origin دون `/v1` |
| Set location | `.env` أو GitHub Actions Variable أو deployment environment |
| Consumer / effect | provider `chatgpt_space`؛ يمثل النسخة الثالثة/fallback الأخير |
| Safe example | `CHATGPT_API_BASE_URL=https://OWNER-SPACE.hf.space` |
| Verification | `curl -fsS "$CHATGPT_API_BASE_URL/health"` ثم طلب `/v1/models` بمفتاح مناسب |
| Common mistake | حذف المتغير لأن اسم provider لا يحتوي `replica-04`؛ سيترك fallback الأخير بلا عنوان صحيح |

التحقق:

```bash
for url in \
  https://yousefsg-chatgpt-api-replica-01.hf.space \
  https://yousefsg-chatgpt-api-replica-02.hf.space \
  https://yousefsg-chatgpt-api-replica-04.hf.space; do
  curl -fsS "$url/health"
done
```

## 12. التثبيت والتشغيل من صفر

```bash
git clone https://github.com/ysrg2003/ai-provider-router.git
cd ai-provider-router
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

ضع في `.env`:

```dotenv
CHATGPT_API_BASE_URL=https://yousefsg-chatgpt-api-replica-04.hf.space
CHATGPT_API_REPLICA_01_BASE_URL=https://yousefsg-chatgpt-api-replica-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://yousefsg-chatgpt-api-replica-02.hf.space
CHATGPT_API_SECRET_KEY=REPLACE_WITH_SPACE_SECRET
AI_ROUTER_CHATGPT_KEYS_JSON=[]
AI_ROUTER_CONFIG_DIR=config
AI_ROUTER_STATE_DB=data/ai_router.db
```

تأكد أن `.env` غير متعقب:

```bash
git ls-files .env
```

## 13. معرفة ترتيب router دون طلب حي

```bash
ai-router --config-dir config --state-db /tmp/chatgpt-plan.db \
  route-plan --user "أنشئ صورة عن مكتبة مستقبلية"
```

النتيجة المتوقعة أن أول ثلاثة providers هي:

```text
chatgpt_space_replica_01
chatgpt_space_replica_02
chatgpt_space
```

## 14. أول طلب نص

```bash
CHATGPT_API_SECRET_KEY="REPLACE_WITH_SPACE_SECRET" \
ai-router --config-dir config --state-db /tmp/router-text.db \
  call-auto --output-type text \
  --operation replica_text \
  --user "قل فقط: نجح اختبار router"
```

النجاح هو JSON يحتوي `output_type: text` و`route: text` ونصًا غير فارغ. إذا فشل replica-01، يفحص router error ثم يجرب replica-02 وفق policy.

## 15. البحث الحي

```bash
CHATGPT_API_SECRET_KEY="REPLACE_WITH_SPACE_SECRET" \
ai-router --config-dir config --state-db /tmp/router-search.db \
  call-auto --output-type text --grounding search \
  --operation replica_search \
  --system "أجب بالعربية واذكر المصادر، ولا تخترع مصدرًا." \
  --user "ابحث عن آخر أخبار نماذج الذكاء الاصطناعي"
```

Router يمرر أداة `google_search` إلى adapter، ويتعرف عليها ويضيف `ابحث في الويب بحث حي:` إلى الرسالة. الناتج النصي ليس ضمانًا لصحة المصادر؛ افحص الروابط والادعاءات قبل الاستخدام الحساس.

## 16. توليد الصورة

```bash
CHATGPT_API_SECRET_KEY="REPLACE_WITH_SPACE_SECRET" \
ai-router --config-dir config --state-db /tmp/router-image.db \
  call-auto --output-type image \
  --operation replica_image \
  --user "generate image of a wise stickman reading a book in a library"
```

النجاح هو `output_type: image` و`mime_type: image/png` و`data_base64` كبير قابل للفك. لا تعتبر النص وحده صورة. يضع adapter مهلة طويلة وإعادة محاولة محدودة عند غياب `images`، لكنه يتوقف عند رسالة quota وينتقل إلى المصدر التالي.

لفك صورة محفوظة في JSON:

```bash
python - <<'PY'
import base64, json
from pathlib import Path
body = json.loads(Path("router-image.json").read_text())
encoded = body["data_base64"]
Path("router-image.png").write_bytes(base64.b64decode(encoded))
PY
file router-image.png
```

## 17. الاستدعاء البرمجي من مشروع آخر

الحد الموصى به بين مشروع آخر وrouter هو CLI أو HTTP، وليس نسخ Playwright. مثال Python يستدعي CLI ويحفظ JSON دون طباعة Secret:

```python
import json
import os
import subprocess

cmd = [
    "ai-router", "--config-dir", "config",
    "--state-db", "/tmp/host-router.db",
    "call-auto", "--output-type", "text",
    "--user", "قل فقط: نجح التكامل",
]
env = os.environ.copy()
env["CHATGPT_API_SECRET_KEY"] = "REPLACE_WITH_SPACE_SECRET"
result = subprocess.run(cmd, env=env, check=True, text=True, capture_output=True)
payload = json.loads(result.stdout)
assert payload["output_type"] == "text"
assert payload["text"]
```

في مشروع آخر، يجب تثبيت commit أو release، وتوفير `config/` و`src/` أو تثبيت الحزمة، وتحديد `state_db` مستقل، وإخفاء Secret من logs. لا تنسخ Cookies إلى المشروع المضيف.

## 18. GitHub Actions

في repository `ysrg2003/ai-provider-router`:

1. افتح **Settings → Secrets and variables → Actions**.
2. اختر **Secrets → New repository secret**.
3. أضف `CHATGPT_API_SECRET_KEY` أو `AI_ROUTER_CHATGPT_KEYS_JSON`.
4. أضف Base URLs كـVariables فقط إذا أردت override؛ لا تحتاج إلى وضعها كSecrets.
5. شغّل workflow bounded، ثم افحص artifact/JSON لا اللون الأخضر وحده.

GitHub يوضح أن Secrets تُستخدم عبر context `secrets` داخل workflow، ولا تُمرر من forked workflows عادةً [3]. لا تضع Cookie session أو `CHATGPT_STORAGE_STATE_JSON` في workflow إلا بعد مراجعة أمنية صريحة؛ الأفضل أن تظل داخل Space الحساب المطابق لها. router يحتاج فقط `CHATGPT_API_SECRET_KEY` أو key pool، ولا يحتاج Cookies أو Storage State.

### Storage State عند فشل Netscape Cookies

إذا ظهرت `Just a moment...` أو `Your session has expired` داخل Space رغم أن Chrome الحي يعمل، صدّر Playwright Storage State من Profile اختباري صالح وضعه في Secret `CHATGPT_STORAGE_STATE_JSON` داخل **Space نفسها**. إذا كان Storage State صالحًا، يستخدمه `chatgpt-api` بدل `CHATGPT_COOKIES_NETSCAPE`. لا تضع هذا JSON في `ai-provider-router`، ولا تشارك State حساب `sg` مع `pn2003` أو `ben2003`؛ لكل replica حساب وجلسة منفصلان.

يجب إثبات النجاح بطلب نص يعيد Assistant response، لا بمجرد ظهور composer. بعد نجاح النص يمكن اختبار البحث، أما اختبار الصورة فيستهلك حصة ChatGPT اليومية وقد يفشل بـ429 حتى عندما تكون الخدمة والجلسة سليمتين.

## 19. الاختبارات

```bash
PYTHONPATH=src python -m compileall -q src tests vendors/chatgpt-api
PYTHONPATH=src python -m unittest discover -s tests -v
python -m json.tool config/providers.json >/dev/null
python -m json.tool config/models.json >/dev/null
```

الاختبارات offline لا تستهلك ChatGPT quota. الاختبار الحي للنص والبحث يستهلك messages/search، واختبار الصورة يستهلك image quota.

## 20. التزامن والـfallback والحدود

يمكن للrouter استقبال عدة عمليات، لكن كل Space مبنية حول جلسة ChatGPT واحدة وقفل واحد. لا يعني وجود ثلاثة providers أن الطلب نفسه يرسل ثلاث مرات بالتوازي. يستخدم router أول replica ناجحة، ويستخدم البقية fallback عند failure أو cooldown. إذا كانت كل replicas تستخدم Cookies من الحساب نفسه، فلن تتضاعف حصة الحساب بمجرد تكرار Spaces.

الصورة قد تحجز جلسة Space لعدة دقائق، ولذلك قد تنتظر طلبات النص والبحث. ضع timeout عمليًا، وحدًا أقصى للطابور، ولا تزيل القفل من `BrowserGateway`.

## 21. استكشاف الأخطاء

| الخطأ | التشخيص | الإجراء |
|---|---|---|
| `401 Invalid API Key` | Secret router لا يطابق Space | طابق `CHATGPT_API_SECRET_KEY` مع `API_SECRET_KEY` في Space |
| كل replicas تعيد 401 | خطأ مشترك في key pool | تحقق من JSON/fallback وSecret names |
| `/health` 503 | Space يبني أو Chromium/Cookies غير جاهزة | افتح runtime/logs ثم أعد التشغيل |
| `Locator.click` timeout | Cookie منتهية أو واجهة ChatGPT غير متوقعة | حدّث Cookies وأعد تشغيل Space |
| `Just a moment...` أو `session expired` | Netscape Cookies لا تحمل Session State كاملة | صدّر Storage State من Profile اختباري صالح، وضعه في `CHATGPT_STORAGE_STATE_JSON` داخل Space المطابقة للحساب |
| `CHATGPT_STORAGE_STATE_JSON is invalid` | Secret ليس JSON صالحًا أو قُص أثناء اللصق | أعد التصدير والصق JSON كاملًا، ولا تضعه في Variable أو Git |
| `You've hit the Free plan limit` | حد ChatGPT Web، غالبًا خاص بالصور | انتظر reset أو استخدم حسابًا يملك الحصة؛ لا تعدّل API key فقط |
| `images=[]` | لا توجد صورة مولدة بعد أو تم رفض asset | انتظر/أعد المحاولة أو راجع Space مباشرة |
| نص البحث بلا مصادر موثوقة | رد النموذج غير كافٍ للتحقق | افحص الروابط خارجيًا، ولا تعتمد على أسماء أو تواريخ غير موثقة |
| `AllProvidersFailed` | فشل كل replicas/keys | اقرأ error classes، افحص كل Space منفردًا، ثم أصلح الأول قبل زيادة retries |
| router لا يرى متغيرًا | `.env` غير محمل أو اسم غير صحيح | نفذ من root، راجع `AI_ROUTER_CONFIG_DIR`، ولا تطبع القيمة |

## 22. الترقية والتراجع

حدّث router ونسخة المصدر المضمنة معًا:

```bash
git fetch --tags
git checkout v1.2.5-chatgpt-three-spaces
PYTHONPATH=src python -m unittest discover -s tests -v
```

راجع [آخر release](https://github.com/ysrg2003/ai-provider-router/releases) قبل الترقية. للتراجع، checkout release سابقًا ثم أعد اختبارات offline وsmoke محدود. لا تغيّر Cookies أو Secrets أثناء rollback إلا إذا كان العطل متعلقًا بها.

## 23. فحص الأسرار قبل commit

```bash
git status --short
git ls-files .env
git grep -nE 'ghp_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|CHATGPT_COOKIES_NETSCAPE=.{20,}' || true
```

يجب ألا يظهر `.env`، ولا token حقيقي، ولا Cookie. لا ترفع JSON يحوي `data_base64` إلى repository إلا إذا كان artifact خاصًا وقصير العمر.

## 24. المراجع الرسمية

[1]: https://huggingface.co/docs/hub/spaces-overview#managing-secrets "Hugging Face Spaces: creation, compute, secrets, variables, and duplication"
[2]: https://huggingface.co/docs/huggingface_hub/en/quick-start#authentication "Hugging Face Hub Quickstart: authentication and token permissions"
[3]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions: using secrets"
[4]: https://github.com/ysrg2003/chatgpt-api "chatgpt-api source repository"
[5]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router source repository"
