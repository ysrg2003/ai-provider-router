# دليل تكامل ChatGPT Spaces مع ai-provider-router

## 1. النتيجة النهائية

بعد إكمال هذا الدليل، يستخدم router نسختين مستقلتين من `chatgpt-api` بالترتيب التالي لمسارات النص والبحث الحي والصورة:

| الأولوية | Provider ID | Space | Base URL |
|---:|---|---|---|
| 1 | `chatgpt_space_replica_01` | `Yousefsg/chatgpt-api-replica-01` | `https://yousefsg-chatgpt-api-replica-01.hf.space` |
| 2 | `chatgpt_space_replica_02` | `Yousefsg/chatgpt-api-replica-02` | `https://yousefsg-chatgpt-api-replica-02.hf.space` |

Space قديمة محفوظة على Hugging Face خارج router، ولا تدخل في `config/providers.json` أو `config/models.json` أو workflow الاختبار.

> `chatgpt-api` ليس OpenAI API رسميًا؛ هو خدمة أتمتة لجلسة ChatGPT Web. قد تتغير واجهة ChatGPT أو شروطها أو حصصها. لا تستخدمه لتجاوز حدود أو ضوابط المزود.

لشرح **إنشاء Space-01 وSpace-02 من الصفر، نشر نفس source revision، إضافة Secrets مستقلة، وربط كل Base URL بالrouter**، استخدم [دليل Spaces وSecrets التفصيلي](chatgpt-vendor-secrets.md).

## 2. المتطلبات

| المتطلب | الحالة | الاستخدام |
|---|---|---|
| Python 3.11+ | مطلوب | router والاختبارات |
| `requests` و`python-dotenv` | مطلوبان | adapter والتهيئة |
| Space-01 وSpace-02 بحالة Running | مطلوب | مصادر ChatGPT HTTP |
| `API_SECRET_KEY` في كل Space | مطلوب | مصادقة HTTP |
| Cookies أو Storage State داخل كل Space | مطلوب للتشغيل الحقيقي | جلسة ChatGPT Web فقط |
| Hugging Face Access Token | للإدارة فقط | إدارة Space، وليس runtime API |
| GitHub repository | اختياري | CI والإصدارات |

## 3. كيف يعمل التكامل

يقرأ `RouterConfig` المزودات من `config/providers.json`، ويقرأ المفاتيح من `config/key_pools.json`. يربط كل provider بـ`ChatGPTSpaceAdapter` مستقل. يمكن للنسختين مشاركة key pool إذا كانت قيمة `API_SECRET_KEY` متطابقة، بينما تظل Cookies وStorage State مستقلة داخل كل Space.

مسارات النص والبحث لا تستخدم HTML أو image extraction. مسار الصورة فقط يقبل `images[].data_url` أو `images[].src` بعد التحقق من أنها صورة مولدة، ويرفض favicon وavatar والصور القديمة. عند فشل Space-01 بخطأ قابل للانتقال، يستخدم router Space-02 كـfallback، ثم ينتقل إلى providers غير ChatGPT الموجودة في route إن كانت مؤهلة.

## 4. Base URLs والأسرار

عناوين Spaces ليست Secrets. تُضبط كـVariables اختيارية في router، أو تُستخدم القيم الافتراضية الموجودة في `config/providers.json`:

```dotenv
CHATGPT_API_REPLICA_01_BASE_URL=https://OWNER-REPLICA-01.hf.space
CHATGPT_API_REPLICA_02_BASE_URL=https://OWNER-REPLICA-02.hf.space
```

يجب أن تكون القيمة origin فقط، دون `/v1` أو `/v1/chat/completions`.

| القيمة | مكان التخزين |
|---|---|
| `API_SECRET_KEY` | Secret داخل Space المقابلة |
| `CHATGPT_COOKIES_NETSCAPE` | Secret داخل Space فقط |
| `CHATGPT_STORAGE_STATE_JSON` | Secret داخل Space فقط عند الحاجة |
| `CHATGPT_API_REPLICA_01_BASE_URL` | Variable في router |
| `CHATGPT_API_REPLICA_02_BASE_URL` | Variable في router |
| `CHATGPT_API_SECRET_KEY` | Secret في router، ويطابق `API_SECRET_KEY` في Space |
| `AI_ROUTER_CHATGPT_KEYS_JSON` | Secret في router، مصفوفة مفاتيح اختيارية مرتبة |

لا تضع Cookies أو Storage State أو Hugging Face tokens أو GitHub tokens في Git. عند تعرض أي Secret، ألغِه أو دوّره في الجهة المالكة ثم حدّث الجهة المستهلكة.

## 5. إعداد كل Space

نفّذ الخطوات التالية لكل من Space-01 وSpace-02:

1. افتح صفحة Space في Hugging Face.
2. اختر **Settings** ثم **Variables and secrets**.
3. أضف Secret باسم `API_SECRET_KEY` بالقيمة التي سيستخدمها router.
4. أضف `CHATGPT_COOKIES_NETSCAPE` أو `CHATGPT_STORAGE_STATE_JSON` حسب طريقة الجلسة المعتمدة، دون طباعتها أو رفعها إلى Git.
5. أعد تشغيل Space وانتظر أن تصبح `Running`.
6. تحقق من readiness:

```bash
curl -fsS https://yousefsg-chatgpt-api-replica-01.hf.space/health
curl -fsS https://yousefsg-chatgpt-api-replica-02.hf.space/health
```

النجاح المتوقع هو JSON يحتوي `"ready":true`. إذا كان `/health` جاهزًا لكن الطلبات تعيد 401، راجع `API_SECRET_KEY`. إذا ظهرت `session expired`، صدّر Cookies أو Storage State جديدة للحساب نفسه داخل Space نفسها.

## 6. إعداد router محليًا

من جذر مستودع `ai-provider-router`:

```bash
cp .env.example .env
```

ضع Secret router في `.env` أو في بيئة التنفيذ، ثم شغّل ملخص الإعداد:

```bash
set -a
source .env
set +a
ai-router --config-dir config --state-db /tmp/chatgpt-router-summary.db summary
```

يجب أن يعرض الملخص provider IDs التالية عند استخدام ChatGPT:

```text
chatgpt_space_replica_01
chatgpt_space_replica_02
```

لا ينبغي أن يظهر provider ثالث من ChatGPT.

## 7. أمثلة الاستخدام

### النص

```bash
CHATGPT_API_SECRET_KEY=YOUR_SPACE_API_SECRET \
ai-router --config-dir config --state-db /tmp/chatgpt-text.db \
  call-auto --output-type text --operation chatgpt_text \
  --user "قل فقط: نجح اختبار النص"
```

### البحث الحي

```bash
CHATGPT_API_SECRET_KEY=YOUR_SPACE_API_SECRET \
ai-router --config-dir config --state-db /tmp/chatgpt-search.db \
  call-auto --output-type text --grounding search --operation chatgpt_search \
  --user "ابحث في الويب بحث حي عن آخر موديل Anthropic AI وأعد المصدر"
```

### الصورة

```bash
CHATGPT_API_SECRET_KEY=YOUR_SPACE_API_SECRET \
ai-router --config-dir config --state-db /tmp/chatgpt-image.db \
  call-auto --output-type image --operation chatgpt_image \
  --user "generate image of a wise stickman reading a book in a library"
```

اختبار الصورة يستهلك quota وقد يستغرق دقائق. لا تعتبر HTTP 200 نجاحًا للصورة؛ يجب وجود `images[]` و`data_url` صالح ثم فحص bytes وMIME والأبعاد. إذا أعادت ChatGPT رسالة Free-plan limit، سجّل الحالة `quota` وانتظر reset بدل تكرار الطلب.

## 8. الاختبار الوظيفي المتسلسل

يستخدم workflow `.github/workflows/chatgpt-spaces-functional.yml` السكربت `scripts/chatgpt_spaces_functional.py`. قائمة الاختبار مقيدة بالنسختين:

```text
chatgpt_space_replica_01
chatgpt_space_replica_02
```

لتقليل استهلاك الحصة، نفّذ النص والبحث أولًا. نفّذ الصورة مرة واحدة فقط لكل Space عندما تكون هناك حاجة، ثم افحص artifact بدل الاعتماد على علامة نجاح workflow وحدها.

## 9. آخر حالة تحقق

في آخر live smoke نجح النص والبحث الحي في Space-01 وSpace-02 HTTP 200. أُرسل طلب صورة واحد فقط لكل نسخة، وأعادت كلتاهما HTTP 200 مع `images=[]` ورسالة ChatGPT Free plan image-generation limit. لذلك الصورة مؤجلة حتى reset quota، بينما text/search مثبتان حيًا.

التقرير الكامل في [`../project-documentation/live-test-report-2026-08-19.md`](../project-documentation/live-test-report-2026-08-19.md)، والـartifacts في [`../project-documentation/live-verification-2026-08-19/summary.json`](../project-documentation/live-verification-2026-08-19/summary.json).

## 10. استكشاف الأخطاء

| العرض | السبب المرجح | الإجراء |
|---|---|---|
| HTTP 401 | Secret router لا يطابق Secret Space | طابق `CHATGPT_API_SECRET_KEY` مع `API_SECRET_KEY` |
| `/health` جاهز وtext يعيد 503 | جلسة ChatGPT داخل Space غير صالحة أو generation عالق | افحص Logs وdiagnostics، ثم حدّث session state داخل Space نفسها |
| بحث بلا مصادر | route لا يملك أداة search أو prompt لم يُصنف بحثًا | تحقق من `grounding=search` وعبارة البحث الحي |
| صورة `images=[]` مع رسالة Free plan limit | quota خارجية | انتظر reset، ولا تغيّر Base URL أو key pool |
| صورة timeout بلا رسالة quota | generation أو DOM غير مستقر | افحص artifact وLogs، ولا تعاود الطلب قبل التأكد من عدم اكتماله خلفيًا |
| Space-01 فشلت وSpace-02 تعمل | اختلاف session أو account أو quota | استخدم Space-02 كـfallback وسجّل السبب لكل provider |

## 11. بوابة الإصدار

قبل أي release:

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m compileall -q src tests vendors/chatgpt-api
python3 -m unittest discover -s tests -v
```

تحقق أيضًا من أن `git grep` لا يعثر على Secrets أو على provider قديم خارج وثائق التاريخ المقصودة، وأن `git diff --check` ينجح.

## المراجع

[1]: https://huggingface.co/docs/hub/spaces-overview#managing-secrets "Hugging Face Spaces: managing secrets and variables"
[2]: https://huggingface.co/docs/huggingface_hub/en/guides/repository "Hugging Face Hub repository management"
[3]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router repository"
