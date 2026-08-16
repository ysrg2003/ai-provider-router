# استخدام الراوتر من مشروع آخر عبر GitHub Actions

هذا المسار مناسب عندما يكون لديك مستودع host مستقل وتريد تشغيل `ai-provider-router` من workflow، ثم حفظ تقرير JSON منقح كـartifact. لا تضع cookies ChatGPT في host router؛ cookies تبقى في خدمة `chatgpt-api` أو Space.

## قبل البدء

| العنصر | القيمة المطلوبة |
|---|---|
| مستودع host | `OWNER/HOST-REPOSITORY` الذي سيحتوي workflow |
| ملف workflow | `.github/workflows/ai-router-smoke.yml` |
| مصدر الراوتر | commit مثبت من `https://github.com/ysrg2003/ai-provider-router` |
| Python | 3.11 |
| Secrets | فقط provider keys التي يحتاجها السيناريو |
| Variables | `ROUTER_SCENARIO` اختياري؛ لا تستخدم Variables للمفاتيح |
| artifact | `ai-router-report-${{ github.run_id }}` لمدة 7 أيام في المثال |

## الخطوة 1: إنشاء Secret في مستودع host

نفّذ الخطوات من GitHub في مستودع host، وليس في مستودع الراوتر:

1. افتح `https://github.com/OWNER/HOST-REPOSITORY`.
2. اختر **Settings**.
3. اختر **Secrets and variables → Actions**.
4. اختر تبويب **Secrets**.
5. اضغط **New repository secret**.
6. اكتب اسمًا مثل `CHATGPT_API_KEY` أو `AI_ROUTER_GEMINI_KEYS_JSON`.
7. الصق القيمة في **Secret**، ثم اضغط **Add secret**.
8. كرر الخطوات فقط للمزودات التي سيستخدمها workflow.

النجاح يعني ظهور اسم السر فقط في قائمة Secrets، لا قيمته. إذا لم يظهر الاسم، تحقق من صلاحية **Admin** أو **Maintain** في المستودع الصحيح.

## الخطوة 2: إنشاء workflow كامل

أنشئ الملف `.github/workflows/ai-router-smoke.yml` في مستودع host:

```yaml
name: AI router smoke

on:
  workflow_dispatch:
    inputs:
      scenario:
        description: "Bounded scenario"
        required: true
        type: choice
        default: text
        options:
          - routing
          - text
          - image
          - openrouter
          - search
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ai-router-${{ github.repository }}-${{ inputs.scenario || 'text' }}
  cancel-in-progress: false

env:
  ROUTER_COMMIT: 31407d2
  SMOKE_SCENARIO: ${{ inputs.scenario || 'text' }}

jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Check out host project
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Download pinned router source
        run: |
          set -euo pipefail
          git clone https://github.com/ysrg2003/ai-provider-router.git router
          git -C router checkout "$ROUTER_COMMIT"

      - name: Install router dependencies
        working-directory: router
        run: python -m pip install -r requirements.txt

      - name: Run offline tests
        working-directory: router
        run: PYTHONPATH=src python -m unittest discover -s tests -v

      - name: Run one bounded smoke scenario
        working-directory: router
        env:
          AI_ROUTER_GEMINI_KEYS_JSON: ${{ secrets.AI_ROUTER_GEMINI_KEYS_JSON }}
          AI_ROUTER_HF_KEYS_JSON: ${{ secrets.AI_ROUTER_HF_KEYS_JSON }}
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
          AI_ROUTER_OPENROUTER_KEYS_JSON: ${{ secrets.AI_ROUTER_OPENROUTER_KEYS_JSON }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          CHATGPT_API_KEY: ${{ secrets.CHATGPT_API_KEY }}
          SMOKE_STATE_DB: /tmp/ai-router-smoke.db
        run: |
          set -euo pipefail
          mkdir -p artifacts
          PYTHONPATH=src python scripts/live_smoke.py | tee artifacts/live-smoke.json
          grep -q '"status": "completed"' artifacts/live-smoke.json

      - name: Upload redacted report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ai-router-report-${{ github.run_id }}
          path: router/artifacts/live-smoke.json
          retention-days: 7
```

غيّر `ROUTER_COMMIT` إلى commit معتمد بعد مراجعة release. لا تضع `CHATGPT_COOKIES_NETSCAPE` في هذا workflow. إذا كان السيناريو `image` أو `text` يعتمد على ChatGPT، يحتاج `CHATGPT_API_KEY` فقط، بينما cookies تظل في Space.

## الخطوة 3: أول تشغيل

1. افتح تبويب **Actions** في مستودع host.
2. اختر **AI router smoke**.
3. اضغط **Run workflow**.
4. اختر branch `main`.
5. اختر `text` في `scenario` أولًا؛ لا تبدأ بالصورة أو `all`.
6. اضغط **Run workflow**.
7. افتح التشغيل الجديد وانتظر انتهاء steps.
8. افتح artifact باسم `ai-router-report-RUN_ID`.
9. افحص أن JSON يحتوي `status: completed` وأن نتيجة السيناريو `passed`.

علامة النجاح ليست اللون الأخضر وحده. يجب أن يوجد ملف artifact صالح وأن يثبت `passed_or_planned` نجاح السيناريو. فشل **Download pinned router source** يعني commit أو شبكة، وفشل **Run offline tests** يعني مشكلة مصدر/اعتماديات، وفشل **Run one bounded smoke scenario** يعني secret أو provider أو quota.

## الخطوة 4: إضافة ChatGPT conversation

في خدمة `chatgpt-api`/Space، ضع `API_SECRET_KEY` و`CHATGPT_COOKIES_NETSCAPE`. في host ضع القيمة المطابقة لـ`API_SECRET_KEY` باسم `CHATGPT_API_KEY`. افحص `/v1/models` أولًا، ثم شغّل `text`، ثم `image`. لا ترسل cookies إلى host أو الراوتر.

## الخطوة 5: التحديث والرجوع

للتحديث، غيّر `ROUTER_COMMIT` إلى commit جديد، شغّل offline tests، ثم شغّل scenario `routing` أو `text`. إذا فشل، أعد `ROUTER_COMMIT` إلى القيمة السابقة وأعد التشغيل. لا تستخدم `git pull` غير مثبت في workflow الإنتاجي.

## الاختبار والتكلفة

`routing` لا ينفذ generation request ويستهلك provider quota فقط إذا كان route plan يستدعي خدمة خارجية، بينما `text`, `image`, `search`, و`openrouter` قد تستهلك الحصة. شغّل سيناريو واحدًا في كل مرة. التنفيذ داخل الراوتر تسلسلي، لذلك لا يرسل نفس الطلب إلى ChatGPT وGemini معًا؛ fallback يحدث بعد انتهاء أو فشل المحاولة الحالية.

## مراجع

[1]: https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions "GitHub Actions Secrets"
[2]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch "workflow_dispatch"
[3]: https://github.com/ysrg2003/ai-provider-router "ai-provider-router"
[4]: https://github.com/ysrg2003/chatgpt-api "chatgpt-api"
