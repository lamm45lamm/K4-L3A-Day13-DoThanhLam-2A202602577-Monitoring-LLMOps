# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ. Ngưỡng khớp `config/slo.yaml` và `config/dashboard.yaml`. Baseline (111 request): P95 905ms, lỗi 0%, quality 0.88.

## Alert 1

- Tên: HighLatencyP95
- Severity: P2
- Duration: 5 phút
- Kênh thông báo: Slack
- SLI/SLO liên quan: `fast_successful_requests` (latency ≤ 3000ms, target 99.5%/28 ngày)
- Điều kiện và thời gian duy trì: P95 `latency_ms` của `response_sent` > 3000ms liên tục 5 phút
- Ảnh hưởng tới người dùng: phản hồi chậm; tiêu hao error budget (0.5% ≈ 201.6 phút/28 ngày)
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Latency: P95 tăng từ khi nào, TTFT P95 có tăng theo không.
  2. Lọc `data/logs.jsonl` các `response_sent` có `latency_ms` > 3000, lấy một `correlation_id`.
  3. Mở trace Langfuse cùng `correlation_id`, xem span `retrieve` hay `llm-generate` chiếm thời gian.
- Mitigation tạm thời: nếu `retrieve` chậm, tắt incident `rag_slow` (`POST /incidents/rag_slow/disable`); nếu `llm-generate` chậm sau khi đổi prompt, rollback label `production` về version trước.
- Owner: student-oncall

## Alert 2

- Tên: HighErrorRate
- Severity: P1
- Duration: 5 phút
- Kênh thông báo: Slack
- SLI/SLO liên quan: guardrail `error_rate_pct_max: 2` và `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: `request_failed / request_received` > 2%, hoặc retrieval success < 90%, liên tục 5 phút
- Ảnh hưởng tới người dùng: request trả lỗi 500 hoặc câu trả lời thiếu ngữ cảnh
- Ba bước kiểm tra đầu tiên:
  1. Panel Errors: xem `error_type` chiếm nhiều nhất và `tool_success_rate`.
  2. Lọc log `request_failed`, đọc `error_type` và `payload.detail`, lấy `correlation_id`.
  3. Mở trace cùng `correlation_id`, xem span nào có level ERROR.
- Mitigation tạm thời: tắt incident `tool_fail` nếu đang bật (`POST /incidents/tool_fail/disable`); rollback prompt hoặc deploy gần nhất; restart API.
- Owner: student-oncall

## Alert 3

- Tên: LowAnswerQuality
- Severity: P3
- Duration: 15 phút
- Kênh thông báo: Slack
- SLI/SLO liên quan: guardrail `quality_score_avg_min: 0.75`
- Điều kiện và thời gian duy trì: trung bình `quality_score` của `response_sent` < 0.75 liên tục 15 phút
- Ảnh hưởng tới người dùng: câu trả lời kém chính xác dù không lỗi; khó thấy nếu chỉ nhìn latency/error
- Ba bước kiểm tra đầu tiên:
  1. Panel Quality: giảm từ thời điểm nào, có trùng thời điểm đổi prompt version không.
  2. Lọc `response_sent` có `quality_score` thấp, lấy `correlation_id`.
  3. Mở trace, kiểm tra `prompt_version`/`prompt_label` trong metadata và số `doc_count` của span `retrieve`.
- Mitigation tạm thời: rollback `production` về prompt version trước; kiểm tra retrieval có trả về tài liệu không.
- Owner: student-oncall
