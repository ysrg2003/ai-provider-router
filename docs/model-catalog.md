# كتالوج النماذج والأدوات

هذا الملف مرجع القراءة البشرية لجدول الحصة المرفق وللـroutes التنفيذية. يحتوي snapshot الجدول على **24 صف Models** و**13 صف Tools**. أما نماذج ChatGPT وOpenRouter فهي مصادر خارجية مستقلة موضحة في README، ولا تُخلط مع snapshot Gemini.

> حدود quota تتغير. الأرقام هنا مرجع تاريخي مؤرخ بـ2026-08-16 وليست ضمانًا مستقبليًا. صف `Gemini 2.5 Flash` محتفظ به لأن الحصة اليومية تتجدد، وليس لأنه مستهلك دائمًا.

## Models — 24 صفًا

| النموذج | الفئة | المدخلات → المخرجات | snapshot الحد | route/الحالة |
|---|---|---|---|---|
| `Antigravity` | Agents | تعليمات وسياق → تقرير/أفعال | RPM 0/60، TPM 0/100K، RPD 0/100 | مرجع كتالوج؛ ليس adapter توليدًا عامًا |
| `Gemini 2.5 Flash` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 3/5، TPM 94.89K/250K، RPD 26/20 | text وvideo؛ الحصة اليومية تتجدد |
| `Gemini 2.5 Flash Lite` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 0/10، TPM 0/250K، RPD 0/20 | text وvideo |
| `Gemini 2.5 Flash Native Audio Dialog` | Live API | نص/صورة/صوت/فيديو → نص وصوت | RPM 0/Unlimited، TPM 0/1M، RPD 0/Unlimited | live route plan |
| `Gemini 2.5 Flash TTS` | TTS | نص وتعليمات نبرة → صوت | RPM 0/3، TPM 0/10K، RPD 0/10 | `gemini-2.5-flash-preview-tts` |
| `Gemini 3 Flash` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 0/5، TPM 0/250K، RPD 0/20 | text وvideo |
| `Gemini 3 Flash Live` | Live API | نص/صورة/صوت/فيديو → نص وصوت | RPM 0/Unlimited، TPM 0/65K، RPD 0/Unlimited | `gemini-3-flash-live-preview` |
| `Gemini 3.1 Flash Lite` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 0/15، TPM 0/250K، RPD 0/500 | text وvideo |
| `Gemini 3.1 Flash TTS` | TTS | نص وتعليمات نبرة → صوت | RPM 0/3، TPM 0/10K، RPD 0/10 | `gemini-3.1-flash-tts-preview` |
| `Gemini 3.5 Flash` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 0/5، TPM 0/250K، RPD 0/20 | text وvideo |
| `Gemini 3.5 Flash Lite` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 0/15، TPM 0/250K، RPD 0/500 | text وmaps |
| `Gemini 3.5 Live Translate` | Live API | نص/صورة/صوت/فيديو → نص وصوت | RPM 0/Unlimited، TPM 0/20K، RPD 0/Unlimited | `gemini-3.5-live-translate-preview` |
| `Gemini 3.6 Flash` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 0/5، TPM 0/250K، RPD 0/20 | text وvideo |
| `Gemini 3.7 Flash` | Text-out | نص/صورة/فيديو/صوت/PDF → نص | RPM 0/5، TPM 0/250K، RPD 0/20 | text وvideo، الأعلى ترتيبًا في Gemini |
| `Gemini Embedding 1` | Embedding | نص → متجه رقمي | RPM 0/100، TPM 0/30K، RPD 0/1K | `gemini-embedding-001` |
| `Gemini Embedding 2` | Embedding | نص → متجه رقمي | RPM 0/100، TPM 0/30K، RPD 0/1K | `gemini-embedding-2` |
| `Gemini Robotics ER 1.5 Preview` | Other | نص ومدخلات متعددة → خطة/استدلال | RPM 0/10، TPM 0/250K، RPD 0/20 | catalog reference فقط |
| `Gemini Robotics ER 1.6 Preview` | Other | نص ومدخلات متعددة → خطة/استدلال | RPM 0/5، TPM 0/250K، RPD 0/20 | catalog reference فقط |
| `Gemini Robotics ER 2 Preview` | Other | نص ومدخلات متعددة → خطة/استدلال | RPM 0/5، TPM 0/250K، RPD 0/20 | catalog reference فقط |
| `Gemma 4 26B` | Other | نص/صورة/فيديو حسب الواجهة → نص | RPM 0/30، TPM 0/16K، RPD 0/14.4K | OpenRouter catalog منفصل |
| `Gemma 4 31B` | Other | نص/صورة/فيديو حسب الواجهة → نص | RPM 0/30، TPM 0/16K، RPD 0/14.4K | OpenRouter catalog منفصل |
| `Imagen 4 Fast Generate` | Image legacy | نص → صورة | RPD 0/25 | `image_legacy` معطل |
| `Imagen 4 Generate` | Image legacy | نص → صورة | RPD 0/25 | `image_legacy` معطل |
| `Imagen 4 Ultra Generate` | Image legacy | نص → صورة | RPD 0/25 | `image_legacy` معطل |

صفوف Imagen 4 محفوظة للتتبع لكنها معطلة في `config/models.json`. لا تعيد تفعيلها دون مراجعة حالة الإيقاف الرسمية وتوافق adapter.

## Tools — 13 صفًا

| الأداة/السياق | النوع | المدخل → المخرج | snapshot RPD | الاستخدام الحالي |
|---|---|---|---:|---|
| `Computer Use Preview` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | مرجع tool |
| `Deep Research Pro Preview` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | مرجع tool |
| `Gemini 2 Flash` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | مرجع tool |
| `Gemini 2.5 Flash` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | mapping مدعوم عبر Gemini |
| `Gemini 2.5 Flash Lite` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | mapping مدعوم عبر Gemini |
| `Gemini 3.1 Flash Lite` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | mapping مدعوم عبر Gemini |
| `Gemini 3.1 Flash TTS` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | catalog reference |
| `Gemini 3.5 Flash Lite` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | أول map model في route |
| `Gemini Robotics ER 1.6 Preview` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | catalog reference |
| `Gemini Robotics ER 2 Preview` — `map_grounding` | Map grounding | سؤال مكان → نص مؤسس | 0/500 | catalog reference |
| `Default` — `search_grounding` | Search grounding | سؤال حديث → نص ومصادر | 0/1.5K | أداة مرجعية |
| `Gemini 2` — `search_grounding` | Search grounding | سؤال حديث → نص ومصادر | 0/1.5K | أداة مرجعية |
| `Gemini 2.5` — `search_grounding` | Search grounding | سؤال حديث → نص ومصادر | 3/1.5K | fallback Gemini الحالي |

Tools ليست نماذج توليد مستقلة. في الراوتر، `search` و`maps` capability metadata، ويجب ألا تضاف إلى route إلا إذا كان adapter يعرف payload المطلوب.

## Runtime mapping

| route | model IDs الحالية | المخرج |
|---|---|---|
| `text` | ChatGPT conversation ثم Gemini/HF | نص |
| `text_grounded_search` | ChatGPT conversation ثم `gemini-2.5-flash` | نص مؤسس |
| `text_grounded_maps` | Gemini 3.5 Flash Lite ثم النماذج التالية | نص مؤسس على الخرائط |
| `image` | ChatGPT conversation، `chatgpt-api`، ثم Gemini image | صورة |
| `audio` | Gemini 3.1 Flash TTS ثم 2.5 Flash TTS | صوت |
| `embedding` | Gemini Embedding 2 ثم Embedding 001 | متجه |
| `live` | ثلاثة Gemini live models | route plan حاليًا |
| `video_analysis` | text-out models | نص تحليل فيديو |

هذه الصفحة توثق snapshot ولا تستبدل فحص provider catalog الحي. راجع [Gemini API][1] و[OpenRouter free collection][2] قبل تغيير model أو quota.

[1]: https://ai.google.dev/gemini-api/docs "Gemini API Documentation"
[2]: https://openrouter.ai/collections/free-models "OpenRouter Free Models"
