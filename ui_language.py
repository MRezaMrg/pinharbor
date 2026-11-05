"""User-facing English/Persian strings, separate from downloader internals.

Keep technical diagnostics and Python exception messages verbatim in logs; only
friendly labels/notifications are localized. A language change is applied at
next launch so Qt layout direction and font initialization stay consistent.
"""
from __future__ import annotations
import re

_LANGUAGE = "fa"


def set_language(language: str) -> None:
    global _LANGUAGE
    _LANGUAGE = language if language in ("fa", "en") else "fa"


def language() -> str:
    return _LANGUAGE


EN = {
    "صف دانلود": "Downloads", "کتابخانه رسانه‌ها": "Library", "تنظیمات": "Settings",
    "تنظیمات پیشرفته": "Advanced settings", "راهنما": "Help",
    "آموزش سریع استفاده از PinHarbor": "How to use PinHarbor",
    "دانلود تصاویر و ویدیوها، مدیریت بوردها و مرور فایل‌ها — همه در یک‌جا": "Save board images and videos. Browse your files in one place.",
    "آماده · لینک بورد را بچسبانید و «دانلود از لینک‌ها» را بزنید.": "Ready · Paste a board URL and choose Download.",
    "افزودن بورد به صف": "Download Pinterest boards",
    "لینک یک بورد را بچسبانید و مستقیم دانلود کنید؛ برای چند بورد، هر لینک را در یک خط بنویسید.": "Paste a board URL. To add multiple boards, enter one URL per line.",
    "لینک بورد را وارد کنید؛ برای چند بورد، هر لینک در یک خط باشد.": "Paste a Pinterest board link. One URL per line.",
    "دانلود از لینک‌ها": "Download now", "فقط افزودن به صف": "Add to queue", "جای‌گذاری": "Paste",
    "بوردهای من": "Download queue", "جست‌وجوی نام بورد...": "Search boards...",
    "نام بورد": "Board", "وضعیت": "Status", "پین کشف‌شده": "Pins found", "جدید": "New", "تکراری": "Already saved", "جزئیات": "Details",
    "هنوز بوردی اضافه نشده. لینک را در بالای صفحه وارد کنید.": "No boards yet. Paste a board link above.",
    "۰ بورد": "0 boards", "حذف انتخاب‌شده": "Remove selected", "حذف تکمیل‌شده‌ها": "Clear finished",
    "بالا": "Move up", "پایین": "Move down", "واردکردن صف": "Import queue", "خروجی صف": "Export queue",
    "دانلود انتخاب‌شده‌ها": "Download selected", "اجرای دوباره موارد ناموفق": "Retry incomplete",
    "انتخاب چندگانه: Ctrl / Shift  ·  بازکردن لینک: دوبار کلیک  ·  حذف: Delete": "Ctrl/Shift to select · Double-click a board to open · Delete to remove",
    "محل ذخیره‌سازی و شروع عملیات": "Download location", "انتخاب پوشه": "Choose folder", "پوشه اجرا": "App folder",
    "بازکردن پوشه": "Open folder", "نوع فایل": "Media", "مرورگر حساب": "Pinterest login",
    "بدون حساب (عمومی)": "Public (no login)", "تصویر و ویدیو": "Images and videos", "فقط تصاویر": "Images only", "فقط ویدیوها": "Videos only",
    "تعداد پین‌های بورد (اختیاری)": "Expected board pins (optional)", "نامشخص": "Not set",
    "برای یک بورد؛ شمارنده تقریبی و قابل‌تغییر است.": "For a single board. The Pinterest count can change.",
    "برای یک بورد، تعداد نمایش‌داده‌شده در پینترست را وارد کنید تا نتیجه کمتر از انتظار مشخص شود.": "Enter the count shown on Pinterest to flag a possible incomplete result.",
    "شروع دانلود همه بوردها": "Download all boards", "ردکردن بورد جاری": "Skip current board", "توقف کل صف": "Stop downloads",
    "تمام بوردها دوباره بررسی می‌شوند؛ آرشیو از دریافت تکراری فایل‌های موفق جلوگیری می‌کند.": "All boards will be checked again; saved files will not be downloaded twice.",
    "پیشرفت بر اساس بوردهای تکمیل‌شده نمایش داده می‌شود، نه تعداد نامشخص پین‌ها.": "Progress follows completed boards; Pinterest may not reveal the total pin count.",
    "بورد پردازش‌شده": "Boards checked", "فایل جدید": "New files", "تکراری / ردشده": "Already saved / skipped", "نیازمند بررسی": "Needs review",
    "فایل‌های دانلودشده": "Downloaded files", "نمایش گزارش فنی و جزئیات دانلود": "Technical details", "پنهان‌کردن گزارش فنی": "Hide technical details",
    "گزارش رویدادها": "Download activity", "ذخیره گزارش TXT": "Save log", "پاک‌کردن نمایش گزارش": "Clear log",
    "بازخوانی پوشه": "Refresh folder", "جست‌وجو در نام و مسیر فایل‌ها ...": "Search files...",
    "همه رسانه‌ها": "All media", "تصویر": "Images", "ویدیو": "Videos",
    "جدیدترین": "Newest first", "نام: الف تا ی": "Name A–Z", "نام: معکوس": "Name Z–A",
    "برای نمایش فایل‌های موجود، «بازخوانی پوشه» را بزنید.": "Choose Refresh folder to view downloaded files.",
    "پیش‌نمایش فایل": "File preview", "یک فایل را انتخاب کنید": "Select a file", "پیش‌نمایش تصویر": "Image preview",
    "نمایش فایل‌های بیشتر": "Load more files", "هر بار حداکثر ۵۵ فایل به گالری اضافه می‌شود.": "Loads up to 55 more files at a time.",
    "بازکردن فایل": "Open file", "بازکردن پوشه فایل": "Show in folder", "کپی مسیر": "Copy path", "خروجی CSV": "Export CSV",
    "این تصویر قابل پیش‌نمایش نیست؛ فایل را باز کنید.": "Preview unavailable. Open the file instead.",
    "برای پخش ویدیو، «بازکردن فایل» را بزنید.": "Select Open file to play the video.",
    "ظاهر و تایپوگرافی": "Appearance", "فونت رابط کاربری": "Interface font",
    "تم زرشکی، صورتی پاستلی و مشکی با پنل‌های شیشه‌ای فعال است. فونت‌ها فقط از میان فونت‌های نصب‌شده انتخاب می‌شوند.": "Burgundy, pastel rose and black theme. Fonts are selected from those installed on your computer.",
    "صفحه رسمی فونت وزیرمتن": "Vazirmatn font website",
    "در صورت تمایل، فونت وزیرمتن را از منبع رسمی نصب کنید و برنامه را دوباره باز کنید.": "Install Vazirmatn from its official website, then restart PinHarbor.",
    "برای استفاده از وزیرمتن، آن را جداگانه روی ویندوز نصب و برنامه را مجدداً اجرا کنید. فایل فونت داخل آپدیت قرار ندارد.": "Vazirmatn is optional and is not bundled with the app.",
    "حالت دریافت": "Download preferences", "ساخت فولدر جداگانه برای هر بورد و بخش": "Organize files by board and section",
    "ذخیره فایل JSON فراداده کنار رسانه": "Save metadata (JSON) next to media",
    "مکث بین درخواست‌ها؛ کاهش احتمال محدودسازی": "Use gentle request pacing",
    "آرشیو دانلود در ‎.pinterest-studio‎ نگهداری می‌شود و با آپدیت برنامه پاک نمی‌شود.": "Download history is retained between app updates.",
    "محدودیت‌ها و کنترل شبکه": "Advanced download controls", "حداکثر رسانه از هر بورد": "Maximum media per board",
    "محدودیت سرعت دانلود": "Download speed limit", "بدون محدودیت": "Unlimited", "نامحدود": "Unlimited",
    "توقف زودهنگام بعد از فایل‌های تکراریِ متوالی": "Stop after consecutive duplicates",
    "غیرفعال (پیشنهادی)": "Off (recommended)",
    "اگر گزینه توقف زودهنگام را فعال کنید، ممکن است پین‌های جدیدِ عقب‌تر از موارد قدیمی بررسی نشوند؛ پیش‌فرض غیرفعال است.": "Early stopping can miss older pins. Leave disabled for full-board checks.",
    "پراکسی (اختیاری، فقط در حافظه همین اجرا)": "Proxy (optional; not saved)",
    "درباره موتور": "Diagnostics", "بررسی بسته‌های نصب‌شده": "Check download components",
    "آزمایش آمادگی دانلود": "Check download readiness", "کپی گزارش فنی (بدون اطلاعات ورود)": "Copy safe diagnostics",
    "ورود فقط با کوکی ذخیره‌شده در مرورگر خودتان انجام می‌شود. برنامه رمز عبور پینترست را درخواست یا ذخیره نمی‌کند.": "Sign-in uses your local browser session. PinHarbor never asks for your Pinterest password.",
    "در انتظار": "Queued", "در حال دانلود": "Downloading", "تکمیل‌شده": "Finished", "متوقف‌شده": "Stopped",
    "بدون رسانه": "No media", "خطا": "Error", "با درخواست کاربر رد شد": "Skipped by user",
    "همه وضعیت‌ها": "All statuses", "همه": "All", "نیازمند بررسی": "Needs review",
    "آدرس نامعتبر": "Invalid link", "صف بیش از حد بزرگ": "Queue limit reached", "صف خالی": "Queue is empty",
    "تنظیمات نادرست": "Invalid settings", "موتور دانلود نصب نیست": "Download components missing",
    "ابتدا فایل Run on Windows.bat را اجرا کنید تا وابستگی‌های لازم نصب شوند.": "Start the app through Run on Windows.bat to install required components.",
    "ابتدا لینک یک یا چند بورد را وارد صف کنید.": "Add a board URL first.",
    "ابتدا یک یا چند بورد را از جدول انتخاب کنید.": "Select one or more boards from the table.",
    "حداکثر ۱۰۰۰ بورد در یک صف پشتیبانی می‌شود.": "A queue can contain up to 1,000 boards.",
    "انتخاب بورد": "Select board", "صف بدون خطا": "No failed downloads",
    "هیچ بورد ناموفق یا متوقف‌شده‌ای در صف نیست.": "Nothing to retry.",
    "هیچ بورد تکمیل‌شده یا ردشده‌ای برای حذف از صف وجود ندارد.": "No finished boards to remove.",
    "راهنمای سریع PinHarbor": "Quick guide",
    "آزمایش آمادگی دانلود": "Check readiness", "وضعیت آمادگی دانلود": "Download readiness",
    "خطای واردکردن": "Import failed", "خطای خروجی": "Export failed", "خطای ذخیره گزارش": "Could not save log",
    "پوشه نامعتبر": "Invalid folder", "خروجی فهرست": "Export complete",
    "در حال آماده‌سازی تصویر...": "Loading preview...", "در حال فهرست‌کردن رسانه‌ها...": "Scanning files...",
    "در حال توقف امن فرایند دانلود...": "Stopping download...",
    "در حال ردکردن بورد فعلی و رفتن به مورد بعدی...": "Skipping current board...",
    "در حال پایان‌دادن امن به پردازش‌ها و بستن برنامه...": "Closing safely...",
    "دانلود فعال است": "Download in progress", "دانلود متوقف شود و برنامه بسته شود؟": "Stop downloading and exit?",
    "مسیر تغییر کرده؛ در حال بررسی پوشه جدید...": "Output folder changed. Refreshing...",
    "پوشه تغییر کرده؛ پس از پایان بررسی قبلی دوباره بررسی می‌شود...": "Folder changed. The new scan will start shortly...",
    "گزارش فنی بدون مشخصات حساب و مسیرهای شخصی کپی شد.": "Diagnostics copied without account or personal paths.",
    "CSV فیلتر فعلی": "Filtered CSV", "موردی با این فیلتر پیدا نشد؛ فیلتر را تغییر دهید.": "No matching files. Try a different filter.",
    "اطلاعات نشست معتبر نیست.": "Saved session is invalid.",
    "۰ بورد": "0 boards", "به درخواست کاربر رد شد": "Skipped by user",
    "پین کشف‌شده": "Pins found",
    "شمارش پین‌ها از موتور دریافت نشد؛ تعداد کامل بورد قابل تأیید نیست. برای بررسی دوباره از حساب مرورگر واردشده استفاده کنید.": "Pin counting was unavailable. Full-board coverage cannot be verified. Retry with a signed-in browser.",
    "در حال ساخت پیش‌نمایش ویدیو ...": "Loading video preview...",
    "موردی با این فیلتر پیدا نشد؛ فیلتر را تغییر دهید.": "No matching boards. Change the filter.",
    "گزارش": "Activity",
    "تصویر": "Image",
    "ویدیو": "Video",
    "فایل": "File",
    "زبان / Language": "Language",
    "نمایش گزینه‌های بیشتر": "More options",
    "پنهان‌کردن گزینه‌های بیشتر": "Hide more options",
    "برداشتن محدودیت دریافت": "Remove download limit",
    "روی نام بورد دوبار کلیک کنید تا در مرورگر باز شود.": "Double-click a board to open it in your browser.",
    "فقط لینک‌های همین کادر را اجرا می‌کند، نه تمام بوردهای صف. میانبر: Ctrl+Enter": "Downloads only the links in this box. Shortcut: Ctrl+Enter",
    "اگر تعداد فایل‌ها کمتر از پین‌های بورد است، مرورگری را انتخاب کنید که در آن وارد Pinterest شده‌اید و بورد را دوباره دانلود کنید.": "If fewer pins are found, select a browser signed into Pinterest and retry the board.",
    "فارسی": "فارسی",
    "زمان اجرا: 00:00": "Elapsed: 00:00",
    "Language changes take effect after restarting the app. / تغییر زبان پس از اجرای مجدد برنامه اعمال می‌شود.": "Language changes take effect after restarting the app.",
    "محدودیت فعال: حداکثر": "Active download limit:",
    "دانلود فعال است": "Download in progress",
}

# Dynamic status strings that are formatted in the app rather than static labels.
DYNAMIC = [
    (r'^نمایش بیشتر \(?(\d[\d,]*) از (\d[\d,]*)\)$', r'Load more (\1 of \2)'),
    (r'^(\d[\d,]*) بورد از صف پاک شد\. فایل‌های دانلودشده حفظ شده‌اند\.$', r'Removed \1 boards from the queue. Downloaded files remain saved.'),
    (r'^صف خوانده شد: (\d[\d,]*) بورد در فهرست\.$', r'Queue loaded: \1 boards.'),
    (r'^فهرست (\d[\d,]*) فایل مطابق فیلتر جاری ذخیره شد\.$', r'Exported \1 matching files.'),
    (r'^محدودیت فعال: حداکثر (\d+) مورد از هر بورد بررسی می‌شود\.$', r'Download limit active: max \1 items per board.'),
    (r'^فقط (\d+) پین شناسایی شد؛ انتظار (\d+) پین بود\. با حساب مرورگر واردشده دوباره بررسی کنید\.$', r'Only \1 pin(s) discovered; expected \2. Retry using a signed-in browser.'),
    (r'^(.+) بورد در فهرست\.$', r'\1 board(s) queued.'),
    (r'^(\d+) بورد جدید افزوده شد؛ (\d+) لینک از قبل در صف بود\.$', r'Added \1 boards; \2 already queued.'),
    (r'^خطای بررسی پوشه: (.+)$', r'Could not scan folder: \1'),
    (r'^(\d+) بورد معتبر شناسایی شد · می‌توانید مستقیم دانلود کنید یا به صف اضافه کنید\.$', r'\1 valid board(s). Download now or add to the queue.'),
    (r'^(\d+) بورد از (\d+) بررسی شد؛ تعداد کل فایل‌های قابل دریافت ممکن است مشخص نباشد\.$', r'\1 of \2 boards checked. Pinterest may not expose the full count.'),
    (r'^(\d+) مورد مطابق فیلتر \| مجموع پوشه: (\d+) فایل$', r'\1 matching files · \2 total'),
    (r'^زمان اجرا: (.+)$', r'Elapsed: \1'),
    (r'^در حال پردازش (\d+) از (\d+): (.+)$', r'Downloading \1 of \2: \3'),
    (r'^پردازش (\d+) بورد آغاز شد؛ تعداد کل فایل‌ها هنوز مشخص نیست\.$', r'Checking \1 board(s). Total media count is not yet known.'),
    (r'^نیاز به اصلاح لینک: (.+)$', r'Invalid board link: \1'),
]


def tr(value: str) -> str:
    if _LANGUAGE != "en" or not isinstance(value, str):
        return value
    if value in EN:
        return EN[value]
    for pattern, replacement in DYNAMIC:
        if re.match(pattern, value):
            return re.sub(pattern, replacement, value)
    return value
