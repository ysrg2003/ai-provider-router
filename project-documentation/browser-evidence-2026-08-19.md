# Browser evidence — 2026-08-19

## Scope

This evidence log records observations from My Browser only. No Cookies, Storage State, API keys, Authorization headers, or personal account data are stored here.

## Step 1 — replica-01 public root

URL: `https://yousefsg-chatgpt-api-replica-01.hf.space/`

Observed response in the live browser:

```json
{"status":"running","ready":true,"service":"chatgpt-web-api","health":"/health","error":null}
```

Interpretation: the public runtime advertises `running=true` and `ready=true`; this is evidence for the HTTP service root only. It does not prove the internal ChatGPT browser/session path works. Browser screenshot upload failed twice, so no screenshot image is claimed for this step. The page HTML was saved by the browser at `/home/ubuntu/upload/yousefsg-chatgpt-api-replica-01.hf.space__1787122630239.html` for passive inspection only.

## Step 2 — replica-02 public root

URL: `https://yousefsg-chatgpt-api-replica-02.hf.space/`

Observed response:

```json
{"status":"running","ready":true,"service":"chatgpt-web-api","health":"/health","error":null}
```

Interpretation: replica-02 has the same public runtime status as replica-01. This does not prove the ChatGPT browser/session path. Browser screenshot upload failed for this page as well; the browser saved passive HTML at `/home/ubuntu/upload/yousefsg-chatgpt-api-replica-02.hf.space__1787122664152.html`.

## Step 3 — replica-04 public root

URL: `https://yousefsg-chatgpt-api-replica-04.hf.space/`

Observed response:

```json
{"status":"running","ready":true,"service":"chatgpt-web-api","health":"/health","error":null}
```

Interpretation: replica-04 also advertises a healthy public runtime root. This conflicts with the API test result of HTTP 503 on `/v1/chat/completions`, which narrows the problem to an internal request path such as browser/session/upstream handling rather than the public HTTP process itself. Browser screenshot upload failed again; passive HTML was saved at `/home/ubuntu/upload/yousefsg-chatgpt-api-replica-04.hf.space__1787122696742.html`.

## Step 4 — replica-04 Swagger UI

URL: `https://yousefsg-chatgpt-api-replica-04.hf.space/docs`

The live browser rendered Swagger UI titled `ChatGPT Web API 1.0.0 OAS 3.1`. The visible operations were:

- `GET /`
- `GET /health`
- `GET /status`
- `GET /v1/models`
- `POST /new-chat`
- `POST /v1/chat/completions`
- `POST /v1/responses`

This is evidence that the API application and its OpenAPI surface are loaded. The browser screenshot was visually captured for this step, but the browser tool did not provide a downloadable screenshot path. No endpoint was executed from Swagger and no secret was entered.

## Step 5 — replica-04 `/status` without Authorization

URL: `https://yousefsg-chatgpt-api-replica-04.hf.space/status`

The live browser displayed:

```json
{"error":{"message":"Invalid API Key","type":"authentication_error"}}
```

Interpretation: `/status` is protected and the browser request did not include the Space API secret. This is expected authentication behavior and is not proof that the internal ChatGPT session is invalid. No key was entered into the browser and no screenshot file was uploaded by the browser tool for this step.

## Step 6 — replica-04 Hugging Face Container Logs via live browser

The live browser opened the Hugging Face Space page and the Logs tab for `Yousefsg/chatgpt-api-replica-04`. The Space UI showed `Running`, and the visible logs showed the following redacted operational pattern:

```text
INFO: ChatGPT browser gateway is ready; loaded 71 cookies
INFO: ChatGPT prompt submitted with explicit send button fallback
ERROR: ChatGPT request failed
TimeoutError: ChatGPT response did not stabilize before timeout (... assistant count=1, lengths=0 ... main article count=0 ... generation_active=True ... send_button_count=1, send_states=True/True)
INFO: POST /v1/chat/completions ... 503 Service Unavailable
INFO: ChatGPT prompt submitted with Enter; generation=True assistant_count_increased=False
ERROR: ChatGPT request failed
TimeoutError: ChatGPT response did not stabilize before timeout (... assistant count=1, lengths=0 ... generation_active=True ...)
```

Interpretation: this is the first direct root-cause evidence for the 503. The Space process and browser gateway initialize, but ChatGPT remains in a generation state without assistant content becoming available or stabilizing; the gateway then maps its timeout to HTTP 503. This is not an API-key rejection and not an image-quota message. The log also shows the gateway loaded 71 cookies, but no cookie values or Storage State were copied into this repository.

The live browser screenshot visibly showed the Hugging Face Logs panel with the timeout traceback and repeated `POST /v1/chat/completions 503 Service Unavailable` lines. The screenshot upload path was not provided by the browser tool, so the visual evidence is represented by the browser capture and this redacted transcript.

## Step 7 — deployment of generation recovery

After source verification, `browser_gateway.py` with generation recovery was uploaded to the three Hugging Face Spaces using the authorized HF session/API path. The redacted deployment results were:

| Space | HF commit | post-deploy public state |
|---|---|---|
| `Yousefsg/chatgpt-api-replica-01` | `85e43bebd060e937e977c9508616e1f59362d66a` | root and `/health` returned `running=true, ready=true` |
| `Yousefsg/chatgpt-api-replica-02` | `590fc82202d3a07db0878e2806f3706c59c78176` | root and `/health` returned `running=true, ready=true` |
| `Yousefsg/chatgpt-api-replica-04` | `0d139e4fd9d269c2df99a1c392dc2b31ac126f5a` | root and `/health` returned `running=true, ready=true` |

The temporary token file was deleted immediately after upload. No token, Cookie, Storage State, or Authorization header was written to the repository or evidence log.

## Step 8 — live post-deploy log inspection (replica-04)

The live Hugging Face Space page showed `Running`, and its Logs panel showed a fresh application startup at `2026-08-19 09:51:23`. The gateway reported `ChatGPT browser gateway is ready; loaded 71 cookies`. The health/root probes returned HTTP 200. No stale-generation timeout, `generation_active=True`, or startup error appeared in the visible post-deploy log window. The panel also contained unrelated automated probes for common secret paths and `/api/predict`; those returned 404 and do not indicate an application failure.

The live browser screenshot captured this state in the session: Space `chatgpt-api-replica-04`, status `Running`, Logs panel open, fresh startup, gateway ready, and HTTP 200 health/root requests.

## Step 9 — live post-deploy log inspection (replica-01)

The live Space page showed `Running`. Its Logs panel showed a fresh application startup at `2026-08-19 09:51:20`, followed by `ChatGPT browser gateway is ready; loaded 90 cookies`. Root and health probes returned HTTP 200. No stale-generation timeout or gateway startup error appeared in the visible post-deploy log window. The live browser capture showed the Space status and Logs panel; cookie values were not displayed or persisted.

## Step 10 — live post-deploy log inspection (replica-02)

The live Space page showed `Running`. Its Logs panel showed a fresh application startup at `2026-08-19 09:51:20`, followed by `ChatGPT browser gateway is ready; loaded 92 cookies`. Root and health probes returned HTTP 200. No stale-generation timeout or gateway startup error appeared in the visible post-deploy log window. The live browser capture showed the Space status and Logs panel; cookie values were not displayed or persisted.

## Step 11 — live functional-test evidence (replica-02)

While GitHub Action `32240146321` was running, the live replica-02 Logs panel showed five `POST /v1/chat/completions` requests returning HTTP 200 between `10:00:20` and `10:05:04`. The gateway messages showed `assistant_count_increased=True` on two requests and `assistant_count_increased=False` on three requests, but all five HTTP requests completed with 200 and no timeout/503 line was visible. This confirms the recovery path prevents the previous stale-generation failure from being converted into HTTP 503 for these requests; response-level pass/fail remains determined by the redacted GitHub artifact.

## Step 12 — live functional-test evidence (replica-01)

During the same GitHub Action, the live replica-01 Logs panel showed two successful `POST /v1/chat/completions` requests returning HTTP 200 at `09:56:22` and `09:56:36`. A later request at `10:00:14` returned HTTP 503 after a timeout diagnostic with `generation_active=False`, assistant count `3`, non-empty assistant lengths, and `main article:count=0`. This is a different failure signature from the original stale active-generation case: the page was no longer actively generating, but the response stabilizer did not accept the DOM state. The recovery patch addresses stale active generations; this new log evidence must be separated from the original root cause rather than misclassified as a complete fix.

## Step 13 — live functional-test evidence (replica-04)

The live replica-04 Logs panel showed the recovery code executing: at `10:09:09` it logged `WARNING ChatGPT generation remained active; reloading the browser page`. The following request still timed out at `10:09:13` with assistant count `1`, length `0`, `generation_active=True`, and returned HTTP 503. A later prompt submission was logged at `10:09:41`. This proves the deployed recovery code is present and active, but it does not guarantee that the same in-flight request will succeed; the current request can still hit the existing stabilization timeout before the recovery is applied to the next request.

## Step 14 — remediation deployment startup (replica-04)

After the second remediation deployment, the live Logs panel showed a fresh startup at `2026-08-19 10:57:44`, followed by `ChatGPT browser gateway is ready; loaded 71 cookies`. Root and health requests returned HTTP 200. The Space UI showed `Running` before functional testing began.

## Step 15 — remediation recovery behavior (replica-04)

During workflow `32245401088`, the live logs showed the first prompt submission at `11:02:16`, then a timeout at `11:05:53`. The new recovery logged `ChatGPT recovery: opening a fresh conversation after timeout`, followed by `ChatGPT request timed out; retrying once after fresh-conversation recovery` at `11:05:57`, and a second prompt submission at `11:06:19`. This is direct evidence that the bounded fresh-conversation retry is active; the final response status remains pending until the workflow artifact completes.

## Step 16 — remediation functional evidence (replica-01)

The live replica-01 Logs panel showed fresh startup at `10:57:43`, gateway readiness with 90 cookies, and three post-deploy `POST /v1/chat/completions` requests returning HTTP 200 at `11:00:10`, `11:00:20`, and `11:00:24`. The third request reported `generation=True` and `assistant_count_increased=False` at submission time but still returned HTTP 200, and no DOM stabilization timeout or 503 appeared in the visible log window.

## Step 17 — remediation functional evidence (replica-04 final)

The final replica-04 Logs window showed the remediation retry twice: the first attempt timed out at `11:05:53`, recovery opened a fresh conversation, and the retry was submitted at `11:06:19`; a later request repeated the same pattern at `11:09:56–11:10:28`, and another at `11:14:04–11:14:37`. The visible diagnostics remained `assistant count=1`, `lengths=0`, `generation_active=True`, with stop control present. Therefore the code-level recovery and bounded retry are functioning, but replica-04's ChatGPT session/upstream state remains unable to produce assistant content. The workflow report classified all three replica-04 scenarios as transient failures.

## Step 19 — replica-04 after real New chat click helper

After deploying the helper that clicks the rendered `New chat`/`دردشة جديدة` link, the limited text/search run showed startup at `11:21:52`, gateway readiness at `11:22:11`, a prompt submission at `11:22:37`, timeout/recovery at `11:26:13–11:26:24`, and a second prompt submission at `11:26:45`. The visible log window still did not show an assistant response or an HTTP 200 completion. This indicates the stored replica-04 ChatGPT session/upstream path remains blocked beyond conversation selection; further code retries would not be evidence of a fix.

## Step 20 — redacted session diagnostics

The new authorized `/diagnostics/session` endpoint returned `ready=true`, `input_visible=true`, and zero stop controls for all three Spaces. Replica-01 and replica-02 reported no visible login marker. Replica-04 reported `markers["log in"] = true` while still showing a composer and `ready=true`; it had 22 cookies versus 20 in each of the other two Spaces. Only cookie counts/names were inspected; no cookie values, Storage State, prompts, or secrets were returned or stored. This is the strongest current evidence that replica-04's stored session state differs or is partially authenticated, rather than a remaining router image-contract defect.

## Step 21 — fail-fast reauthentication verification

After deploying the fail-fast guard, one text request was sent to replica-04 only. It returned HTTP 503 with `ChatGPT session requires re-authentication; visible auth control detected` in `2.881228` seconds. This replaces the previous 268-second transient timeout behavior with an actionable terminal session signal. No image request was repeated.

## Step 22 — live image-path inspection preparation (replica-01/02)

The live Logs panels for replica-01 and replica-02 were opened without sending new prompts. Both Spaces showed fresh application startup and `ChatGPT browser gateway is ready`: replica-01 loaded 90 cookies and replica-02 loaded 92 cookies. The visible windows contained only health/UI probes and no new `POST /v1/chat/completions` image request, so no image quota was consumed during this inspection step.

## Step 23 — live ChatGPT image DOM inspection without submission

The connected ChatGPT browser was opened without sending a new prompt. The composer contained the previously typed image prompt `generate image of a simple blue star on a white background`, but it remained unsent: the page showed a textarea and send button, no assistant image, no `<img>` result, and no active generation indicator. Opening the recent-chats control exposed only new-chat/organizer controls in the current viewport; no completed image conversation was selected. This step consumed no image request.

## Step 24 — live ChatGPT image library inspection

The live ChatGPT Library page showed previously generated image assets, including `Vivid Blue Star on White.png` at 765 KB, `image-gen-1.png` at 817 KB, and several library images between 1.8 MB and 3.1 MB. The assets appeared as PNG/JPG library rows with dedicated image buttons, separate from the unsent composer on the home page. This demonstrates that a successful ChatGPT image flow persists a downloadable library asset even when the current conversation DOM is not displaying a generated image.

## Step 25 — live generated-image preview and download controls

Opening `Vivid Blue Star on White.png` in the live Library showed the actual blue-star image preview in a large image canvas. The UI exposed dedicated controls for `تنزيل الصورة` (download), `مشاركة` (share), `إزالة` (remove), aspect-ratio display, and comments. No new generation was started. This is the clearest live reference for the completed-image contract: a finished image is a library asset with a real preview and an explicit download action, not merely an `<img>` found in the unsent composer page.

## Step 26 — definitive sg versus replica-04 session check

The connected live browser visibly showed the signed-in account `Yousef Sg` with the Free plan and an active composer. The refined redacted diagnostics in replica-04, after deployment, showed `ready=true` and `input_visible=true` but also a **real visible `button` labeled `log in`** with a nontrivial bounding box of `68.2×36` pixels. The details contained no hidden/aria-hidden flag and no sensitive values. This proves the earlier `log in` marker was not merely hidden text: the replica-04 Space has a different or partially expired ChatGPT session from the authenticated live sg browser, even though both are intended to represent account sg.

## Step 27 — independent image byte verification (one request per replica)

A separate image-only workflow [32251162719](https://github.com/ysrg2003/ai-provider-router/actions/runs/32251162719) ran exactly one image scenario per replica-01 and replica-02. Its redacted artifact reported `2 passed`, `output_type=image`, `mime_type=image/png`, and large non-empty Base64 lengths for both.

A direct independent HTTP verification then sent one image request to each Space and decoded the returned data without retrying. Replica-02 returned `status_code=200` with a `data_url`; decoding produced a real PNG (`831230` bytes, `1254×1254`, valid PNG signature). Replica-01 returned `status_code=200` and the prompt submission completed, but the response contained no usable image bytes in the direct contract inspection. Its live Logs showed `generation=True assistant_count_increased=True` and HTTP 200, but no evidence of a returned downloadable image in that response. Therefore the strict byte-level result is **replica-02 verified; replica-01 not independently verified as fetched**, despite the earlier harness pass. No additional image request was sent after this discrepancy.

## Step 18 — live ChatGPT account reconnaissance

The connected live browser opened `https://chatgpt.com/` without sending a prompt. It showed the signed-in `Yousef Sg` Free account, a visible composer textarea, and the send button. No login wall, challenge, or `session expired` page was visible. This is evidence about the live browser account only; it does not prove that replica-04's stored Space session state is valid or equivalent. The rendered sidebar also showed a `دردشة جديدة` control, confirming that the live UI exposes a fresh-chat path; no prompt was submitted and no account state was changed.
