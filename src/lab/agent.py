"""GUIDE Phần 1 - Dựng tác tử (agent) bằng Deep Agents.   >>> SINH VIÊN CÀI ĐẶT make_backend VÀ build_agent <<<

Pseudo-code: guides/pseudocode/01_agent.md
Kiểm tra:    pytest tests/test_02_agent.py
"""
import os
import shlex
import sys
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from .model import make_model
from .subagents import get_subagents

# ---- CÓ SẴN, KHÔNG SỬA: system prompt dùng chung cho mọi sinh viên (để đường cơ sở so sánh được) ----
PATHS_NOTE = (
    "PATHS: every path is relative to the sandbox root and never starts with '/'. "
    "The task files are in the folder workspace/ (for example workspace/app.log). "
    "Use exactly this relative form both in the file tools and in the shell (execute); "
    "the shell starts in the sandbox root. "
)
BASE_PROMPT = (
    "You are an engineering assistant working in a sandbox. "
    + PATHS_NOTE
    + "Use the shell to run Python and tests. "
    "When you are done, reply with a short summary that mentions only files you really created or changed."
)
SKILLS_NOTE = (
    " Skills are in the folder skills/ (one sub-folder per skill with a SKILL.md). "
    "As your FIRST action, read the SKILL.md of every skill whose description could apply to the task, "
    "then follow them. Never modify skills/."
)
SUBAGENTS_NOTE = (
    " You have specialised subagents (see the description of the task tool). "
    "For anything beyond a trivial step, delegate to a suitable subagent and put ALL the task rules and file paths "
    "in the delegation message, because a subagent sees only what you send. "
    "Check what a subagent returns before you rely on it."
)
# --------------------------------------------------------------------------------------------------


class IsolatedShellBackend(LocalShellBackend):
    """Chạy lệnh shell của tác tử bằng một user không đặc quyền (dùng trong Dockerfile.isolated).

    LocalShellBackend chỉ cô lập công cụ tệp (virtual_mode); shell vẫn chạy với quyền của tiến trình runner
    nên đọc được kho mã nguồn (tasks/*/check.py, tác vụ đánh giá, .env). Với user riêng, kho nằm dưới một
    thư mục chỉ root vào được, còn sandbox được mở quyền cho user đó.
    """

    def __init__(self, *args, user: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self._share_sandbox()

    def _share_sandbox(self):
        # công cụ tệp chạy bằng root và tạo tệp với quyền 0o644, nên mở quyền ghi cho user của tác tử
        for p in [self.cwd, *self.cwd.rglob("*")]:
            p.chmod(p.stat().st_mode | (0o777 if p.is_dir() else 0o666))

    def write(self, file_path, content):
        result = super().write(file_path, content)
        self._share_sandbox()
        return result

    def upload_files(self, files):
        result = super().upload_files(files)
        self._share_sandbox()
        return result

    def execute(self, command, *, timeout=None):
        wrapped = f"setpriv --reuid={self._user} --regid={self._user} --init-groups -- /bin/sh -c {shlex.quote(command)}"
        return super().execute(wrapped, timeout=timeout)


def make_backend(sandbox: Path):
    """Tạo backend (môi trường thực thi) cho tác tử.

    Yêu cầu:
      - Thư mục gốc (root_dir) là `sandbox`; đường dẫn tương đối `workspace/...` và `skills/...`
        phải dùng được ở CẢ công cụ tệp lẫn shell (shell chạy với thư mục làm việc = `sandbox`).
      - Tác tử chạy được lệnh shell và gọi được `python` (cần đặt PATH).
      - KHÔNG chuyển biến môi trường của bạn vào shell của tác tử (khóa API không được lộ).
    """
    env = {
        # thư mục chứa python đang chạy (venv) đứng đầu, sau đó là các thư mục hệ thống
        "PATH": os.pathsep.join([str(Path(sys.executable).parent), "/usr/local/bin", "/usr/bin", "/bin"]),
        "HOME": str(sandbox),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    kwargs = dict(
        root_dir=sandbox,
        virtual_mode=True,
        inherit_env=False,  # không kế thừa biến môi trường của tiến trình cha (khóa API)
        env=env,
        timeout=120,
    )
    user = os.getenv("LAB_AGENT_USER")       # chỉ đặt trong Dockerfile.isolated
    if user:
        return IsolatedShellBackend(user=user, **kwargs)
    return LocalShellBackend(**kwargs)


def build_agent(sandbox: Path, mode: str = "single", use_skills: bool = False, model=None):
    """Tạo tác tử Deep Agents.

    Tham số:
      sandbox:    thư mục chứa `workspace/` (và `skills/` nếu có).
      mode:       "single"    -> tác tử mặc định (có subagent `general-purpose` sẵn của Deep Agents)
                  "subagents" -> thêm các subagent từ `get_subagents()` (nối PATHS_NOTE vào `system_prompt` của MỖI subagent,
                                 vì subagent không nhận BASE_PROMPT) và thêm SUBAGENTS_NOTE vào prompt chính
      use_skills: True -> nạp thư mục "/skills/" qua tham số `skills=` của create_deep_agent
                  và thêm SKILLS_NOTE vào prompt.
      model:      mô hình ngôn ngữ; None -> dùng `make_model()`.
    mode không hợp lệ -> ném ValueError.
    Trả về: đồ thị (graph) đã biên dịch, gọi bằng `.invoke({"messages": [...]})`.
    """
    if mode not in ("single", "subagents"):
        raise ValueError(f"unknown mode: {mode!r} (expected 'single' or 'subagents')")

    kwargs = {}
    prompt = BASE_PROMPT
    if mode == "subagents":
        # subagent không nhận BASE_PROMPT, nên mỗi subagent cần quy ước đường dẫn riêng
        kwargs["subagents"] = [{**sub, "system_prompt": sub["system_prompt"] + " " + PATHS_NOTE}
                               for sub in get_subagents()]
        prompt += SUBAGENTS_NOTE
    if use_skills:
        kwargs["skills"] = ["/skills/"]  # đường dẫn ảo, tính từ root_dir của backend
        prompt += SKILLS_NOTE

    return create_deep_agent(
        model=model if model is not None else make_model(),
        system_prompt=prompt,
        backend=make_backend(sandbox),
        **kwargs,
    )
