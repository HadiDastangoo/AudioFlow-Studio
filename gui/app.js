let currentFilePath = "";
let isModified = false;
let cachedInitialTags = null;
let cachedInitialCovers = [];
let currentCovers = [];
let activeCoverIndex = -1;
let pendingNewCoverType = 3;

let currentSelectedDetailItem = null;
let cachedOrigLyrics = "";
let cachedTransLyrics = "";
let cachedCombinedLyrics = "";
let currentLyricsTab = "original";

let latestDownloadUrl = "";
let lastCheckedTimestamp = null;

let cropImg = new Image();
let cropScale = 1;
let cropPanX = 0;
let cropPanY = 0;
let isDraggingCrop = false;
let dragStartX = 0, dragStartY = 0;

let activeInputTarget = null;

const APIC_TYPE_NAMES = {
  3: "Front Cover (Main)",
  4: "Back Cover",
  7: "Lead Artist / Performer",
  11: "Composer",
  9: "Band / Orchestra",
  12: "Lyricist",
  15: "Recording Location",
  14: "Illustration",
  19: "Artist Logo",
  20: "Publisher / Studio Logo"
};

const translations = {
  en: {
    btnAbout: "About",
    dropText: "Drop audio or video files here or browse",
    dropSubtext: "Supported: MP3 (Edit directly) • FLAC, MP4, M4A, WAV, AAC, MKV, FLV (Convert & Edit)",
    lblCurrentFile: "Current File:",
    nonMp3Notice: "This is not an MP3 file; convert to MP3 to edit tags.",
    btnConvert: "Convert to MP3",
    chooseCover: "Choose Album Cover",
    changeCover: "Change & Crop",
    lblTitle: "Title",
    lblArtist: "Artist",
    lblAlbum: "Album",
    lblGenre: "Genre",
    lblComposer: "Composer",
    lblYear: "Year",
    lblTrack: "Track #",
    lblDisc: "Disc #",
    lblCopyright: "Copyright",
    lblComment: "Comment",
    lblOtherTags: "Extended / Other Tags (Publisher, Lyrics, Mood, ...)",
    lblPublisher: "Publisher / Label",
    lblMood: "Mood",
    lblBpm: "BPM",
    lblOrigArtist: "Original Artist",
    lblIsrc: "ISRC",
    lblLyrics: "Unsynchronized Lyrics",
    btnSearchOnline: "Search Online Metadata",
    btnReset: "Reset",
    btnSave: "Save Tags",
    btnClearAll: "Clear All",
    clearAllModalTitle: "Clear All Tags",
    clearAllModalDesc: "All metadata fields in this file will be cleared. Are you sure you want to proceed?",
    chkDeleteCovers: "Also remove all embedded covers",
    btnConfirmClear: "Clear Tags",
    chooseCoverTypeTitle: "Select Cover Type",
    chooseCoverTypeDesc: "Select the image type you want to add to this audio file:",
    btnContinue: "Continue & Browse",
    onlineMatches: "Online Matches (Up to 10 releases)",
    detailsTitle: "Release Details",
    btnClose: "Close",
    settingsTitle: "Preferences & Storage",
    lblLanguage: "Language",
    lblTheme: "Theme",
    themeSystem: "System Default",
    themeLight: "Light",
    themeDark: "Dark",
    overwriteNotice: "Overwrite original file (If unchecked, saves as new file)",
    lblOutputDir: "Output folder path:",
    btnBrowse: "Browse",
    btnSaveAndClose: "Save & Apply",
    resetConfirmTitle: "Reset Warning",
    resetConfirmDesc: "Unsaved changes detected. Are you sure you want to discard them and revert to initial tags?",
    btnCancel: "Cancel",
    btnConfirmReset: "Yes, Revert",
    cropTitle: "Square Crop Cover",
    btnApplyCrop: "Apply 1:1 Crop",
    aboutDesc: "Modern MP4 to MP3 converter & intelligent ID3 tag batch editor.",
    aboutDev: "Developer: Hadi Dastangoo",
    searching: "Searching online...",
    copied: "Copied to clipboard!",
    savedSuccess: "Tags and covers saved successfully.",
    applyTags: "Set Tags",
    applyCover: "Set Cover",
    applyAll: "Set Tags & Cover",
    viewLyrics: "Lyrics",
    btnApplyLyricsToComment: "Set as Track Comment & Lyrics",
    lyricsTitle: "Lyrics",
    noLyricsFound: "No lyrics found for this track online.",
    fetchingLyrics: "Fetching lyrics...",
    lblAppUpdate: "Software Update:",
    btnCheckUpdate: "Check for Updates",
    checkingUpdate: "Checking...",
    updateAvailable: "New version available!",
    updateLatest: "You are using the latest version.",
    btnDownload: "Download",
    lastCheckedNever: "Last checked: Never",
    lastCheckedPrefix: "Last checked: ",
    noInternet: "Unable to connect to the internet. Please check your network connection.",
    allCoversAdded: "All supported cover types are already added.",
    tabCombined: "Original + Translation",
    tabTranslated: "Translation",
    tabOriginal: "Original",
    btnTranslate: "Translate",
    translating: "Translating...",
    ctxCut: "Cut",
    ctxCopy: "Copy",
    ctxPaste: "Paste",
    ctxSelectAll: "Select All"
  },
  fa: {
    btnAbout: "درباره برنامه",
    dropText: "فایل صوتی یا تصویری را اینجا بکشید یا برای انتخاب کلیک کنید",
    dropSubtext: "فرمت‌های پشتیبانی‌شده: MP3 (ویرایش مستقیم) • FLAC, MP4, M4A, WAV, AAC, MKV, FLV (تبدیل و ویرایش)",
    lblCurrentFile: "فایل بارگذاری‌شده:",
    nonMp3Notice: "این فایل MP3 نیست؛ برای ویرایش تگ‌ها تبدیل به MP3 الزامی است.",
    btnConvert: "تبدیل به MP3",
    chooseCover: "انتخاب کاور آهنگ (کلیک کنید)",
    changeCover: "برش و تغییر",
    lblTitle: "عنوان آهنگ (Title)",
    lblArtist: "هنرمند / خواننده (Artist)",
    lblAlbum: "آلبوم (Album)",
    lblGenre: "سبک موسیقی (Genre)",
    lblComposer: "آهنگساز (Composer)",
    lblYear: "سال انتشار (Year)",
    lblTrack: "شماره ترک (Track)",
    lblDisc: "شماره دیسک (Disc)",
    lblCopyright: "کپی‌رایت (Copyright)",
    lblComment: "توضیحات (Comment)",
    lblOtherTags: "سایر تگ‌ها / فیلدهای پیشرفته (ناشر، شعر، حس‌وحال و...)",
    lblPublisher: "ناشر / لیبل (Publisher)",
    lblMood: "حس و حال (Mood)",
    lblBpm: "تمپو / ضرب‌آهنگ (BPM)",
    lblOrigArtist: "خواننده اصلی (Original Artist)",
    lblIsrc: "شناسه استاندارد ISRC",
    lblLyrics: "متن کامل ترانه (Unsynchronized Lyrics)",
    btnSearchOnline: "جستجوی آنلاین اطلاعات آهنگ",
    btnReset: "بازنشانی",
    btnSave: "ذخیره اطلاعات آهنگ",
    btnClearAll: "حذف تمام تگ‌ها",
    clearAllModalTitle: "حذف کامل تمام متادیتاها",
    clearAllModalDesc: "تمامی مقادیر تگ‌ها در این فایل پاک خواهند شد. آیا از انجام این کار اطمینان دارید؟",
    chkDeleteCovers: "حذف تمامی کاورها و تصاویر فایل صوتی",
    btnConfirmClear: "پاکسازی تمام تگ‌ها",
    chooseCoverTypeTitle: "انتخاب نوع کاور جدید",
    chooseCoverTypeDesc: "نوع تصویری که می‌خواهید به فایل صوتی اضافه کنید را انتخاب کنید:",
    btnContinue: "ادامه و انتخاب فایل",
    onlineMatches: "نتایج هوشمند آنلاین (تا ۱۰ مورد مشابه)",
    detailsTitle: "جزئیات انتشار آهنگ",
    btnClose: "بستن",
    settingsTitle: "تنظیمات و ذخیره‌سازی",
    lblLanguage: "زبان برنامه",
    lblTheme: "پوسته ظاهری",
    themeSystem: "پوسته سیستم",
    themeLight: "روز (روشن)",
    themeDark: "شب (تاریک)",
    overwriteNotice: "نوشتن مستقیم بر روی فایل اصلی (در صورت غیرفعال بودن، فایل جدید ایجاد می‌شود)",
    lblOutputDir: "پوشه ذخیره‌سازی خروجی:",
    btnBrowse: "انتخاب پوشه",
    btnSaveAndClose: "تأیید و اعمال",
    resetConfirmTitle: "هشدار بازنشانی",
    resetConfirmDesc: "تغییرات ذخیره‌نشده‌ای وجود دارد. آیا از بازگردانی اطلاعات اولیه اطمینان دارید؟",
    btnCancel: "انصراف",
    btnConfirmReset: "بله، بازنشانی کن",
    cropTitle: "برش مربعی کاور",
    btnApplyCrop: "تأیید و اعمال کاور",
    aboutDesc: "برنامه استخراج و تگ‌گذاری پیشرفته موسیقی با استانداردهای مدرن.",
    aboutDev: "توسعه‌دهنده: هادی داستانگو",
    searching: "در حال جستجو...",
    copied: "در حافظه کپی شد!",
    savedSuccess: "تگ‌ها و کاورها با موفقیت ذخیره شدند.",
    applyTags: "تنظیم اطلاعات",
    applyCover: "تنظیم کاور",
    applyAll: "تنظیم اطلاعات و کاور",
    viewLyrics: "متن ترانه",
    btnApplyLyricsToComment: "درج در فیلد توضیحات و شعر",
    lyricsTitle: "متن ترانه",
    noLyricsFound: "متن ترانه‌ای برای این آهنگ یافت نشد.",
    fetchingLyrics: "در حال دریافت شعر...",
    lblAppUpdate: "بروزرسانی برنامه:",
    btnCheckUpdate: "بررسی بروزرسانی",
    checkingUpdate: "در حال بررسی...",
    updateAvailable: "نسخه جدید منتشر شده است!",
    updateLatest: "شما از آخرین نسخه برنامه استفاده می‌کنید.",
    btnDownload: "دانلود نسخه جدید",
    lastCheckedNever: "آخرین بررسی: هنوز انجام نشده",
    lastCheckedPrefix: "آخرین بررسی: ",
    noInternet: "امکان برقراری ارتباط با وب وجود ندارد. لطفاً اتصال اینترنت خود را بررسی نمایید.",
    allCoversAdded: "تمام انواع مجاز کاور قبلاً اضافه شده‌اند.",
    tabCombined: "متن و ترجمه (ترکیبی)",
    tabTranslated: "ترجمه",
    tabOriginal: "متن اصلی",
    btnTranslate: "ترجمه متن",
    translating: "در حال ترجمه...",
    ctxCut: "برش (Cut)",
    ctxCopy: "کپی (Copy)",
    ctxPaste: "جای‌گذاری (Paste)",
    ctxSelectAll: "انتخاب همه (Select All)"
  }
};

let currentLang = "en";

let appRepoUrl = "https://github.com/HadiDastangoo/AudioFlow-Studio";

async function initAppInfo() {
  try {
    const info = await window.pywebview.api.get_app_info();
    if (info) {
      // تنظیم متون هدر
      const headerTitle = document.getElementById('appHeaderTitle');
      const headerVersion = document.getElementById('appHeaderVersion');
      if (headerTitle) headerTitle.innerText = info.name;
      if (headerVersion) headerVersion.innerText = info.version;

      // تنظیم متون مدال About
      const aboutName = document.getElementById('aboutAppName');
      const aboutVer = document.getElementById('aboutAppVersion');
      if (aboutName) aboutName.innerText = info.name;
      if (aboutVer) aboutVer.innerText = info.version;

      // تنظیم نسخه در بخش تنظیمات/بروزرسانی
      const currentVerText = document.getElementById('txtCurrentVersion');
      if (currentVerText) currentVerText.innerText = info.version;

      // ذخیره لینک گیت‌هاب
      if (info.repo_url) appRepoUrl = info.repo_url;
    }
  } catch (err) {
    console.error("Failed to load app info:", err);
  }
}

function openGithubRepo() {
  window.pywebview.api.open_external_url(appRepoUrl);
}

function applyLanguage(lang) {
  currentLang = lang;
  document.documentElement.lang = lang;
  document.documentElement.dir = (lang === "fa") ? "rtl" : "ltr";

  const dict = translations[lang];
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) el.innerText = dict[key];
  });

  if (lastCheckedTimestamp) {
    formatAndDisplayLastChecked(lastCheckedTimestamp);
  }
  renderCoversStrip();

  if (window.cachedOnlineItems && window.cachedOnlineItems.length > 0) {
    renderOnlineResults(window.cachedOnlineItems);
  }
}

function applyTheme(theme) {
  document.body.classList.remove('theme-dark', 'theme-light', 'theme-system');
  if (theme === 'system') {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) document.body.classList.add('theme-dark');
  } else if (theme === 'dark') {
    document.body.classList.add('theme-dark');
  }
}

function showToast(msg, isError = false) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  if (isError) {
    toast.classList.add('toast-error');
  } else {
    toast.classList.remove('toast-error');
  }
  toast.style.display = 'block';
  setTimeout(() => { toast.style.display = 'none'; }, 4000);
}

async function handleSelectFile() {
  const res = await window.pywebview.api.select_file_dialog();
  if (res) renderFileState(res);
}

const allModals = ['detailModal', 'lyricsModal', 'settingsModal', 'confirmResetModal', 'cropModal', 'aboutModal', 'clearAllModal', 'coverTypeModal'];
allModals.forEach(modalId => {
  const modalEl = document.getElementById(modalId);
  if (modalEl) {
    modalEl.addEventListener('click', (e) => {
      if (e.target === modalEl) modalEl.style.display = 'none';
    });
  }
});

const dropZone = document.getElementById('dropZone');
['dragenter', 'dragover'].forEach(eventName => {
  window.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); });
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault(); e.stopPropagation();
    dropZone.classList.add('dragover');
  });
});

['dragleave', 'dragend'].forEach(eventName => {
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault(); e.stopPropagation();
    dropZone.classList.remove('dragover');
  });
});

dropZone.addEventListener('drop', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  dropZone.classList.remove('dragover');

  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    const fileObj = e.dataTransfer.files[0];
    const fullPath = fileObj.pywebviewFullPath || fileObj.path || "";
    if (fullPath) {
      const res = await window.pywebview.api.process_selected_file(fullPath);
      if (res) renderFileState(res);
    } else {
      handleSelectFile();
    }
  }
});

function renderFileState(res) {
  resetAudioPlayer();

  if (res.status === 'error') {
    showToast(res.message, true);
    return;
  }
  currentFilePath = res.file_path;

  const bar = document.getElementById('loadedFilenameBar');
  const nameTxt = document.getElementById('displayLoadedFilename');
  bar.style.display = 'flex';
  nameTxt.innerText = res.filename || res.file_path.split('\\').pop().split('/').pop();

  if (res.status === 'needs_conversion') {
    document.getElementById('conversionBanner').style.display = 'flex';
    document.getElementById('nonMp3Name').innerText = res.filename;
    document.getElementById('editorGrid').style.display = 'none';
    document.getElementById('onlineSection').style.display = 'none';
  } else if (res.status === 'ready_mp3') {
    document.getElementById('conversionBanner').style.display = 'none';
    cachedInitialTags = JSON.parse(JSON.stringify(res.tags));
    cachedInitialCovers = JSON.parse(JSON.stringify(res.covers || []));
    loadMp3IntoEditor(res.file_path, res.tags, res.covers || [], res.audio_data);
  }
}

function copyCurrentFilename(btnEl) {
  const nameTxt = document.getElementById('displayLoadedFilename').innerText;
  if (nameTxt && nameTxt !== '---') {
    smartCopyText(nameTxt, btnEl);
  }
}

async function convertCurrentFile() {
  const btn = document.getElementById('btnConvert');
  btn.disabled = true;
  btn.innerText = (currentLang === "fa") ? "در حال تبدیل..." : "Converting...";
  const res = await window.pywebview.api.convert_to_mp3(currentFilePath);
  btn.disabled = false;
  btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg> <span>${translations[currentLang].btnConvert}</span>`;

  if (res.status === 'success') {
    document.getElementById('conversionBanner').style.display = 'none';
    document.getElementById('displayLoadedFilename').innerText = res.filename;
    cachedInitialTags = JSON.parse(JSON.stringify(res.tags));
    cachedInitialCovers = JSON.parse(JSON.stringify(res.covers || []));
    loadMp3IntoEditor(res.file_path, res.tags, res.covers || [], res.audio_data);
    showToast((currentLang === "fa") ? "تبدیل با موفقیت انجام شد." : "Conversion complete.");
  } else {
    showToast(res.message, true);
  }
}

function resetAudioPlayer() {
  const audioEl = document.getElementById('audioElement');
  if (audioEl) {
    audioEl.pause();
    audioEl.currentTime = 0;
    audioEl.src = "";
  }
  document.getElementById('playBtnIcon').innerHTML = `<polygon points="5 3 19 12 5 21 5 3"></polygon>`;
  document.getElementById('playerProgressFill').style.width = "0%";
  document.getElementById('playerCurrentTime').innerText = "00:00";
  document.getElementById('playerTotalTime').innerText = "00:00";
}

function loadMp3IntoEditor(filePath, tags, covers, audioDataUrl) {
  currentFilePath = filePath;
  document.getElementById('editorGrid').style.display = 'grid';

  resetAudioPlayer();

  const audioEl = document.getElementById('audioElement');
  if (audioDataUrl) {
    audioEl.src = audioDataUrl;
    audioEl.load();
  }

  fillInputFields(tags);

  currentCovers = JSON.parse(JSON.stringify(covers));
  activeCoverIndex = currentCovers.length > 0 ? 0 : -1;
  renderCoversStrip();
  updateCoverDisplay();

  isModified = false;
  document.getElementById('btnSave').disabled = true;
  checkSearchBtnState();

  if (tags.title || tags.artist) {
    searchOnline();
  }
}

function fillInputFields(tags) {
  document.getElementById('inputTitle').value = tags.title || "";
  document.getElementById('inputArtist').value = tags.artist || "";
  document.getElementById('inputAlbum').value = tags.album || "";
  document.getElementById('inputGenre').value = tags.genre || "";
  document.getElementById('inputComposer').value = tags.composer || "";
  document.getElementById('inputYear').value = tags.year || "";
  document.getElementById('inputTrack').value = tags.track || "";
  document.getElementById('inputDisc').value = tags.disc || "";
  document.getElementById('inputCopyright').value = tags.copyright || "";
  document.getElementById('inputComment').value = tags.comment || "";

  document.getElementById('inputPublisher').value = tags.publisher || "";
  document.getElementById('inputMood').value = tags.mood || "";
  document.getElementById('inputBpm').value = tags.bpm || "";
  document.getElementById('inputOriginalArtist').value = tags.original_artist || "";
  document.getElementById('inputIsrc').value = tags.isrc || "";
  document.getElementById('inputLyrics').value = tags.lyrics || "";
}

function handleFieldChange() {
  isModified = true;
  document.getElementById('btnSave').disabled = false;
  checkSearchBtnState();
}

function checkSearchBtnState() {
  const title = document.getElementById('inputTitle').value.trim();
  const artist = document.getElementById('inputArtist').value.trim();
  document.getElementById('btnOnlineSearch').disabled = (title === "" && artist === "");
}

function toggleExtendedTagsAccordion() {
  const header = document.getElementById('accordionToggleBtn');
  const body = document.getElementById('accordionBody');
  const isOpen = header.classList.toggle('open');
  body.style.display = isOpen ? 'flex' : 'none';
}

function renderCoversStrip() {
  const strip = document.getElementById('coversThumbsStrip');
  strip.innerHTML = "";

  currentCovers.forEach((cov, idx) => {
    const item = document.createElement('div');
    item.className = 'thumb-item' + (idx === activeCoverIndex ? ' active' : '');
    item.title = cov.type_name || APIC_TYPE_NAMES[cov.type] || `Type ${cov.type}`;
    item.onclick = () => selectCoverIndex(idx);
    item.innerHTML = `<img src="${cov.dataUrl}" alt="Cover ${idx}">`;
    strip.appendChild(item);
  });

  const availableTypes = Object.keys(APIC_TYPE_NAMES).filter(t => !currentCovers.some(c => c.type == t));
  if (availableTypes.length > 0) {
    const addBtn = document.createElement('div');
    addBtn.className = 'thumb-add-btn';
    addBtn.title = (currentLang === 'fa') ? "افزودن کاور جدید" : "Add Cover";
    addBtn.onclick = openAddCoverTypeModal;
    addBtn.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
      <span>${(currentLang === 'fa') ? 'کاور جدید' : 'Add'}</span>
    `;
    strip.appendChild(addBtn);
  }
}

function selectCoverIndex(idx) {
  if (idx >= 0 && idx < currentCovers.length) {
    activeCoverIndex = idx;
    renderCoversStrip();
    updateCoverDisplay();
  }
}

function updateCoverDisplay() {
  const img = document.getElementById('coverImage');
  const placeholder = document.getElementById('coverPlaceholder');
  const badge = document.getElementById('coverTypeBadge');
  const overlay = document.getElementById('coverOverlay');

  if (activeCoverIndex >= 0 && activeCoverIndex < currentCovers.length) {
    const cov = currentCovers[activeCoverIndex];
    img.src = cov.dataUrl;
    img.style.display = 'block';
    placeholder.style.display = 'none';
    badge.innerText = cov.type_name || APIC_TYPE_NAMES[cov.type] || `Type ${cov.type}`;
    badge.style.display = 'block';
    overlay.style.display = 'flex';
  } else {
    img.src = "";
    img.style.display = 'none';
    placeholder.style.display = 'flex';
    badge.style.display = 'none';
    overlay.style.display = 'none';
  }
}

function triggerAddCover(typeNum = 3) {
  pendingNewCoverType = typeNum;
  document.getElementById('coverFileInput').click();
}

function openAddCoverTypeModal() {
  const select = document.getElementById('selectNewCoverType');
  select.innerHTML = "";
  
  const existingTypes = currentCovers.map(c => parseInt(c.type));
  let hasAny = false;

  for (const [tCode, tName] of Object.entries(APIC_TYPE_NAMES)) {
    if (!existingTypes.includes(parseInt(tCode))) {
      const opt = document.createElement('option');
      opt.value = tCode;
      opt.innerText = tName;
      select.appendChild(opt);
      hasAny = true;
    }
  }

  if (!hasAny) {
    showToast(translations[currentLang].allCoversAdded, true);
    return;
  }

  document.getElementById('coverTypeModal').style.display = 'flex';
}

function closeCoverTypeModal() {
  document.getElementById('coverTypeModal').style.display = 'none';
}

function proceedToPickCoverFile() {
  const select = document.getElementById('selectNewCoverType');
  pendingNewCoverType = parseInt(select.value) || 3;
  closeCoverTypeModal();
  document.getElementById('coverFileInput').click();
}

function triggerEditCurrentCover() {
  if (activeCoverIndex >= 0 && activeCoverIndex < currentCovers.length) {
    pendingNewCoverType = currentCovers[activeCoverIndex].type;
    document.getElementById('coverFileInput').click();
  }
}

function deleteCurrentCover() {
  if (activeCoverIndex >= 0 && activeCoverIndex < currentCovers.length) {
    currentCovers.splice(activeCoverIndex, 1);
    if (currentCovers.length === 0) {
      activeCoverIndex = -1;
    } else if (activeCoverIndex >= currentCovers.length) {
      activeCoverIndex = currentCovers.length - 1;
    }
    renderCoversStrip();
    updateCoverDisplay();
    handleFieldChange();
    showToast((currentLang === "fa") ? "کاور حذف گردید؛ دکمه ذخیره را بزنید." : "Cover deleted. Save to apply.");
  }
}

function handleCoverFileSelected(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    cropImg.onload = () => {
      cropScale = 1;
      cropPanX = 0;
      cropPanY = 0;
      document.getElementById('cropZoomSlider').value = 1;
      document.getElementById('cropModal').style.display = 'flex';
      initOfflineCanvasCrop();
    };
    cropImg.src = event.target.result;
  };
  reader.readAsDataURL(file);
  e.target.value = "";
}

function initOfflineCanvasCrop() {
  const canvas = document.getElementById('cropCanvas');
  const ctx = canvas.getContext('2d');
  drawCropCanvas(ctx, canvas);

  canvas.onmousedown = (e) => {
    isDraggingCrop = true;
    dragStartX = e.clientX - cropPanX;
    dragStartY = e.clientY - cropPanY;
  };
  window.onmousemove = (e) => {
    if (!isDraggingCrop) return;
    cropPanX = e.clientX - dragStartX;
    cropPanY = e.clientY - dragStartY;
    drawCropCanvas(ctx, canvas);
  };
  window.onmouseup = () => { isDraggingCrop = false; };
}

function updateCropTransform() {
  cropScale = parseFloat(document.getElementById('cropZoomSlider').value);
  const canvas = document.getElementById('cropCanvas');
  drawCropCanvas(canvas.getContext('2d'), canvas);
}

function drawCropCanvas(ctx, canvas) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const size = Math.min(cropImg.width, cropImg.height);
  const renderW = (cropImg.width / size) * canvas.width * cropScale;
  const renderH = (cropImg.height / size) * canvas.height * cropScale;
  const drawX = (canvas.width - renderW) / 2 + cropPanX;
  const drawY = (canvas.height - renderH) / 2 + cropPanY;
  ctx.drawImage(cropImg, drawX, drawY, renderW, renderH);
}

function closeCropModal() {
  document.getElementById('cropModal').style.display = 'none';
}

function applyCrop() {
  const canvas = document.getElementById('cropCanvas');
  const croppedBase64 = canvas.toDataURL('image/jpeg', 0.94);
  
  const typeNum = pendingNewCoverType || 3;
  const typeName = APIC_TYPE_NAMES[typeNum] || `Type ${typeNum}`;

  const existingIdx = currentCovers.findIndex(c => c.type == typeNum);
  const newCoverObj = {
    type: typeNum,
    type_name: typeName,
    mime: "image/jpeg",
    desc: typeName,
    dataUrl: croppedBase64
  };

  if (existingIdx !== -1) {
    currentCovers[existingIdx] = newCoverObj;
    activeCoverIndex = existingIdx;
  } else {
    currentCovers.push(newCoverObj);
    activeCoverIndex = currentCovers.length - 1;
  }

  renderCoversStrip();
  updateCoverDisplay();
  handleFieldChange();
  closeCropModal();
  showToast((currentLang === "fa") ? "کاور تنظیم شد؛ جهت ذخیره نهایی دکمه ذخیره را بزنید." : "Cover set. Press Save to apply.");
}

function openClearAllModal() {
  document.getElementById('chkDeleteCovers').checked = false;
  document.getElementById('clearAllModal').style.display = 'flex';
}

function closeClearAllModal() {
  document.getElementById('clearAllModal').style.display = 'none';
}

function performClearAllTags() {
  closeClearAllModal();

  document.getElementById('inputTitle').value = "";
  document.getElementById('inputArtist').value = "";
  document.getElementById('inputAlbum').value = "";
  document.getElementById('inputGenre').value = "";
  document.getElementById('inputComposer').value = "";
  document.getElementById('inputYear').value = "";
  document.getElementById('inputTrack').value = "";
  document.getElementById('inputDisc').value = "";
  document.getElementById('inputCopyright').value = "";
  document.getElementById('inputComment').value = "";
  document.getElementById('inputPublisher').value = "";
  document.getElementById('inputMood').value = "";
  document.getElementById('inputBpm').value = "";
  document.getElementById('inputOriginalArtist').value = "";
  document.getElementById('inputIsrc').value = "";
  document.getElementById('inputLyrics').value = "";

  const deleteCovers = document.getElementById('chkDeleteCovers').checked;
  if (deleteCovers) {
    currentCovers = [];
    activeCoverIndex = -1;
    renderCoversStrip();
    updateCoverDisplay();
  }

  handleFieldChange();
  showToast((currentLang === "fa") ? "تمام تگ‌ها پاک شدند؛ برای نهایی‌شدن ذخیره را بزنید." : "All tags cleared. Save to apply.");
}

function promptResetTags() {
  if (isModified) {
    document.getElementById('confirmResetModal').style.display = 'flex';
  } else {
    performResetTags();
  }
}

function closeConfirmResetModal() {
  document.getElementById('confirmResetModal').style.display = 'none';
}

function performResetTags() {
  closeConfirmResetModal();
  if (!cachedInitialTags) return;

  fillInputFields(cachedInitialTags);
  currentCovers = JSON.parse(JSON.stringify(cachedInitialCovers || []));
  activeCoverIndex = currentCovers.length > 0 ? 0 : -1;
  renderCoversStrip();
  updateCoverDisplay();

  isModified = false;
  document.getElementById('btnSave').disabled = true;
  checkSearchBtnState();
  showToast((currentLang === "fa") ? "اطلاعات اولیه آهنگ بازنشانی شد." : "Tags reverted to original.");
}

const audioEl = document.getElementById('audioElement');
const playBtn = document.getElementById('playerPlayBtn');
const playBtnIcon = document.getElementById('playBtnIcon');
const progressFill = document.getElementById('playerProgressFill');
const currTimeTxt = document.getElementById('playerCurrentTime');
const totalTimeTxt = document.getElementById('playerTotalTime');

function formatTime(sec) {
  if (isNaN(sec) || sec < 0) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
}

function togglePlayAudio() {
  if (audioEl.paused) {
    audioEl.play();
  } else {
    audioEl.pause();
  }
}

audioEl.onplay = () => {
  playBtnIcon.innerHTML = `<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>`;
};
audioEl.onpause = () => {
  playBtnIcon.innerHTML = `<polygon points="5 3 19 12 5 21 5 3"></polygon>`;
};
audioEl.ontimeupdate = () => {
  currTimeTxt.innerText = formatTime(audioEl.currentTime);
  const pct = (audioEl.currentTime / audioEl.duration) * 100 || 0;
  progressFill.style.width = `${pct}%`;
};
audioEl.onloadedmetadata = () => {
  totalTimeTxt.innerText = formatTime(audioEl.duration);
};

function seekAudio(e) {
  const wrap = document.getElementById('playerProgressWrap');
  const rect = wrap.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const pct = Math.max(0, Math.min(1, clickX / rect.width));
  if (audioEl.duration) {
    audioEl.currentTime = pct * audioEl.duration;
  }
}

function changeVolume(val) {
  audioEl.volume = parseFloat(val);
}

async function searchOnline() {
  const title = document.getElementById('inputTitle').value.trim();
  const artist = document.getElementById('inputArtist').value.trim();

  const btn = document.getElementById('btnOnlineSearch');
  const txt = document.getElementById('txtOnlineSearch');
  btn.disabled = true;
  txt.innerText = translations[currentLang].searching;

  const res = await window.pywebview.api.search_online_metadata(title, artist);
  btn.disabled = false;
  txt.innerText = translations[currentLang].btnSearchOnline;

  if (res.status === 'no_internet') {
    showToast(translations[currentLang].noInternet, true);
    return;
  }

  renderOnlineResults(res.results || []);
}

function setViewMode(mode) {
  const grid = document.getElementById('resultsGrid');
  const btnGrid = document.getElementById('btnViewGrid');
  const btnList = document.getElementById('btnViewList');
  if (mode === 'grid') {
    grid.className = 'results-grid view-grid';
    btnGrid.classList.add('active');
    btnList.classList.remove('active');
  } else {
    grid.className = 'results-grid view-list';
    btnList.classList.add('active');
    btnGrid.classList.remove('active');
  }
}

function renderOnlineResults(items) {
  const grid = document.getElementById('resultsGrid');
  const section = document.getElementById('onlineSection');
  grid.innerHTML = "";

  if (!items || items.length === 0) {
    section.style.display = 'none';
    showToast((currentLang === "fa") ? "موردی در جستجوی آنلاین یافت نشد." : "No online matches found.");
    return;
  }

  section.style.display = 'block';
  const dict = translations[currentLang];
  items.forEach((item, index) => {
    const card = document.createElement('div');
    card.className = 'result-card';
    card.onclick = () => openDetailModal(index);
    card.innerHTML = `
      <img class="result-thumb" src="${item.artwork_url}" alt="Cover">
      <div class="result-details">
        <h4 title="${item.title}">${item.title}</h4>
        <p title="${item.artist}">${item.artist} | ${item.album || 'Single'}</p>
        <p>${item.year ? (currentLang==='fa' ? 'سال: ' : 'Year: ') + item.year : ''} ${item.genre ? ' | ' + item.genre : ''}</p>
      </div>
      <div class="result-buttons" onclick="event.stopPropagation()">
        <button class="btn-sm" onclick="applyOnlineData(${index}, 'tags')">${dict.applyTags}</button>
        <button class="btn-sm" onclick="applyOnlineData(${index}, 'cover')">${dict.applyCover}</button>
        <button class="btn-sm full-apply" onclick="applyOnlineData(${index}, 'all')">${dict.applyAll}</button>
        <button class="btn-sm btn-lyrics" onclick="showLyricsModal(${index})">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
          <span>${dict.viewLyrics}</span>
        </button>
      </div>
    `;
    grid.appendChild(card);
  });
  window.cachedOnlineItems = items;
}

async function applyOnlineData(idx, mode) {
  const item = window.cachedOnlineItems[idx];
  if (!item) return;

  if (mode === 'tags' || mode === 'all') {
    document.getElementById('inputTitle').value = item.title;
    document.getElementById('inputArtist').value = item.artist;
    document.getElementById('inputAlbum').value = item.album;
    document.getElementById('inputYear').value = item.year;
    document.getElementById('inputTrack').value = item.track;
    if (item.genre) document.getElementById('inputGenre').value = item.genre;
    if (item.composer) document.getElementById('inputComposer').value = item.composer;
    if (item.copyright) document.getElementById('inputCopyright').value = item.copyright;
  }

  if (mode === 'cover' || mode === 'all') {
    showToast((currentLang === "fa") ? "در حال دریافت کاور باکیفیت..." : "Fetching high-res cover...");
    const res = await window.pywebview.api.fetch_image_base64(item.artwork_url);
    if (res.status === 'success') {
      const frontIdx = currentCovers.findIndex(c => c.type == 3);
      const newFront = {
        type: 3,
        type_name: APIC_TYPE_NAMES[3],
        mime: "image/jpeg",
        desc: "Front Cover (Main)",
        dataUrl: res.dataUrl
      };
      if (frontIdx !== -1) {
        currentCovers[frontIdx] = newFront;
        activeCoverIndex = frontIdx;
      } else {
        currentCovers.unshift(newFront);
        activeCoverIndex = 0;
      }
      renderCoversStrip();
      updateCoverDisplay();
      handleFieldChange();
      showToast((currentLang === "fa") ? "کاور اعمال گردید." : "Cover set successfully.");
    } else if (res.status === 'no_internet') {
      showToast(translations[currentLang].noInternet, true);
    } else {
      showToast("Error downloading cover.", true);
    }
  }
  handleFieldChange();
}

function openDetailModal(index) {
  const item = window.cachedOnlineItems[index];
  if (!item) return;
  currentSelectedDetailItem = item;

  document.getElementById('detailCoverImg').src = item.artwork_url;
  const list = document.getElementById('detailFieldsList');
  list.innerHTML = "";

  const fields = [
    { key: "Title", val: item.title },
    { key: "Artist", val: item.artist },
    { key: "Album", val: item.album },
    { key: "Year", val: item.year },
    { key: "Track", val: item.track },
    { key: "Genre", val: item.genre },
    { key: "Composer", val: item.composer },
    { key: "Copyright", val: item.copyright }
  ];

  fields.forEach(f => {
    if (!f.val) return;
    const row = document.createElement('div');
    row.className = 'detail-field-item';
    row.innerHTML = `
      <div class="field-info">
        <span class="field-title">${f.key}</span>
        <span class="field-val" title="${f.val}">${f.val}</span>
      </div>
      <button class="copy-btn" title="Copy" onclick="smartCopyText('${f.val.replace(/'/g, "\\'")}', this)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
      </button>
    `;
    list.appendChild(row);
  });

  document.getElementById('detailModal').style.display = 'flex';
}

function closeDetailModal() {
  document.getElementById('detailModal').style.display = 'none';
}

async function smartCopyText(text, btnElement = null) {
  if (!text) return;
  
  let copiedViaPython = false;
  try {
    const res = await window.pywebview.api.copy_text_to_clipboard(text);
    if (res && res.status === 'success') {
      copiedViaPython = true;
    }
  } catch (err) {}

  if (!copiedViaPython) {
    const normalized = text.split('\r\n').join('\n').split('\r').join('\n').split('\n').join('\r\n');
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(normalized);
      } catch (e) {
        fallbackCopy(normalized);
      }
    } else {
      fallbackCopy(normalized);
    }
  }

  if (btnElement) {
    const originalSvg = btnElement.innerHTML;
    btnElement.classList.add('copied');
    btnElement.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#28a745" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    setTimeout(() => {
      btnElement.classList.remove('copied');
      btnElement.innerHTML = originalSvg;
    }, 1200);
  }
  showToast(translations[currentLang].copied);
}

function fallbackCopy(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.left = "-999999px";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand('copy');
  } catch (err) {}
  document.body.removeChild(textArea);
}

async function showLyricsModal(index) {
  const item = window.cachedOnlineItems[index];
  if (!item) return;

  const modal = document.getElementById('lyricsModal');
  const titleEl = document.getElementById('lyricsModalTitle');
  const box = document.getElementById('lyricsContentBox');

  titleEl.innerText = `${item.artist} - ${item.title}`;
  modal.style.display = 'flex';

  cachedOrigLyrics = "";
  cachedTransLyrics = "";
  cachedCombinedLyrics = "";

  switchLyricsTab('original');
  updateTranslationTabsAvailability(false);

  box.innerText = translations[currentLang].fetchingLyrics;

  const selectLang = document.getElementById('selectLyricsLang');
  selectLang.value = (currentLang === "fa") ? "fa" : "en";

  const res = await window.pywebview.api.fetch_lyrics(item.title, item.artist);
  if (res.status === 'success') {
    cachedOrigLyrics = res.lyrics;
    displayActiveLyricsTab();
  } else if (res.status === 'no_internet') {
    box.innerText = translations[currentLang].noInternet;
  } else {
    box.innerText = translations[currentLang].noLyricsFound;
  }
}

function updateTranslationTabsAvailability(hasTranslation) {
  const btnCombined = document.getElementById('tabLyricsCombined');
  const btnTrans = document.getElementById('tabLyricsTrans');
  
  btnCombined.disabled = !hasTranslation;
  btnTrans.disabled = !hasTranslation;
  btnCombined.style.opacity = hasTranslation ? "1" : "0.5";
  btnTrans.style.opacity = hasTranslation ? "1" : "0.5";
  btnCombined.style.cursor = hasTranslation ? "pointer" : "not-allowed";
  btnTrans.style.cursor = hasTranslation ? "pointer" : "not-allowed";
}

async function translateCurrentLyrics() {
  if (!cachedOrigLyrics) return;

  const targetLang = document.getElementById('selectLyricsLang').value;
  const box = document.getElementById('lyricsContentBox');
  const btn = document.getElementById('btnDoTranslate');

  btn.disabled = true;
  btn.innerText = translations[currentLang].translating;
  box.innerText = translations[currentLang].translating;

  const res = await window.pywebview.api.translate_lyrics(cachedOrigLyrics, targetLang);
  btn.disabled = false;
  btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg> <span>${translations[currentLang].btnTranslate}</span>`;

  if (res.status === 'success') {
    cachedTransLyrics = res.translated_text;
    cachedCombinedLyrics = res.combined_text;
    updateTranslationTabsAvailability(true);
    switchLyricsTab('combined');
  } else {
    cachedTransLyrics = "";
    cachedCombinedLyrics = "";
    updateTranslationTabsAvailability(false);
    switchLyricsTab('original');
    showToast((res.status === 'no_internet') ? translations[currentLang].noInternet : "Translation error.", true);
  }
}

function switchLyricsTab(tabName) {
  if ((tabName === 'combined' || tabName === 'translated') && !cachedTransLyrics) {
    return;
  }
  currentLyricsTab = tabName;
  document.getElementById('tabLyricsCombined').classList.toggle('active', tabName === 'combined');
  document.getElementById('tabLyricsTrans').classList.toggle('active', tabName === 'translated');
  document.getElementById('tabLyricsOrig').classList.toggle('active', tabName === 'original');
  displayActiveLyricsTab();
}

function displayActiveLyricsTab() {
  const box = document.getElementById('lyricsContentBox');
  let textToShow = "";
  if (currentLyricsTab === 'combined') {
    textToShow = cachedCombinedLyrics || cachedOrigLyrics;
  } else if (currentLyricsTab === 'translated') {
    textToShow = cachedTransLyrics || cachedOrigLyrics;
  } else {
    textToShow = cachedOrigLyrics;
  }
  box.innerText = textToShow;
}

function closeLyricsModal() {
  document.getElementById('lyricsModal').style.display = 'none';
}

function copyLyricsText(btnEl) {
  const box = document.getElementById('lyricsContentBox');
  const text = box.innerText;
  if (text && text !== translations[currentLang].noLyricsFound && text !== translations[currentLang].fetchingLyrics && text !== translations[currentLang].translating) {
    smartCopyText(text, btnEl);
  }
}

function applyLyricsToComment() {
  const box = document.getElementById('lyricsContentBox');
  const activeText = box.innerText.trim();
  if (activeText && activeText !== translations[currentLang].noLyricsFound) {
    document.getElementById('inputComment').value = activeText;
    document.getElementById('inputLyrics').value = activeText;
    handleFieldChange();
    closeLyricsModal();
    showToast((currentLang === 'fa') ? "متن انتخابی ترانه در تگ‌ها قرار گرفت." : "Lyrics set to tags successfully.");
  }
}

async function copyImageToClipboard() {
  if (!currentSelectedDetailItem) return;
  showToast((currentLang === "fa") ? "در حال کپی تصویر..." : "Copying image...");
  const res = await window.pywebview.api.fetch_image_base64(currentSelectedDetailItem.artwork_url);
  if (res.status === 'success') {
    const copyRes = await window.pywebview.api.copy_image_to_clipboard(res.dataUrl);
    if (copyRes.status === 'success') {
      showToast(translations[currentLang].copied);
    } else {
      showToast("Error copying image: " + (copyRes.message || ""), true);
    }
  } else if (res.status === 'no_internet') {
    showToast(translations[currentLang].noInternet, true);
  }
}

async function saveCoverToFile() {
  if (!currentSelectedDetailItem) return;
  showToast((currentLang === "fa") ? "در حال دریافت فایل تصویر..." : "Downloading image...");
  const res = await window.pywebview.api.fetch_image_base64(currentSelectedDetailItem.artwork_url);
  if (res.status === 'success') {
    const saveRes = await window.pywebview.api.save_image_dialog(res.dataUrl, `${currentSelectedDetailItem.artist} - ${currentSelectedDetailItem.title}.jpg`);
    if (saveRes.status === 'success') {
      showToast((currentLang === "fa") ? "تصویر با موفقیت ذخیره شد." : "Image saved successfully.");
    }
  } else if (res.status === 'no_internet') {
    showToast(translations[currentLang].noInternet, true);
  }
}

function openLightbox(url) {
  document.getElementById('lightboxImg').src = url;
  document.getElementById('lightboxModal').style.display = 'flex';
}
function closeLightbox() {
  document.getElementById('lightboxModal').style.display = 'none';
}

async function saveTags() {
  const tags = {
    title: document.getElementById('inputTitle').value.trim(),
    artist: document.getElementById('inputArtist').value.trim(),
    album: document.getElementById('inputAlbum').value.trim(),
    genre: document.getElementById('inputGenre').value.trim(),
    composer: document.getElementById('inputComposer').value.trim(),
    year: document.getElementById('inputYear').value.trim(),
    track: document.getElementById('inputTrack').value.trim(),
    disc: document.getElementById('inputDisc').value.trim(),
    copyright: document.getElementById('inputCopyright').value.trim(),
    comment: document.getElementById('inputComment').value.trim(),
    publisher: document.getElementById('inputPublisher').value.trim(),
    mood: document.getElementById('inputMood').value.trim(),
    bpm: document.getElementById('inputBpm').value.trim(),
    original_artist: document.getElementById('inputOriginalArtist').value.trim(),
    isrc: document.getElementById('inputIsrc').value.trim(),
    lyrics: document.getElementById('inputLyrics').value.trim()
  };

  const btn = document.getElementById('btnSave');
  btn.disabled = true;

  const res = await window.pywebview.api.save_music_tags(currentFilePath, tags, currentCovers);

  btn.disabled = false;
  if (res.status === 'success') {
    currentFilePath = res.new_path;
    if (res.filename) {
      document.getElementById('displayLoadedFilename').innerText = res.filename;
    }
    isModified = false;
    btn.disabled = true;
    showToast(translations[currentLang].savedSuccess);
  } else {
    showToast(res.message, true);
  }
}

async function openSettingsModal() {
  const settings = await window.pywebview.api.get_settings();
  document.getElementById('settingOverwrite').checked = settings.overwrite_original;
  document.getElementById('settingPathDisplay').value = settings.custom_output_dir || (currentLang === 'fa' ? "کنار فایل اصلی (پیش‌‌‌‌فرض)" : "Same directory as source");
  document.getElementById('settingLanguage').value = settings.language || "en";
  document.getElementById('settingTheme').value = settings.theme || "system";
  document.getElementById('settingsModal').style.display = 'flex';
}

function closeSettingsModal() {
  document.getElementById('settingsModal').style.display = 'none';
}

async function browseOutputDir() {
  const path = await window.pywebview.api.select_folder_dialog();
  if (path) {
    document.getElementById('settingPathDisplay').value = path;
  }
}

async function saveSettingsModal() {
  const lang = document.getElementById('settingLanguage').value;
  const theme = document.getElementById('settingTheme').value;
  const newSettings = {
    overwrite_original: document.getElementById('settingOverwrite').checked,
    custom_output_dir: (document.getElementById('settingPathDisplay').value.includes("Same") || document.getElementById('settingPathDisplay').value.includes("پیش‌فرض")) ? "" : document.getElementById('settingPathDisplay').value,
    language: lang,
    theme: theme
  };
  await window.pywebview.api.update_settings(newSettings);
  applyLanguage(lang);
  applyTheme(theme);
  closeSettingsModal();
  showToast((lang === 'fa') ? "تنظیمات اعمال و ذخیره شد." : "Settings saved permanently.");
}

function formatAndDisplayLastChecked(date) {
  lastCheckedTimestamp = date;
  const lbl = document.getElementById('txtLastCheckedTime');
  const prefix = translations[currentLang].lastCheckedPrefix;
  if (currentLang === 'fa') {
    const faDate = new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    }).format(date);
    lbl.innerText = `${prefix}${faDate}`;
  } else {
    const enDate = new Intl.DateTimeFormat('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    }).format(date);
    lbl.innerText = `${prefix}${enDate}`;
  }
}

async function checkAppUpdates(isManual = false) {
  const btn = document.getElementById('btnManualCheckUpdate');
  if (isManual) {
    btn.disabled = true;
    btn.innerText = translations[currentLang].checkingUpdate;
  }

  const res = await window.pywebview.api.check_for_updates();
  formatAndDisplayLastChecked(new Date());

  if (isManual) {
    btn.disabled = false;
    btn.innerText = translations[currentLang].btnCheckUpdate;
  }

  const badge = document.getElementById('settingsUpdateBadge');
  const banner = document.getElementById('updateFoundBanner');
  const bannerTitle = document.getElementById('updateFoundTitle');
  const sizeBadge = document.getElementById('updateFileSizeBadge');
  const notesBox = document.getElementById('updateReleaseNotesBox');

  if (res && res.status === 'success') {
    if (res.has_update) {
      badge.style.display = 'block';
      banner.style.display = 'flex';
      bannerTitle.innerText = `${translations[currentLang].updateAvailable} (${res.latest_version})`;
      
      if (res.file_size) {
        sizeBadge.innerText = res.file_size;
        sizeBadge.style.display = 'inline-block';
      } else {
        sizeBadge.style.display = 'none';
      }

      if (res.release_notes && res.release_notes.trim()) {
        notesBox.innerText = res.release_notes.trim();
        notesBox.style.display = 'block';
      } else {
        notesBox.style.display = 'none';
      }

      latestDownloadUrl = res.download_url;
      if (isManual) {
        showToast(`${translations[currentLang].updateAvailable} (${res.latest_version})`);
      }
    } else {
      badge.style.display = 'none';
      banner.style.display = 'none';
      if (isManual) {
        showToast(translations[currentLang].updateLatest);
      }
    }
  } else if (isManual && res && res.status === 'no_internet') {
    showToast(translations[currentLang].noInternet, true);
  }
}

function manualCheckForUpdates() {
  checkAppUpdates(true);
}

async function downloadLatestRelease() {
  if (latestDownloadUrl) {
    await window.pywebview.api.open_external_url(latestDownloadUrl);
  }
}

function openAboutModal() { document.getElementById('aboutModal').style.display = 'flex'; }
function closeAboutModal() { document.getElementById('aboutModal').style.display = 'none'; }

const contextMenu = document.getElementById('inputContextMenu');
const ctxItemCut = document.getElementById('ctxItemCut');
const ctxItemPaste = document.getElementById('ctxItemPaste');
const ctxDivider = document.getElementById('ctxDivider');

document.addEventListener('contextmenu', (e) => {
  const target = e.target;
  const isInput = target && target.classList && target.classList.contains('input-tag-field');
  const isLyricsBox = target && (target.id === 'lyricsContentBox' || target.closest('#lyricsContentBox'));

  if (isInput || isLyricsBox) {
    e.preventDefault();
    activeInputTarget = isLyricsBox ? document.getElementById('lyricsContentBox') : target;

    if (isLyricsBox) {
      ctxItemCut.style.display = 'none';
      ctxItemPaste.style.display = 'none';
      ctxDivider.style.display = 'none';
    } else {
      ctxItemCut.style.display = 'flex';
      ctxItemPaste.style.display = 'flex';
      ctxDivider.style.display = 'block';
    }

    const menuWidth = 175;
    const menuHeight = isLyricsBox ? 85 : 155;
    let posX = e.clientX;
    let posY = e.clientY;

    if (posX + menuWidth > window.innerWidth) {
      posX = window.innerWidth - menuWidth - 10;
    }
    if (posY + menuHeight > window.innerHeight) {
      posY = window.innerHeight - menuHeight - 10;
    }

    contextMenu.style.left = `${posX}px`;
    contextMenu.style.top = `${posY}px`;
    contextMenu.style.display = 'flex';
  } else {
    contextMenu.style.display = 'none';
  }
});

document.addEventListener('click', (e) => {
  if (contextMenu.style.display === 'flex' && !contextMenu.contains(e.target)) {
    contextMenu.style.display = 'none';
  }
});

async function execContextMenuAction(action) {
  if (!activeInputTarget) return;
  const el = activeInputTarget;
  contextMenu.style.display = 'none';
  const isEditableInput = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA');

  if (isEditableInput) {
    el.focus();
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const val = el.value;

    if (action === 'cut') {
      if (start !== end) {
        const selectedText = val.substring(start, end);
        smartCopyText(selectedText);
        el.value = val.substring(0, start) + val.substring(end);
        el.selectionStart = el.selectionEnd = start;
        handleFieldChange();
      }
    } else if (action === 'copy') {
      if (start !== end) {
        const selectedText = val.substring(start, end);
        smartCopyText(selectedText);
      }
    } else if (action === 'paste') {
      let textToPaste = "";
      try {
        const res = await window.pywebview.api.get_clipboard_text();
        if (res && res.status === 'success') {
          textToPaste = res.text;
        }
      } catch (e) {}

      if (!textToPaste && navigator.clipboard && navigator.clipboard.readText) {
        try {
          textToPaste = await navigator.clipboard.readText();
        } catch (e) {}
      }

      if (textToPaste) {
        el.value = val.substring(0, start) + textToPaste + val.substring(end);
        el.selectionStart = el.selectionEnd = start + textToPaste.length;
        handleFieldChange();
      }
    } else if (action === 'selectall') {
      el.select();
    }
  } else {
    if (action === 'copy') {
      const selection = window.getSelection();
      let selectedText = "";
      if (selection && selection.rangeCount > 0 && !selection.isCollapsed) {
        const container = document.createElement("div");
        for (let i = 0; i < selection.rangeCount; ++i) {
          container.appendChild(selection.getRangeAt(i).cloneContents());
        }
        selectedText = container.innerText || selection.toString();
      }
      const textToCopy = selectedText || el.innerText;
      smartCopyText(textToCopy);
    } else if (action === 'selectall') {
      const range = document.createRange();
      range.selectNodeContents(el);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
  }
}

async function initSavedSettings() {
  try {
    const settings = await window.pywebview.api.get_settings();
    applyLanguage(settings.language || 'en');
    applyTheme(settings.theme || 'system');
  } catch (e) {
    applyLanguage('en');
    applyTheme('system');
  }
  setTimeout(() => {
    checkAppUpdates(false);
  }, 1500);
}

window.addEventListener('pywebviewready', async () => {
  await initAppInfo();
  await initSavedSettings();
});

window.addEventListener('DOMContentLoaded', () => {
  setTimeout(initSavedSettings, 200);
});

const lyricsBox = document.getElementById('lyricsContentBox');
if (lyricsBox) {
  lyricsBox.addEventListener('copy', (e) => {
    e.preventDefault();
    const selection = window.getSelection();
    let selectedText = "";
    
    if (selection && selection.rangeCount > 0 && !selection.isCollapsed) {
      const container = document.createElement("div");
      for (let i = 0; i < selection.rangeCount; ++i) {
        container.appendChild(selection.getRangeAt(i).cloneContents());
      }
      selectedText = container.innerText || selection.toString();
    }

    if (!selectedText) {
      selectedText = lyricsBox.innerText;
    }

    smartCopyText(selectedText);
  });
}
