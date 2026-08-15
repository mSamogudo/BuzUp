import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Assinatura release via key.properties (gitignored). Sem o ficheiro, o build
// release cai na chave de debug (so para testes locais).
val keystoreProperties = Properties().apply {
    val f = rootProject.file("key.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}
val releaseStoreFile = keystoreProperties.getProperty("storeFile")
val hasReleaseSigning = !releaseStoreFile.isNullOrBlank() && file(releaseStoreFile).exists()

android {
    namespace = "mz.coupdigital.buzup_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // applicationId vem do perfil de build (BUZUP_MOBILE_APPLICATION_ID,
        // exportado pelos scripts) -> staging usa sufixo .staging para poder
        // coexistir com a prod no mesmo aparelho. Default = prod.
        applicationId = System.getenv("BUZUP_MOBILE_APPLICATION_ID") ?: "mz.coupdigital.buzup_mobile"
        // Nome sob o icone. Vem do perfil de build porque a mesma app
        // serve varios operadores: um terminal da TPM-TUR com "BuzUp Passageiro"
        // escrito por baixo do icone e a primeira coisa que o cliente ve.
        manifestPlaceholders["appLabel"] = System.getenv("BUZUP_MOBILE_APP_LABEL") ?: "BuzUp Passageiro"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // Telefones-alvo sao todos ARM; sem isto, plugins com .so x86_64
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
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
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
