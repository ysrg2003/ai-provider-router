# NVIDIA NIM Free Endpoint

أضيف مزود NVIDIA NIM إلى router بعد OpenRouter في سلاسل النماذج ومسارات النص والبحث الحي. يستخدم المزود واجهة OpenAI-compatible الرسمية:

```text
https://integrate.api.nvidia.com/v1/chat/completions
```

## إعداد المفتاح

لا تُحفظ مفاتيح NVIDIA في Git أو في `config/*.json`. ضع المفتاح في بيئة التشغيل:

```dotenv
NVIDIA_API_KEY=nvapi-REPLACE_ME
```

وللتدوير بين أكثر من مفتاح:

```dotenv
NVIDIA_API_KEYS_JSON=[{"id":"nvidia-key-1","key":"nvapi-REPLACE_ME","project":"default"}]
```

تُقرأ القيم عبر `config/key_pools.json` من `NVIDIA_API_KEYS_JSON` أولًا، ثم `NVIDIA_API_KEY` كـfallback. إذا لم يوجد مفتاح، يتجاوز router NVIDIA تلقائيًا وينتقل إلى provider التالي؛ لا يسبب ذلك فشل تهيئة router.

## الكتالوج الكامل

الرابط الرسمي المحدد للفلتر هو [NVIDIA Free Endpoint](https://build.nvidia.com/models?filters=nimType%3Anim_type_preview). وقت الالتقاط كان يعرض **57 Free Endpoint** موزعة على ثلاث صفحات. توجد القائمة الكاملة الملتقطة في [`config/nvidia_free_catalog.json`](../config/nvidia_free_catalog.json)، وتشمل لكل نتيجة الاسم و`api_model` والقدرة وحالة deprecation.

المصدر النصي الرسمي [llms.txt](https://build.nvidia.com/llms.txt) يؤكد Base URL والتوافق مع Chat Completions، بينما [models.md](https://build.nvidia.com/models.md) يوفر روابط canonical للنماذج.

## ترتيب النماذج الناجحة

يوجد الترتيب العملي الكامل للنماذج الـ12 العامة المفعّلة في [docs/nvidia-ranking.md](nvidia-ranking.md). الترتيب يميز بين القدرة العامة والتخصص، ويطابق ترتيب `nvidia_free` داخل `config/models.json`.

## ما يدخل routes العامة

من أصل 57 نتيجة، أظهر `/v1/models` لحساب الاختبار 30 نموذجًا من المرشحين النشطين. الاختباران الوظيفيان [32218928597](https://github.com/ysrg2003/ai-provider-router/actions/runs/32218928597) و[32219540211](https://github.com/ysrg2003/ai-provider-router/actions/runs/32219540211) اختبرا النماذج بسؤال معرفة ومسألة استدلال؛ نجحت **12 من 12 نموذجًا عامًا** بعد إعادة فحص transient، ونجح Riva عند اختباره بترجمة مباشرة. لذلك أصبحت 12 نماذج عامة فقط مفعّلة في `model_chains.nvidia_free` بعد OpenRouter، بينما Riva مفعّل في `output_routes.translation` خارج السلسلة العامة، وLlama Vision وLlama 8B خارج عقد JSON العام. واجه GLM quota مؤقتًا ثم نجح في الجولة اللاحقة.

بقية النتائج تبقى محفوظة في catalog الكامل لكنها لا تدخل route النص العام. منها نماذج ظهرت للحساب لكنها أعادت 400 أو 503 أو timeout أو ردًا فارغًا، ومنها نتائج لم تظهر في `/v1/models` وقت الاختبار، ومنها endpoints متخصصة للـembedding أو reranking أو moderation أو audio/TTS أو video/3D أو protein أو image/vision. عدم إدخالها في route النص لا يعني حذفها؛ بل يمنع إرسال prompt نصي عام إلى endpoint يتطلب payload أو adapter مختلفًا.

| حالة الاختبار | العدد | سياسة router |
|---|---:|---|
| نماذج عامة نجحت في الاختبارين الوظيفيين | 12 من 12 | مفعلة في routes النصية بعد OpenRouter |
| Riva ترجمة متخصصة نجحت بترجمة مباشرة | 1 | مفعّل في `output_routes.translation` وخارج النص العام |
| نماذج غير متوافقة مع عقد JSON العام | 2 | Vision وLlama 8B محفوظان في catalog وdisabled من routes النصية |
| quota transient أثناء جولة ثم نجاح في الإعادة | 1 | GLM محفوظ ومفعّل مع احترام cooldown |
| نماذج غير ظاهرة أو غير مؤكدة في catalog | 27 | محفوظة في catalog وdisabled |
| إجمالي catalog | 57 | يتضمن كل Free Endpoint المرصود |

حالة specialization وdeprecation محفوظة لكل entry داخل catalog. النماذج المتخصصة تحتاج routes/normalizers أو adapters منفصلة قبل تفعيلها؛ Riva هو الاستثناء الحالي لأنه يملك `translation` adapter/route مثبتًا. والنماذج التي أعلنت NVIDIA قرب deprecation لا تُفعّل تلقائيًا.

العدد الدقيق، ونتيجة live test لكل نموذج، ونتيجة الاختبار الوظيفي وسبب الفشل المنقح محفوظة في `config/nvidia_free_catalog.json`. هذا الفصل مهم لأن الكتالوج العام يتغير، كما أن `/v1/models` يختلف حسب الحساب والوقت.

## الترتيب وfallback


السلوك عند الفشل هو نفسه لبقية OpenAI-compatible providers: `401/403` يصنف كمشكلة مصادقة غير قابلة لإعادة المحاولة، و`429` كـquota، وأخطاء 408/409/425/5xx كـtransient وفق سياسة router. يسجل SQLite الفشل ويطبق cooldown ثم ينتقل إلى provider/model التالي.

## الاختبار المحلي

بعد وضع المفتاح:

```bash
cd /home/ubuntu/work/ai-provider-router
export PYTHONPATH=src
export NVIDIA_API_KEY='nvapi-REPLACE_ME'
python3 -m ai_router.cli.main \
  --config-dir config \
  --state-db /tmp/router-nvidia.db \
  call-auto \
  --chain nvidia_free \
  --output-type text \
  --operation nvidia_free_probe \
  --user 'Return exactly: NVIDIA free chain works'
```

لا تسجل قيمة المفتاح في shell history أو CI logs. استخدم Secret manager أو متغير بيئة خادمي، ولا تضع `NVIDIA_API_KEY` في frontend أو متصفح المستخدم.

## أحدث تحقق حي عبر GitHub Actions

بعد إضافة المفتاح الجديد إلى GitHub Secret، أضيف سيناريو `nvidia` إلى [`scripts/live_smoke.py`](../scripts/live_smoke.py) وworkflow [`live-smoke.yml`](../.github/workflows/live-smoke.yml). نجح التشغيل [`32217577979`](https://github.com/ysrg2003/ai-provider-router/actions/runs/32217577979) على فرع `main`، وكانت النتيجة المنقحة:

| الحقل | النتيجة |
|---|---|
| `scenario_filter` | `nvidia` |
| `route` | `nvidia_free` |
| `status` | `passed` |
| `loaded_key_counts.nvidia` | `1` |
| `json_fields` | `ok` |

الـartifact لم يتضمن قيمة المفتاح أو Authorization header. هذا يثبت المصادقة والـtext completion عبر السلسلة الحالية في ذلك التشغيل فقط؛ لا يثبت توفر كل نماذج catalog ولا يضيف routes للصور أو الصوت أو الفيديو.

## قيود مهمة

Free Endpoint يعني free trial أو وصولًا مجانيًا محدودًا وفق حالة النموذج والحساب والازدحام وسياسة NVIDIA الحالية؛ لا يعني استخدامًا تجاريًا غير محدود، ولا يضمن حدًا ثابتًا لكل نموذج. قد تطلب NVIDIA تحقق الحساب أو الهاتف قبل إصدار API key. راجع صفحة النموذج قبل الاعتماد الإنتاجي.
