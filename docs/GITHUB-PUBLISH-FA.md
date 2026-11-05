# راهنمای انتشار پروژه در GitHub

**مسیر ساده و جدید:** [راهنمای انتشار با فایل BAT](ONE-CLICK-PUBLISH-FA.md). پس از نصب Git/GitHub CLI، فایل `Publish to GitHub.bat` این مراحل را ساده می‌کند.

## ۱. ایجاد ریپازیتوری

پیشنهاد نام: `pinharbor`، درباره (About): `A desktop Pinterest board media downloader with a local gallery, download queues and safe updates. Built with Python & PySide6.`؛ سایت خارجی وارد نکنید مگر واقعاً موجود باشد.

پیشنهاد Topics: `pinterest`, `board-downloader`, `media-downloader`, `pyside6`, `python`, `desktop-app`, `gallery-dl`, `yt-dlp`, `windows`, `open-source`.

گزینه **Add a README / license** را در صفحه ایجاد مخزن خاموش بگذارید؛ هر دو فایل داخل بسته هستند. نام و علامت تجاری PinHarbor برای عرضه واقعی باید مستقلاً بررسی شود و جست‌وجوی اولیه تضمین مالکیت نام نیست.

## ۲. آپلود سورس

در پوشه اصلی پروژه این دستورات را اجرا کنید:

```bash
git init
git branch -M main
git add .
git commit -m "Initial public release: PinHarbor 2.5.0"
git remote add origin https://github.com/OWNER/pinharbor.git
git push -u origin main
```

`OWNER` باید با نام کاربری/سازمان واقعی جایگزین شود. اگر GitHub CLI دارید، می‌توانید با `gh repo create` هم پروژه را بسازید؛ بدون تأیید کاربر هیچ ریپازیتوری عمومی خودکار ایجاد نمی‌شود.

## ۳. انتشار دانلودها

در GitHub به تب **Actions** بروید؛ پس از موفقیت تست‌ها، Tag `v2.5.0` را Push کنید تا workflow برای ویندوز خروجی بسازد. در صورت موفقیت، Release به همراه ZIP ویندوز، ZIP سورس، ZIP آپدیت و SHA256SUMS ساخته می‌شود. انتشار رسمی را تنها پس از آزمون دانلود زنده و نصب در ویندوز انجام دهید.

فایل‌هایی که در این پاسخ جداگانه دریافت می‌کنید، از قبل برای آپلود دستی به Releases هم آماده شده‌اند؛ **بسته Windows EXE آماده** در این محیط تولید نشده است. بسته GitHub repository را به‌جای ZIP exe منتشر نکنید.

## ۴. مشارکت کاربران

در تنظیمات مخزن Issues را فعال بگذارید، برای گزارش امنیتی Private vulnerability reporting را فعال کنید و در صورت تمایل Discussions را برای پرسش‌ها باز کنید. فایل‌های `.github/ISSUE_TEMPLATE/` فرم گزارش باگ و پیشنهاد قابلیت دارند. `SUPPORT.md`، `CONTRIBUTING.md` و `SECURITY.md` مسیرهای ارتباط را روشن می‌کنند.

## ۵. بعد از انتشار

اسکرین‌شات **واقعی** از تب صف، کتابخانه و تنظیمات ویندوز تهیه کنید. لینک Release واقعی را در README و شبکه‌های اجتماعی معرفی کنید. پیش از عرضه عمومی به موضوع امضای کد و مجوزهای Qt/FFmpeg رسیدگی کنید.
