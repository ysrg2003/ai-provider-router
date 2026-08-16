# استكشاف الأخطاء

ابدأ دائمًا بفحص محلي offline، ثم route plan، ثم health للـprovider، ثم smoke محدود. لا تبدأ `all` قبل تحديد الفئة التي فشلت.

## لا توجد مفاتيح محملة

إذا كان `summary.config.secrets_loaded` يساوي صفرًا، قارن اسم environment مع `config/key_pools.json`. الاسم الحالي لـOpenRouter هو `AI_ROUTER_OPENROUTER_KEYS_JSON`، مع fallback `OPENROUTER_API_KEY`. لا تعتمد على اسم مكتوب في ملف قديم.

استخدم قيمة تجريبية وهمية فقط في الاختبارات offline. لا تستخدم `printenv` أو `echo "$SECRET"` للتحقق من secret حقيقي؛ يكفي فحص أن summary يعرض count دون value.

## `AllProvidersFailed`

هذا يعني أن كل المحاولات التي سُمح بها في route انتهت بالفشل أو تم تجاوزها بسبب cooldown. افتح آخر 12 محاولة في رسالة الخطأ، وابدأ بأول خطأ زمنيًا. `auth` يحتاج تدوير السر، `quota` يحتاج الانتظار أو key pool آخر، و`transient` يحتاج التحقق من الشبكة أو endpoint.

لا تخلط بين فشل provider الأول وفشل route كامل. إذا فشل ChatGPT conversation، يجب أن ترى انتقالًا إلى `chatgpt_image` أو Gemini في image route عندما تكون keys متاحة.

## ChatGPT health يعمل لكن النص/الصورة تفشل

افحص الخدمة مباشرة:

```bash
curl --fail https://yousefsg-chatgpt-api.hf.space/
curl --fail https://yousefsg-chatgpt-api.hf.space/v1/models \
  --header "Authorization: Bearer $CHATGPT_API_KEY"
```

health يثبت أن Uvicorn يعمل فقط. طلب النص يثبت Authorization والجلسة. طلب الصورة يحتاج أيضًا أن تظهر صورة في رد المساعد. إذا انتهت cookies، حدّث `CHATGPT_COOKIES_NETSCAPE` في Space، لا في الراوتر.

## بحث حي بلا مصادر

استخدم نصًا صريحًا يحتوي `ابحث في الويب بحث حي` واطلب الروابط. route plan الصحيح هو `text_grounded_search` وأول provider هو `chatgpt_conversation`. إذا فشل، يجب أن يظهر fallback Gemini `gemini-2.5-flash` مع grounded search. افحص `annotations` أو وجود روابط في النص، ولا تعتبر إجابة عامة بحثًا حيًا.

## OpenRouter لا يعمل

تحقق من أن `AI_ROUTER_OPENROUTER_KEYS_JSON` يحتوي JSON array صالحًا أو أن `OPENROUTER_API_KEY` موجود. تحقق من أن model موجود ومفعّل في `openrouter_free`. بعض النماذج المجانية لا تدعم `response_format` أو أنواع إدخال معينة؛ لا تغير method إلى `json` إذا كان provider لا يدعمها.

## JSON أو import failure

نفّذ:

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m json.tool config/key_pools.json >/dev/null
python3 -m json.tool config/policies.json >/dev/null
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

إذا فشل JSON، لا تشغّل live smoke. أصلح الفاصلة أو النوع أولًا. إذا فشل import، تحقق من virtualenv و`PYTHONPATH=src`.

## SQLite أو state قديم

يحفظ SQLite cursor وcooldown. قد يبدو model متجاوزًا رغم أن key جديدًا يعمل لأن state قديم. أوقف العمليات، احتفظ بنسخة من `data/ai_router.db`، ثم استخدم DB جديدة للاختبار. لا تحذف state أثناء تشغيل worker.

## GitHub Actions يفشل قبل الطلب

تحقق من أن secret names مضافة في المستودع وأن workflow اختار scenario صحيحًا. `permissions` الحالية `contents: read`، وartifact يحتفظ بالتقرير 7 أيام. إذا كان `loaded_key_counts` صفرًا فالخلل في Secrets، لا في provider.

## أخطاء أمنية

إذا ظهر secret أو cookie في log، أوقف التشغيل، ألغِ القيمة ودوّرها، احذف artifact المتأثر، ثم راجع Git history. لا تكتفِ بحذف السطر من آخر commit لأن القيمة قد تبقى في التاريخ.

## المراجع

[1]: https://github.com/ysrg2003/ai-provider-router "الراوتر"
[2]: https://github.com/ysrg2003/chatgpt-api "خدمة ChatGPT"
[3]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Secrets"
