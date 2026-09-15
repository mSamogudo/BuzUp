import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Assinatura release: key.properties (gitignored) ou variaveis BUZUP_POS_STORE_*.
// Sem nenhuma das duas, o build release cai na chave de debug (so para testes locais).
val keystoreProperties = Properties().apply {
    val f = rootProject.file("key.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}
val releaseStoreFile = System.getenv("BUZUP_POS_STORE_FILE")
    ?: keystoreProperties.getProperty("storeFile")
val releaseStorePassword = System.getenv("BUZUP_POS_STORE_PASSWORD")
    ?: keystoreProperties.getProperty("storePassword")
val releaseKeyAlias = System.getenv("BUZUP_POS_KEY_ALIAS")
    ?: keystoreProperties.getProperty("keyAlias")
val releaseKeyPassword = System.getenv("BUZUP_POS_KEY_PASSWORD")
    ?: keystoreProperties.getProperty("keyPassword")
val hasReleaseSigning = !releaseStoreFile.isNullOrBlank() && file(releaseStoreFile).exists()

android {
    namespace = "mz.coupdigital.pos_app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    // Compile the SUNMI printer AIDL files under src/main/aidl/.
    buildFeatures {
        aidl = true
    }

    defaultConfig {
        // applicationId vem do perfil de build (BUZUP_POS_APPLICATION_ID,
        // exportado pelos scripts): dev=.dev, staging=.staging, prod=base.
        //
        // O valor por omissao so serve para builds de DEBUG na maquina de quem
        // desenvolve. Num release tem de vir do perfil, e a falta dele e erro:
        // a 2026-09-14 saiu um APK 1.9.1 com o identificador base em vez do
        // `.tpmtur`, e para o Android isso e outra aplicacao — a instalacao
        // NUNCA podia suceder. Como a actualizacao estava marcada obrigatoria,
        // os terminais ficaram presos numa caixa sem botao de dispensar.
        //
        // Um valor por omissao que produz um APK valido mas com a identidade
        // errada e pior do que nao ter valor nenhum. Aqui grita.
        val idDoPerfil: String? = System.getenv("BUZUP_POS_APPLICATION_ID")
        val vaiAssinar = gradle.startParameter.taskNames.any {
            it.contains("Release", ignoreCase = true)
        }
        if (vaiAssinar && idDoPerfil.isNullOrBlank()) {
            throw GradleException(
                "BUZUP_POS_APPLICATION_ID nao esta definido e isto e um build de release.\n" +
                "  Compile pelos scripts, que carregam o perfil:\n" +
                "    scripts/pos-build-apk-tpmtur.sh   (TPM-TUR, .tpmtur)\n" +
                "    scripts/pos-build-apk-prod.sh     (BuzUp, identificador base)\n" +
                "  Um APK com o identificador errado instala-se como aplicacao\n" +
                "  nova em vez de actualizar, e o terminal fica com as duas."
            )
        }
        applicationId = idDoPerfil ?: "mz.coupdigital.pos_app"
        // Nome sob o icone. Vem do perfil de build porque a mesma app
        // serve varios operadores: um terminal da TPM-TUR com "BuzUp POS"
        // escrito por baixo do icone e a primeira coisa que o cliente ve.
        manifestPlaceholders["appLabel"] = System.getenv("BUZUP_POS_APP_LABEL") ?: "BuzUp POS"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // Terminais/telefones sao todos ARM; sem isto, plugins com .so x86_64
        // (emuladores Intel) engordam o APK universal.
        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a")
        }
    }

    // O plugin do Flutter volta a juntar x86_64 aos abiFilters; excluir no
    // empacotamento e o unico corte garantido.
    packaging {
        jniLibs {
            excludes += listOf("lib/x86/**", "lib/x86_64/**")
        }
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = file(releaseStoreFile!!)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        release {
            signingConfig = if (hasReleaseSigning) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

flutter {
    source = "../.."
}
