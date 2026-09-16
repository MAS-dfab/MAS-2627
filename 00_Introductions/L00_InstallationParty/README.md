# MAS ETH DFAB 2627 Installation Party

> Welcome! Please follow the steps below to prepare your environment for the course.
>
> ⚠️ Start with the Google Workspace step **before** the installation party — the license has to be approved by ETH IT and that is not instant. Everything else can be installed on the day.

## 🔑 Google Workspace access

Your ETH account does not have Google Workspace switched on by default. You request it once, through the IT-Shop, and wait for approval. Without it you cannot open the course Drive.

1. Go to the [IT-Shop](https://itshop.ethz.ch) and log in with your ETH credentials.
2. In the Service Catalog, under **Cloud Services**, choose **Personal Cloud Subscription**.
3. Choose **Request Cloud Subscription (non Microsoft)**.
4. Read the usage rules for external cloud services, fill in the form and submit it.
5. Wait for the confirmation email from the IT-Shop.

Once you have the confirmation, sign in at [accounts.google.com](https://accounts.google.com):

- **Username:** `username@ethz.ch`
- **Password:** your ETH password, then your one-time password — you will be redirected to the ETH AD authentication page

After signing in, the Google apps live behind the "waffle" icon (⋮⋮⋮) in the top right corner.

Full instructions from ETH IT: [Google Workspace — first steps](https://unlimited.ethz.ch/en/help/googlews/getting-started/first-steps)

## 📁 Course Materials

All course materials are available on our [Google Drive](https://drive.google.com/drive/u/0/folders/0AE0mCJZHB44PUk9PVA).

Sign in with your `@ethz.ch` account first. If you land on a "request access" page, you are most likely signed in with a private Google account — switch accounts, or open the link in a private window.

## 🛠️ Required Software

Install the following before the first session:

### 1. [Git](https://git-scm.com/downloads)
Version control for code and collaboration.

### 2. [Rhino 8](https://www.rhino3d.com/download/)
3D modeling software used in the course.

### 3. [Visual Studio Code](https://code.visualstudio.com/Download)
Recommended code editor.

### 4. [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
Lightweight Python distribution for managing environments and packages.

⚠️ **During the install, leave "Add Miniconda3 to my PATH environment variable" unchecked.** The installer itself labels that option "not recommended". Ticking it puts conda's Python — and a large pile of conda's own DLLs — ahead of everything else for *every* program on your machine, so unrelated software can start picking up the wrong libraries. Rhino ships its own Python, and this is exactly the kind of conflict that makes it misbehave in ways that are very hard to trace.

Leave **"Register Miniconda3 as my default Python"** as it is (checked). That one lets editors find the interpreter without touching `PATH`.

Instead of `PATH`, let conda wire itself into your shell. Open the **Anaconda Prompt** from the Windows Start menu (on macOS, any terminal) and run the line for each shell you actually use:

```bash
conda init powershell   # Windows: PowerShell, and the VS Code terminal
conda init bash         # Windows: Git Bash
conda init zsh          # macOS: the default shell
```

Then close every open terminal and open a new one.

**Make sure it worked:**

```bash
conda --version         # prints a version number
conda activate base     # your prompt should now start with (base)
```

The second line is the one that matters. `conda --version` working only proves conda is *findable*; if the prompt does not change to `(base)`, environments will not work and none of the later course setup will behave.

**If something goes wrong**

- *`conda activate` prints nothing at all and the prompt does not change* — conda is reachable but the shell hook is missing, so activation silently does nothing. Run the matching `conda init` line above from the Anaconda Prompt, then open a new terminal.
- *PowerShell says "running scripts is disabled on this system"* — the hook lives in your PowerShell profile, which Windows blocks by default. Run once in PowerShell: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, confirm with `Y`, then open a new terminal.
- *`conda` is not recognised at all* — use the Anaconda Prompt. It works even when nothing else does.
- *Every terminal now opens in `(base)` and you would rather it did not* — `conda config --set auto_activate_base false`.

## ✅ Before you leave the installation party

- [ ] Google Workspace license requested **and** confirmation email received
- [ ] Course Drive opens with your ETH account
- [ ] Rhino 8 starts
- [ ] VS Code starts
- [ ] `conda activate base` puts `(base)` in your prompt


---
If you have any issues, reach out!
