# VoteFree GitHub 发布新手指南（一步一步）

这份指南按“第一次发布”的顺序写，你照着做即可。

## 1. 准备发布内容（本地）

1. 确认源码目录里已经有这些文件：
   - `README.md`
   - `LICENSE`
   - `.gitignore`
   - `CHANGELOG.md`
2. 确认可执行包已生成：
   - `dist/VoteFree/`
3. 确认“空白发布包”存在（不含数据）：
   - `VoteFree_Blank_Release_*.zip`

## 2. 在 GitHub 创建仓库

1. 打开 GitHub，点击右上角 `+` -> `New repository`。
2. 仓库名建议：`VoteFree`。
3. 选择 `Public`（公开）或 `Private`（私有）。
4. `不要勾选` 初始化 README（因为你本地已有项目）。
5. 点击 `Create repository`。

## 3. 首次推送源码（PowerShell）

在项目根目录 `D:\Program\VoteFree` 打开终端，按顺序执行：

```powershell
git init
git add .
git commit -m "chore: initial open-source release"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

如果提示要登录，按 GitHub 提示完成网页登录授权即可。

## 4. 打版本标签（Tag）

例如发布 `v1.0.0`：

```powershell
git tag v1.0.0
git push origin v1.0.0
```

## 5. 在 GitHub 创建 Release

1. 进入仓库页面 -> 右侧 `Releases` -> `Create a new release`。
2. `Choose a tag` 选择 `v1.0.0`。
3. 标题写：`VoteFree v1.0.0`。
4. 内容可复制 `RELEASE_TEMPLATE.md`，改成你的实际描述。
5. 上传附件（拖拽即可）：
   - Windows 程序包（建议你自己打包命名为 `VoteFree-v1.0.0-windows-x64.zip`）
   - 空白包（你已有 `VoteFree_Blank_Release_...zip`）
6. 点击 `Publish release`。

## 6. 发布前最后检查（非常重要）

1. 仓库里不应出现：
   - `data/`
   - `.db`、`.pem`、`.vote`
   - `back/data/`
2. Release 附件可以有 exe zip，但源码仓库不要提交业务数据。
3. 下载 Release 附件自测一次，确认可运行。

## 7. 以后每次发版的固定流程

1. 改代码 -> 更新 `CHANGELOG.md`
2. `git add .` -> `git commit`
3. `git tag vX.Y.Z` -> `git push` -> `git push --tags`
4. 创建对应 Release 并上传附件

---

如果你希望，我可以在下一步直接给你“可复制粘贴的一套命令”，把你这次版本按 `v1.0.0` 一次性发布完。
