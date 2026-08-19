# نظرة عامة على ai-provider-router

## 1. ما المشروع؟

`ai-provider-router` مكتبة وCLI بلغة Python لتوحيد استدعاء عدة مزودي ذكاء اصطناعي خلف routes وmodel chains قابلة للتهيئة. يختار router المخرج، يرتب models وkeys، ينفذ طلبًا بمهلة محددة، يستخدم fallback محدودًا، ويحفظ metadata التشغيلية في SQLite.

لا يستضيف المشروع النماذج ولا ينشئ credentials ولا يضمن availability لكل model خارجي. أول دليل حقيقي على نجاح provider هو response أو artifact صالح، وليس route plan فقط.

## 2. ما استخداماته؟

يستخدمه مشروع يحتاج إلى تبديل Gemini وHugging Face وOpenRouter وNVIDIA وChatGPT Spaces دون كتابة adapter منفصل لكل تطبيق. يمكن أيضًا اختيار providers لكل طلب، أو استبعاد Gemini، أو استخدام NVIDIA Riva للترجمة، أو تنظيم keys وcooldowns عبر SQLite.

## 3. مسارات التشغيل

| المسار | البداية |
|---|---|
| GitHub Actions | checkout مثبت على tag، Secrets في GitHub، workflow manual/live smoke |
| محلي | clone، venv، `pip install -e .`، `.env`، `summary` ثم `call-auto` |
| Docker | `Dockerfile` الجذري، `docker build` ثم `docker run --env-file` |
| Python | `from ai_router import AIRouter` واستدعاء `complete_auto` |
| لغة أخرى | CLI subprocess يستهلك JSON stdout وexit code |

التفاصيل التنفيذية في [`README.md`](../README.md) و[`project-documentation/README.md`](README.md).

## 4. خريطة المشروع

| المسار | الدور |
|---|---|
| `src/ai_router/router.py` | orchestration وfallback وprovider filters |
| `src/ai_router/config.py` | `.env` وJSON وkey parsing |
| `src/ai_router/providers/` | adapters |
| `src/ai_router/store.py` | SQLite state |
| `config/` | providers/models/key pools/policies/catalog |
| `scripts/` | live smoke وcapability audit |
| `tests/` | regression وcontract tests |
| `.github/workflows/` | offline CI وmanual jobs |
| `docs/` | credentials وprovider guides |
| `project-documentation/` | guides وevidence وrelease records |

## 5. دورة الطلب

```text
input -> intent/output type -> route/chain -> provider filters
      -> model capability -> key ordering/cooldown
      -> adapter request -> response/error -> fallback/state
```

عدم تمرير provider filters يعني كل providers الموجودة في route. تمرير `--providers` يقيد القائمة، و`--exclude-providers` يستبعد مزودًا.

## 6. القدرات الحالية

| القدرة | الحالة |
|---|---|
| text | route متعدد providers |
| search/maps | عند وجود tool في model spec |
| image | Gemini وChatGPT routes، مع quota خارجية |
| audio/embedding | Gemini routes |
| translation | NVIDIA Riva route |
| video analysis | adapter و`video_uri` مطلوبان |
| video generation/live | مؤجلان أو plan-only حسب route |

## 7. الأمان

كل API keys وtokens وChatGPT session values تبقى في `.env` غير المتعقب أو GitHub Secrets. Base URLs غير سرية ويمكن ضبطها كـVariables. لا تضع Secrets في config JSON أو Docker image أو artifacts.

## 8. التحقق

```bash
python3 -m json.tool config/providers.json >/dev/null
python3 -m json.tool config/models.json >/dev/null
python3 -m compileall -q src scripts tests vendors/chatgpt-api
python3 -m unittest discover -s tests -v
```

## 9. مراجع

- [فهرس التوثيق الكامل](README.md)
- [بطاقات الاعتمادات](../docs/credentials.md)
- [دليل المزودين](providers.md)
- [دليل troubleshooting](troubleshooting.md)
- [AI_CONTEXT](../AI_CONTEXT.md)
