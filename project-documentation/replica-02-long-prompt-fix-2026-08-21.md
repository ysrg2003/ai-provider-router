# إصلاح فشل النصوص الطويلة في replica-02 — 2026-08-21

## النتيجة التنفيذية

كان فشل replica-02 عند prompts قريبة من 1,000 حرف ناتجًا عن مسار إدخال بطيء داخل محرر ChatGPT ProseMirror، وليس حدًا ثابتًا لطول prompt أو نفاد quota.

## الدليل

في `chatgpt-api`، الحد الافتراضي `MAX_PROMPT_CHARS=50000`. إذا تجاوز prompt هذا الحد، يعيد `main.py` HTTP 400 برسالة `Prompt is empty or too large`. أما HTTP 503 الذي ظهر فعليًا فكان ينتج بعد فشل `BrowserGateway._submit_prompt()`.

سجل Space-02 أثبت أن المحرر كان:

| الإشارة | القيمة |
|---|---|
| `#prompt-textarea` | ظاهر وقابل للتحرير |
| النوع | ProseMirror `div[contenteditable=true]` |
| الفشل | `Locator.press_sequentially: Timeout 12000ms exceeded` |
| النتيجة | `POST /v1/chat/completions` أعاد 503 |

المسار القديم كان يستخدم `press_sequentially(prompt, delay=5, timeout=12_000)`. هذا يعني انتظارًا ثابتًا لكل حرف، ولذلك ينتهي timeout مع prompt أطول.

## الإصلاح

أُضيف `_populate_input()` إلى source `browser_gateway.py`:

1. `fill()` بمهلة 20 ثانية.
2. عند رفض ProseMirror لـ`fill()`، استخدام `keyboard.insert_text(prompt)` كعملية إدخال واحدة سريعة.
3. استخدام `press_sequentially(..., delay=0)` كـfallback أخير مع timeout مرتبط بطول النص.
4. التحقق من محتوى المحرر قبل dispatch للإدخال ثم Enter/send-button.

أُضيف regression test لطلب ProseMirror بطول 1,500 حرف.

## النشر والتحقق

| العنصر | النتيجة |
|---|---|
| source tests | 15 اختبارًا ناجحًا |
| router tests بعد merge remote | 68 اختبارًا ناجحًا |
| source commit | `967517d` |
| router merge commit | `3d83448` |
| Space-02 commit | `b623ed6` |
| SHA256 source/vendor | متطابق |
| Space-02 بعد النشر | HTTP 200 لطلب نصي بطول 1,500 حرف مع استجابة غير فارغة |
| الصور | لم تُختبر ولم تُرسل |
| replica-01 | لم تُعدّل |
| replica-04 | لم تُلمس |

تم حذف ملفات المصادقة والـprobe المؤقتة بعد الاختبار. لم تُحفظ Cookies أو Storage State أو API secrets أو prompt body في Git أو artifacts.
