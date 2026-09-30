# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** `Đỗ Thanh Lâm`
- **MSSV:** 2A202602577
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/lamm45lamm/K4-L3A-Day13-DoThanhLam-2A202602577-Monitoring-LLMOps.git
- **Commit SHA cuối:** `8fe0ca40261c2a694b51ff02863f7092a0544f45`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602577`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` |30/100 (21 records; 20 thiếu required fields; 20 thiếu enrichment; 0 correlation ID) | 100/100: 107 record, 0 thiếu field, 0 thiếu enrichment, 51 correlation ID, 0 PII leak| Đạt cả 4 mục: schema, correlation ID, enrichment, PII |
| `validate_dashboard.py` | HỢP LỆ: 6/6 panel  | HỢP LỆ: 6/6 panel | Đủ sáu panel theo contract |
| `pytest` | 22 pased trong 0.92s| 24 passed trong 1.08s| Toàn bộ test qua |
| Số traces hợp lệ | 0 | Nhiều trace `day13-agent-request`, mỗi trace có `lab-agent-run` → `retrieve` + `llm-generate` (`06-trace-list.png`) | Trace đủ cấu trúc, tạo từ project cá nhân |
| Số PII leak | 0 | 0 | Evidence riêng kiểm tra đồng thời email, điện thoại Việt Nam, CCCD và thẻ thanh toán.|
| Latency P95 / TTFT P95 | P95 905ms (111 request, `config/slo.yaml`) | P95 938ms, P99 1442ms, TTFT P95 55ms (`11-dashboard-overview.png`) | Dưới ngưỡng SLO 3000ms |
| Retrieval success rate | 100% | 100.00%, error rate 0.00% | Không lỗi trong điều kiện bình thường |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` ([app/middleware.py](../app/middleware.py)) gọi `clear_contextvars()` đầu mỗi request, lấy header `x-request-id` nếu có, không thì sinh `req-<8 hex>`; bind vào `structlog.contextvars` nên mọi log line của request đều mang cùng ID; ID cũng được gắn vào response header `x-request-id` và `x-response-time-ms`. Ví dụ: `req-6f550d25` xuất hiện ở cả `request_received` lẫn `response_sent` (`04-structured-log.png`).
- **Các metadata được ghi vào structured log:** `service`, `env`, `level`, `ts`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`; với `response_sent` thêm `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, `payload.answer_preview`.
- **Cách bảo đảm PII được scrub trước khi ghi:** [app/pii.py](../app/pii.py) `scrub_text` thay email, SĐT VN, CCCD, thẻ tín dụng, hộ chiếu, địa chỉ bằng `[REDACTED_<LOẠI>]`; log chỉ ghi `summarize_text` (đã scrub, cắt 80 ký tự) thay vì message gốc; `user_id` được băm SHA-256 (12 ký tự) thành `user_id_hash`. Input của generation trong Langfuse cũng qua `scrub_text`.
- **Cách kiểm chứng kết quả:** gửi request chứa `a@b.com`, `0901234567`, CCCD 12 số, số thẻ 4111… bằng curl, rồi `tail -2 data/logs.jsonl` thấy `Email [REDACTED_EMAIL], sdt [REDACTED_PHONE_VN], CCCD [REDACTED_CCCD]...` (`05-pii-redaction.png`); `validate_logs.py` báo 0 PII leak.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** trace xem trong project Langfuse `day13-k4-l3a-2A202602577`; version prompt hiển thị "by Lâm Đỗ Thanh" (`09-prompt-versions.png`); metadata trace có `scope.attributes.public_key` của project này (`08-trace-metadata.png`). Ảnh đã kiểm tra không lộ secret key.
- **Cấu trúc root/retrieval/generation observations:** root `lab-agent-run` (agent) chứa hai con: `retrieve` (retriever, input đã scrub, output `{"doc_count": N}`) và `llm-generate` (generation, có `model`, `prompt`, `usage_details` input/output, `cost_details`). Cài đặt ở [app/agent.py](../app/agent.py) qua helper `start_observation` trong [app/tracing.py](../app/tracing.py) (no-op khi chưa cấu hình Langfuse). Xem `06-trace-list.png`, `07-trace-waterfall.png`.
- **Cách nối trace với log:** `correlation_id` được ghi trong metadata của trace (cùng `model`, `feature`) — `08-trace-metadata.png` có `correlation_id=req-180c8363`. Tìm log bằng ID này trong `data/logs.jsonl`, hoặc lọc Langfuse bằng `metadata.correlation_id:<id>`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1, label `baseline` (tạo 9/29/2026 11:59 PM)
- **Version/label candidate:** v2, label `candidate` + `latest` (thêm dòng "Answer in no more than three concise bullet points."; tạo 9/30/2026 12:03 AM)
- **Trace ID của mỗi version:** v1 → `9d8cf34a513…`; v2 → `609a82aeab5…` và `919abaa7960…`; sau rollback về v1 → `f689d12bf1f13…` (ID rút gọn theo ảnh `10-prompt-rollback.png`, bản đầy đủ xem trong Langfuse).
- **Cách promote và rollback `production`:** đổi `LANGFUSE_PROMPT_LABEL` trong `.env` (baseline/candidate/production) và chuyển label `production` giữa các version trong Langfuse Prompt Management, không sửa code. Trong `10-prompt-rollback.png`, các trace v2 (11:04:40) được theo sau bởi trace v1 (11:07:25–26) sau khi rollback.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** [scripts/dashboard.py](../scripts/dashboard.py) (Streamlit, đọc `data/logs.jsonl`, cửa sổ 60 phút, refresh 30s) khớp `config/dashboard.yaml`: (1) Latency P50/P95/P99 + TTFT, (2) Request traffic, (3) Error rate + retrieval success, (4) Cost over time, (5) Input/output tokens, (6) Quality proxy. Mỗi panel hiển thị ngưỡng. Ảnh `11-dashboard-overview.png`: 60 request, P50 160 / P95 938 / P99 1442ms, TTFT P95 55ms, 1.62 req/phút, lỗi 0%, retrieval 100%, cost $0.124824, tokens 2288/7864, quality 0.880.
- **SLO và lý do chọn:** [config/slo.yaml](../config/slo.yaml): request thành công và ≤ 3000ms đạt 99.5% trong 28 ngày. Baseline 111 request: P95 905ms, P99 951ms, lỗi 0%. Ngưỡng 3000ms ≈ 3 lần P99 baseline nên chỉ bị vượt khi có sự cố thật (ví dụ `rag_slow`); 99.5% nghiêm nhưng không báo nhầm vì baseline gần 100%.
- **Cách tính error budget:** budget = 100% − 99.5% = 0.5%. Cửa sổ 28 ngày = 40 320 phút → 0.5% × 40 320 = 201.6 phút; tương đương tối đa 50 request chậm/lỗi trên mỗi 10 000 request. Hết budget thì dừng thay đổi tính năng, chỉ làm ổn định.
- **Ba alert và runbook tương ứng:** [docs/alerts.md](../docs/alerts.md): `HighLatencyP95` (P1/P2: P95 > 3000ms trong 5 phút), `HighErrorRate` (P1: lỗi > 2% hoặc retrieval < 90% trong 5 phút), `LowAnswerQuality` (P3: quality trung bình < 0.75 trong 15 phút). Mỗi alert có SLI, 3 bước kiểm tra đầu tiên (dashboard → log → trace cùng `correlation_id`), mitigation và owner.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 2026-09-30, khoảng 04:46 UTC (11:46 giờ VN) với session `k4-l3a-challenge-s01`, feature `monitoring`.
- **Triệu chứng từ metrics:** dashboard cửa sổ 14 record (`12-incident-metric.png`): latency P50 2666ms, P95 3340ms, P99 3474ms — P95 vượt ngưỡng 3000ms; trong khi lỗi 0%, retrieval 100%, TTFT P95 vẫn 55ms, quality 0.840. So với baseline P95 ≈ 905–938ms, latency tăng gấp ~3.5 lần nhưng chỉ chậm, không lỗi.
- **Log line và correlation ID liên quan:** `req-ee1c6265`: `request_received` (04:46:17Z, message "Explain why metrics traces and logs work together.") rồi `response_sent` với `latency_ms=3508`, `ttft_ms=54`, `tokens_out=138`, `tool_name=retrieval`, `tool_success=true` (`13-incident-log.png`). TTFT và token bình thường nên phần chậm không nằm ở sinh token.
- **Trace ID và span gây ảnh hưởng:** trace có `correlation_id=req-f02e9361` (`14-incident-trace.png`): root `lab-agent-run` 2.65s, trong đó span retrieval (`knowledge-retrieval`) 2.50s, generation chỉ 0.15s (TTFT 0.05s). Span retrieval chiếm ~94% thời gian. Trace ID đầy đủ lấy từ Langfuse.
- **Root cause:** bước retrieval (RAG) chậm thêm khoảng 2.5s mỗi request (incident `rag_slow`, `app/mock_rag.py` `time.sleep(2.5)` khi `STATE["rag_slow"]` bật). LLM không phải nguyên nhân. Log có sự kiện `incident_enabled`/`incident_disabled` với `name=rag_slow` (`04-structured-log.png`).
- **Fix action:** tắt incident bằng `POST /incidents/rag_slow/disable`; latency trở lại khoảng 160ms P50 như baseline.
- **Preventive measure:** giữ alert `HighLatencyP95` (P95 > 3000ms trong 5 phút) và thêm timeout/cache cho retrieval; ghi latency riêng từng span để thấy ngay retrieval hay generation chậm; runbook luôn đi metrics → log → trace.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** tách `retrieve` và `llm-generate` thành observation con riêng dưới root `lab-agent-run`, kèm `correlation_id` trong metadata. Nhờ đó trace cho thấy ngay span nào chậm và nối được với log. Helper `start_observation` trả no-op khi không có Langfuse client nên app và test vẫn chạy khi tắt tracing.
- **Một lỗi/blocker đã gặp:** bước đầu trace chỉ có một observation gốc, không thấy span con và token/cost của generation.
- **Cách tìm nguyên nhân và xử lý:** đọc TODO (CP2) trong [app/agent.py](../app/agent.py), bọc `retrieve()` và `FakeLLM.generate()` bằng observation con, truyền `prompt`, `usage_details`, `cost_details`; kiểm tra lại bằng `06-trace-list.png` và `07-trace-waterfall.png`.
- **Cách hiểu luồng Metrics → Logs → Traces:** metrics cho biết có vấn đề (P95 3340ms > 3000ms); logs thu hẹp vào request cụ thể qua `correlation_id` (latency 3508ms, TTFT bình thường); trace chỉ ra span chậm (retrieval 2.50s) từ đó suy ra root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** prompt version cho biết request dùng bản nào nên so sánh được v1/v2 và rollback nhanh không sửa code; token/cost theo dõi chi phí từng generation và giới hạn ngân sách ngày; SLO + error budget biến "chậm" thành ngưỡng đo được để quyết định khi nào ngừng thay đổi.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace (xem lưu ý: log `req-ee1c6265` và trace `req-f02e9361` khác ID).
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret (ảnh 08 hiện public key `pk-lf-…`, nên che).
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
