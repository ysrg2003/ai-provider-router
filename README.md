# AI Provider Router

## ما هذا المشروع؟

هذا المشروع هو **مدير مستقل لاستدعاء نماذج الذكاء الاصطناعي**. وظيفته أن يستقبل منك طلباً واحداً، ثم يجرّب المزودات والنماذج ومفاتيح API بالترتيب الذي تحدده أنت، ويسجل النتيجة، وينتقل تلقائياً إلى البديل التالي إذا حدث خطأ أو انتهت الحصة أو تعطل أحد المفاتيح.

تخيل أن لديك الخطة التالية:

```text
1. Gemini 2.5 Flash باستخدام المفتاح الأول
2. Gemini 2.5 Flash باستخدام المفتاح الثاني
3. Gemini 2.5 Flash-Lite باستخدام المفتاح الأول
4. Gemini 2.5 Flash-Lite باستخدام المفتاح الثاني
5. Hugging Face باستخدام النموذج الاحتياطي الأول
6. Hugging Face باستخدام النموذج الاحتياطي الثاني
```

بدلاً من كتابة ستة مسارات داخل كل مشروع، يكتب المشروع المستهلك طلباً واحداً فقط. أما التبديل بين الستة فيحدث هنا داخل **AI Provider Router**.

هذا المشروع لا يعرف شيئاً عن Xiangqi أو الفيديو أو يوتيوب. لذلك يمكنك استخدامه مع مشروع تحليل مستندات، أو تطبيق خدمة عملاء، أو مولد مقالات، أو أي برنامج يحتاج إلى مخرجات JSON منظمة.

> الفكرة الأساسية: عدّل الملفات الموجودة داخل `config/` لتغيير المزود أو النموذج أو الترتيب أو مجموعة المفاتيح، ولا تعدّل المشروع الذي يستعمل المدير.

> **حالة التحقق الأخيرة:** في 2026-08-16 ثبت أن النص وSearch وMaps وEmbedding تعمل، وأن TTS أعاد صوتًا فعليًا. أما Image فالمسار البرمجي صحيح الآن ويستخدم `generateContent`، لكن المفاتيح الستة أعادت `429 RESOURCE_EXHAUSTED` بسبب الحصة. نماذج Imagen 4 محفوظة كـlegacy معطلة لأنها معلنة للإيقاف.

---

## قبل أن تبدأ: ماذا تحتاج؟

تحتاج إلى جهاز عليه Python 3.11 أو أحدث، وحساب لدى مزود واحد على الأقل. التشغيل المحلي لا يحتاج إلى GitHub. أما التشغيل التلقائي فيحتاج إلى مستودع GitHub وإضافة الأسرار داخله.

| الشيء | هل هو مطلوب؟ | لماذا؟ |
| --- | --- | --- |
| Python 3.11 أو أحدث | نعم | تشغيل الحزمة والاختبارات |
| مفتاح Gemini | اختياري | تفعيل مسارات Text وImage وTTS وEmbedding وGrounding بحسب الحصة |
| مفتاح Hugging Face | اختياري | تفعيل خطة الاحتياط |
| مفتاح OpenRouter | اختياري | تفعيل 19 نموذجًا مجانيًا موثقًا، منها 16 نموذجًا عامًا نشطًا |
| Git | اختياري محلياً | استنساخ المشروع وتحديثه |
| GitHub | اختياري للتشغيل اليدوي، مطلوب للتشغيل التلقائي | حفظ المشروع وتشغيل workflow |

يمكنك تثبيت المشروع وتشغيل ملخصه **من دون أي مفتاح API**. ما لن يعمل من دون مفتاح هو طلب حقيقي إلى نموذج ذكاء اصطناعي.

---

# القسم الأول: تنزيل المشروع وتشغيل أول فحص

## الخطوة 1: تنزيل المستودع

افتح Terminal في Linux أو macOS، أو PowerShell في Windows، ثم نفّذ:

```bash
git clone https://github.com/ysrg2003/ai-provider-router.git
cd ai-provider-router
```

إذا لم يكن Git مثبتاً لديك، نزّل ملف ZIP من صفحة GitHub ثم فك الضغط، وانتقل داخل المجلد:

```bash
cd ai-provider-router
```

تأكد أنك داخل المجلد الصحيح. يجب أن ترى ملفات مثل:

```text
README.md
pyproject.toml
requirements.txt
config/
src/
tests/
```

يمكنك التحقق بالأمر:

```bash
ls
```

في Windows PowerShell استخدم:

```powershell
Get-ChildItem
```

## الخطوة 2: إنشاء بيئة Python خاصة

أنشئ بيئة خاصة للمشروع حتى لا تختلط مكتباته مع بقية برامجك:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

في Windows PowerShell استخدم:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

عندما تنجح العملية سترى غالباً اسم البيئة مثل `(.venv)` في بداية سطر الأوامر.

## الخطوة 3: تثبيت المكتبات

نفّذ:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

شرح الأوامر:

| الأمر | معناه |
| --- | --- |
| `python -m pip install --upgrade pip` | تحديث مدير حزم Python |
| `python -m pip install -r requirements.txt` | تثبيت `requests` و`python-dotenv` |
| `python -m pip install -e .` | تثبيت المشروع نفسه بحيث يعمل الأمر `ai-router` من أي مكان داخل البيئة |

## الخطوة 4: تشغيل الاختبارات قبل إضافة أي مفتاح

نفّذ:

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -v
```

النتيجة الصحيحة تشبه:

```text
Ran 31 tests
OK
```

إذا ظهرت النتيجة `OK`، فهذا يعني أن المشروع نفسه سليم، وأن اختبار تدوير المفاتيح التجريبي يعمل من دون اتصال فعلي بمزود خارجي.

## الخطوة 5: قراءة ملخص الإعدادات

نفّذ:

```bash
ai-router --config-dir config --state-db data/ai_router.db summary
```

سترى شيئاً قريباً من:

```json
{
  "config": {
    "providers": ["google_gemini", "huggingface"],
    "chains": {
      "default": [
        {"provider": "google_gemini", "model": "gemini-2.5-flash"},
        {"provider": "google_gemini", "model": "gemini-2.5-flash-lite"},
        {"provider": "huggingface", "model": "openai/gpt-oss-120b:fastest"},
        {"provider": "huggingface", "model": "deepseek-ai/DeepSeek-V4-Flash-0731:fastest"},
        {"provider": "huggingface", "model": "zai-org/GLM-5.2:fastest"},
        "... eight additional Hugging Face fallback entries ..."
      ]
    },
    "secrets_loaded": {
      "google_gemini": 0,
      "huggingface": 0
    }
  },
  "state": {
    "calls": 0,
    "provider_states": 0
  }
}
```

معنى `secrets_loaded: 0` أن المشروع لم يجد مفاتيح بعد. إذا أضفت `HF_TOKEN` فقط فستظهر `huggingface: 1`، وسيعمل مسار Hugging Face بالنماذج العشرة الافتراضية. هذا ليس خطأ في التثبيت.

---

# القسم الثاني: فهم الملفات قبل تعديلها

جميع الإعدادات التي يحتاجها المبتدئ موجودة داخل `config/`.

| الملف | متى تعدله؟ | مثال على التعديل |
| --- | --- | --- |
| `config/providers.json` | عند إضافة مزود أو حذف مزود أو تغيير عنوان API | إضافة مزود OpenAI-compatible |
| `config/models.json` | عند إضافة نموذج أو حذف نموذج أو تغيير الترتيب | جعل Flash-Lite قبل Flash |
| `config/key_pools.json` | عند تغيير اسم متغير الأسرار | تغيير `AI_ROUTER_GEMINI_KEYS_JSON` إلى اسم آخر |
| `config/policies.json` | عند تغيير عدد المحاولات أو زمن التبريد | زيادة تبريد خطأ 429 أو استيعاب كل مسارات fallback |
| `.env` | عند التشغيل المحلي وإضافة المفاتيح | وضع JSON للمفاتيح محلياً |
| `src/` | عند كتابة محول لمزود لا يستخدم واجهة معروفة | إضافة محول API خاص |

لا تضع قيمة API key في ملفات JSON الموجودة في `config/`. هذه الملفات تصف **كيف يقرأ البرنامج السر**، لكنها لا تحتوي السر نفسه.

---

# القسم الثالث: إضافة مفاتيح Gemini محلياً

## الخطوة 6: إنشاء ملف `.env`

انسخ نموذج البيئة:

```bash
cp .env.example .env
```

في Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

افتح `.env`. ابدأ بهذا الشكل:

```dotenv
AI_ROUTER_GEMINI_KEYS_JSON=[]
AI_ROUTER_HF_KEYS_JSON=[]
AI_ROUTER_CONFIG_DIR=config
AI_ROUTER_STATE_DB=data/ai_router.db
```

## الخطوة 7: وضع مفتاح Gemini واحد

إذا كان لديك مفتاح Gemini واحد، اجعل قيمة `AI_ROUTER_GEMINI_KEYS_JSON` مصفوفة تحتوي عنصراً واحداً:

```dotenv
AI_ROUTER_GEMINI_KEYS_JSON=[{"id":"gemini-main","key":"ضع_المفتاح_الحقيقي_هنا","project":"my-gemini-project"}]
```

استبدل فقط `ضع_المفتاح_الحقيقي_هنا` بالقيمة التي حصلت عليها من Google AI Studio أو Google Cloud. لا تضع مسافات أو تعليقات داخل قيمة JSON.

## الخطوة 8: وضع عدة مفاتيح بالترتيب

إذا كان لديك ثلاثة مفاتيح، اكتبها بهذا الشكل:

```dotenv
AI_ROUTER_GEMINI_KEYS_JSON=[
  {"id":"gemini-1","key":"المفتاح_الأول","project":"project-a"},
  {"id":"gemini-2","key":"المفتاح_الثاني","project":"project-a"},
  {"id":"gemini-3","key":"المفتاح_الثالث","project":"project-b"}
]
```

ترتيب العناصر مهم جداً. سيستخدم المدير `gemini-1` أولاً، ثم `gemini-2`، ثم `gemini-3` عند الحاجة.

لكل عنصر:

| الحقل | وظيفته |
| --- | --- |
| `id` | اسم داخلي يظهر في سجل الحالة، مثل `gemini-1` |
| `key` | قيمة API key الحقيقية |
| `project` | اسم المشروع الذي ينتمي إليه المفتاح، للتشخيص فقط |

## الخطوة 9: فهم ترتيب نماذج Gemini

افتح `config/models.json`. السلاسل الحالية تضع نماذج Gemini النصية القابلة للتشغيل في adapter بترتيب تنازلي حسب الإصدار:

```text
Gemini 3.7 Flash
Gemini 3.6 Flash
Gemini 3.5 Flash
Gemini 3.5 Flash-Lite
Gemini 3.1 Flash-Lite
Gemini 3 Flash
Gemini 2.5 Flash
Gemini 2.5 Flash-Lite
```

بعد انتهاء مسار Gemini ينتقل الراوتر إلى نماذج Hugging Face الموجودة في السلسلة نفسها. لا تُضاف نماذج TTS أو Image أو Embedding إلى `default` تلقائيًا؛ لكل فئة route وadapter مستقلان. مسار Image الحالي يستخدم نماذج Nano Banana عبر `generateContent`، ومسار TTS يستخدم Interactions، بينما Imagen 4 محفوظ في `image_legacy` معطل.

مع وجود مفتاحين، يبدأ كل مفتاح من النموذج الأول. إذا فشل النموذج الأول للمفتاح، يحفظ الراوتر أن هذا المفتاح وصل إلى النموذج التالي. عند الطلب اللاحق، يستأنف هذا المفتاح من موضعه المحفوظ، بينما يبدأ مفتاح جديد من أول نموذج.

إذا أردت إيقاف نموذج مؤقتاً، غيّر `enabled` إلى `false`:

```json
{"provider": "google_gemini", "model": "gemini-2.5-flash-lite", "enabled": false}
```

لا تحذف الفاصلة السابقة أو التالية بالخطأ. JSON حساس للصياغة.

---

# القسم الرابع: إضافة Hugging Face كخطة احتياطية

### الفكرة المهمة للمبتدئ

القائمة الافتراضية تحتوي على **عشرة نماذج Hugging Face**. لا تحتاج إلى إضافة أسماء النماذج يدوياً، ولا تحتاج إلى إنشاء مفتاح لكل نموذج. أضف Access Token واحداً فقط باسم `HF_TOKEN`، وسيجرب النظام النماذج العشرة بالترتيب الموجود في `config/models.json`.

> التوفر والسرعة والحصة تختلف حسب الحساب والنموذج والمزود الذي يختاره Hugging Face. القائمة الافتراضية عملية ومرتبة، لكنها ليست ضماناً أن كل نموذج سيظل متاحاً أو مجانياً في كل وقت.

## الخطوة 10: إضافة Access Token واحد فقط

أنشئ Hugging Face fine-grained Access Token مع صلاحية **Make calls to Inference Providers** من [صفحة إنشاء الرموز](https://huggingface.co/settings/tokens/new?ownUserPermissions=inference.serverless.write&tokenType=fineGrained). بعد الحصول على القيمة، افتح `.env` وضع:

```dotenv
HF_TOKEN=hf_ضع_التوكن_الحقيقي_هنا
```

لا تحتاج في أبسط حالة إلى كتابة `AI_ROUTER_HF_KEYS_JSON`. الإعداد الموجود في `config/key_pools.json` يقول للنظام إن `HF_TOKEN` هو fallback لمجموعة Hugging Face.

شغّل الملخص:

```bash
ai-router --config-dir config --state-db data/ai_router.db summary
```

ابحث عن:

```json
"secrets_loaded": {
  "google_gemini": 0,
  "huggingface": 1
}
```

إذا ظهرت `huggingface: 1`، فالمشروع قرأ التوكن بنجاح دون عرض قيمته.

## الخطوة 11: النماذج العشرة الافتراضية

يستخدم `model_chains.default` النماذج التالية بعد انتهاء Gemini أو عدم وجود مفاتيحه:

| الترتيب في مسار Hugging Face | النموذج | الاستخدام المقصود |
| ---: | --- | --- |
| 1 | `openai/gpt-oss-120b:fastest` | النموذج العام الأول، والمهام المنظمة واستدعاء الأدوات |
| 2 | `deepseek-ai/DeepSeek-V4-Flash-0731:fastest` | إجابات عامة سريعة عالية القدرة |
| 3 | `zai-org/GLM-5.2:fastest` | التخطيط والتحليل العام |
| 4 | `Qwen/Qwen3-Coder-480B-A35B-Instruct:fastest` | البرمجة والتعليمات التقنية |
| 5 | `deepseek-ai/DeepSeek-R1:fastest` | التفكير والتحليل متعدد الخطوات |
| 6 | `Qwen/Qwen3-4B-Thinking-2507:fastest` | تفكير أخف عندما لا تحتاج إلى نموذج ضخم |
| 7 | `Qwen/Qwen2.5-7B-Instruct-1M:fastest` | تعليمات طويلة وسياقات ممتدة |
| 8 | `Qwen/Qwen2.5-Coder-32B-Instruct:fastest` | كود ومخرجات تقنية منظمة |
| 9 | `meta-llama/Llama-3.1-8B-Instruct:fastest` | fallback عام أصغر وأكثر خفة |
| 10 | `openai/gpt-oss-20b:fastest` | fallback عام أخف من نموذج 120B |

تم اختيار القائمة بناءً على نماذج توصي بها وثائق Hugging Face لمهام Chat Completion، ونماذج ظاهرة في قائمة Text Generation المتاحة لـ Inference Providers، مع تنويع الأحجام والاستخدامات [1] [2].

## الخطوة 12: فهم ترتيب التجربة الكامل

إذا كان لديك Gemini Token واحد وHF Token واحد، يحاول النظام Gemini بهذا الترتيب، ثم ينتقل إلى Hugging Face:

```text
1. Gemini 3.7 Flash
2. Gemini 3.6 Flash
3. Gemini 3.5 Flash
4. Gemini 3.5 Flash-Lite
5. Gemini 3.1 Flash-Lite
6. Gemini 3 Flash
7. Gemini 2.5 Flash
8. Gemini 2.5 Flash-Lite
9. Hugging Face: openai/gpt-oss-120b
10. Hugging Face: deepseek-ai/DeepSeek-V4-Flash-0731
11. Hugging Face: zai-org/GLM-5.2
12. Hugging Face: Qwen/Qwen3-Coder-480B-A35B-Instruct
13. Hugging Face: deepseek-ai/DeepSeek-R1
14. Hugging Face: Qwen/Qwen3-4B-Thinking-2507
15. Hugging Face: Qwen/Qwen2.5-7B-Instruct-1M
16. Hugging Face: Qwen/Qwen2.5-Coder-32B-Instruct
17. Hugging Face: meta-llama/Llama-3.1-8B-Instruct
18. Hugging Face: openai/gpt-oss-20b
```

إذا لم تضف Gemini، يبدأ النظام مباشرة من النموذج الأول في Hugging Face. وإذا فشل نموذج بسبب 404 أو 403 أو 429 أو timeout أو JSON غير صالح، ينتقل إلى النموذج التالي ويسجل الحالة في SQLite.

## الخطوة 13: استخدام عدة HF Tokens اختيارياً

إذا أردت تدوير عدة Hugging Face tokens بدلاً من Token واحد، استخدم:

```dotenv
AI_ROUTER_HF_KEYS_JSON=[
  {"id":"hf-1","key":"التوكن_الأول","project":"hf-router"},
  {"id":"hf-2","key":"التوكن_الثاني","project":"hf-router"}
]
```

عند وجود `AI_ROUTER_HF_KEYS_JSON`، يفضله النظام على `HF_TOKEN` ويجرب العناصر بالترتيب. أما المبتدئ فلا يحتاج إلى ذلك؛ `HF_TOKEN` الواحد كافٍ لتفعيل النماذج العشرة.

## الخطوة 14: تغيير نموذج أو تعطيله

عدّل `config/models.json` فقط. لتعطيل نموذج:

```json
{"provider": "huggingface", "model": "openai/gpt-oss-20b:fastest", "enabled": false}
```

لتغيير الترتيب، انقل الكائن إلى موضع آخر داخل `default`. لا تعدّل `src/ai_router/router.py` لمجرد تغيير اسم نموذج.

---

# القسم الخامس: تفعيل OpenRouter والنماذج المجانية

OpenRouter مزود OpenAI-compatible؛ يستخدم المشروع endpoint `https://openrouter.ai/api/v1/chat/completions`، ولذلك لا يحتاج إلى adapter جديد. أُضيفت النماذج المجانية من [صفحة Free Models][8] و[Free Models Router][9] و[Models API][10]، مع ترتيب المجموعة الرسمية أولًا ثم بقية النماذج المجانية.

## الخطوة 15: إنشاء مفتاح OpenRouter

افتح [صفحة مفاتيح OpenRouter](https://openrouter.ai/keys) وأنشئ API key. لا تضعه في `config/` أو داخل Git. للاستخدام المحلي، انسخ `.env.example` إلى `.env` ثم أضف:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-ضع_المفتاح_هنا
```

إذا كنت تحتاج إلى تدوير عدة مفاتيح، استخدم:

```dotenv
AI_ROUTER_OPENROUTER_KEYS_JSON=[
  {"id":"openrouter-1","key":"sk-or-v1-المفتاح_الأول","project":"openrouter"},
  {"id":"openrouter-2","key":"sk-or-v1-المفتاح_الثاني","project":"openrouter"}
]
```

يقرأ الراوتر المصفوفة أولًا، ثم يستخدم `OPENROUTER_API_KEY` كـfallback. لكل مفتاح cursor مستقل في SQLite، وينتقل إلى النموذج التالي عند خطأ المصادقة أو الحصة أو timeout أو JSON غير صالح.

## الخطوة 16: التحقق المحلي دون استهلاك الطلب

نفّذ من جذر المشروع:

```bash
ai-router --config-dir config --state-db /tmp/openrouter-check.db summary
```

يجب أن يظهر `openrouter` ضمن providers. إذا أضفت المفتاح سيظهر عدد الأسرار فقط، لا القيمة.

## الخطوة 17: تجربة سلسلة OpenRouter المجانية

بعد إضافة المفتاح، شغّل:

```bash
ai-router --config-dir config --state-db /tmp/openrouter-live.db call-json \\
  --chain openrouter_free \\
  --operation openrouter_smoke \\
  --system "Return JSON only." \\
  --user "Return a JSON object with ok=true and provider=openrouter."
```

السلسلة تضم 16 نموذجًا عامًا نشطًا، وتضع `openrouter/free` في النهاية. النموذج `nvidia/nemotron-3.5-content-safety:free` لا يدخل سلسلة التوليد العامة؛ له route moderation معطل. نموذجا Lyria الصوتيان موثقَان لكنهما معطلان حتى يضاف adapter صوت مناسب.

إذا ظهر `429`، فهذا rate limit أو نفاد الحصة المجانية، وسيواصل الراوتر التدوير وفق سياسة cooldown. إذا ظهر `400`، فراجع metadata للنموذج، خصوصًا `supports_response_format`؛ الراوتر يحذف `response_format` تلقائيًا للنماذج التي لا تعلن دعمه.

يراجع [كتالوج OpenRouter التفصيلي](docs/openrouter-free.md) كل model ID ومدخلاته ومخرجاته وسياقه وحالة route الخاصة به.

# القسم السادس: تنفيذ أول طلب حقيقي

## الخطوة 12: تشغيل ملخص جديد للتأكد من قراءة المفاتيح

بعد حفظ `.env`، نفّذ:

```bash
ai-router --config-dir config --state-db data/ai_router.db summary
```

ابحث عن:

```json
"secrets_loaded": {
  "google_gemini": 1,
  "huggingface": 0
}
```

إذا وضعت مفتاحين لـ Gemini يجب أن ترى `google_gemini: 2`.

> لا يطبع البرنامج قيمة المفتاح نفسه. سيطبع العدد فقط.

## الخطوة 13: تنفيذ طلب JSON من سطر الأوامر

نفّذ هذا المثال:

```bash
ai-router \
  --config-dir config \
  --state-db data/ai_router.db \
  call-json \
  --chain default \
  --operation first_test \
  --system "Return JSON only. You are a helpful assistant." \
  --user "Create one short idea for a beginner lesson about Xiangqi. Return title and hook."
```

في Windows PowerShell اكتب الأمر في سطر واحد:

```powershell
ai-router --config-dir config --state-db data/ai_router.db call-json --chain default --operation first_test --system "Return JSON only. You are a helpful assistant." --user "Create one short idea for a beginner lesson about Xiangqi. Return title and hook."
```

إذا نجح الاستدعاء، ستصل استجابة JSON مثل:

```json
{
  "title": "The First Xiangqi Trap",
  "hook": "This simple-looking move hides a cannon attack."
}
```

قد تختلف الكلمات؛ المهم أن تكون النتيجة JSON وأن يظهر الطلب لاحقاً في قاعدة SQLite.

## الخطوة 14: التحقق من تسجيل الاستدعاء

شغّل الملخص مرة أخرى:

```bash
ai-router --config-dir config --state-db data/ai_router.db summary
```

يجب أن يصبح:

```json
"state": {
  "calls": 1,
  "provider_states": 1
}
```

إذا فشل المفتاح ثم نجح البديل، ستكون قيمة `calls` أكبر من واحد، لأن النظام يسجل كل محاولة، وليس النجاح فقط.

---

# القسم السادس: كيف يعمل التبديل فعلياً؟

افترض أن لديك مفتاحين ونموذجين. يضبط المشروع الافتراضي `max_attempts` على 64. التسلسل الأولي يكون:

| الترتيب | المحاولة |
| ---: | --- |
| 1 | النموذج الأول بالمفتاح `gemini-1` |
| 2 | النموذج الأول بالمفتاح `gemini-2` |
| 3 | النموذج الثاني بالمفتاح `gemini-1` إذا كان الأول قد فشل لهذا المفتاح |
| 4 | النموذج الثاني بالمفتاح `gemini-2` إذا كان الأول قد فشل لهذا المفتاح |
| 5 | أول نموذج Hugging Face بالمفتاح الأول |
| 6 | أول نموذج Hugging Face بالمفتاح الثاني |

يحفظ SQLite جدول `key_model_cursor` بمفتاح مركب من المزود والـchain والمفتاح والمشروع. هذا يعني أن فشل `gemini-1` في النموذج الأول لا يجعل المفتاح الثاني يقفز إلى النموذج الثاني، ولا يعيد المفتاح الأول إلى البداية في الطلب التالي. نجاح الطلب لا يزيل cursor؛ فالهدف هو الاستئناف من الموضع التالي الذي وصل إليه المفتاح.

إذا أعاد المزود **401 أو 403**، يسجل النظام خطأ مصادقة ويضع المفتاح في تبريد طويل. إذا أعاد **429**، يسجل أن الحصة أو المعدل انتهى ويضع المفتاح في تبريد المدة الموجودة في `config/policies.json`. إذا حدث خطأ شبكة أو 5xx، يستخدم backoff ثم ينتقل إلى المحاولة التالية. إذا أعاد النموذج نصاً ليس JSON صحيحاً، يعتبر الاستجابة غير صالحة وينتقل إلى البديل.

لا تحتاج إلى كتابة هذا المنطق داخل مشروعك. مشروعك يستدعي:

```python
result = router.complete_json(
    chain="default",
    operation="my_operation",
    system_prompt="Return JSON only.",
    user_prompt="Do the requested work.",
)
```

ثم يتولى AI Router بقية العمل.

---

# القسم السابع: استخدامه داخل Python Project آخر

## الخطوة 15: تثبيت AI Router داخل مشروع جديد

لنفترض أن لديك مشروعاً آخر في مجلد اسمه `my-project`. نفّذ:

```bash
cd my-project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e /path/to/ai-provider-router
```

أو إذا أردت تثبيته من GitHub مباشرة:

```bash
python -m pip install "git+https://github.com/ysrg2003/ai-provider-router.git"
```

بما أن المستودع خاص، ستحتاج إلى صلاحية Git مناسبة أو نسخة محلية من المشروع.

## الخطوة 16: استدعاؤه من كود المشروع الجديد

أنشئ ملفاً اسمه `example_app.py`:

```python
from ai_router import AIRouter, AllProvidersFailed

router = AIRouter(
    config_dir="/path/to/ai-provider-router/config",
    state_db="data/my_project_ai_router.db",
)

try:
    result = router.complete_json(
        chain="creative",
        operation="article_outline",
        system_prompt=(
            "Return JSON only. "
            "You are a professional article editor."
        ),
        user_prompt=(
            "Create an outline for a beginner article about Chinese chess. "
            "Return title and sections."
        ),
    )
    print(result)
except AllProvidersFailed as error:
    print("All AI providers failed:", error)
finally:
    router.close()
```

شغّل:

```bash
python example_app.py
```

المشروع الجديد لا يعرف أسماء مفاتيح Gemini أو تفاصيل Hugging Face. هذه المعرفة تبقى داخل `config/` في AI Router.

---

# القسم الثامن: ربطه مع Chinese Cheese Video

يوجد في مشروع الفيديو ملف جسر اسمه `python/ai_router_bridge.py`. هذا الملف يبحث عن AI Router في المسار الموجود داخل `AI_ROUTER_PATH`، ثم يستعمل واجهة `AIRouter`.

## التشغيل المحلي للمشروعين

إذا كان المجلدان بجانب بعضهما:

```text
projects/
├── ai-provider-router/
└── chinese-cheese-video/
```

انتقل إلى مشروع الفيديو، ثم اضبط:

```bash
cd projects/chinese-cheese-video
export AI_ROUTER_PATH=../ai-provider-router
export AI_ROUTER_CONFIG_DIR=../ai-provider-router/config
export AI_ROUTER_STATE_DB=data/ai_router.db
export AI_ROUTER_GEMINI_KEYS_JSON='[{"id":"gemini-1","key":"ضع_المفتاح","project":"project-a"}]'
```

بعدها شغّل:

```bash
python3 python/run_pipeline.py --storage local --language en
```

لتشغيل الصينية:

```bash
python3 python/run_pipeline.py --storage local --language zh
```

إذا لم تضع مفاتيح أو تعطل AI Router، سيعود مشروع الفيديو إلى fallback المحلي بدلاً من التوقف.

---

# القسم التاسع: إعداد GitHub Actions للمشروع الخاص

## الخطوة 17: أسرار مستودع AI Router

مستودع AI Router نفسه يحتوي workflow للاختبارات فقط، ولا يحتاج إلى مفاتيح حتى ينجح اختبار CI. لا تضع المفاتيح داخل ملفات GitHub أو داخل `config/`.

## الخطوة 18: أسرار مستودع Chinese Cheese Video

إذا كان مشروع الفيديو في مستودع GitHub خاص، افتح:

```text
Repository → Settings → Secrets and variables → Actions → New repository secret
```

أضف الأسرار التالية:

| الاسم | القيمة |
| --- | --- |
| `AI_ROUTER_REPO_TOKEN` | Personal Access Token بصلاحية قراءة مستودع AI Router الخاص |
| `AI_ROUTER_GEMINI_KEYS_JSON` | مصفوفة مفاتيح Gemini المرتبة |
| `AI_ROUTER_HF_KEYS_JSON` | مصفوفة مفاتيح Hugging Face المرتبة |
| `YOUTUBE_API_KEY` | اختياري لاكتشاف فيديوهات Xiangqi الحديثة |

مثال قيمة `AI_ROUTER_GEMINI_KEYS_JSON` داخل GitHub Secret:

```json
[
  {"id":"gemini-1","key":"AIza...","project":"project-a"},
  {"id":"gemini-2","key":"AIza...","project":"project-b"}
]
```

لا تضف علامات اقتباس إضافية حول JSON كله. ألصق المصفوفة كما هي.

## الخطوة 19: تشغيل workflow يدوياً

افتح تبويب **Actions** في مستودع الفيديو، واختر workflow المسمى **Chinese Cheese Video — autonomous production**، ثم اضغط **Run workflow**.

القيم المقترحة لأول تجربة:

| الحقل | القيمة |
| --- | --- |
| `daily_count` | `1` |
| `languages` | `en,zh` |
| `discovery_limit` | `5` |

بعد التشغيل راقب الخطوات بهذا الترتيب:

1. Checkout repository.
2. Checkout reusable AI Router.
3. Install Python dependencies.
4. Run autonomous discovery and production.
5. Upload videos, logs, and SQLite snapshot.
6. Commit SQLite catalog and workflow state.

إذا فشل checkout في خطوة **Checkout reusable AI Router**، فالمشكلة غالباً في `AI_ROUTER_REPO_TOKEN`. إذا فشل توليد AI لكن استمر الفيديو باستخدام fallback، فالمشكلة في مفاتيح Gemini أو Hugging Face، ويجب قراءة سجل الخطأ دون نشر قيمة المفتاح.

---

# القسم العاشر: ماذا أعدل إذا أردت تغييراً معيناً؟

| المطلوب | الملف | التعديل |
| --- | --- | --- |
| جعل Flash-Lite قبل Flash | `config/models.json` | بدّل ترتيب العنصرين داخل chain |
| تعطيل Hugging Face | `config/models.json` | ضع `enabled: false` على نموذج Hugging Face |
| إضافة مفتاح Gemini | `.env` محلياً أو GitHub Secret | أضف عنصراً جديداً إلى JSON مع `id` و`key` و`project` |
| تغيير اسم secret | `config/key_pools.json` | غيّر قيمة `env` ثم استخدم الاسم الجديد في البيئة |
| زيادة مدة تبريد 429 | `config/policies.json` | عدّل `cooldowns_seconds.quota` |
| إضافة chain جديدة | `config/models.json` | أضف اسماً جديداً مثل `fast` أو `long_form` |
| استخدام chain جديدة في Python | كود المشروع المستهلك | غيّر `chain="default"` إلى اسم chain الجديدة |
| تغيير عنوان API | `config/providers.json` | عدّل `base_url` فقط إذا كان المزود نفسه |
| إضافة مزود OpenAI-compatible | `providers.json`, `key_pools.json`, `models.json` | أضف المزود ومفتاحه ونموذجه |
| إضافة مزود API خاص | `src/ai_router/providers/` ثم `router.py` | أنشئ adapter يطبق الواجهة الموحدة |
| تغيير مكان قاعدة الحالة | متغير `AI_ROUTER_STATE_DB` | ضع مسار SQLite آخر |

---

# القسم الحادي عشر: مشكلات شائعة وحلولها

| الرسالة أو المشكلة | السبب المحتمل | الحل خطوة بخطوة |
| --- | --- | --- |
| `ModuleNotFoundError: ai_router` | لم تثبت الحزمة أو البيئة غير مفعلة | فعّل `.venv` ثم نفّذ `python -m pip install -e .` |
| `No such file or directory: config/providers.json` | شغلت الأمر من مجلد آخر أو مررت مساراً خاطئاً | انتقل إلى جذر المشروع أو استخدم `--config-dir /المسار/الكامل/config` |
| `AI_ROUTER_GEMINI_KEYS_JSON must contain a JSON array` | قيمة المتغير ليست JSON صالحاً | استخدم مصفوفة تبدأ بـ `[` وتنتهي بـ `]`، وتأكد من علامات الاقتباس |
| `secrets_loaded` تساوي صفر | `.env` غير موجود أو اسم المتغير خاطئ | انسخ `.env.example` إلى `.env` وتأكد من الاسم exact |
| `AllProvidersFailed` | كل المفاتيح أو النماذج فشلت | افحص `data/ai_router.db`، اختبر المفتاح، ثم جرّب fallback |
| خطأ 401 أو 403 | مفتاح غير صحيح أو لا يملك الصلاحية | أنشئ مفتاحاً جديداً أو أصلح صلاحية الحساب، ولا تكرر المفتاح الفاشل بلا تغيير |
| خطأ 429 | انتهى المعدل أو الحصة المؤقتة | انتظر التبريد، أضف مزوداً احتياطياً، أو عدّل chain وفق حصتك |
| JSON غير صالح من النموذج | النموذج لم يلتزم بصيغة JSON | اترك `response_format` كما هو، وشدد system prompt على `Return JSON only` |
| GitHub Actions لا يستطيع checkout | المستودع المستقل خاص وtoken غير موجود | أضف `AI_ROUTER_REPO_TOKEN` في مستودع الفيديو بصلاحية قراءة |
| ظهرت المفاتيح في Git | تم وضعها في ملف أو commit | ألغِ المفتاح فوراً من مزوده، نظّف commit إن لزم، واستخدم GitHub Secrets |

---

# القسم الثاني عشر: فحص أمان بسيط قبل الرفع

قبل `git push` نفّذ:

```bash
git status
git diff -- .env config/
git grep -nE 'AIza[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{20,}' || true
```

يجب ألا ترى مفتاحاً حقيقياً. وجود النصوص الشكلية مثل `AIza...` داخل التوثيق ليس مفتاحاً حقيقياً، لكن لا تستبدلها بقيمك داخل README.

تأكد أيضاً من أن `.env` ليس ضمن الملفات المتعقبة:

```bash
git ls-files .env
```

يجب ألا يطبع شيئاً.

---

# الحالة التشغيلية المؤكدة للمخرجات

الجدول التالي يفرق بين ما تم اختباره فعليًا وما تم التحقق من خطة مساره فقط:

| الفئة | المسار | المدخل | المخرج | الحالة الأخيرة |
|---|---|---|---|---|
| Text/JSON | `text` | نص أو وسائط متعددة حسب النموذج | نص/JSON | يعمل في الاختبارات الحية |
| Search grounding | `text_grounded_search` | سؤال حديث | نص مع citations | يعمل في الاختبارات الحية |
| Maps grounding | `text_grounded_maps` | سؤال عن مكان أو مسار | نص مع بيانات أماكن | يعمل في الاختبارات الحية |
| Image | `image` | نص أو صورة مرجعية | صورة | المسار صحيح، لكن الحصة أعادت `429 RESOURCE_EXHAUSTED` لكل المفاتيح الستة |
| TTS | `audio` | نص وتعليمات صوت | PCM audio | **نجح فعليًا**؛ MIME `audio/l16; rate=24000; channels=1` |
| Embedding | `embedding` | نص | متجه embedding | يعمل فعليًا؛ أبعاد 3072 في الاختبار السابق |
| Live | `live` | نص/صورة/صوت/فيديو | تدفق نص/صوت | route plan فقط؛ يحتاج WebSocket adapter |
| Video generation | `video_generation` | prompt فيديو | job فيديو | غير مفعّل؛ لا يوجد Veo في جدول available-limits المرفق |

للتفاصيل القابلة لإعادة الإنتاج، راجع [دليل التشغيل](docs/operations.md) و[كتالوج النماذج والحدود](docs/model-catalog.md). يحتوي دليل التشغيل على روابط GitHub Actions وتقارير smoke المنزوعة الحساسية، ولا يحتوي قيم المفاتيح.

# القسم الثالث عشر: كيف تعرف أن النظام يعمل؟

النظام يعمل بالشكل الصحيح إذا تحققت الشروط التالية:

1. تنجح اختبارات `unittest` وتظهر `OK`.
2. يعرض أمر `summary` المزودات والنماذج وعدد الأسرار، دون عرض القيم السرية.
3. ينفذ `call-json` ويرجع JSON.
4. يزيد عدد `calls` في SQLite بعد الطلب.
5. عند تعمد تعطيل المفتاح الأول، ينتقل الطلب إلى المفتاح التالي بدلاً من التوقف مباشرة.
6. عند حذف كل المفاتيح، يظهر `AllProvidersFailed` بصورة واضحة، ويستطيع المشروع المستهلك استخدام fallback الخاص به.

أعد تشغيل الاختبار الكامل في أي وقت عبر:

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -v
ai-router --config-dir config --state-db /tmp/ai-router-check.db summary
```

---

# مراجع رسمية

[1] [Google Gemini API — Models](https://ai.google.dev/gemini-api/docs/models)

[2] [Google Gemini API — Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)

[3] [Hugging Face — Inference Providers](https://huggingface.co/docs/inference-providers/en/index)

[4] [GitHub Actions — Secrets](https://docs.github.com/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)

[8] [OpenRouter Free Models collection](https://openrouter.ai/collections/free-models)

[9] [OpenRouter Free Models Router](https://openrouter.ai/openrouter/free)

[10] [OpenRouter Models API](https://openrouter.ai/api/v1/models)

[7] [Google Gemini API — Nano Banana image generation via generateContent](https://ai.google.dev/gemini-api/docs/generate-content/image-generation)

## آخر اختبار حي بالمفاتيح الجديدة

بعد إضافة `HF_TOKEN` و`OPENROUTER_API_KEY` إلى GitHub Secrets، شُغّل [workflow الكامل](https://github.com/ysrg2003/ai-provider-router/actions/runs/31931217466) على commit `dc65957`. حُمّل `huggingface: 1` و`openrouter: 1` إلى جانب مفاتيح Gemini الستة، ونجح سيناريو OpenRouter الفعلي عبر `openrouter_free`. نجحت أيضًا مسارات النص وSearch وMaps وTTS وEmbedding؛ أما Image ففشل بسبب `RESOURCE_EXHAUSTED/429` في حصة Gemini الحالية، وليس بسبب خطأ في endpoint أو أسماء النماذج. Live وVideo generation وVideo analysis بقيت `route_plan_only` لأنها تحتاج adapters متخصصة.

المحصلة: **9 حالات ناجحة أو مخططة من أصل 10**. أُصلح أثناء التشغيل خطأ برمجي كان يمنع تمرير `chain` إلى `complete_auto()`، وأضيف اختبار حماية لذلك في commit `dc65957`. راجع [دليل التشغيل](docs/operations.md) للتقرير التفصيلي والـartifact المنزوع الحساسية.

## مسارات المخرجات والاكتشاف التلقائي

لم يعد `default` هو المسار الوحيد. يعرّف `config/models.json` قسم `output_routes` سلاسل مستقلة حسب المخرج المطلوب، ويختار `complete_auto()` المسار تلقائيًا من كلمات الطلب أو من `output_type` الصريح.

| نوع الطلب | المسار | المخرجات | التنفيذ الحالي |
|---|---|---|---|
| نص أو JSON | `text` | نص | Gemini ثم Hugging Face |
| صورة | `image` | Base64 image block | Nano Banana عبر `generateContent`؛ Imagen 4 في `image_legacy` فقط |
| OpenRouter free | `openrouter_free` | نص، وبعض النماذج تستقبل صورة/فيديو/صوت | نص/JSON | OpenRouter chat completions مع تدوير النماذج والمفاتيح |
| صوت من نص | `audio` | PCM audio | Gemini TTS |
| متجهات | `embedding` | embedding vectors | Gemini Embeddings |
| تحليل فيديو | `video_analysis` | نص/JSON | Gemini Interactions |
| محادثة مباشرة | `live` | Audio/Text stream | route plan فقط؛ يحتاج WebSocket session adapter |
| توليد فيديو | `video_generation` | Video/Audio job | route plan فقط؛ يحتاج Veo async adapter |

مثال لاكتشاف المسار دون إرسال طلب خارجي:

```bash
PYTHONPATH=src python -m ai_router.cli.main \
  --config-dir config --state-db data/ai_router.db \
  route-plan --user "أنشئ صورة لمدينة مستقبلية مع مصادر حديثة"
```

وللتنفيذ الفعلي بعد إعداد الأسرار:

```bash
PYTHONPATH=src python -m ai_router.cli.main \
  --config-dir config --state-db data/ai_router.db \
  call-auto --user "حوّل هذا النص إلى صوت: مرحبًا بك" \
  --output-type audio --voice Kore
```

## Grounding كقدرة مستقلة

عند طلب `google_search` أو `google_maps`، يختار الراوتر مسارًا يحتوي فقط على نماذج معلن دعمها للأداة. مسار `text_grounded_search` يستخدم الآن Gemini `GenerateContent` مع payload `tools: [{"google_search": {}}]`، لأن هذا هو المسار الذي يطابق مثال Google GenAI ويعيد `groundingMetadata` وURL citations. أما المسارات التفاعلية الأخرى فتستمر عبر Interactions API. إذا كان النموذج الأساسي لا يملك Grounding، لا يرسل الراوتر إليه tool غير مدعوم؛ بل ينتقل إلى نموذج Gemini في مسار grounded مناسب. هذا يحافظ على صحة الإسناد بدل إنتاج إجابة تبدو grounded وهي ليست كذلك.

نتيجة Grounding تعيد `annotations` و`grounding_metadata`، ويمكن للتطبيق إظهار citations واستخراج روابط المصادر. في Google Maps يجب عرض إسناد Google Maps للمستخدم، وفي Google Search يمكن عرض روابط `url_citation` التي يعيدها API [5] [6]. لا يتم تمرير Google Search أو Google Maps تلقائيًا إلى Hugging Face، لأن adapter OpenAI-compatible لا يملك هذه الأدوات من تلقاء نفسه؛ لإضافة fallback خارجي لـ Hugging Face نحتاج مزود Search/Maps مستقلًا ومفاتيحه.

المسارات `live` و`video_generation` تعرض خطة اختيار النموذج فقط في هذه المرحلة. Live يحتاج WebSocket stateful، وVeo يحتاج job creation/polling؛ لذلك لا تُعامل هذه العمليات كطلب JSON قصير.

### المراجع

[5]: https://ai.google.dev/gemini-api/docs/google-search "Grounding with Google Search — Google AI for Developers"
[6]: https://ai.google.dev/gemini-api/docs/maps-grounding "Grounding with Google Maps — Google AI for Developers"


## التشغيل الحي والأسرار

لإعداد `AI_ROUTER_GEMINI_KEYS_JSON` و`AI_ROUTER_OPENROUTER_KEYS_JSON` وتشغيل السيناريوهات الحية بأمان، راجع [دليل التشغيل والأسرار](docs/operations.md). يبدأ الدليل بفحص `routing` المحلي الذي لا يستهلك حصة، ثم يشرح تشغيل `text` و`search` و`maps` و`image` و`audio` و`embedding` و`openrouter_free` كلًّا على حدة، مع تفسير `403` و`404` و`429` وتدوير المفاتيح. لاحظ أن `429` في Image بعد استخدام `generateContent` يعني نفاد الحصة، بينما `404` التاريخي كان خاصًا بـImagen 4 legacy. OpenRouter له rate limits وحصة مجانية مستقلة.


## استخدام chatgpt-api لتوليد الصور كأول خيار

يدعم الراوتر الآن مشروع [chatgpt-api](https://github.com/ysrg2003/chatgpt-api) المستضاف في [Hugging Face Space](https://yousefsg-chatgpt-api.hf.space) كأول خيار في مسار `image`. هذا المسار يرسل prompt نصيًا إلى job queue الخاصة بالـSpace، ينتظر اكتمال المهمة، ثم يعيد الصورة بصيغة Base64 و`mime_type` موحدين مع مخرجات Gemini.

لتمكينه، يجب أن تكون قيمة `API_KEY` الموجودة في إعدادات Space محفوظة أيضًا في Secrets الخاصة بمستودع الراوتر باسم `CHATGPT_API_KEY`. ويمكن استخدام `AI_ROUTER_CHATGPT_IMAGE_KEYS_JSON` عند الحاجة إلى تدوير أكثر من مفتاح. لا تضع المفتاح في `config/` أو `.env` committed أو أي تقرير.

يصبح الترتيب التنفيذي لمسار الصورة:

```text
1. chatgpt_image / chatgpt-api
2. Gemini Native Image / gemini-3-pro-image
3. Gemini Native Image / gemini-3.1-flash-image
4. Gemini Native Image / gemini-3.1-flash-lite-image
5. Gemini Native Image / gemini-2.5-flash-image
```

إذا كان مفتاح `CHATGPT_API_KEY` غائبًا أو أعاد الـSpace خطأ مصادقة أو فشلت المهمة أو انتهت مهلة polling، ينتقل الراوتر تلقائيًا إلى Gemini. يدعم ChatGPT Space في هذا المسار prompt نصيًا إلى صورة؛ أما image-input editing فيبقى مسارًا منفصلًا ولا تُرسل الصورة إلى endpoint النصي كأنها نص.

للتأكد من الترتيب دون طلب خارجي:

```bash
PYTHONPATH=src python -m ai_router.cli.main \
  --config-dir config --state-db /tmp/ai-router-image.db \
  route-plan --user "أنشئ صورة لدائرة زرقاء على خلفية بيضاء"
```

يجب أن يظهر `chatgpt_image/chatgpt-api` كأول عنصر في route `image`. الاختبار الحي يتطلب إضافة `CHATGPT_API_KEY` إلى مستودع الراوتر، لأن Secret الموجود داخل Space لا يمكن للراوتر قراءته تلقائيًا.
