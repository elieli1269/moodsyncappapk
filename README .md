# MoodSync Android

App Android native pour MoodSync — WebView + FCM + PeerJS + Bottom Nav.

## Structure

```
├── main.py                        # App Kivy principale
├── buildozer.spec                 # Config build APK
├── google-services.json           # Config Firebase FCM
└── .github/
    └── workflows/
        └── build.yml              # GitHub Actions → APK auto
```

## Build APK

Push sur `main` → GitHub Actions build automatiquement → onglet **Actions** → télécharger `MoodSync-APK.zip`

## Installation

1. Télécharger le `.apk` depuis les artifacts GitHub Actions
2. Transférer sur le téléphone
3. Activer **Sources inconnues** (Paramètres → Sécurité)
4. Installer l'APK

## API PHP à uploader sur alwaysdata

```
moodsync/api/
├── me.php
├── messages_count.php
├── notifications_count.php
├── fcm_register.php
└── send_push.php
```

## Firebase

- Projet : `moodsync-adf98`
- Package : `net.alwaysdata.moodsync`
- API FCM V1 activée
