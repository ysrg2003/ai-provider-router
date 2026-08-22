# Artifact inventory

هذا الجرد يحدد الملفات التي يعتمد عليها التوثيق الهندسي. لا يحتوي على أسرار أو محتوى Cookies أو Storage State.

| المسار | النوع | المعرفة المستخرجة | الحساسية | الاستخدام |
|---|---|---|---|---|
| `README.md` | beginner guide | التثبيت وGitHub والمحلي وDocker وPython | منخفضة | نقطة البدء العامة |
| `AI_CONTEXT.md` | engineering context | الطبقات والعقود ودورة البيانات والقيود | منخفضة | agent/developer context |
| `project-documentation/README.md` | documentation index | ترتيب القراءة الكامل | منخفضة | فهرس التشغيل |
| `docs/credentials.md` | credential cards | acquisition/storage/rotation لكل Secret وVariable | أسماء فقط، بلا قيم | إعداد البيئة |
| `project-documentation/configuration-guide.md` | configuration guide | routes وprovider filters | منخفضة | تعديل config |
| `config/providers.json` | provider registry | IDs وkind وBase URL وtimeouts | URLs عامة | source of truth للproviders |
| `config/models.json` | route/model registry | chains وmethods وcapabilities والأولوية | منخفضة | source of truth للـroutes |
| `config/key_pools.json` | secret mapping | أسماء env vars وfallback وrotation | منخفضة | ربط config بالبيئة |
| `config/policies.json` | retry policy | attempts/backoff/cooldown | منخفضة | سلوك الفشل |
| `src/ai_router/router.py` | orchestration code | route resolution وfallback وfilters وstate | منخفضة | التنفيذ الأساسي |
| `src/ai_router/config.py` | config loader | `.env` وJSON وkey parsing وredacted summary | منخفضة | boundary config |
| `src/ai_router/store.py` | persistence code | SQLite cursor/cooldown/stats | metadata تشغيلية | state lifecycle |
| `src/ai_router/cli/main.py` | CLI entrypoint | commands وflags وprovider selectors | منخفضة | تشغيل المستخدم |
| `scripts/` | operational scripts | live smoke وcapability audit وfunctional tests | قد تتعامل مع Secrets عبر env | CI/manual operations |
| `tests/` | regression suite | contracts وfallback وmodel catalog وprovider filters | منخفضة | release gate |
| `.github/workflows/` | automation | offline CI وmanual live workflows | Secrets injected at runtime | GitHub operation |
| `Dockerfile` | container recipe | تشغيل CLI في صورة Python 3.11 | منخفضة | Docker option |
| `.dockerignore` | container boundary | منع `.env` وDB وartifacts | منخفضة | secret/data hygiene |
| `project-documentation/live-verification-2026-08-19/` | redacted evidence | نتائج smoke التاريخية | يجب ألا تحتوي secrets/base64 | evidence only |
| `project-documentation/*.png` | image evidence | artifact بصري تاريخي | راجع المحتوى قبل النشر | evidence only |

## حدود الجرد
