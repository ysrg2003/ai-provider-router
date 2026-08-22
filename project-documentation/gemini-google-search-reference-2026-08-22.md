# Gemini Google Search grounding — reference (2026-08-22)

المصدر الرسمي: https://ai.google.dev/gemini-api/docs/google-search

توضح الوثيقة أن Google Search grounding يربط Gemini بالويب في الوقت الفعلي ويعيد annotations وروابط مصادر. توصي الصفحة الحالية بـInteractions API، لكن طلب المستخدم يستخدم GenerateContentConfig؛ لذلك يطبق router مسارًا RESTيًا صريحًا على `generateContent`، وهو المكافئ العملي لصيغة Python SDK:

```python
config = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())],
    temperature=0.3,
)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What happened today?",
    config=config,
)
```

في REST يحول adapter الأداة الداخلية `{"type": "google_search"}` إلى:

```json
{"tools": [{"google_search": {}}]}
```

تحتوي استجابة GenerateContent على `candidates[].content.parts[].text`، وقد تحتوي `candidates[].groundingMetadata.groundingChunks[].web` مع `uri` و`title`، إضافة إلى `groundingSupports`. يحول adapter هذه المصادر إلى `grounding_sources` و`url_citations`.

تذكر الوثيقة أن `google_search` هي الأداة الحالية للنماذج الحديثة، وأن `google_search_retrieval` مخصص للنماذج القديمة. في عقد router الحالي، مسار `text_grounded_search` يستخدم Gemini وحده، ويفشل بعقدة واضحة إذا لم يستخرج رابطًا موثقًا.

## GenerateContent note

صفحة مرجع GenerateContent الحالية تؤكد أن GenerateContent واجهة قائمة، وأن Google توصي بـInteractions API للوصول إلى أحدث الميزات. احتفظ router بمسار GenerateContent لأن ذلك يطابق طلب المستخدم ويدعم schema `groundingMetadata` المطلوب، مع إبقاء Interactions API للمسارات الأخرى التي تعتمد عليه.
