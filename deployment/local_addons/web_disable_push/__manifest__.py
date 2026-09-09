{
    "name": "Disable Web Push (local)",
    "summary": "Skip browser push registration so local/dev browsers do not show a failure toast",
    "version": "18.0.1.0.0",
    "category": "Hidden",
    "license": "LGPL-3",
    "depends": ["mail"],
    "installable": True,
    "application": False,
    "assets": {
        "web.assets_backend": [
            "web_disable_push/static/src/webclient_patch.js",
        ],
    },
}
