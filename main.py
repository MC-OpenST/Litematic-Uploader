import os
import json
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import glob

# ---------------- 基础路径 ----------------
BASE = os.getcwd()
FILES = os.path.join(BASE, "files")
LITEMATIC = os.path.join(FILES, "litematic")
IMAGES = os.path.join(FILES, "images")
CFG = os.path.join(BASE, "config.json")
GIT_DIR = os.path.join(BASE, ".repo")  # 隐藏 Git 仓库

# ---------------- 工具函数 ----------------
def run(cmd, cwd=BASE, check=True):
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW

    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        creationflags=creationflags  # Windows 隐藏窗口
    )
    if check and r.returncode != 0:
        msg = r.stderr.strip() or r.stdout.strip() or f"命令执行失败: {' '.join(cmd)}"
        print("Git 错误信息:", msg)
        raise RuntimeError(msg)
    return r.stdout.strip()

def ensure_dirs():
    os.makedirs(LITEMATIC, exist_ok=True)
    os.makedirs(IMAGES, exist_ok=True)

def ensure_gitignore():
    gi = os.path.join(BASE, ".gitignore")
    if os.path.exists(gi):
        return
    with open(gi, "w", encoding="utf-8") as f:
        f.write(
            "*\n"
            "!files/\n"
            "!files/litematic/\n"
            "!files/images/\n"
            "!files/litematic/**\n"
            "!files/images/**\n"
            "!.repo/\n"
        )

def load_cfg():
    if not os.path.exists(CFG):
        return {"repo": "", "token": "", "tags": ['大宗','空盒仓库','MIS多物品分类','MBS多种类潜影盒分类','细雪展示','SIS无实体输入','编码相关','远程大宗','不可堆叠分类','打包机','混杂打包','自适应打包机','地狱门加载器','分盒器','盒子分类','盒子合并','红石合成站','解码器','潜影盒展示','四边形大宗','整流器','仓库成品']}
    with open(CFG, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cfg(data):
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_repo(repo_url, token):
    os.makedirs(GIT_DIR, exist_ok=True)
    run(["git", "init"], cwd=GIT_DIR)
    if os.name == 'nt':
        subprocess.run(["attrib", "+h", GIT_DIR], creationflags=subprocess.CREATE_NO_WINDOW)

    run(["git", "remote", "remove", "origin"], cwd=GIT_DIR, check=False)
    remote = repo_url.replace("https://", f"https://{token}@")
    print("设置远程 URL:", remote)
    run(["git", "remote", "add", "origin", remote], cwd=GIT_DIR)

    try:
        run(["git", "fetch", "origin", "main"], cwd=GIT_DIR)
        branch = "main"
    except RuntimeError:
        run(["git", "fetch", "origin"], cwd=GIT_DIR)
        branch = "HEAD"

    for pattern in ["files/litematic/*", "files/images/*"]:
        abs_pattern = os.path.join(GIT_DIR, pattern.replace("/", os.sep))
        for f in glob.glob(abs_pattern):
            if os.path.isfile(f):
                os.remove(f)
            elif os.path.isdir(f):
                shutil.rmtree(f)

    run(["git", "checkout", "-B", "upload-temp", f"origin/{branch}"], cwd=GIT_DIR)

def git_commit_push(msg, paths):
    rel_paths = [os.path.relpath(p, GIT_DIR) for p in paths]
    run(["git", "add"] + rel_paths, cwd=GIT_DIR)
    status = run(["git", "status", "--porcelain"], cwd=GIT_DIR)
    if not status:
        print("没有文件变化，跳过 commit")
        return
    run(["git", "commit", "-m", msg], cwd=GIT_DIR)
    run(["git", "push", "origin", "HEAD:main"], cwd=GIT_DIR)

def bind_scroll(canvas):
    # 鼠标滚轮滚动
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * int(e.delta / 120), "units"))
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

# ---------------- GUI ----------------
class App(tk.Tk):
    def reset_form(self):
        # 清空名称
        self.name_entry.delete(0, tk.END)

        # 清空文件选择
        self.litematics = []
        self.image = ""
        self.update_hint()

        # 取消所有标签勾选
        for v in self.tag_vars.values():
            v.set(False)

    def __init__(self):
        super().__init__()
        self.title("Litematic Uploader v0.3.2")
        self.geometry("640x520")
        self.resizable(True, True)  # 允许窗口自适应

        ensure_dirs()
        ensure_gitignore()

        self.cfg = load_cfg()
        self.litematics = []
        self.image = ""

        self.build_ui()

    def build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # 顶部固定框架
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", side="top")

        # 底部固定框架
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", side="bottom", pady=5)

        self.status = ttk.Label(bottom_frame, text="就绪")
        self.status.pack(side="left", padx=10)
        ttk.Button(bottom_frame, text="上传", command=self.upload).pack(side="right", padx=10)

        # 中间滚动区域
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(fill="both", expand=True, side="left")
        scrollbar.pack(fill="y", side="right")

        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # 让鼠标滚轮滚动
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * int(event.delta / 120), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # ----------- 文件选择 -----------
        box_files = ttk.LabelFrame(self.scrollable_frame, text="文件选择")
        box_files.pack(fill="x", **pad)
        ttk.Button(box_files, text="选择 Litematic（可多选）", command=self.pick_litematic).pack(side="left", padx=10)
        ttk.Button(box_files, text="选择 图片（可选）", command=self.pick_image).pack(side="left", padx=10)
        self.file_hint = ttk.Label(box_files, text="未选择文件")
        self.file_hint.pack(side="left", padx=10)

        # ----------- 命名 -----------
        box_name = ttk.LabelFrame(self.scrollable_frame, text="命名")
        box_name.pack(fill="x", **pad)
        ttk.Label(box_name, text="基础名称").pack(anchor="w", padx=10)
        self.name_entry = ttk.Entry(box_name)
        self.name_entry.pack(fill="x", padx=10)

        # ----------- 标签 -----------
        box_tags = ttk.LabelFrame(self.scrollable_frame, text="标签（复选）")
        box_tags.pack(fill="x", **pad)
        self.tag_vars = {}
        self.tags_frame = ttk.Frame(box_tags)
        self.tags_frame.pack(fill="x", padx=10)
        self.render_tags()

        addf = ttk.Frame(box_tags)
        addf.pack(fill="x", padx=10, pady=6)
        self.new_tag = ttk.Entry(addf)
        self.new_tag.pack(side="left", fill="x", expand=True)
        ttk.Button(addf, text="+ 添加标签", command=self.add_tag).pack(side="left", padx=6)

        # ----------- 仓库配置 -----------
        box_repo = ttk.LabelFrame(self.scrollable_frame, text="仓库配置（只需一次）")
        box_repo.pack(fill="x", **pad)
        ttk.Label(box_repo, text="仓库 HTTPS URL").pack(anchor="w", padx=10)
        self.repo_entry = ttk.Entry(box_repo)
        self.repo_entry.pack(fill="x", padx=10)
        self.repo_entry.insert(0, self.cfg.get("repo", ""))
        ttk.Label(box_repo, text="GitHub Token").pack(anchor="w", padx=10)
        self.token_entry = ttk.Entry(box_repo, show="*")
        self.token_entry.pack(fill="x", padx=10)
        self.token_entry.insert(0, self.cfg.get("token", ""))
        ttk.Button(box_repo, text="保存配置", command=self.save_repo).pack(pady=6)

    def render_tags(self):
        for w in self.tags_frame.winfo_children():
            w.destroy()
        self.tag_vars.clear()
        for i, t in enumerate(self.cfg.get("tags", [])):
            v = tk.BooleanVar(value=False)
            self.tag_vars[t] = v
            row = i // 5  # 每行最多 5 个标签
            col = i % 5
            ttk.Checkbutton(self.tags_frame, text=t, variable=v).grid(row=row, column=col, padx=6, pady=3,
                                                                          sticky="w")
            # 让列自适应
            self.tags_frame.columnconfigure(col, weight=1)

    def pick_litematic(self):
        self.litematics = filedialog.askopenfilenames(filetypes=[("Litematic", "*.litematic")])
        self.update_hint()

    def pick_image(self):
        self.image = filedialog.askopenfilename(filetypes=[("Image", "*.png")])
        self.update_hint()

    def update_hint(self):
        parts = []
        if self.litematics:
            parts.append(f"{len(self.litematics)} 个 litematic")
        if self.image:
            parts.append("已选图片")
        self.file_hint.config(text=" / ".join(parts) if parts else "未选择文件")

    def add_tag(self):
        t = self.new_tag.get().strip()
        if not t or t in self.cfg["tags"]:
            return
        self.cfg["tags"].append(t)
        self.new_tag.delete(0, tk.END)
        self.render_tags()
        save_cfg(self.cfg)

    def save_repo(self):
        self.cfg["repo"] = self.repo_entry.get().strip()
        self.cfg["token"] = self.token_entry.get().strip()
        save_cfg(self.cfg)
        messagebox.showinfo("完成", "配置已保存")

    def upload(self):
        try:
            name = self.name_entry.get().strip()
            if not name:
                raise RuntimeError("请填写名称")

            if not self.litematics and not self.image:
                raise RuntimeError("请至少选择一个 litematic 或一张图片")
            repo = self.repo_entry.get().strip()
            token = self.token_entry.get().strip()
            if not repo or not token:
                raise RuntimeError("请先保存仓库配置")

            self.status.config(text="准备仓库…")
            self.update_idletasks()
            ensure_repo(repo, token)

            tags = [t for t, v in self.tag_vars.items() if v.get()]
            tag_str = f"[{' '.join(tags)}]" if tags else ""
            base_name = f"{name}{tag_str}"

            self.status.config(text="生成上传文件…")
            self.update_idletasks()

            repo_base = GIT_DIR
            litematic_repo = os.path.join(repo_base, "files", "litematic")
            images_repo = os.path.join(repo_base, "files", "images")
            os.makedirs(litematic_repo, exist_ok=True)
            os.makedirs(images_repo, exist_ok=True)

            files_to_upload = []

            for src in self.litematics:
                dst = os.path.join(litematic_repo, base_name + ".litematic")
                shutil.copy(src, dst)
                files_to_upload.append(dst)

            if self.image:
                dst_img = os.path.join(images_repo, base_name + ".png")
                shutil.copy(self.image, dst_img)
                files_to_upload.append(dst_img)

            self.status.config(text="提交并推送…")
            self.update_idletasks()

            git_commit_push(f"Add {base_name}", files_to_upload)

            self.status.config(text="完成")
            messagebox.showinfo("成功", f"上传完成：{base_name}")
            self.reset_form()


        except Exception as e:
            messagebox.showerror("失败", str(e))
            self.status.config(text="失败")

# ---------------- 入口 ----------------
if __name__ == "__main__":
    App().mainloop()
