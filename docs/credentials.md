# بطاقات الأسرار والمتغيرات

لا يحتاج `ai-provider-router` إلى cookies ChatGPT. cookies تبقى داخل خدمة `chatgpt-api` فقط. كل قيمة أدناه تُحفظ في environment محلي أو GitHub Secret، ولا تُكتب في `config/` أو logs.

## `AI_ROUTER_GEMINI_KEYS_JSON`

| الحقل | التفاصيل |
|---|---|
| التصنيف | Secret؛ JSON key pool |
| مطلوب؟ | مطلوب فقط لمسارات Gemini |
| من أين تحصل عليه | افتح [Google AI Studio API Keys][1] بالحساب الذي يملك مشروعًا/صلاحية Gemini، وأنشئ API key أو استخدم key موجودًا في المشروع الصحيح. |
| الصيغة | JSON array أو wrapper تقبله `config.py`، مثل `[ {"id":"gemini-1","key":"REDACTED","project":"optional"} ]` |
| التخزين | محليًا في `.env` غير المتعقب، أو GitHub **Settings → Secrets and variables → Actions → New repository secret** بنفس الاسم |
| فحص الصحة | شغّل `route_plan` أولًا، ثم smoke `text` أو `image` عند اختيار route Gemini؛ لا تطبع key |
| النجاح | `secrets_loaded` يحتوي العدد المتوقع ونتيجة provider تمر |
| الفشل | `401/403`: تحقق من key/project؛ `429`: انتظر الحصة أو انتقل إلى key آخر |
| التدوير والإلغاء | احذف key القديم من Google AI Studio، أنشئ بديلًا، حدّث secret، ثم أعد smoke محدودًا |

**الخطوات:**

1. افتح [aistudio.google.com/apikey][1] وسجّل الدخول بالحساب الصحيح.
2. اختر المشروع المطلوب أو أنشئ مشروعًا إذا كانت الصفحة تطلب ذلك.
3. اضغط **Create API key** أو انسخ key موجودًا بصلاحية مناسبة.
4. ضع key في JSON array داخل Secret `AI_ROUTER_GEMINI_KEYS_JSON`.
5. شغّل فحص JSON و`route_plan`؛ إذا ظهر صفر في `secrets_loaded` فاسم secret أو صيغة JSON غير صحيحة.

## `AI_ROUTER_HF_KEYS_JSON` أو `HF_TOKEN`

| الحقل | التفاصيل |
|---|---|
| التصنيف | Secret؛ access token لـHugging Face |
| مطلوب؟ | اختياري، ويحتاجه route Hugging Face |
| من أين تحصل عليه | افتح [Hugging Face User Access Tokens][2]، اختر **Create new token**، وحدد أقل صلاحية لازمة للـInference. |
| الصيغة | `HF_TOKEN` token واحد، أو JSON array في `AI_ROUTER_HF_KEYS_JSON` |
| التخزين | GitHub Secret أو environment محلي؛ لا تضعه في README أو model config |
| فحص الصحة | شغّل route يختار Hugging Face أو اختبر model endpoint المحدد في provider config |
| النجاح | provider يعيد response غير `401/403` |
| الفشل | راجع صلاحية token، model availability، و429/503 من inference service |
| التدوير والإلغاء | من صفحة tokens احذف token القديم وأنشئ بديلًا، ثم حدّث secret |

**الخطوات:**

1. افتح [huggingface.co/settings/tokens][2].
2. اضغط **Create new token**، اختر أقل permission يدعم الاستخدام المطلوب، ثم أنشئ token.
3. خزّنه في `HF_TOKEN` إذا كان token واحدًا، أو حوّله إلى JSON pool في `AI_ROUTER_HF_KEYS_JSON`.
4. شغّل الاختبارات offline ثم smoke محدودًا لمسار Hugging Face.

## `AI_ROUTER_OPENROUTER_KEYS_JSON` أو `OPENROUTER_API_KEY`

| الحقل | التفاصيل |
|---|---|
| التصنيف | Secret؛ OpenRouter API key |
| مطلوب؟ | اختياري، ويحتاجه `openrouter_free` أو provider OpenRouter |
| من أين تحصل عليه | افتح [OpenRouter API Keys][3] بعد تسجيل الدخول، واضغط **Create Key**. تحقق من القيود والرصيد/الحصة في الحساب قبل الاختبار. |
| الصيغة | `OPENROUTER_API_KEY` token واحد، أو JSON array في `AI_ROUTER_OPENROUTER_KEYS_JSON` |
| التخزين | environment محلي أو GitHub Secret؛ لا تضعه في `providers.json` |
| فحص الصحة | استخدم `route_plan(..., chain="openrouter_free")` ثم smoke `openrouter` |
| النجاح | التقرير يعرض route OpenRouter و`status=passed` |
| الفشل | `401`: key خاطئ؛ `429`: quota/rate limit؛ model غير موجود: حدّث catalog من [OpenRouter Models][4] |
| التدوير والإلغاء | احذف key من OpenRouter Settings، أنشئ key جديدًا، وحدّث secret دون تعديل الكود |

**الخطوات:**

1. افتح [openrouter.ai/settings/keys][3].
2. اضغط **Create Key**، سمّه باسم يوضح البيئة، ولا تمنحه أكثر مما يلزم.
3. ضع القيمة في `OPENROUTER_API_KEY` أو في `AI_ROUTER_OPENROUTER_KEYS_JSON` بصيغة JSON صالحة.
4. تحقق من الاسم عبر `config/key_pools.json` ثم شغّل smoke `openrouter` مرة واحدة.

## `CHATGPT_API_KEY` أو `AI_ROUTER_CHATGPT_CONVERSATION_KEYS_JSON`

| الحقل | التفاصيل |
|---|---|
| التصنيف | Secret للمصادقة بين الراوتر وخدمة chatgpt-api؛ ليس OpenAI key |
| مطلوب؟ | مطلوب لمسارات ChatGPT |
| من أين تحصل عليه | أنشئ قيمة عشوائية خاصة بك لتكون مساوية تمامًا لـ`API_SECRET_KEY` في خدمة chatgpt-api/Space. لا تستخرجها من ChatGPT ولا تستبدلها بـcookies. |
| الصيغة | token نصي واحد أو JSON array داخل pool |
| التخزين | `CHATGPT_API_KEY` في الراوتر و`API_SECRET_KEY` في الخدمة؛ خزّنهما في GitHub/Space Secrets حسب مكان التشغيل |
| فحص الصحة | نفّذ `/v1/models` في الخدمة باستخدام `Authorization: Bearer $CHATGPT_API_KEY`، ثم route plan، ثم طلب نص محدود |
| النجاح | `/v1/models` يعيد `200` ويصل الطلب إلى `chatgpt_conversation` |
| الفشل | `401`: القيمتان غير متطابقتين؛ timeout: افحص Space health وcookies داخل الخدمة |
| التدوير والإلغاء | أنشئ قيمة جديدة، حدّث السر في الراوتر والخدمة، أعد التشغيل، ثم احذف القديم |

**الخطوات:**

1. أنشئ سرًا عشوائيًا خاصًا بك في password manager.
2. خزّنه في خدمة chatgpt-api باسم `API_SECRET_KEY`.
3. خزّن القيمة نفسها في الراوتر باسم `CHATGPT_API_KEY` أو pool conversation.
4. نفّذ `/v1/models` ثم طلب نص واحد؛ لا تشغّل image أو `all` قبل نجاح النص.

## GitHub Actions Secrets وVariables

في مستودع الراوتر افتح **Settings → Secrets and variables → Actions**. اختر **New repository secret** لكل قيمة حساسة، ولا تستخدم **Variables** للمفاتيح. المتغيرات غير الحساسة مثل `SMOKE_SCENARIO` و`CHATGPT_IMAGE_SMOKE_TIMEOUT` تبقى داخل workflow أو Variables إذا احتاج المستخدم تغييرها.

| الاسم | Secret/Variable | يستهلكه |
|---|---|---|
| `AI_ROUTER_GEMINI_KEYS_JSON` | Secret | workflow smoke وGemini key pool |
| `AI_ROUTER_HF_KEYS_JSON` | Secret | workflow smoke وHF pool |
| `HF_TOKEN` | Secret | HF fallback |
| `AI_ROUTER_OPENROUTER_KEYS_JSON` | Secret | OpenRouter pool |
| `OPENROUTER_API_KEY` | Secret | OpenRouter fallback |
| `AI_ROUTER_CHATGPT_IMAGE_KEYS_JSON` | Secret | direct chatgpt_image diagnostic |
| `CHATGPT_API_KEY` | Secret | ChatGPT conversation/image |
| `SMOKE_SCENARIO` | Workflow input | اختيار السيناريو |
| `CHATGPT_IMAGE_SMOKE_TIMEOUT` | Non-secret variable/env | حد تشخيص direct image |

لا ترفق قيمة secret في issue أو artifact. بعد تغيير أي secret، شغّل smoke محدودًا لا `all`، وتحقق من response أو artifact المنقح.

[1]: https://aistudio.google.com/apikey "Google AI Studio API keys"
[2]: https://huggingface.co/settings/tokens "Hugging Face User Access Tokens"
[3]: https://openrouter.ai/settings/keys "OpenRouter API keys"
[4]: https://openrouter.ai/api/v1/models "OpenRouter models API"
[5]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions secrets"
