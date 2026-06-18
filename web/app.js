const $ = (selector) => document.querySelector(selector);

const shareText = $("#shareText");
const parseButton = $("#parseButton");
const workspace = $("#workspace");
const downloadButton = $("#downloadButton");
const outputDir = $("#outputDir");
const openOutputButton = $("#openOutputButton");
const notice = $("#notice");
let sessionId = null;
let pollTimer = null;
let activeJobId = null;

function setNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.toggle("error", isError);
}

function setBusy(button, busy, busyText, idleText) {
  button.disabled = busy;
  button.firstChild.textContent = busy ? busyText : idleText;
}

function setDownloadBusy(busy) {
  downloadButton.disabled = busy;
  downloadButton.innerHTML = busy
    ? '正在下载… <span>↻</span>'
    : '开始下载 <span>↓</span>';
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

function showInfo(info) {
  sessionId = info.session_id;
  $("#videoTitle").textContent = info.title;
  $("#author").textContent = `作者 · ${info.author}`;
  $("#duration").textContent = info.duration;
  const cover = $("#cover");
  cover.src = info.thumbnail || "";
  cover.style.display = info.thumbnail ? "block" : "none";
  const tags = $("#formatTags");
  tags.replaceChildren(...info.formats.map((format) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = format;
    return tag;
  }));
  workspace.classList.remove("is-hidden");
  workspace.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

parseButton.addEventListener("click", async () => {
  const value = shareText.value.trim();
  if (!value) {
    setNotice("请先粘贴抖音分享链接或分享文本", true);
    shareText.focus();
    return;
  }
  setBusy(parseButton, true, "正在解析…", "解析视频 ");
  setNotice("正在访问公开页面并获取视频信息…");
  try {
    const info = await request("/api/parse", {
      method: "POST",
      body: JSON.stringify({ share_text: value }),
    });
    showInfo(info);
    setNotice("解析完成，可以选择清晰度下载");
  } catch (error) {
    setNotice(error.message, true);
  } finally {
    setBusy(parseButton, false, "正在解析…", "解析视频 ");
  }
});

function updateProgress(job) {
  $("#progressBar").style.width = `${job.progress}%`;
  $("#progressNumber").textContent = `${job.progress}%`;
  $("#speed").textContent = job.speed;
  $("#eta").textContent = job.eta;
  $("#progressStatus").textContent = job.message;
}

async function pollJob(jobId) {
  if (activeJobId !== jobId) return true;
  try {
    const job = await request(`/api/jobs/${jobId}`);
    updateProgress(job);
    if (job.status === "complete") {
      clearInterval(pollTimer);
      pollTimer = null;
      activeJobId = null;
      setDownloadBusy(false);
      $("#result").textContent = `已保存：${job.saved_path}`;
      setNotice(job.message);
      window.alert(`下载成功！\n\n文件已保存到：\n${job.saved_path}`);
      return true;
    } else if (job.status === "failed") {
      clearInterval(pollTimer);
      pollTimer = null;
      activeJobId = null;
      setDownloadBusy(false);
      setNotice(job.message, true);
      return true;
    }
  } catch (error) {
    clearInterval(pollTimer);
    pollTimer = null;
    activeJobId = null;
    setDownloadBusy(false);
    setNotice(error.message, true);
    return true;
  }
  return false;
}

downloadButton.addEventListener("click", async () => {
  if (!sessionId) return;
  const outputValue = outputDir.value.trim();
  if (!outputValue) {
    setNotice("请输入视频保存目录", true);
    outputDir.focus();
    return;
  }
  setDownloadBusy(true);
  $("#result").textContent = "";
  updateProgress({ progress: 0, speed: "计算中", eta: "计算中", message: "正在下载" });
  setNotice("正在下载视频，请保持页面打开…");
  try {
    const data = await request("/api/download", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        quality: $("#quality").value,
        output_dir: outputValue,
      }),
    });
    activeJobId = data.job_id;
    const finished = await pollJob(data.job_id);
    if (!finished) pollTimer = setInterval(() => pollJob(data.job_id), 700);
  } catch (error) {
    setDownloadBusy(false);
    setNotice(error.message, true);
  }
});

openOutputButton.addEventListener("click", async () => {
  const outputValue = outputDir.value.trim();
  if (!outputValue) {
    setNotice("请输入视频保存目录", true);
    outputDir.focus();
    return;
  }
  openOutputButton.disabled = true;
  openOutputButton.textContent = "打开中…";
  try {
    const data = await request("/api/open-output", {
      method: "POST",
      body: JSON.stringify({ output_dir: outputValue }),
    });
    setNotice(`已打开保存目录：${data.path}`);
  } catch (error) {
    setNotice(error.message, true);
  } finally {
    openOutputButton.disabled = false;
    openOutputButton.textContent = "打开目录";
  }
});
