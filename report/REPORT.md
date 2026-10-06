# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Nguyễn Đức Thắng | 2A202602605 | Toàn bộ (làm cá nhân) |

- Mô hình: `LAB_MODEL=deepseek:deepseek-chat` (API DeepSeek, cấu hình Option 2 của `model.py`); `LAB_TEMPERATURE=0`; `recursion_limit=60` (mặc định của runner) cho mọi lần chạy.
- Deep Agents 0.7.21; máy Windows 11, mọi lần chạy tác tử thực hiện trong Docker (`python:3.12-slim`) bằng `Dockerfile.isolated` (xem Phụ lục: shell của tác tử chạy bằng user không đặc quyền, không đọc được kho mã nguồn).
- Số lần chạy tác vụ: 9 lần trên tác vụ học trước khi đóng băng (baseline 3, subagents 3, skills-auto 3), 1 lần chạy curator. Lần chạy DeepSeek thoát sandbox (trước khi vá) được giữ ở `results/_quarantine/` làm bằng chứng và mô tả ở Phụ lục, không dùng trong bảng.
- Commit của tag `freeze`: (điền sau Phần 4.1)

## 2. Giả thuyết (commit TRƯỚC tag `freeze`, Phần 4.0)

- H1 (subagents so với baseline): `subagents` KHÔNG cao hơn `baseline` trên tác vụ đánh giá (dự đoán thấp hơn hoặc bằng) và tốn token nhiều hơn rõ rệt (≥ 1,5 lần). Căn cứ: trên tác vụ học, `subagents` đạt 6/27 check so với 13/27 của `baseline` với token trung bình 370.517 so với 197.703 (1,87 lần); tác tử chính chỉ giao việc ở 1/3 tác vụ (`subagent_calls` = 0, 2, 0), nên phần lớn chênh lệch là do prompt dài hơn và nhiễu chứ không phải do phân công. Bài viết của Anthropic về hệ thống nghiên cứu đa tác tử ghi nhận đa tác tử tốn khoảng 15 lần token so với hội thoại thường; lợi ích chỉ xuất hiện ở tác vụ chia nhỏ song song được, còn các tác vụ ở đây là tuần tự và nhỏ.
- H2 (skills-auto so với baseline): `skills-auto` KHÔNG cải thiện đáng kể điểm trung bình trên tác vụ đánh giá (chênh lệch nằm trong nhiễu, khoảng ±2 check); nếu có lợi thì chỉ ở các check quy ước `rule_` được tác vụ đánh giá dùng lại từ tác vụ học (ví dụ tiền là số nguyên cent, khối `schema_version`/`generated_by`), không ở check kỹ thuật. Căn cứ: lỗi chiếm đa số ở baseline là nhóm E (quy ước) và nhóm G (cạn ngân sách bước), không phải A-D; skill sinh ra nêu quy ước còn mơ hồ (thiếu định dạng gạch đầu dòng changelog, thiếu khối `meta`) và ở Phần 3.4 tác tử đọc đủ 3 skill nhưng vẫn ưu tiên đề bài khi mâu thuẫn ("number" so với cent). SkillsBench ghi nhận skill do mô hình tự sinh trung bình không có lợi.
- H3 (tác vụ học so với tác vụ đánh giá): Check quy ước MỚI của mỗi tác vụ đánh giá sẽ thất bại ở cả ba điều kiện, vì curator chỉ thấy phản hồi của tác vụ học nên không thể biết quy ước mới; mọi lợi ích của skill (nếu có) trên tác vụ học sẽ lớn hơn trên tác vụ đánh giá (quá khớp, như SkillEvolBench ghi nhận). Ngoài ra, do nhiễu lớn của mô hình ở nhiệt độ 0 (vòng lặp lặp lại lệnh, cạn 60 bước), điểm cùng điều kiện giữa Phần 3.4 và sau đóng băng có thể lệch vài check.

## 3. Làm quen Deep Agents (Phần 0.3)

1. Tác tử mặc định có 9 công cụ: 7 công cụ tệp (`ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep`), 1 công cụ shell (`execute`) và 1 công cụ giao việc cho subagent (`task`). Chỉ `execute` cho phép chạy lệnh; mô tả của nó ghi rõ công cụ này chỉ hoạt động khi backend cài đặt `SandboxBackendProtocol` (với backend không có shell, công cụ trả về lỗi).
2. Mô tả của `task` cho biết `general-purpose` là subagent đa dụng dùng để nghiên cứu câu hỏi phức tạp, tìm tệp/nội dung và thực hiện tác vụ nhiều bước, và "has access to all tools as the main agent". Về ngữ cảnh: subagent là tạm thời (ephemeral) và không trạng thái (stateless) - "the agent sees only the prompt you give it and returns a single final report". Nó không thấy lịch sử hội thoại, đề bài gốc hay system prompt của tác tử chính; mọi quy tắc cần thiết phải được tác tử chính chép vào lời giao việc. Báo cáo cuối của subagent cũng không hiện cho người dùng, tác tử chính phải tự tóm tắt lại.
3. System prompt mặc định là chuỗi rỗng (`''`), nên hành vi của tác tử đến từ mô tả công cụ:
   - Từ `task`: "Put full detail in the prompt and state exactly what it should return".
   - Từ `execute`: "You MUST avoid using search commands like find and grep. Instead use the grep, glob tools to search."

   Nhận xét: mô tả `execute` còn khuyên "Use absolute paths and avoid `cd`", mâu thuẫn với quy ước của lab (`PATHS_NOTE`: mọi đường dẫn tương đối với gốc sandbox, không bắt đầu bằng `/`). Đây là lý do harness phải bổ sung `BASE_PROMPT`; nếu không, tác tử dễ dùng `/workspace/...` trong shell và gặp lỗi `No such file or directory`.

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

Nguồn: `results/baseline/<tác vụ học>/run.json` (khóa `checks`) và `trace.md`.

| Tác vụ | Check thất bại | Nhóm lỗi (A-G) | Bằng chứng (trích ngắn từ `detail` hoặc vết) |
|---|---|---|---|
| code-learn | `rule_type_hints` | E | `RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value.` |
| code-learn | `rule_regression_tests` | E | `RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3)` |
| code-learn | `rule_changelog` | E | `RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): ...'` |
| logs-learn | `rule_service_names` | E | `RULE: service names in the output are lower-case with '-' replaced by '_'` |
| logs-learn | `rule_sorted_errors` | E | `RULE: errors is sorted by service, then by timestamp_utc, ascending.` |
| logs-learn | `rule_schema_header` | E | `RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage".` |
| data-learn | `rule_clean_csv` | E | `RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents; ...` |
| data-learn | 5 check kỹ thuật (`north_q1_revenue`, `north_q1_orders`, `top_region`, `missing_amount_orders`, `duplicate_rows_removed`) và `rule_money_in_cents`, `rule_meta_block` | G (cạn ngân sách bước khi đi tìm tài liệu không tồn tại) | `detail`: `FileNotFoundError: ... workspace/answer.json`; `error`: `GraphRecursionError: Recursion limit of 60 reached`. Vết: sau khi đọc dữ liệu, tác tử chạy hơn 20 lệnh dò hệ thống tệp để tìm "Acme reporting conventions" (`find / -iname '*convention*'`, `find / -iname '*acme*' -o -iname '*review*bot*'`, đọc `/usr/share/lintian/profiles/dpkg/main.profile`) và hết 60 bước trước khi ghi `answer.json`. |

Nhận xét:
- **Nhóm E chiếm đa số** trong các lỗi có `detail` phát biểu quy tắc: 7/7 check `rule_` có phản hồi đều là quy ước không có trong đề. Đây là đúng loại lỗi mà skill có thể phòng ngừa: quy ước ổn định giữa các tác vụ cùng họ, curator đọc được nguyên văn từ `detail`.
- **Bằng chứng phủ định cho A-D** (`python scripts/check_breakdown.py`: baseline học 13/18 check kỹ thuật đạt). Ở hai tác vụ tác tử làm xong, check kỹ thuật đạt 100%: code-learn 7/7 (gồm `parse_price_all_formats`, `discount_rounds_half_up`, `low_stock_follows_docstring`, tức đã đọc docstring và sửa nguyên nhân gốc ở hàm dùng chung - không có A, C), logs-learn 6/6 (gồm `timestamps_utc`, `repeat_counts` - không có D). Vết cho thấy tác tử chạy lại test sau khi sửa (`python -m pytest tests -q` lần 2) - không có B. Câu trả lời cuối chỉ nêu tệp có thật - không có F.
- **Nhóm G là phát hiện riêng của cấu hình này**: câu "checked by Acme's review bot against the Acme reporting conventions" khiến DeepSeek đi tìm tài liệu quy ước trên toàn hệ thống tệp. Ở data-learn hành vi này làm mất trọn 5 check kỹ thuật. Ở lần chạy trước khi vá sandbox (Phụ lục), cùng hành vi này dẫn tới việc tác tử đọc `tasks/*/check.py` (kể cả tác vụ đánh giá) và tự chấm 8/8 - một dạng reward hacking. Skill có thể giảm G một phần bằng cách nêu sẵn quy ước (tác tử khỏi đi tìm), nhưng không giải quyết được vòng lặp do mô hình.

## 5. Điều kiện `subagents` (Phần 2.3)

- Các subagent đã định nghĩa (`src/lab/subagents.py`), mỗi vai trò nhắm vào một nhóm lỗi:
  - `explorer` (chỉ đọc): đọc README, docstring, mẫu dữ liệu, báo cáo quy tắc/định dạng/dữ liệu bẩn; không sửa tệp. Nhắm vào A, D. `description` yêu cầu gọi ĐẦU TIÊN.
  - `implementer`: sửa nguyên nhân gốc, xử lý dữ liệu bẩn, chạy lại để kiểm chứng, chỉ báo cáo tệp có thật. Nhắm vào C, D, F.
  - `reviewer` (chỉ đọc): kiểm tra độc lập theo từng quy tắc của đề, trả về PASS hoặc danh sách lỗi kèm bằng chứng. Nhắm vào B, F. `description` yêu cầu gọi CUỐI.
- `subagent_calls`: code-learn 0, data-learn 2, logs-learn 0. Ở data-learn, theo nội dung lời giao việc, lần 1 là việc thực hiện (tính toán, ghi `answer.json`) và lần 2 là kiểm tra độc lập ("Independently review output files against the task rules. Do NOT fix anything; report PASS or concrete problems"); không gọi `explorer` vì tác tử chính đã tự đọc README và dữ liệu. (Trường `subagent_type` bị `render_trace` cắt ở 1.500 ký tự nên không hiện trong vết.) Ở code-learn và logs-learn, tác tử chính không giao việc: nó dùng hết bước để dò hệ thống tệp (code-learn: đọc `site-packages`, `.pytest_cache`, thậm chí `p.parse_price.__code__.co_consts`; logs-learn: `find / -maxdepth 4 -iname '*convention*'`, duyệt `site-packages`) rồi chạm `GraphRecursionError`. `SUBAGENTS_NOTE` khuyến khích giao việc nhưng không đủ để thay đổi hành vi khi tác tử đang "săn" tài liệu quy ước.
- Thông tin khi giao việc (data-learn): đủ. Lời giao việc chép lại toàn bộ quy tắc của đề và README (dedup theo `order_id`, ba định dạng ngày và chuyển UTC, chuẩn hóa vùng, `-999` là thiếu, cửa sổ Q1 tính theo UTC). Báo cáo của subagent được kiểm tra: tác tử chính tự chạy lại một script tính toán độc lập rồi mới gọi reviewer. Tuy vậy, lời giao việc chỉ chứa câu "plus whatever the Acme reporting conventions require" mà không có quy ước nào, nên cả implementer và reviewer đều báo PASS trong khi 3 check `rule_` thất bại: reviewer không thể kiểm tra quy tắc mà chính nó không biết.
- Token và thời gian: trung bình 370.517 token/lần (baseline 197.703, gấp 1,87 lần); thời gian 31,2 / 65,9 / 31,2 giây so với 18,0 / 29,1 / 23,2 giây. Ở data-learn, giao việc giúp làm xong 5/5 check kỹ thuật (baseline 0/5 vì cạn bước) với 16 tool call ở luồng chính so với 31, nhưng tốn 355.744 token và 65,9 giây (chậm nhất). Ở hai tác vụ còn lại, không có giao việc mà token vẫn gần gấp đôi, cho thấy chênh lệch chủ yếu do vòng lặp dò tìm chứ không do subagent.

## 6. Self-evolving: skill do curator sinh (Phần 3)

- Curator chạy 1 lần (`python -m lab.curator`, nguồn: `results/baseline`, 3 tác vụ học), sinh 3 skill, cả 3 qua `validate_skill`. Không xóa skill nào và không chạy lại: không skill nào chứa định danh tác vụ đánh giá hay hướng dẫn gây hại; các thiếu sót (mục dưới) là thiếu chi tiết chứ không sai hướng. Không sửa tay nội dung skill.

| Skill | Tổng quát hay riêng cho tác vụ học? | Đúng hay sai (nêu chỗ sai nếu có) | Độ dài, `description` và `skills_read` ở Phần 3.4 |
|---|---|---|---|
| `package-conventions-compliance` | Tổng quát cho họ `code`: nêu ba quy ước (type hint, `tests/test_regressions.py`, changelog `## Unreleased`) dưới dạng quy trình, không nêu tên hàm hay tệp của workspace. | Đúng một phần. Sai phạm vi: "each public function you touch or add" hẹp hơn quy tắc gốc "every public function in the package". Thiếu chi tiết: không ghi nguyên văn định dạng `- fix(<function name>): ...`, chỉ ghi "required bullet format". Bước 1 ("scan the repo for convention sources") có thể khuyến khích hành vi dò tìm của nhóm G. | 13 dòng; `description` "Use when a coding task asks to fix bugs or add features in an existing package..." - đúng tình huống kích hoạt. Được đọc ở cả 3 tác vụ học. |
| `deliverable-artifacts` | Khá tổng quát (họ `data`), nhưng ví dụ nêu `workspace/answer.json`, `workspace/clean.csv`. Đây là tệp do quy ước yêu cầu nên được phép theo `05_skill_quality.md`. | Đúng nhưng thiếu: có "money as integer cents", không có khối `meta` (vì `detail` của `rule_meta_block` ở baseline là `FileNotFoundError`, curator không thấy quy tắc), không ghi thứ tự cột của `clean.csv`. Câu "a correct analysis that is never written is a failed task" đúng với lỗi G của baseline. | 13 dòng; `description` "Use when a data or analysis task requires writing output files..." - rộng, khớp họ data. Được đọc ở cả 3 tác vụ học. |
| `output-normalization-rules` | Tổng quát hóa quy ước của họ `logs` thành quy tắc chung "chuẩn hóa định danh, sắp xếp, metadata", với ví dụ nguyên văn. | Đúng với logs. Rủi ro áp dụng sai họ: `description` rộng ("transforming or aggregating records into a structured output") nên ở data-learn tác tử đã thêm `schema_version`/`generated_by` vào `answer.json` - quy ước của họ logs bị đem sang họ data. | 12 dòng; `description` rất rộng - được đọc ở cả 3 tác vụ học (kể cả code-learn, nơi không liên quan). |

Phần 3.4 (`results/skills-auto-dev/`, chạy trước khi đóng băng): `skills_read` = 3 ở cả 3 tác vụ (tác tử đọc mọi skill ngay bước đầu theo `SKILLS_NOTE`). Điểm: code-learn 1/10, data-learn 5/8, logs-learn 0/9 (baseline 7/10, 0/8, 6/9). Đọc skill không đồng nghĩa làm theo: ở data-learn tác tử đọc "money as integer cents" rồi tự lập luận "The task says the value is a 'number' ... the task's explicit definition takes precedence" và giữ USD, nên `rule_money_in_cents` vẫn thất bại. Ở code-learn và logs-learn tác tử rơi vào vòng lặp lặp nguyên một lệnh (`python -m pytest tests -q 2>&1 | sed -n '1,1p'` hơn 15 lần; `grep -n "repeated" workspace/app.log | tail -3` hơn 15 lần) và chạm giới hạn 60 bước - lỗi của mô hình ở nhiệt độ 0, không liên quan đến nội dung skill.

## 7. Kết quả so sánh (Phần 4.3, 4.4)

> Dán nội dung `report/table.md` và kết quả `python scripts/check_breakdown.py`. Nêu các lần chạy có `error` hoặc `skills_modified = true` (nếu có) và cách xử lý.

```text
(dán bảng ở đây)
```

## 8. Phân tích

> Trả lời từng câu bằng số liệu từ mục 7 và bằng chứng từ vết. Kết quả âm hoặc không có khác biệt vẫn hợp lệ nếu được phân tích tốt.

1. So với `baseline`, điều kiện nào cải thiện điểm tác vụ **học**? Điều kiện nào cải thiện điểm tác vụ **đánh giá**? Có điều kiện nào cải thiện tác vụ học nhưng không cải thiện tác vụ đánh giá? Nếu có, đó là dấu hiệu gì?
2. Tách điểm thành check kỹ thuật và check quy ước (`rule_`). Skill do curator sinh giúp nhóm check nào? Check quy ước **mới** của tác vụ đánh giá có được skill giúp không, và vì sao?
3. Dựa vào vết và `skills_read`, giải thích một check mà skill giúp đạt và một check mà skill không giúp (skill chưa được đọc, đọc nhưng không làm theo, skill thiếu hoặc sai).
4. Chi phí: so sánh số token trung bình giữa các điều kiện. Điều kiện nào có hiệu quả tốt nhất theo điểm trên mỗi token? Đa tác tử có đáng chi phí trong thí nghiệm này không?
5. Có dấu hiệu rò rỉ dữ liệu hoặc quá khớp nào trong skill sinh ra không? Nhóm đã phòng tránh như thế nào?
6. Nhiễu: so sánh điểm tác vụ học của cùng bộ skill ở Phần 3.4 (đã sao lưu) và sau đóng băng. Chênh lệch bao nhiêu? Nó cho biết điều gì về độ tin cậy của các chênh lệch trong bảng ở mục 7?

## 9. Hạn chế và tính hợp lệ

> Nêu ít nhất 3 hạn chế và ảnh hưởng của từng hạn chế đến kết luận (ví dụ: chỉ 3 tác vụ mỗi vai trò, mỗi cấu hình chạy một lần, nhiễu của mô hình, tác vụ do giảng viên thiết kế sẵn quy ước, chỉ một mô hình).

1.
2.
3.

## 10. Kết luận

> Tối đa 5 câu. Chỉ khẳng định điều số liệu hỗ trợ. Nêu một đề xuất cải tiến tiếp theo.

## Phụ lục

- Lệnh đã chạy (theo thứ tự):
- Thử thách mở rộng (nếu có): hướng chọn, kết quả, nhận xét.
- Ghi chú khác:
