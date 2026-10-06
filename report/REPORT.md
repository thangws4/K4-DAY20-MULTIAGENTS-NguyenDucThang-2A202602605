# Báo cáo Lab: Self evolving Agentic

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Nguyễn Đức Thắng | 2A202602605 | Toàn bộ (làm cá nhân) |

- Mô hình: `LAB_MODEL=deepseek:deepseek-chat` (API DeepSeek, cấu hình Option 2 của `model.py`); `LAB_TEMPERATURE=0`; `recursion_limit=60` (mặc định của runner) cho mọi lần chạy.
- Deep Agents 0.7.21; máy Windows 11, mọi lần chạy tác tử thực hiện trong Docker (`python:3.12-slim`) bằng `Dockerfile.isolated` (xem Phụ lục: shell của tác tử chạy bằng user không đặc quyền, không đọc được kho mã nguồn).
- Số lần chạy tác vụ: 9 lần trên tác vụ học trước khi đóng băng (baseline 3, subagents 3, skills-auto 3), 1 lần chạy curator. Lần chạy DeepSeek thoát sandbox (trước khi vá) được giữ ở `results/_quarantine/` làm bằng chứng và mô tả ở Phụ lục, không dùng trong bảng.
- Commit của tag `freeze`: `7f6164d` ("freeze skills", 2026-10-06T11:50:25+07:00); commit giả thuyết `8d71ba6` ("hypotheses") đứng ngay trước.

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

`report/table.md` (sinh bởi `python -m lab.compare`):

```text
| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 7/10 | 1/10 | 1/10 |
| data-learn | 0/8 | 5/8 | 0/8 |
| logs-learn | 6/9 | 0/9 | 0/9 |
| code-eval | 7/11 | 1/11 | 9/11 |
| data-eval | 5/9 | 5/9 | 5/9 |
| logs-eval | 6/10 | 6/10 | 7/10 |
| **Mean score - learning tasks** | 0.46 | 0.24 | 0.03 |
| **Mean score - evaluation tasks** | 0.60 | 0.42 | 0.69 |
| **Mean tokens per run** | 134,845 | 349,615 | 256,122 |
| **Runs that read a skill** | 0/6 | 0/6 | 6/6 |
```

`python scripts/check_breakdown.py`:

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval     18/18         0/12          71,988      0/3
baseline      learn    13/18         0/9          197,703      0/3
subagents     eval     12/18         0/12         328,714      0/3
subagents     learn     6/18         0/9          370,517      0/3
skills-auto   eval     18/18         3/12         187,447      3/3
skills-auto   learn     1/18         0/9          324,796      3/3
```

`python scripts/verify_freeze.py` (chạy trong container Linux): `checked 6 runs of skill conditions: OK`.

Lần chạy có `error`: tất cả đều là `GraphRecursionError: Recursion limit of 60 reached` (baseline data-learn; subagents code-learn, logs-learn, code-eval; skills-auto code-learn, data-learn, logs-learn). Đây là hành vi của tác tử (dò hệ thống tệp hoặc lặp lệnh, mục 4 và 6), không phải lỗi hạ tầng, nên giữ nguyên và chấm trên workspace hiện có, không chạy lại. Không lần chạy nào có `skills_modified = true`.

## 8. Phân tích

1. **Học và đánh giá.** Trên tác vụ học, không điều kiện nào hơn `baseline` (0,46): `subagents` 0,24, `skills-auto` 0,03. Trên tác vụ đánh giá, `skills-auto` cao nhất (0,69 so với 0,60; +3 check trên 30: code-eval 9/11 so với 7/11, logs-eval 7/10 so với 6/10, data-eval bằng nhau), `subagents` thấp nhất (0,42). Không có điều kiện nào "cải thiện học nhưng không cải thiện đánh giá" - mẫu điển hình của quá khớp không xuất hiện. Thay vào đó là mẫu ngược: `skills-auto` kém ở học nhưng khá ở đánh giá. Điểm học thấp không do nội dung skill mà do 3/3 lần chạy học sau đóng băng chạm giới hạn 60 bước (code-learn và logs-learn lặp nguyên một lệnh; data-learn dò hệ thống tệp 18 lệnh, tương tự baseline). Riêng trên check kỹ thuật, `skills-auto` ở tác vụ đánh giá bằng `baseline` (18/18), nên phần hơn chỉ đến từ check quy ước (câu 2).
2. **Kỹ thuật và quy ước.** Check kỹ thuật ở tác vụ đánh giá: baseline 18/18, subagents 12/18 (mất 6 check vì code-eval cạn bước), skills-auto 18/18 - skill không giúp check kỹ thuật (baseline đã đạt trần). Check quy ước: baseline 0/12, subagents 0/12, skills-auto 3/12. Ba check skill giúp đạt đều là quy ước dùng lại từ tác vụ học: `rule_type_hints`, `rule_regression_tests` (code-eval) và `rule_sorted_errors` (logs-eval). Ba check quy ước MỚI của tác vụ đánh giá (`rule_version_bump`, `rule_sorted_keys_format`, `rule_source_line`) thất bại ở cả 3 điều kiện (0/9): curator chỉ thấy phản hồi của tác vụ học (đề không nêu các quy ước này) nên skill không thể chứa chúng. Kết quả này khớp H3.
3. **Một check skill giúp và một check skill không giúp.**
   - Giúp: `rule_regression_tests` và `rule_type_hints` ở code-eval. `skills_read` = 3; vết bắt đầu bằng "I'll start by reading the skills that could apply", đọc `package-conventions-compliance` (bước 3: type hint cho hàm public; bước 4: `tests/test_regressions.py`, một test cho mỗi lỗi). Baseline cùng tác vụ không làm hai việc này (thất bại cả hai), skills-auto đạt cả hai.
   - Không giúp: `rule_changelog` ở code-eval - skill thiếu chi tiết. Tác tử có làm theo bước 5 (ghi vào `## Unreleased`), nhưng viết ``- Fix `parse_duration` to accept all documented formats ...`` thay vì định dạng bắt buộc `- fix(<function name>): <short description>`, vì skill chỉ ghi "using the required bullet format" mà không chép nguyên văn quy ước từ `detail`. Tương tự, `rule_schema_header` ở logs-eval thất bại: skill chỉ ghi "`schema_version` and `generated_by` with their required values" mà không có giá trị (`2`, `"log-triage"`), còn `rule_money_in_cents` ở data-eval thất bại vì tác tử đọc skill nhưng ưu tiên đề bài (như đã thấy ở Phần 3.4).
4. **Chi phí.** Token trung bình mỗi lần chạy: baseline 134.845, skills-auto 256.122 (1,9 lần), subagents 349.615 (2,6 lần); riêng tác vụ đánh giá: 71.988, 187.447 (2,6 lần), 328.714 (4,6 lần). Điểm trên 100.000 token ở tác vụ đánh giá: baseline 0,60 / 0,72 = 0,83; skills-auto 0,69 / 1,87 = 0,37; subagents 0,42 / 3,29 = 0,13. `baseline` hiệu quả nhất; `skills-auto` mua thêm 0,09 điểm với giá gấp 2,6 lần token (một phần do đọc 3 skill ở mọi lần chạy, kể cả skill không liên quan). Đa tác tử không đáng chi phí trong thí nghiệm này: điểm thấp hơn, token gấp 4,6 lần, giao việc chỉ ở 3/6 lần chạy (`subagent_calls` 0, 2, 0, 0, 2, 1) và khi giao việc thì subagent cũng không biết quy ước nên không cứu được check `rule_`. Kết quả khớp H1.
5. **Rò rỉ và quá khớp.** Không thấy rò rỉ: cả 3 skill qua `validate_skill` (không chứa `eval_markers()`), và không chứa tên quy ước mới của tác vụ đánh giá (tìm `version`, `source_line`, `sorted_keys` trong `skills/auto/` chỉ thấy `schema_version` - một quy ước của logs-learn). Biện pháp phòng tránh: (a) curator chỉ đọc run có `role == "learn"` (có test `test_04` kiểm tra); (b) shell của tác tử bị cô lập khỏi kho mã nguồn (Phụ lục) - trước khi vá, một lần chạy đã đọc `check.py` của tác vụ đánh giá; vết đó được chuyển sang `results/_quarantine/` TRƯỚC khi chạy curator nên không vào prompt của curator; (c) giả thuyết được commit và skill được đóng băng trước khi chạy tác vụ đánh giá (`verify_freeze.py` OK). Dấu hiệu quá khớp theo nghĩa "khớp nhầm họ": `output-normalization-rules` có `description` rộng nên ở data-learn (Phần 3.4) tác tử đem `schema_version`/`generated_by` của họ logs vào `answer.json`; skill có ví dụ nguyên văn của tác vụ học (ví dụ `payment-service`) - hữu ích khi quy ước giữ nguyên, vô dụng với quy ước mới.
6. **Nhiễu.** Cùng bộ skill, cùng nhiệt độ 0: Phần 3.4 đạt 1/10, 5/8, 0/9 (6/27); sau đóng băng đạt 1/10, 0/8, 0/9 (1/27). Riêng data-learn lệch 5 check (5/8 → 0/8): lần sau tác tử lại đi dò hệ thống tệp và cạn bước. Như vậy nhiễu giữa hai lần chạy có thể tới 5 check trên một tác vụ, lớn hơn mọi chênh lệch giữa `skills-auto` và `baseline` ở tác vụ đánh giá (+2 ở code-eval, +1 ở logs-eval). Kết luận "skills-auto tốt hơn baseline trên tác vụ đánh giá" KHÔNG đủ tin cậy với một lần chạy; điều đứng vững hơn là các mẫu định tính lặp lại ở nhiều lần chạy: quy ước mới luôn thất bại (9/9), check quy ước chỉ đạt khi skill nêu quy ước đủ cụ thể, và `subagents` luôn tốn token nhiều nhất.

## 9. Hạn chế và tính hợp lệ

1. **Mỗi cấu hình chạy một lần, mô hình nhiễu lớn.** Cùng skill, cùng nhiệt độ 0 mà data-learn lệch 5/8 check (mục 8.6). Nhiệt độ 0 không làm DeepSeek tất định; hơn nữa vòng lặp và cạn bước xảy ra ngẫu nhiên ở 9/21 lần chạy chính thức. Mọi chênh lệch dưới khoảng 5 check mỗi tác vụ trong bảng mục 7 cần được coi là chưa kết luận; cần ít nhất 3 lần lặp mỗi điều kiện (hướng 6e) để có khoảng dao động.
2. **Ít tác vụ, tác vụ do giảng viên thiết kế.** Chỉ 3 tác vụ mỗi vai trò, mỗi họ 1 cặp; quy ước được thiết kế để ổn định trong họ và có đúng một quy ước mới ở tác vụ đánh giá. Do đó tỉ lệ "quy ước mới 0/9" phản ánh thiết kế tác vụ nhiều hơn năng lực tổng quát hóa thật; kết quả không suy rộng cho tác vụ ngoài 3 họ này.
3. **Một mô hình, một cấu hình bước.** Chỉ dùng `deepseek-chat` với `recursion_limit` 60. Hành vi nổi bật nhất (đi dò hệ thống tệp để tìm "Acme reporting conventions", lặp lệnh) có thể đặc thù cho mô hình này; với mô hình khác hoặc giới hạn bước lớn hơn, điểm học của baseline và subagents có thể cao hơn nhiều, làm đổi thứ hạng ở tác vụ học.
4. **Harness thay đổi so với bản tối thiểu.** Shell của tác tử chạy bằng user không đặc quyền (`IsolatedShellBackend`, Phụ lục) và runner dùng `agent.stream` để giữ vết khi lỗi. Hai thay đổi này cần cho tính hợp lệ (không đọc được `check.py`) nhưng làm môi trường khác với các nhóm chạy `LocalShellBackend` trực tiếp: điểm không so sánh trực tiếp được giữa các nhóm, và ở môi trường không cô lập, điểm baseline có thể bị thổi phồng do tác tử đọc bộ chấm.
5. **`subagent_calls` và vết chỉ phản ánh luồng chính.** Không thấy subagent làm gì bên trong, và trường `subagent_type` bị cắt ở 1.500 ký tự trong `trace.md`, nên nhận định về vai trò subagent được gọi là suy ra từ nội dung lời giao việc.

## 10. Kết luận

Trong thí nghiệm này, skill do curator tự sinh chỉ giúp các check quy ước được dùng lại từ tác vụ học (3/12 so với 0/12 của baseline trên tác vụ đánh giá), không giúp check kỹ thuật (đã đạt 18/18 ở baseline) và không giúp quy ước mới (0/9 ở mọi điều kiện). Mức tăng điểm đánh giá của `skills-auto` (0,69 so với 0,60) nhỏ hơn nhiễu đo được giữa hai lần chạy cùng bộ skill (tới 5 check mỗi tác vụ), nên chưa thể khẳng định là cải thiện thật. Đa tác tử không có lợi: điểm thấp hơn (0,42) với chi phí gấp 4,6 lần token trên tác vụ đánh giá. Lỗi nguy hiểm nhất không nằm ở chất lượng skill mà ở harness: shell không cô lập cho phép tác tử đọc bộ chấm, và ngân sách 60 bước bị tiêu vào việc dò tìm tài liệu không tồn tại. Đề xuất tiếp theo: yêu cầu curator chép NGUYÊN VĂN từng câu `RULE:` vào skill (để tránh lỗi thiếu chi tiết như `rule_changelog`, `rule_schema_header`) và lặp mỗi điều kiện ít nhất 3 lần để tách tác dụng khỏi nhiễu.

## Phụ lục

- Lệnh đã chạy (theo thứ tự; mọi lệnh `lab.runner`/`lab.curator` chạy trong `docker run --rm -v "${PWD}:/secure/lab" lab-isolated ...`):
  1. `docker build -f Dockerfile.isolated -t lab-isolated .`
  2. `pytest tests/` (29 passed)
  3. `python -m lab.runner --condition baseline --tasks data-learn`
  4. `python -m lab.runner --condition baseline --tasks code-learn logs-learn`
  5. `python -m lab.runner --condition subagents --tasks learn`
  6. `python -m lab.curator`
  7. `python -m lab.runner --condition skills-auto --tasks learn`, rồi `mv results/skills-auto results/skills-auto-dev`
  8. `git commit -m "hypotheses"`; `git commit --allow-empty -m "freeze skills" && git tag freeze`
  9. `python -m lab.runner --condition baseline --tasks eval`
  10. `python -m lab.runner --condition subagents --tasks eval`
  11. `python -m lab.runner --condition skills-auto --tasks all`
  12. `python scripts/verify_freeze.py` (OK); `python -m lab.compare > report/table.md`; `python scripts/check_breakdown.py`
- Thử thách mở rộng: không thực hiện.
- Ghi chú khác - cô lập sandbox (thay đổi harness):
  - Trong lần chạy DeepSeek đầu tiên (Docker thường, repo mount ở `/lab`), shell của `LocalShellBackend` chạy bằng root nên tác tử đọc được cả kho mã nguồn. Vết (`results/_quarantine/baseline-data-learn-sandbox-escape/trace.md`) cho thấy tác tử dò `find / -maxdepth 3 -iname '*convention*'`, tìm thấy `/lab`, đọc `instruction.md` và `check.py` của cả 6 tác vụ (kể cả 3 tác vụ đánh giá), tự chạy `python3 /lab/tasks/data-learn/check.py` và đạt 8/8. Tệp `.env` có xuất hiện trong danh sách thư mục nhưng không được mở. Lần chạy này bị loại khỏi kết quả và khỏi đầu vào của curator.
  - Cách vá: `IsolatedShellBackend` trong `src/lab/agent.py` chạy mọi lệnh shell bằng user `agent` (qua `setpriv`), sandbox được mở quyền cho user này; `Dockerfile.isolated` mount kho vào `/secure/lab` với `/secure` mode 700. Đã kiểm tra: user `agent` vẫn dùng được `workspace/`, `python`, nhưng `ls /secure/lab` trả về `Permission denied`. Công cụ tệp vốn đã bị `virtual_mode=True` giới hạn trong sandbox. Cơ chế chỉ bật khi có biến `LAB_AGENT_USER`, nên test của giảng viên chạy như cũ.
  - `runner.py` dùng `agent.stream(..., stream_mode="values")` thay cho `invoke` (mở rộng tùy chọn trong `03_runner.md`) để vẫn có vết và số đếm khi gặp `GraphRecursionError`.
  - `verify_freeze.py` phải chạy trên Linux: trên Windows, `hash_skills` băm đường dẫn có dấu `\` nên không khớp `skills_sha256` ghi trong container.
