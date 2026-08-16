# تكامل ChatGPT conversation

هذا التكامل يستخدم HTTP boundary بين `ai-provider-router` وخدمة [`ysrg2003/chatgpt-api`][1]. الراوتر لا يستورد `main.py` ولا يحمل Playwright ولا يستلم cookies. الخدمة وحدها تملك cookies وتفتح المحادثة العادية في ChatGPT.

## البنية

```text
المشروع المستهلك
      |
      | AIRouter.complete_auto()
      v
ai-provider-router
      |
      | Authorization: Bearer CHATGPT_API_KEY
      | POST /v1/chat/completions
      v
chatgpt-api / Hugging Face Space
      |
      | CHATGPT_COOKIES_NETSCAPE داخل BrowserContext فقط
      v
chatgpt.com conversation
```

## الإعداد

في خدمة `chatgpt-api` ضع `API_SECRET_KEY` و`CHATGPT_COOKIES_NETSCAPE` كـSecrets. في الراوتر ضع `CHATGPT_API_KEY` مساويًا لـ`API_SECRET_KEY`. إذا أردت pool خاصًا بالـconversation، استخدم `AI_ROUTER_CHATGPT_CONVERSATION_KEYS_JSON`; أما fallback البسيط فهو `CHATGPT_API_KEY`.

| القيمة | مكانها | هل تُرسل إلى الراوتر؟ |
|---|---|---:|
| `CHATGPT_COOKIES_NETSCAPE` | chatgpt-api/Space | لا |
| `API_SECRET_KEY` | chatgpt-api/Space | لا؛ تُستخدم قيمتها المطابقة فقط في الراوتر |
| `CHATGPT_API_KEY` | ai-provider-router | نعم كـAuthorization للخدمة |
| `AI_ROUTER_CHATGPT_CONVERSATION_KEYS_JSON` | ai-provider-router | نعم كـpool اختياري |

لا تضع cookies في `ai-provider-router` أو في GitHub Actions لهذا المشروع. GitHub Secret الموجود في مستودع chatgpt-api لا ينتقل تلقائيًا إلى Hugging Face Space.

## الصور

عند `output_type="image"` يختار الراوتر `chatgpt_conversation/chatgpt-conversation` أولًا. يرسل adapter prompt المستخدم إلى `/v1/chat/completions`. يتوقع أن تكون `choices[0].message.content` قائمة تحتوي عنصرًا من النوع `image_url` ورابطًا يبدأ بـ`data:image/` ويحتوي Base64.

```python
from ai_router import AIRouter

router = AIRouter()
try:
    image = router.complete_auto(
        user_prompt="أنشئ صورة بسيطة لدائرة زرقاء على خلفية بيضاء.",
        output_type="image",
        operation="create_image",
    )
    print(image["mime_type"], len(image["data_base64"]))
finally:
    router.close()
```

إذا أعاد ChatGPT نصًا فقط أو Base64 غير صالح، يسجل الراوتر ProviderError ثم يجرب `chatgpt_image` وبعده Gemini image models. لا تُرسل الصورة نفسها إلى Gemini في المحاولة الأولى؛ كل provider يستلم الطلب فقط عندما يصل دوره.

## النص

عند `output_type="text"` يكون ChatGPT conversation أول route. يعيد adapter `output_type="text"` و`text`، ويحتفظ الراوتر ببيانات route وintent. إذا لم يوجد ChatGPT key صالح، يبدأ الراوتر بالنموذج التالي في route النص.

## البحث الحي

استخدم prompt صريحًا:

```text
ابحث في الويب بحث حي عن آخر أخبار الذكاء الاصطناعي، واذكر المصادر والروابط.
```

`intent.py` يكتشف markers مثل `بحث حي` و`ابحث` و`web search` ويختار `text_grounded_search`. يضيف adapter تعليمات إلى ChatGPT لتنفيذ بحث حي وذكر المصادر. لا ينفذ الراوتر بحثًا منفصلًا ولا يرسل الطلب بالتوازي إلى Gemini. عند فشل ChatGPT، يأتي Gemini `gemini-2.5-flash` مع `grounded_search` كـfallback.

يجب على التطبيق المستهلك التحقق من وجود مصادر وروابط في النص؛ status `200` وحده لا يثبت أن browsing حدث فعليًا.

## المهلة والتسلسل

الـprovider في `config/providers.json` مضبوط حاليًا على timeout قدره 270 ثانية. `_complete_route` تسلسلي: provider/model ثم key واحد في كل مرة. عند النجاح يتوقف فورًا. عند الفشل يسجل الخطأ، يحدّث cursor، يطبق backoff عند الحاجة، ثم ينتقل إلى التالي. لا يوجد fan-out أو تكرار متوازٍ للطلب الواحد.

## فحص الاتصال قبل الطلب

```bash
curl --fail https://yousefsg-chatgpt-api.hf.space/
curl --fail https://yousefsg-chatgpt-api.hf.space/v1/models \
  --header "Authorization: Bearer $CHATGPT_API_KEY"
```

إذا أعاد `/` health لكن أعاد `/v1/chat/completions` خطأ `401`، فالقيمة المطابقة بين `CHATGPT_API_KEY` و`API_SECRET_KEY` ناقصة. إذا ظهر timeout مع جلسة صالحة، اختبر الخدمة مباشرة قبل تغيير route الراوتر.

## اختبار offline

اختبارات adapter في `tests/test_chatgpt_conversation_image.py` تستخدم responses وهمية وتتحقق من استخراج النص والصورة، search instruction، و401. لا تحتاج cookies أو شبكة.

## التراجع

لإيقاف الأولوية مؤقتًا، غيّر `enabled` للعنصر `chatgpt_conversation` في routes المناسبة إلى `false`، أو احذف secret pool الخاص به مع إبقاء Gemini. نفّذ JSON validation والاختبارات، ثم راقب route plan قبل smoke حي.

[1]: https://github.com/ysrg2003/chatgpt-api "خدمة chatgpt-api"
