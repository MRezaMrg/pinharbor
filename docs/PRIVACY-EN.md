# Privacy statement (English)

PinHarbor is a **local desktop program**, not a hosted download service. The project's source code does not deliberately implement account registration, telemetry, ads or a remote analytics endpoint.

It **does** make network connections through gallery-dl and yt-dlp to Pinterest, media hosts and related services to retrieve data and media. External services can observe those requests according to their own policies. On first launch from source, `pip` accesses dependency package registries. The updater's optional `Update Engines.bat` also accesses Python package services.

Download files, the `.pinterest-studio/download_archive.sqlite3` archive and Qt settings are stored locally. Qt settings use the retained organization/application ID `PinterestBoardStudio/Desktop` so an in-place upgrade can preserve existing settings. The app's browser-cookie option allows the third-party download engine to read session cookies from a locally selected browser for authenticated access. **No user password is requested by PinHarbor**, but cookies are sensitive secrets: never share them or logs that contain them.

The software is provided without a hosted backend. This is not a guarantee that external dependencies or Pinterest cannot log requests. If you publish a fork with telemetry or any additional services, update this statement.

You can remove your downloaded files and local archive manually after closing the application. For Windows Qt settings, review the application settings stored by Qt for the retained organization/application ID. Do not delete the archive unless you understand that previously downloaded items may be downloaded again.
